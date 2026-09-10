"""
Comprehensive Automated Test Suite for SamadhanSetu Administrator System
Tests the exact 10 Test Cases demanded by the user specification:
TEST 1: Email = admin@samadhansetu.com, Password = Admin@123 -> SUCCESS -> Admin Dashboard
TEST 2: Wrong email -> "Invalid admin email or password."
TEST 3: Correct email + wrong password -> "Invalid admin email or password."
TEST 4: Open /dashboard without login -> Redirect to login page
TEST 5: Refresh dashboard after successful login -> Remain logged in using session
TEST 6: Click Logout -> Session destroyed and user redirected to login
TEST 7: Check old Demo Account buttons -> Must no longer exist in templates/DOM
TEST 8: Refresh Challenges page multiple times -> The same database challenges remain; no random challenges
TEST 9: Add a challenge as Admin -> Challenge saved to database
TEST 10: Edit/delete challenge as Admin -> Database updates correctly
"""

import sys
import os
from datetime import datetime

PROJECT_DIR = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, PROJECT_DIR)

from app import app, db, User, Challenge, seed_database

def run_all_tests():
    print("=======================================================")
    print("  RUNNING STRICT SPECIFICATION TESTS (TESTS 1 to 10)  ")
    print("=======================================================")

    with app.app_context():
        seed_database()

    client = app.test_client()

    # ---------------------------------------------------------
    # TEST 1: Email = admin@samadhansetu.com, Password = Admin@123
    # Expected: SUCCESS -> Admin Dashboard
    # ---------------------------------------------------------
    print("\n[TEST 1] Testing Valid Admin Login...")
    res = client.post('/login', data={
        'login_id': 'admin@samadhansetu.com',
        'password': 'Admin@123',
        'remember': 'on'
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b"Admin Dashboard" in res.data or b"ADMINISTRATOR" in res.data
    assert b"Welcome Administrator! Signed in successfully." in res.data
    print(" -> [PASS] TEST 1 PASSED: Valid admin credentials granted access to Admin Dashboard.")

    # ---------------------------------------------------------
    # TEST 2: Wrong email
    # Expected: "Invalid admin email or password."
    # ---------------------------------------------------------
    print("\n[TEST 2] Testing Wrong Email...")
    client_t2 = app.test_client()
    res = client_t2.post('/login', data={
        'login_id': 'hacker@example.com',
        'password': 'Admin@123'
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b"Invalid admin email or password." in res.data
    print(" -> [PASS] TEST 2 PASSED: Wrong email rejected with 'Invalid admin email or password.'")

    # ---------------------------------------------------------
    # TEST 3: Correct email + wrong password
    # Expected: "Invalid admin email or password."
    # ---------------------------------------------------------
    print("\n[TEST 3] Testing Correct Email + Wrong Password...")
    client_t3 = app.test_client()
    res = client_t3.post('/login', data={
        'login_id': 'admin@samadhansetu.com',
        'password': 'WrongPassword999'
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b"Invalid admin email or password." in res.data
    print(" -> [PASS] TEST 3 PASSED: Wrong password rejected with 'Invalid admin email or password.'")

    # ---------------------------------------------------------
    # TEST 4: Open /dashboard without login
    # Expected: Redirect to login page
    # ---------------------------------------------------------
    print("\n[TEST 4] Testing Direct Access to /dashboard Without Login...")
    client_t4 = app.test_client()
    res = client_t4.get('/dashboard', follow_redirects=False)
    assert res.status_code in [302, 301]
    assert '/login' in res.headers.get('Location', '')
    res_followed = client_t4.get('/dashboard', follow_redirects=True)
    assert b"Please log in as Administrator to continue." in res_followed.data
    assert b"Sign in to continue to your project workspace." in res_followed.data
    print(" -> [PASS] TEST 4 PASSED: Unauthenticated user redirected to /login.")

    # ---------------------------------------------------------
    # TEST 5: Refresh dashboard after successful login
    # Expected: Remain logged in using the session
    # ---------------------------------------------------------
    print("\n[TEST 5] Testing Session Persistence on Dashboard Refresh...")
    # client has active session from TEST 1
    res_refresh1 = client.get('/dashboard')
    assert res_refresh1.status_code == 200
    assert b"ADMINISTRATOR" in res_refresh1.data

    res_refresh2 = client.get('/dashboard')
    assert res_refresh2.status_code == 200
    assert b"ADMINISTRATOR" in res_refresh2.data
    print(" -> [PASS] TEST 5 PASSED: User remains logged in across multiple refreshes using session.")

    # ---------------------------------------------------------
    # TEST 6: Click Logout
    # Expected: Session destroyed and user redirected to login
    # ---------------------------------------------------------
    print("\n[TEST 6] Testing Logout & Session Clearing...")
    res_logout = client.get('/logout', follow_redirects=True)
    assert res_logout.status_code == 200
    assert b"You have been securely signed out" in res_logout.data

    # Now verify dashboard can no longer be accessed with this client
    res_after_logout = client.get('/dashboard', follow_redirects=False)
    assert res_after_logout.status_code in [302, 301]
    assert '/login' in res_after_logout.headers.get('Location', '')
    print(" -> [PASS] TEST 6 PASSED: Session destroyed on logout, access revoked.")

    # ---------------------------------------------------------
    # TEST 7: Try old Demo Account buttons
    # Expected: They must no longer exist in templates / DOM
    # ---------------------------------------------------------
    print("\n[TEST 7] Verifying Demo Account Buttons Completely Removed...")
    res_login_page = client.get('/login')
    html = res_login_page.data.decode('utf-8')
    assert "Quick Demo Accounts" not in html, "Found 'Quick Demo Accounts' in login HTML!"
    assert "Student Lead" not in html, "Found 'Student Lead' demo button!"
    assert "IT Faculty" not in html, "Found 'IT Faculty' demo button!"
    assert "Tata Industry" not in html, "Found 'Tata Industry' demo button!"
    assert "fillLogin" not in html, "Found 'fillLogin' javascript function!"
    print(" -> [PASS] TEST 7 PASSED: All demo account buttons and autofill scripts completely removed.")

    # ---------------------------------------------------------
    # TEST 8: Refresh Challenges page multiple times
    # Expected: The same database challenges remain; no random challenges appear
    # ---------------------------------------------------------
    print("\n[TEST 8] Verifying Controlled Stable Challenges (Zero Randomness on Refresh)...")
    # Log back in as admin for protected routes
    client.post('/login', data={'login_id': 'admin@samadhansetu.com', 'password': 'Admin@123'})
    client.get('/dashboard')  # Consume one-time login flash message
    
    res_ch1 = client.get('/challenges')
    res_ch2 = client.get('/challenges')
    res_ch3 = client.get('/challenges')

    assert res_ch1.data == res_ch2.data, "Challenges page output changed between refreshes!"
    assert res_ch2.data == res_ch3.data, "Challenges page output changed on second refresh!"
    
    with app.app_context():
        count = Challenge.query.count()
        assert count == 8, f"Expected exactly 8 controlled challenges, got {count}"
    print(" -> [PASS] TEST 8 PASSED: Challenges page output is 100% deterministic and stable across refreshes.")

    # ---------------------------------------------------------
    # TEST 9: Add a challenge as Admin
    # Expected: Challenge saved to database
    # ---------------------------------------------------------
    print("\n[TEST 9] Adding Challenge as Admin into Database...")
    new_challenge_data = {
        'title': 'AI Urban Flood Drain Telemetry System',
        'category': 'Smart Cities',
        'department': 'Public Works Department (PWD)',
        'location': 'Chennai, Tamil Nadu',
        'priority': 'Critical',
        'status': 'Open',
        'organization': 'Greater Chennai Corporation',
        'deadline': '2026-12-31',
        'description': 'Monsoon inundation sensors needed across storm water drain nodes to prevent urban flash flooding.',
        'required_skills': 'IoT, Hydrology, Python, Telemetry',
        'expected_outcome': 'Real-time alert grid preventing localized waterlogging in 12 flood-prone catchments.'
    }

    res_add = client.post('/challenge/new', data=new_challenge_data, follow_redirects=True)
    assert res_add.status_code == 200
    assert b"AI Urban Flood Drain Telemetry System" in res_add.data

    with app.app_context():
        created_ch = Challenge.query.filter_by(title='AI Urban Flood Drain Telemetry System').first()
        assert created_ch is not None, "Challenge not found in database!"
        assert created_ch.department == 'Public Works Department (PWD)'
        assert created_ch.priority == 'Critical'
        assert created_ch.organization == 'Greater Chennai Corporation'
        created_id = created_ch.id
    print(f" -> [PASS] TEST 9 PASSED: Challenge #{created_id} successfully saved to database with all fields.")

    # ---------------------------------------------------------
    # TEST 10: Edit/delete challenge as Admin
    # Expected: Database updates correctly
    # ---------------------------------------------------------
    print("\n[TEST 10] Testing Edit and Delete Challenge as Admin...")
    # 1. Edit challenge
    res_edit = client.post(f'/challenge/{created_id}/edit', data={
        'title': 'AI Urban Flood Drain Telemetry System (UPDATED)',
        'category': 'Smart Cities',
        'department': 'Urban Traffic Police & Smart City Authority',
        'location': 'Chennai Coastal Zone',
        'priority': 'High',
        'status': 'In Progress',
        'organization': 'Greater Chennai Corporation & Disaster Management',
        'deadline': '2026-11-30',
        'description': 'Updated monsoon sensor scope with drone verification.',
        'required_skills': 'IoT, Computer Vision, Drone Telemetry',
        'expected_outcome': 'Full catchment automation.'
    }, follow_redirects=True)
    assert res_edit.status_code == 200
    assert b"Challenge specifications updated successfully" in res_edit.data

    with app.app_context():
        updated_ch = Challenge.query.get(created_id)
        assert updated_ch.title == 'AI Urban Flood Drain Telemetry System (UPDATED)'
        assert updated_ch.department == 'Urban Traffic Police & Smart City Authority'
        assert updated_ch.priority == 'High'
        assert updated_ch.status == 'In Progress'
    print(" -> Edit verified: Database updated properly.")

    # 2. Delete challenge
    res_del = client.post(f'/challenge/{created_id}/delete', follow_redirects=True)
    assert res_del.status_code == 200
    assert b"was deleted successfully from the database" in res_del.data

    with app.app_context():
        deleted_ch = Challenge.query.get(created_id)
        assert deleted_ch is None, "Challenge was not deleted from database!"
    print(" -> Delete verified: Challenge successfully removed from database.")
    print(" -> [PASS] TEST 10 PASSED: Edit and Delete CRUD operations working flawlessly.")

    print("\n=======================================================")
    print("  ALL 10 SPECIFICATION TESTS PASSED WITH 100% SUCCESS! ")
    print("=======================================================\n")

if __name__ == '__main__':
    run_all_tests()
