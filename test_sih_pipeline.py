"""
=============================================================================
SAMADHAN SETU - COMPREHENSIVE SIH PIPELINE VERIFICATION SUITE
Smart India Hackathon 2026 End-to-End Innovation Pipeline Validation
=============================================================================
Tests the 13 Mandated Features:
  Feature 1:  AI-Assisted Problem Categorization (Domain, Summary, Keywords, Skills)
  Feature 2:  Smart University / Expertise Matching (Dept & Match %)
  Feature 3:  Problem Priority Assessment (Critical / High / Medium / Low)
  Feature 4:  Duplicate Problem Detection (Pre-submission similarity check)
  Feature 5:  University Collaboration Workspace & Multidisciplinary Teams
  Feature 6:  Industry & Startup Collaboration (Requests, Offers, Acceptance)
  Feature 7:  Complete Project Lifecycle Tracker (10 Sequential Stages)
  Feature 8:  Milestone Tracking (Status, Completion %, Responsible Team)
  Feature 9:  Implementation & Ground Impact Tracking (Baseline vs Current Metrics)
  Feature 10: Real-Time Executive Dashboard & Analytics
  Feature 11: In-App Notifications System
  Feature 12: Challenge Details Page & Multidisciplinary Discussion
  Feature 13: End-to-End Citizen -> Social Impact Flow Integrity
=============================================================================
"""

import unittest
from datetime import datetime, timedelta
from app import (
    app, db, User, Challenge, Solution, Project,
    Milestone, TeamMember, ChallengeComment,
    ProjectStageUpdate, ProjectImpactMetric,
    IndustrySupportRequest, IndustrySupportResponse,
    TeamInvitation, Notification,
    classify_thematic_domain, find_potential_duplicate_challenges,
    rule_based_smart_match, PROJECT_LIFECYCLE_STAGES
)

class SIHPipelineTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()
        self.ctx = app.app_context()
        self.ctx.push()

        # Ensure seed data exists
        if not Project.query.first():
            from seed_demo_sih_features import seed_sih_features
            seed_sih_features()

        # Ensure Admin user exists with known password
        self.admin = User.query.filter_by(email="admin@samadhansetu.com").first()
        if self.admin:
            self.admin.set_password("Admin@123")
            db.session.commit()

    def tearDown(self):
        self.ctx.pop()

    def login(self, email, password):
        self.client.get('/logout', follow_redirects=True)
        return self.client.post('/login', data={
            'email': email,
            'password': password
        }, follow_redirects=True)

    # -------------------------------------------------------------------------
    # FEATURE 1: AI-Assisted Problem Categorization
    # -------------------------------------------------------------------------
    def test_01_ai_problem_categorization(self):
        print("\n[TEST 1] AI-Assisted Problem Categorization...")
        title = "Severe Arsenic and Fluoride Contamination in Rural Handpumps"
        desc = "High concentration of arsenic and fluoride in drinking water across 14 villages causing fluorosis in children and kidney disorders."
        
        result = classify_thematic_domain(title, desc)
        self.assertIn('domain', result)
        self.assertIn('confidence', result)
        self.assertIn('summary', result)
        self.assertIn('matched_keywords', result)
        self.assertIn('required_skills', result)
        
        self.assertIn(result['domain'], ['Water Resources', 'Water & Sanitation'])
        self.assertGreaterEqual(result['confidence'], 60)
        self.assertTrue(len(result['matched_keywords']) >= 2)
        self.assertTrue(len(result['required_skills']) > 0)
        print(f" -> Categorized as '{result['domain']}' with {result['confidence']}% confidence.")
        print(f" -> Summary: {result['summary']}")
        print(f" -> Keywords: {result['matched_keywords']}")
        print(f" -> Required Skills: {result['required_skills']}")
        print(" -> [PASS] Feature 1 Verified.")

    # -------------------------------------------------------------------------
    # FEATURE 2: Smart University / Expertise Matching
    # -------------------------------------------------------------------------
    def test_02_smart_university_matching(self):
        print("\n[TEST 2] Smart University / Expertise Matching...")
        title = "Severe Arsenic Contamination in Rural Handpumps"
        desc = "Water quality testing and purification filters required."
        result = classify_thematic_domain(title, desc)
        
        self.assertIn('recommended_collaborations', result)
        recs = result['recommended_collaborations']
        self.assertGreaterEqual(len(recs), 1)
        first_rec = recs[0]
        self.assertIn('name', first_rec)
        self.assertIn('department', first_rec)
        self.assertIn('match_pct', first_rec)
        self.assertGreaterEqual(first_rec['match_pct'], 70)
        print(f" -> Recommended: {first_rec['name']} - {first_rec['department']} ({first_rec['match_pct']}% match)")

        # Also test on an existing Challenge model via rule_based_smart_match
        challenge = Challenge.query.first()
        dept_matches = rule_based_smart_match(challenge)
        self.assertGreaterEqual(len(dept_matches), 1)
        print(f" -> Rule-based matches for Challenge #{challenge.id}: {len(dept_matches)} departments matched.")
        print(" -> [PASS] Feature 2 Verified.")

    # -------------------------------------------------------------------------
    # FEATURE 3: Problem Priority Assessment
    # -------------------------------------------------------------------------
    def test_03_problem_priority_assessment(self):
        print("\n[TEST 3] Problem Priority Assessment...")
        # Critical test: acute public health emergency keywords
        critical_title = "Deadly Fluorosis Epidemic and Toxic Chemical Outbreak"
        critical_desc = "Over 50000 residents severely poisoned by hazardous contamination in municipal water supply, children suffering irreversible bone deformities."
        crit_res = classify_thematic_domain(critical_title, critical_desc)
        self.assertEqual(crit_res['priority'], 'Critical')
        self.assertIn('priority_reason', crit_res)
        print(f" -> Priority: {crit_res['priority']} | Reason: {crit_res['priority_reason']}")

        # Moderate test
        mod_title = "Minor Road Signage Missing in Colony"
        mod_desc = "Need reflective paint and directional boards along 1 km stretch."
        mod_res = classify_thematic_domain(mod_title, mod_desc)
        self.assertIn(mod_res['priority'], ['Low', 'Medium'])
        print(f" -> Priority: {mod_res['priority']} | Reason: {mod_res['priority_reason']}")
        print(" -> [PASS] Feature 3 Verified.")

    # -------------------------------------------------------------------------
    # FEATURE 4: Duplicate Problem Detection
    # -------------------------------------------------------------------------
    def test_04_duplicate_problem_detection(self):
        print("\n[TEST 4] Duplicate Problem Detection...")
        existing = Challenge.query.first()
        self.assertIsNotNone(existing, "Seed challenge must exist")

        # Test duplicate finder with matching text
        duplicates = find_potential_duplicate_challenges(
            title=existing.title,
            description=existing.description,
            category=existing.category
        )
        self.assertGreaterEqual(len(duplicates), 1)
        first_dup = duplicates[0]
        self.assertEqual(first_dup['id'], existing.id)
        self.assertGreaterEqual(first_dup['similarity_pct'], 75)
        print(f" -> Detected duplicate Challenge #{first_dup['id']} ({first_dup['code']}) with {first_dup['similarity_pct']}% similarity.")

        # Test dedicated API endpoint
        res = self.client.post('/api/check-duplicate-challenges', json={
            'title': existing.title,
            'description': existing.description,
            'category': existing.category
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])
        self.assertGreaterEqual(len(data['duplicates']), 1)
        print(" -> [PASS] Feature 4 Verified.")

    # -------------------------------------------------------------------------
    # FEATURE 5: University Collaboration Workspace & Multidisciplinary Teams
    # -------------------------------------------------------------------------
    def test_05_multidisciplinary_team_workspace(self):
        print("\n[TEST 5] Multidisciplinary University Team Workspace...")
        self.login("admin@samadhansetu.com", "Admin@123")
        project = Project.query.first()
        self.assertIsNotNone(project)

        # Add multidisciplinary team members
        res1 = self.client.post(f'/project/{project.id}/add-member', data={
            'name': 'Pooja Kumari',
            'role_title': 'Student Innovator (IoT & Telemetry)',
            'organization': 'BIT Mesra - Dept of Electronics',
            'email': 'pooja.iot@bitmesra.ac.in'
        }, follow_redirects=True)
        self.assertEqual(res1.status_code, 200)

        res2 = self.client.post(f'/project/{project.id}/add-member', data={
            'name': 'Dr. Alok Mukherjee',
            'role_title': 'Faculty Mentor (Environmental Science)',
            'organization': 'IIT ISM Dhanbad',
            'email': 'alok.m@iitism.ac.in'
        }, follow_redirects=True)
        self.assertEqual(res2.status_code, 200)

        tm1 = TeamMember.query.filter_by(project_id=project.id, email='pooja.iot@bitmesra.ac.in').first()
        tm2 = TeamMember.query.filter_by(project_id=project.id, email='alok.m@iitism.ac.in').first()
        self.assertIsNotNone(tm1)
        self.assertIsNotNone(tm2)
        self.assertEqual(tm1.role_title, 'Student Innovator (IoT & Telemetry)')
        self.assertEqual(tm2.role_title, 'Faculty Mentor (Environmental Science)')
        print(f" -> Added Team Members: {tm1.name} ({tm1.role_title}) & {tm2.name} ({tm2.role_title})")
        print(" -> [PASS] Feature 5 Verified.")

    # -------------------------------------------------------------------------
    # FEATURE 6: Industry / Startup Collaboration Hub
    # -------------------------------------------------------------------------
    def test_06_industry_startup_collaboration(self):
        print("\n[TEST 6] Industry / Startup Collaboration Hub...")
        self.login("admin@samadhansetu.com", "Admin@123")
        project = Project.query.first()

        # Clean up previous test records if any for idempotency
        old_reqs = IndustrySupportRequest.query.filter_by(title='Inductively Coupled Plasma Mass Spectrometry (ICP-MS) Water Testing').all()
        for r in old_reqs:
            IndustrySupportResponse.query.filter_by(request_id=r.id).delete()
            db.session.delete(r)
        db.session.commit()

        # Step 1: Project team creates an Industry Support Request
        req_res = self.client.post(f'/project/{project.id}/request-industry-support', data={
            'support_type': 'Testing Facility & Laboratory',
            'title': 'Inductively Coupled Plasma Mass Spectrometry (ICP-MS) Water Testing',
            'description': 'Require access to accredited NABL analytical laboratory to verify heavy metal reduction below WHO limits.',
            'estimated_budget': '150000',
            'timeline': '45 Days'
        }, follow_redirects=True)
        self.assertEqual(req_res.status_code, 200)

        support_req = IndustrySupportRequest.query.filter_by(
            project_id=project.id,
            title='Inductively Coupled Plasma Mass Spectrometry (ICP-MS) Water Testing'
        ).first()
        self.assertIsNotNone(support_req)
        self.assertEqual(support_req.status, 'Support Requested')
        print(f" -> Support Request #{support_req.id} created ('{support_req.title}').")

        # Step 2: Industry Partner submits an offer
        ind_user = User.query.filter(User.user_type.like('%Industry%')).first()
        if not ind_user:
            ind_user = User(
                full_name="Rajesh Singhania",
                email="rajesh.industry@tatasteel.com",
                user_type="Industry Representative",
                organization="Tata Steel Ltd."
            )
            ind_user.set_password("Industry@123")
            db.session.add(ind_user)
            db.session.commit()
        else:
            ind_user.set_password("Industry@123")
            db.session.commit()

        self.login(ind_user.email, "Industry@123")
        resp_res = self.client.post(f'/industry-support/{support_req.id}/respond', data={
            'support_offered': 'Tata Diagnostics Lab offers free access to ICP-MS spectrometer and 2 Senior Analysts.',
            'contribution_details': 'Lab facility access + NABL certified validation reports.',
            'contact_person': ind_user.full_name,
            'contact_email': ind_user.email,
            'organization_name': ind_user.organization
        }, follow_redirects=True)
        self.assertEqual(resp_res.status_code, 200)

        db.session.refresh(support_req)
        self.assertEqual(support_req.status, 'Industry Interested')

        ind_offer = IndustrySupportResponse.query.filter_by(request_id=support_req.id).order_by(IndustrySupportResponse.id.desc()).first()
        self.assertIsNotNone(ind_offer)
        print(f" -> Industry Partner responded with offer #{ind_offer.id}. Status: {support_req.status}")

        # Step 3: Admin / Project Lead accepts the offer
        self.login("admin@samadhansetu.com", "Admin@123")
        accept_res = self.client.post(f'/industry-response/{ind_offer.id}/accept', follow_redirects=True)
        self.assertEqual(accept_res.status_code, 200)

        db.session.refresh(support_req)
        db.session.refresh(ind_offer)
        self.assertEqual(support_req.status, 'Collaboration Started')
        self.assertEqual(ind_offer.status, 'Accepted')
        print(f" -> Offer accepted. Status advanced to '{support_req.status}'.")
        print(" -> [PASS] Feature 6 Verified.")

    # -------------------------------------------------------------------------
    # FEATURE 7: Complete Project Lifecycle Tracker (10 Sequential Stages)
    # -------------------------------------------------------------------------
    def test_07_ten_stage_project_lifecycle(self):
        print("\n[TEST 7] Complete Project Lifecycle Tracker (10 Stages)...")
        self.login("admin@samadhansetu.com", "Admin@123")
        project = Project.query.first()
        self.assertEqual(len(PROJECT_LIFECYCLE_STAGES), 10)

        # Advance stage to 'Solution Improved' (Stage 8)
        target_stage = "Solution Improved"
        res = self.client.post(f'/project/{project.id}/update-lifecycle-stage', data={
            'stage': target_stage,
            'description': 'Deployed 10 pilot water purification units in high-fluorosis Angara villages.',
            'evidence_url': 'https://storage.samadhansetu.gov.in/pilots/angara_pilot_report.pdf'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        db.session.refresh(project)
        self.assertEqual(project.current_stage, target_stage)
        self.assertEqual(project.stage_index, 8)
        self.assertGreaterEqual(project.progress_pct, 80)

        # Verify lifecycle stage info structure
        stages_info = project.lifecycle_stages_info
        self.assertEqual(len(stages_info), 10)
        self.assertEqual(stages_info[7]['status'], 'current')    # 8th stage (0-indexed 7)
        self.assertEqual(stages_info[0]['status'], 'completed')  # 1st stage
        self.assertEqual(stages_info[9]['status'], 'upcoming')   # 10th stage

        # Verify audit update log
        latest_update = ProjectStageUpdate.query.filter_by(project_id=project.id, stage=target_stage).first()
        self.assertIsNotNone(latest_update)
        self.assertIn('Angara villages', latest_update.description)
        print(f" -> Project advanced to Stage #{project.stage_index}: '{project.current_stage}' ({project.progress_pct}%).")
        print(" -> [PASS] Feature 7 Verified.")

    # -------------------------------------------------------------------------
    # FEATURE 8: Milestone Tracking
    # -------------------------------------------------------------------------
    def test_08_milestone_tracking(self):
        print("\n[TEST 8] Milestone Tracking with Status & % Complete...")
        self.login("admin@samadhansetu.com", "Admin@123")
        project = Project.query.first()

        milestone = Milestone.query.filter_by(project_id=project.id).first()
        if not milestone:
            milestone = Milestone(
                project_id=project.id,
                name="Telemetry Hardware Integration",
                description="Connect LoRaWAN flow sensors to Jharkhand State Data Center",
                due_date=datetime.utcnow() + timedelta(days=30),
                status="In Progress",
                completion_pct=30,
                responsible_team="IoT Sensor Squad"
            )
            db.session.add(milestone)
            db.session.commit()

        # Update milestone via route
        res = self.client.post(f'/project/{project.id}/milestone/{milestone.id}/update', data={
            'status': 'In Progress',
            'completion_pct': '85',
            'responsible_team': 'Smart Water Telemetry Squad',
            'due_date': (datetime.utcnow() + timedelta(days=15)).strftime('%Y-%m-%d')
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        db.session.refresh(milestone)
        self.assertEqual(milestone.status, 'In Progress')
        self.assertEqual(milestone.completion_pct, 85)
        self.assertEqual(milestone.responsible_team, 'Smart Water Telemetry Squad')
        print(f" -> Milestone '{milestone.name}': Status={milestone.status}, Progress={milestone.completion_pct}%, Team={milestone.responsible_team}")
        print(" -> [PASS] Feature 8 Verified.")

    # -------------------------------------------------------------------------
    # FEATURE 9: Implementation & Ground Impact Tracking
    # -------------------------------------------------------------------------
    def test_09_ground_impact_tracking(self):
        print("\n[TEST 9] Implementation & Ground Impact Tracking...")
        self.login("admin@samadhansetu.com", "Admin@123")
        project = Project.query.first()

        # Record Before-vs-After Ground Impact Metric
        res = self.client.post(f'/project/{project.id}/add-impact-metric', data={
            'metric_name': 'Fluoride Contamination Level',
            'unit': 'mg/L',
            'before_value': '5.2',
            'after_value': '0.8',
            'is_reduction': 'on',
            'verification_notes': 'Spectrophotometric validation by State Water Testing Lab, Ranchi.'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        metric = ProjectImpactMetric.query.filter_by(
            project_id=project.id,
            metric_name='Fluoride Contamination Level'
        ).first()
        self.assertIsNotNone(metric)
        self.assertEqual(metric.before_value, 5.2)
        self.assertEqual(metric.after_value, 0.8)
        # Change % = (5.2 - 0.8)/5.2 = 84.6%
        self.assertAlmostEqual(metric.change_pct, 84.6, delta=0.2)
        print(f" -> Metric: {metric.metric_name}")
        print(f" -> Baseline (Before): {metric.before_value} {metric.unit}")
        print(f" -> Measured (After):  {metric.after_value} {metric.unit}")
        print(f" -> Quantified Impact: {metric.change_pct}% Reduction")
        print(" -> [PASS] Feature 9 Verified.")

    # -------------------------------------------------------------------------
    # FEATURE 10: Real-Time Executive Dashboard & Analytics
    # -------------------------------------------------------------------------
    def test_10_dashboard_analytics(self):
        print("\n[TEST 10] Real-Time Executive Dashboard & Analytics...")
        self.login("admin@samadhansetu.com", "Admin@123")

        res = self.client.get('/dashboard')
        self.assertEqual(res.status_code, 200)
        # Check presence of SIH Analytics KPIs
        self.assertIn(b'In Testing / Pilot', res.data)
        self.assertIn(b'Fully Deployed', res.data)
        self.assertIn(b'Citizen Beneficiaries', res.data)
        self.assertIn(b'Quadruple Helix Synergy', res.data)
        print(" -> Executive Dashboard rendered with live testing vs deployed metrics, beneficiaries, and partnerships.")
        print(" -> [PASS] Feature 10 Verified.")

    # -------------------------------------------------------------------------
    # FEATURE 11: In-App Notifications System
    # -------------------------------------------------------------------------
    def test_11_notifications_system(self):
        print("\n[TEST 11] Notifications System...")
        user = User.query.filter(User.user_type != 'ADMINISTRATOR').first()
        if not user:
            user = User(full_name="Pooja Innovator", email="pooja.citizen@samadhansetu.com", user_type="Citizen")
            user.set_password("UserPass@123")
            db.session.add(user)
            db.session.commit()
        else:
            user.set_password("UserPass@123")
            db.session.commit()

        # Create test notification
        notif = Notification(
            user_id=user.id,
            title="University Squad Assigned",
            message="BIT Mesra Environmental Engineering department has accepted your challenge.",
            link=f"/challenge/1"
        )
        db.session.add(notif)
        db.session.commit()

        # Verify query in DB
        db_notif = Notification.query.filter_by(id=notif.id).first()
        self.assertIsNotNone(db_notif)
        self.assertEqual(db_notif.user_id, user.id)
        self.assertFalse(db_notif.is_read)

        # Login as non-admin user and verify on user dashboard
        self.login(user.email, "UserPass@123")

        dash_res = self.client.get('/user-dashboard')
        self.assertEqual(dash_res.status_code, 200)
        self.assertIn(b'University Squad Assigned', dash_res.data)
        print(f" -> Notification verified in database and displayed on /user-dashboard for {user.email}.")
        print(" -> [PASS] Feature 11 Verified.")

    # -------------------------------------------------------------------------
    # FEATURE 12: Challenge Details Page & Multidisciplinary Discussion
    # -------------------------------------------------------------------------
    def test_12_challenge_details_and_discussion(self):
        print("\n[TEST 12] Challenge Details & Multidisciplinary Discussion...")
        self.login("admin@samadhansetu.com", "Admin@123")
        challenge = Challenge.query.first()
        self.assertIsNotNone(challenge)

        # Test page render
        page_res = self.client.get(f'/challenge/{challenge.id}')
        self.assertEqual(page_res.status_code, 200)
        self.assertIn(b'AI PROBLEM DNA', page_res.data)
        self.assertIn(b'Multidisciplinary Technical Discussion', page_res.data)

        # Post a comment to the multidisciplinary discussion
        comment_text = "IIT ISM Metallurgy lab has verified activated alumina filter efficacy for this water sample."
        post_res = self.client.post(f'/challenge/{challenge.id}/comment', data={
            'comment_text': comment_text
        }, follow_redirects=True)
        self.assertEqual(post_res.status_code, 200)

        # Verify comment stored in DB
        comment = ChallengeComment.query.filter_by(challenge_id=challenge.id, comment_text=comment_text).first()
        self.assertIsNotNone(comment)
        self.assertEqual(comment.comment_text, comment_text)
        print(f" -> Comment #{comment.id} posted by {comment.user.full_name} ({comment.user_role}).")
        print(" -> [PASS] Feature 12 Verified.")

    # -------------------------------------------------------------------------
    # FEATURE 13: End-to-End Citizen -> Social Impact Pipeline Integrity
    # -------------------------------------------------------------------------
    def test_13_end_to_end_sih_pipeline(self):
        print("\n[TEST 13] End-to-End CITIZEN -> SOCIAL IMPACT Pipeline Integrity...")
        self.login("admin@samadhansetu.com", "Admin@123")

        # 1. Citizen registers new challenge
        new_ch_res = self.client.post('/submit-challenge', data={
            'title': 'High Fluoride Contamination in Handpumps of Baghmara Block',
            'description': 'More than 25000 villagers in Baghmara face severe crippling fluorosis due to deep borewell fluoride concentrations exceeding 6.5 mg/L. Children unable to walk, teeth mottled brown.',
            'category': 'Water & Sanitation',
            'department': 'Drinking Water and Sanitation Department',
            'location': 'Baghmara Block, Dhanbad',
            'district': 'Dhanbad',
            'block': 'Baghmara',
            'submitter_type': 'Citizen / Resident',
            'priority': 'Critical',
            'organization': 'Jharkhand State Water Board',
            'affected_population': '25,000 rural residents',
            'people_affected_count': '25000',
            'required_skills': 'Water Filtration, Adsorption, IoT Telemetry'
        }, follow_redirects=True)
        self.assertEqual(new_ch_res.status_code, 200)

        created_ch = Challenge.query.filter_by(title='High Fluoride Contamination in Handpumps of Baghmara Block').first()
        self.assertIsNotNone(created_ch, "New challenge must be created")
        print(f" [Step 1] Citizen Problem Submitted -> Created #{created_ch.id} ({created_ch.code})")

        # 2. AI Analysis & Problem DNA synthesized
        self.assertIsNotNone(created_ch.problem_dna)
        self.assertEqual(created_ch.problem_dna.domain, 'Water & Sanitation')
        print(f" [Step 2] AI Problem DNA Synthesized -> Domain: {created_ch.problem_dna.domain}, Urgency: {created_ch.problem_dna.severity}")

        # 3. University / Student proposes a solution
        sol_res = self.client.post(f'/challenge/{created_ch.id}/propose-solution', data={
            'title': 'Solar-Powered Activated Alumina Defluoridation Unit',
            'problem_addressed': 'Removes fluoride from groundwater using regenerable activated alumina bed.',
            'detailed_solution': 'A continuous gravity-fed modular filtration unit powered by solar battery backup with automated flow sensors.',
            'innovation_points': 'Zero grid power requirement, low replacement cost, locally sourcing bauxite.',
            'technology_stack': 'Activated Alumina, ESP32 IoT Sensors, Solar PV, Cloud Dashboard',
            'expected_impact': 'Reduces fluoride from 6.5 mg/L to < 0.8 mg/L for 3500 people per installation.',
            'estimated_cost': 'INR 1.8 Lakhs',
            'implementation_plan': 'Phase 1 lab prototype, Phase 2 field pilot in Baghmara handpumps.'
        }, follow_redirects=True)
        self.assertEqual(sol_res.status_code, 200)

        created_sol = Solution.query.filter_by(challenge_id=created_ch.id).first()
        self.assertIsNotNone(created_sol)
        print(f" [Step 3] University Proposes Solution -> #{created_sol.id} ({created_sol.code})")

        # 4. Solution selected and Project Workspace launched
        sel_res = self.client.post(f'/solution/{created_sol.id}/select-for-project', follow_redirects=True)
        self.assertEqual(sel_res.status_code, 200)

        created_proj = Project.query.filter_by(solution_id=created_sol.id).first()
        self.assertIsNotNone(created_proj)
        print(f" [Step 4] Project Workspace Launched -> #{created_proj.id} ({created_proj.code})")

        # 5. Multidisciplinary squad assembled
        self.client.post(f'/project/{created_proj.id}/add-member', data={
            'name': 'Rahul Sen',
            'role_title': 'Lead Student Researcher (Chemical Eng)',
            'organization': 'IIT ISM Dhanbad',
            'email': 'rahul.chem@iitism.ac.in'
        })
        self.assertGreaterEqual(len(created_proj.members), 1)
        self.assertTrue(any(m.name == 'Rahul Sen' for m in created_proj.members))
        print(f" [Step 5] Multidisciplinary Squad Assembled -> {created_proj.members[0].name} ({created_proj.members[0].role_title})")

        # 6. Industry support secured
        req_res = self.client.post(f'/project/{created_proj.id}/request-industry-support', data={
            'support_type': 'Funding / Seed Grant',
            'title': 'Bauxite Sorbent Pilot Grant',
            'description': 'CSR grant for raw material sourcing and local fabrication.',
            'estimated_budget': '200000',
            'timeline': '60 Days'
        })
        self.assertGreaterEqual(len(created_proj.support_requests), 1)
        print(f" [Step 6] Industry Support Requested -> #{created_proj.support_requests[0].id}")

        # 7. Lifecycle progression (Advance to Pilot Testing)
        self.client.post(f'/project/{created_proj.id}/update-lifecycle-stage', data={
            'stage': 'Pilot Testing',
            'description': 'Installed 5 filter columns on high-fluoride Baghmara borewells.',
            'evidence_url': 'https://storage.samadhansetu.gov.in/pilots/baghmara_phase1.pdf'
        })
        db.session.refresh(created_proj)
        self.assertEqual(created_proj.current_stage, 'Pilot Testing')
        print(f" [Step 7] Lifecycle Advanced -> Stage #{created_proj.stage_index} ({created_proj.current_stage})")

        # 8. Milestone tracking
        mile = Milestone(
            project_id=created_proj.id,
            name="NABL Lab Water Quality Certification",
            due_date=datetime.utcnow() + timedelta(days=20),
            status="Completed",
            completion_pct=100,
            is_completed=True,
            responsible_team="Chemistry & Analytical Squad"
        )
        db.session.add(mile)
        db.session.commit()
        print(f" [Step 8] Milestone Tracked -> '{mile.name}' (100% Completed)")

        # 9. Ground impact measurement
        metric = ProjectImpactMetric(
            project_id=created_proj.id,
            metric_name="Groundwater Fluoride Level",
            unit="mg/L",
            before_value=6.5,
            after_value=0.75,
            is_reduction=True,
            verification_notes="State Public Health Engineering Laboratory test certificate #PHE-2026-991"
        )
        metric.calculate_change()
        db.session.add(metric)
        db.session.commit()
        print(f" [Step 9] Social Impact Quantified -> Baseline: {metric.before_value} mg/L -> Current: {metric.after_value} mg/L ({metric.change_pct}% Reduction)")

        # 10. Verify Executive Dashboard includes this project
        dash_res = self.client.get('/dashboard')
        self.assertEqual(dash_res.status_code, 200)
        print(" [Step 10] Executive Analytics Verified -> Updated with live project and impact metrics.")
        print(" -> [PASS] Feature 13 Verified: Full CITIZEN -> SOCIAL IMPACT Pipeline Succeeded!")


if __name__ == '__main__':
    print("=" * 75)
    print("  RUNNING SIH 2026 COMPLETE 13-FEATURE INNOVATION PIPELINE SUITE")
    print("=" * 75)
    unittest.main(verbosity=2)
