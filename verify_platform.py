"""
Automated Verification Script for SamadhanSetu Platform
Tests database initialization, seed data integrity, authentication hashing,
rule-based smart matching, impact score calculations, and project workspace generation.
"""

import sys
import os

# Add project dir to path
PROJECT_DIR = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, PROJECT_DIR)

from app import (
    app, db, User, Organization, Challenge, Solution, Project,
    Milestone, Task, TeamMember, Notification, ImpactMetric,
    calculate_ai_impact_score, rule_based_smart_match, seed_database
)

def run_tests():
    print("-------------------------------------------------------")
    print("  RUNNING AUTOMATED INTEGRITY TESTS FOR SAMADHAN SETU  ")
    print("-------------------------------------------------------")

    with app.app_context():
        # 1. Database seeding
        print("[TEST 1] Testing Database Seeding...")
        seed_database()
        
        users_count = User.query.count()
        challenges_count = Challenge.query.count()
        orgs_count = Organization.query.count()
        solutions_count = Solution.query.count()
        projects_count = Project.query.count()
        milestones_count = Milestone.query.count()
        tasks_count = Task.query.count()

        print(f" -> Users: {users_count}")
        print(f" -> Challenges: {challenges_count}")
        print(f" -> Organizations: {orgs_count}")
        print(f" -> Solutions: {solutions_count}")
        print(f" -> Projects: {projects_count}")
        print(f" -> Milestones: {milestones_count}")
        print(f" -> Tasks: {tasks_count}")

        assert users_count >= 6, "Expected at least 6 seeded users"
        assert challenges_count >= 8, "Expected at least 8 seeded challenges"
        assert orgs_count >= 8, "Expected at least 8 seeded organizations"
        assert projects_count >= 2, "Expected at least 2 seeded projects"
        print(" -> [PASS] Database seed data verified successfully.")

        # 2. Authentication & Hashing Verification
        print("\n[TEST 2] Testing Password Hashing & Security...")
        admin = User.query.filter_by(email="admin@samadhansetu.gov.in").first()
        assert admin is not None, "Admin user not found"
        assert admin.check_password("Admin@123"), "Admin password validation failed"
        assert not admin.check_password("WrongPassword"), "Security flaw: invalid password passed"
        print(" -> [PASS] Password hashing and verification passed.")

        # 3. Rule-Based AI Impact Score Test
        print("\n[TEST 3] Testing AI Impact Score Generator...")
        score_crit = calculate_ai_impact_score('Critical', 1000000, 'Python, AI, IoT', 'Full automated clean water reduction', 'LoRa, ESP32')
        score_low = calculate_ai_impact_score('Low', 50, '', '', '')
        print(f" -> Critical large-scale impact score: {score_crit}/100")
        print(f" -> Low small-scale impact score: {score_low}/100")
        assert score_crit > score_low, "Critical score should be higher than low score"
        assert 40 <= score_crit <= 100, "Score out of range"
        print(" -> [PASS] AI impact scoring algorithm verified.")

        # 4. Rule-Based Smart Matching Engine Test
        print("\n[TEST 4] Testing University & Industry Matchmaking Engine...")
        ch1 = Challenge.query.first()
        matches = rule_based_smart_match(ch1)
        print(f" -> Target Challenge: {ch1.title[:40]}... (Category: {ch1.category})")
        print(f" -> Top Matched Universities: {[u['name'] for u in matches['universities']]}")
        print(f" -> Top Matched Industries: {[i['name'] for i in matches['industries']]}")
        assert len(matches['universities']) > 0, "No universities matched"
        assert len(matches['industries']) > 0, "No industries matched"
        print(" -> [PASS] Matchmaking engine delivered ranked recommendations.")

        # 5. Client Test Execution
        print("\n[TEST 5] Testing Flask Web Endpoints via Test Client...")
        client = app.test_client()

        # Landing page
        res = client.get('/')
        assert res.status_code == 200, f"Landing page error: {res.status_code}"
        assert b"Turn Societal Challenges Into" in res.data, "Hero text missing from landing"
        print(" -> Landing page (GET /): 200 OK")

        # Login page
        res = client.get('/login')
        assert res.status_code == 200, f"Login page error: {res.status_code}"
        assert b"Sign in to continue to your project workspace" in res.data, "Login subtitle missing"
        print(" -> Login page (GET /login): 200 OK")

        # Challenges discovery
        res = client.get('/challenges')
        assert res.status_code == 200, f"Challenges marketplace error: {res.status_code}"
        print(" -> Challenges Discovery (GET /challenges): 200 OK")

        # Challenge detail
        res = client.get(f'/challenge/{ch1.id}')
        assert res.status_code == 200, f"Challenge detail error: {res.status_code}"
        print(f" -> Challenge Detail (GET /challenge/{ch1.id}): 200 OK")

        # Solutions directory
        res = client.get('/solutions')
        assert res.status_code == 200, f"Solutions directory error: {res.status_code}"
        print(" -> Solutions Directory (GET /solutions): 200 OK")

        # Projects directory
        res = client.get('/projects')
        assert res.status_code == 200, f"Projects directory error: {res.status_code}"
        print(" -> Projects Directory (GET /projects): 200 OK")

        # Impact analytics
        res = client.get('/impact')
        assert res.status_code == 200, f"Impact dashboard error: {res.status_code}"
        print(" -> Impact Analytics (GET /impact): 200 OK")

        # Organizations directory
        res = client.get('/organizations')
        assert res.status_code == 200, f"Organizations directory error: {res.status_code}"
        print(" -> Organizations Directory (GET /organizations): 200 OK")

        print("-------------------------------------------------------")
        print("  ALL 5 INTEGRITY TESTS PASSED WITH ZERO ERRORS!       ")
        print("-------------------------------------------------------")

if __name__ == '__main__':
    run_tests()

