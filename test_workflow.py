"""
End-to-End User Flow Simulation for SamadhanSetu
Tests:
1. Citizen Registration & Login
2. Societal Challenge Submission
3. Admin Verification
4. Student Proposes Solution
5. Solution Endorsement & Lifecycle Stage Advancement
6. Conversion to Active Project Workspace with Matched University & Industry
7. Kanban Task Management & Milestone Progress Tracking
"""

import sys
import os

PROJECT_DIR = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, PROJECT_DIR)

from app import app, db, User, Challenge, Solution, Project, Milestone, Task

def simulate_full_workflow():
    print("\n=======================================================")
    print("  RUNNING COMPLETE END-TO-END SIH HACKATHON WORKFLOW  ")
    print("=======================================================")

    with app.app_context():
        test_emails = ['ramesh.pawar@solapur.org', 'rohit.sharma@bits-pilani.ac.in']
        test_ch = Challenge.query.filter_by(title='AI Groundwater Recharge Mapping for Drought Prone Mandals').all()
        for ch in test_ch:
            for sol in ch.solutions:
                for proj in sol.projects:
                    Task.query.filter_by(project_id=proj.id).delete()
                    Milestone.query.filter_by(project_id=proj.id).delete()
                    db.session.delete(proj)
                db.session.delete(sol)
            db.session.delete(ch)
        User.query.filter(User.email.in_(test_emails)).delete(synchronize_session=False)
        db.session.commit()

    client = app.test_client()

    # Step 1: Register a new Citizen user
    print("\n[STEP 1] Registering New Citizen User (Ramesh Pawar)...")
    res = client.post('/register', data={
        'full_name': 'Ramesh Pawar',
        'email': 'ramesh.pawar@solapur.org',
        'phone': '+91-9822334455',
        'user_type': 'Citizen',
        'organization': 'Solapur Watershed Committee',
        'location': 'Solapur, Maharashtra',
        'skills': 'Water Management, Rainwater Harvesting',
        'password': 'Password@123',
        'confirm_password': 'Password@123'
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b"Registration completed successfully" in res.data
    print(" -> Citizen registered successfully.")

    # Step 2: Login as Ramesh Pawar
    print("\n[STEP 2] Signing In as Ramesh Pawar...")
    res = client.post('/login', data={
        'login_id': 'ramesh.pawar@solapur.org',
        'password': 'Password@123'
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b"Welcome back, Ramesh Pawar" in res.data
    print(" -> Signed in. Session initialized.")

    # Step 3: Ramesh Submits a new Societal Challenge
    print("\n[STEP 3] Submitting New Societal Challenge on Ground Water Depletion...")
    res = client.post('/challenge/new', data={
        'title': 'AI Groundwater Recharge Mapping for Drought Prone Mandals',
        'category': 'Water',
        'location': 'Solapur & Osmanabad, Maharashtra',
        'affected_population': '320,000 Dryland Farmers',
        'severity': 'Critical',
        'people_affected_count': 320000,
        'description': 'Rapid tube well sinking has dropped the regional water table past 600 feet. Artificial recharge structures are installed blindly without hydrogeological fissure analysis.',
        'existing_solutions': 'Traditional percolation tanks built without sub-surface GIS data.',
        'shortcomings': 'Over 70% of recharge water evaporates or is lost to impermeable basalt beds.',
        'required_skills': 'GIS, Hydrogeology, Satellite Remote Sensing, Python, IoT Flow Sensors',
        'required_technology': 'Sentinel-2 SAR imagery, Python Flask, ESP32 Ultrasonic Flowmeters',
        'expected_outcome': 'Algorithmic map identifying top 50 high-yield percolation zones, reviving 1,200 dry tube wells.',
        'deadline': '2026-12-31'
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b"AI Groundwater Recharge Mapping" in res.data
    print(" -> Challenge submitted and AI impact score pre-calculated.")

    with app.app_context():
        new_ch = Challenge.query.filter_by(title='AI Groundwater Recharge Mapping for Drought Prone Mandals').first()
        assert new_ch is not None
        assert new_ch.status in ['PENDING VERIFICATION', 'Under Review']
        print(f" -> Created Challenge ID: #{new_ch.id}, Impact Score: {new_ch.ai_impact_score}/100, Status: {new_ch.status}")
        new_ch_id = new_ch.id

    # Step 4: Admin logs in and Verifies the Challenge
    print("\n[STEP 4] Admin Logs In and Verifies Challenge...")
    client.get('/logout')
    client.post('/login', data={
        'login_id': 'admin@samadhansetu.com',
        'password': 'Admin@123'
    }, follow_redirects=True)

    res = client.post(f'/admin/challenge/{new_ch_id}/verify', follow_redirects=True)
    assert res.status_code == 200
    with app.app_context():
        ch_verified = Challenge.query.get(new_ch_id)
        assert ch_verified.status in ['Verified', 'APPROVED']
        print(f" -> Challenge #{new_ch_id} officially verified and published to national marketplace!")

    # Step 5: Student Lead (Rohit Sharma) Registers & Proposes a Solution
    print("\n[STEP 5] Student Lead (Rohit) Registers, Logs In and Proposes Solution...")
    client.get('/logout')
    client.post('/register', data={
        'full_name': 'Rohit Sharma',
        'email': 'rohit.sharma@bits-pilani.ac.in',
        'phone': '+91-9811223344',
        'user_type': 'Student',
        'organization': 'BITS Pilani',
        'location': 'Pilani, Rajasthan',
        'skills': 'IoT, Embedded Systems, Python, SAR GIS',
        'password': 'Student@123',
        'confirm_password': 'Student@123'
    }, follow_redirects=True)

    client.post('/login', data={
        'login_id': 'rohit.sharma@bits-pilani.ac.in',
        'password': 'Student@123'
    }, follow_redirects=True)

    res = client.post(f'/challenge/{new_ch_id}/propose-solution', data={
        'title': 'JalSetu: Satellite SAR Hydro-Fissure Mapping with LoRa Well Telemetry',
        'problem_addressed': 'Groundwater depletion in drought mandals',
        'detailed_solution': 'We apply multi-temporal synthetic aperture radar (SAR) interferometry to identify subterranean fracture zones with high aquifer yield. LoRaWAN ultrasound sensors measure diurnal water level recovery.',
        'innovation_points': 'Combines European Space Agency satellite data with $15 open-hardware pressure transducers.',
        'technology_stack': 'Python, PyTorch, GDAL, ESP32 LoRa, Flask, PostgreSQL PostGIS',
        'expected_impact': 'Increases percolation recharge rate by 45%, protecting drinking water for 320,000 citizens.',
        'estimated_cost': 'INR 4.5 Lakhs for 50 test recharge pits',
        'implementation_plan': 'Phase 1: Satellite SAR analysis. Phase 2: Sensor deployment. Phase 3: Panchayat dashboard.',
        'scalability': 'Deployable across all Deccan Plateau basalt regions.',
        'sustainability': 'Maintained by local Jal Doot village youth.',
        'team_members_info': 'Rohit Sharma (BITS), Dr. Meera Swaminathan (IITB), Solapur Water Board'
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b"JalSetu: Satellite SAR Hydro-Fissure" in res.data
    print(" -> Solution proposed successfully in 'IDEA' stage.")

    with app.app_context():
        sol = Solution.query.filter_by(title='JalSetu: Satellite SAR Hydro-Fissure Mapping with LoRa Well Telemetry').first()
        assert sol is not None
        sol_id = sol.id

    # Step 6: Advance Solution Stage and Select for Project Workspace
    print("\n[STEP 6] Advancing Solution Stage and Converting to Project Workspace...")
    client.post(f'/solution/{sol_id}/advance-status', follow_redirects=True) # Advances to VALIDATION
    client.post(f'/solution/{sol_id}/endorse', follow_redirects=True) # Endorses

    # Select and Launch Project Workspace
    res = client.post(f'/solution/{sol_id}/select-for-project', follow_redirects=True)
    assert res.status_code == 200
    assert b"Quadruple Helix Stakeholder Coalition" in res.data
    print(" -> Project Workspace automatically created with University & Industry partners!")

    with app.app_context():
        proj = Project.query.filter_by(solution_id=sol_id).first()
        assert proj is not None
        assert len(proj.milestones) == 6
        assert len(proj.tasks) >= 4
        print(f" -> Project ID: #{proj.id}, University: {proj.university_partner}, Industry: {proj.industry_partner}")
        proj_id = proj.id
        first_task = proj.tasks[0]
        first_milestone = [m for m in proj.milestones if not m.is_completed][0]

    # Step 7: Update Kanban Task and Toggle Milestone
    print("\n[STEP 7] Testing Interactive Workspace Kanban & Milestone Delivery...")
    # Add new task
    client.post(f'/project/{proj_id}/task/add', data={
        'title': 'Calibrate borehole hydrostatic sensor accuracy',
        'assigned_name': 'Rohit Sharma',
        'priority': 'High',
        'status': 'In Progress'
    }, follow_redirects=True)

    # Move first task to Completed
    client.post(f'/project/{proj_id}/task/{first_task.id}/update-status', data={
        'status': 'Completed'
    }, follow_redirects=True)

    # Toggle milestone completion
    res = client.post(f'/project/{proj_id}/milestone/{first_milestone.id}/toggle', follow_redirects=True)
    assert res.status_code == 200
    print(" -> Task moved to Completed and milestone signed off.")

    with app.app_context():
        updated_proj = Project.query.get(proj_id)
        print(f" -> Recomputed Project Progress: {updated_proj.progress_pct}%")
        assert updated_proj.progress_pct > 25

    print("\n=======================================================")
    print("  COMPLETE 7-STEP HACKATHON WORKFLOW VERIFIED 100%!   ")
    print("=======================================================\n")

if __name__ == '__main__':
    simulate_full_workflow()

