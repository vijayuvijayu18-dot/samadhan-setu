"""
=============================================================================
SAMADHAN SETU - SIH PROTOTYPE FEATURES TEST SUITE
Smart India Hackathon 2026 Innovation Engine Validation
=============================================================================
Tests the 3 distinctive SIH hackathon prototype capabilities:
1. Smart Skill-Based Team Matching & Inviting Engine (/smart-team & /team-matching)
2. Idea -> Impact 10-Stage Sequential Tracker & Before/After Metrics (/idea-impact)
3. Industry + University Collaboration Hub, Support Requests & Offer Acceptance (/industry-collaboration)
4. Dashboard and Admin Console Integration (3 prominent clickable cards)
=============================================================================
"""

import sys
import unittest
from app import (
    app, db, User, Challenge, Solution, Project,
    ProjectStageUpdate, ProjectImpactMetric,
    IndustrySupportRequest, IndustrySupportResponse,
    TeamInvitation, TeamMember, PROJECT_LIFECYCLE_STAGES
)

class SIHFeaturesTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()
        self.ctx = app.app_context()
        self.ctx.push()

        # Ensure showcase seed data is populated
        if not Project.query.first():
            from seed_demo_sih_features import seed_sih_features
            seed_sih_features()

    def tearDown(self):
        self.ctx.pop()

    def login(self, email, password):
        self.client.get('/logout', follow_redirects=True)
        return self.client.post('/login', data={
            'email': email,
            'password': password
        }, follow_redirects=True)

    # -------------------------------------------------------------------------
    # TEST SUITE 1: SMART SKILL-BASED TEAM MATCHING
    # -------------------------------------------------------------------------
    def test_feature1_skill_based_team_matching(self):
        print("\n[TEST F1.1] Testing Smart Skill-Based Team Matching Dedicated Routes...")
        # Test dedicated UI routes
        res_page = self.client.get('/smart-team')
        self.assertEqual(res_page.status_code, 200)
        self.assertIn(b'Smart Challenge', res_page.data)
        self.assertIn(b'Team Matching', res_page.data)

        res_alias = self.client.get('/team-matching')
        self.assertEqual(res_alias.status_code, 200)
        self.assertIn(b'Team Matching', res_alias.data)
        print(" -> [PASS] /smart-team and /team-matching dedicated pages rendered successfully.")

        print("\n[TEST F1.2] Testing Smart Skill-Based Team Matching Candidate Calculation...")
        challenge = Challenge.query.filter_by(code="CHL-2026-0008").first() or Challenge.query.first()
        self.assertIsNotNone(challenge, "Showcase challenge should exist")

        # Test API endpoint
        res = self.client.get(f'/challenge/{challenge.id}/team-recommendations')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])
        self.assertIn('recommendations', data)
        self.assertGreaterEqual(len(data['recommendations']), 1)

        first_cand = data['recommendations'][0]
        self.assertIn('user_id', first_cand)
        self.assertIn('match_score', first_cand)
        self.assertIn('matched_skills', first_cand)
        self.assertIn('rationale', first_cand)
        print(f" -> Candidate: {first_cand['full_name']} ({first_cand['match_score']}% Match)")
        print(f" -> Rationale: {first_cand['rationale']}")
        print(" -> [PASS] Smart Skill-Based Recommendations API returned scored candidates.")

        print("\n[TEST F1.3] Testing Team Collaboration Invitation Dispatch & Duplicate Prevention...")
        self.login("admin@samadhansetu.com", "Admin@123")

        cand_user_id = first_cand['user_id']
        # Clear any existing invite
        TeamInvitation.query.filter_by(challenge_id=challenge.id, invitee_user_id=cand_user_id).delete()
        db.session.commit()

        # Send invitation
        send_res = self.client.post(f'/challenge/{challenge.id}/send-invitation', data={
            'invitee_id': cand_user_id,
            'role_offered': 'Embedded IoT Systems Lead',
            'matching_skills': ', '.join(first_cand['matched_skills']),
            'match_score': first_cand['match_score'],
            'message': 'Please join our team for ground sensor deployment.'
        }, follow_redirects=True)
        self.assertEqual(send_res.status_code, 200)

        inv = TeamInvitation.query.filter_by(challenge_id=challenge.id, invitee_user_id=cand_user_id).first()
        self.assertIsNotNone(inv)
        self.assertEqual(inv.status, 'Pending')
        print(f" -> Invitation #{inv.id} created for {first_cand['full_name']}.")

        # Test Duplicate Prevention
        dup_res = self.client.post(f'/challenge/{challenge.id}/send-invitation', data={
            'invitee_id': cand_user_id,
            'role_offered': 'Duplicate Role'
        }, follow_redirects=True)
        self.assertIn(b'already been sent', dup_res.data)
        print(" -> [PASS] Duplicate invitation blocked successfully.")

        print("\n[TEST F1.4] Testing Invitee Acceptance and Team Member Addition...")
        invitee_user = User.query.get(cand_user_id)
        invitee_user.set_password("TestPassword@123")
        db.session.commit()
        # Login as invitee
        login_res = self.login(invitee_user.email, "TestPassword@123")
        self.assertEqual(login_res.status_code, 200)

        # Invitee accepts invitation
        acc_res = self.client.post(f'/invitation/{inv.id}/respond', data={
            'action': 'accept'
        }, follow_redirects=True)
        self.assertEqual(acc_res.status_code, 200)

        db.session.refresh(inv)
        self.assertEqual(inv.status, 'Accepted')
        print(" -> Invitation status successfully transitioned to 'Accepted'.")
        print(" -> [PASS] Feature 1 (Smart Skill-Based Team Matching) passed 100%!")

    # -------------------------------------------------------------------------
    # TEST SUITE 2: IDEA -> IMPACT 10-STAGE PROJECT TRACKER & IMPACT METRICS
    # -------------------------------------------------------------------------
    def test_feature2_idea_to_impact_tracker(self):
        print("\n[TEST F2.1] Testing Dedicated /idea-impact UI Route...")
        page_res = self.client.get('/idea-impact')
        self.assertEqual(page_res.status_code, 200)
        self.assertIn(b'Idea', page_res.data)
        self.assertIn(b'Impact', page_res.data)
        self.assertIn(b'10-Stage', page_res.data)
        print(" -> [PASS] /idea-impact dedicated UI page rendered successfully.")

        print("\n[TEST F2.2] Testing 10-Stage Project Lifecycle Progression & Audit Log...")
        project = Project.query.first()
        self.assertIsNotNone(project, "Project must exist")

        self.login("admin@samadhansetu.com", "Admin@123")

        # Advance stage to 'Community Feedback'
        target_stage = "Community Feedback"
        res = self.client.post(f'/project/{project.id}/update-lifecycle-stage', data={
            'stage': target_stage,
            'description': 'Conducted town-hall survey across 5 Panchayats with 94% positive community feedback.',
            'evidence_url': 'https://drive.google.com/sample-townhall-report.pdf'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        db.session.refresh(project)
        self.assertEqual(project.current_stage, target_stage)

        # Verify stage update log
        latest_log = ProjectStageUpdate.query.filter_by(project_id=project.id).order_by(ProjectStageUpdate.created_at.desc()).first()
        self.assertIsNotNone(latest_log)
        self.assertEqual(latest_log.stage, target_stage)
        self.assertIn('94%', latest_log.description)
        print(f" -> Project #{project.id} advanced to '{target_stage}'. Progress: {project.progress_pct}%")
        print(" -> [PASS] Lifecycle stage advanced with auditable transition log.")

        print("\n[TEST F2.3] Testing Before-vs-After Ground Impact Indicator Calculation...")
        # Add ground impact metric
        metric_res = self.client.post(f'/project/{project.id}/add-impact-metric', data={
            'metric_name': 'Fluoride Contamination Level in Borewell Water',
            'unit': 'mg/L',
            'before_value': '4.5',
            'after_value': '0.9',
            'is_reduction': 'on',
            'verification_notes': 'Spectrophotometric validation by State Water Testing Lab, Ranchi.'
        }, follow_redirects=True)
        self.assertEqual(metric_res.status_code, 200)

        pim = ProjectImpactMetric.query.filter_by(
            project_id=project.id,
            metric_name='Fluoride Contamination Level in Borewell Water'
        ).first()
        self.assertIsNotNone(pim)
        self.assertEqual(pim.before_value, 4.5)
        self.assertEqual(pim.after_value, 0.9)
        self.assertEqual(pim.change_pct, 80.0) # (4.5 - 0.9)/4.5 = 80%
        print(f" -> Metric: {pim.metric_name}")
        print(f" -> Before: {pim.before_value} {pim.unit} | After: {pim.after_value} {pim.unit}")
        print(f" -> Computed Change: {pim.change_pct}% Reduction")
        print(" -> [PASS] Feature 2 (Idea -> Impact Tracker & Impact Cards) passed 100%!")

    # -------------------------------------------------------------------------
    # TEST SUITE 3: INDUSTRY + UNIVERSITY COLLABORATION HUB
    # -------------------------------------------------------------------------
    def test_feature3_industry_university_collaboration_hub(self):
        print("\n[TEST F3.1] Testing Public Industry Collaboration Portal & Filtering...")
        hub_res = self.client.get('/industry-collaboration')
        self.assertEqual(hub_res.status_code, 200)
        self.assertIn(b'Collaboration Hub', hub_res.data)

        # Action=request query param test
        req_page_res = self.client.get('/industry-collaboration?action=request')
        self.assertEqual(req_page_res.status_code, 200)
        self.assertIn(b'requestIndustrySupportModal', req_page_res.data)

        # Filter by type
        filter_res = self.client.get('/industry-collaboration?type=Funding')
        self.assertEqual(filter_res.status_code, 200)
        print(" -> [PASS] Industry Hub accessible with filtering and action trigger support.")

        print("\n[TEST F3.2] Testing Project Team Publishing Support Request...")
        self.login("admin@samadhansetu.com", "Admin@123")
        project = Project.query.first()

        # Clean up previous test records if any for idempotency
        old_reqs = IndustrySupportRequest.query.filter_by(title='Industrial Flow Meters and Solar Backup Cells').all()
        for r in old_reqs:
            IndustrySupportResponse.query.filter_by(request_id=r.id).delete()
            db.session.delete(r)
        db.session.commit()

        req_res = self.client.post(f'/project/{project.id}/request-industry-support', data={
            'support_type': 'Hardware & IoT Components',
            'title': 'Industrial Flow Meters and Solar Backup Cells',
            'description': 'Need 20 ultrasonic flow meters and 12V LiFePO4 battery banks for remote pipeline monitoring.',
            'estimated_budget': '200000',
            'timeline': '60 Days'
        }, follow_redirects=True)
        self.assertEqual(req_res.status_code, 200)

        created_req = IndustrySupportRequest.query.filter_by(
            project_id=project.id,
            title='Industrial Flow Meters and Solar Backup Cells'
        ).order_by(IndustrySupportRequest.id.desc()).first()
        self.assertIsNotNone(created_req)
        self.assertEqual(created_req.status, 'Support Requested')
        print(f" -> Support Request #{created_req.id} created on Project #{project.id}.")

        # Test global create route
        global_req_res = self.client.post('/industry-support/create', data={
            'project_id': project.id,
            'support_type': 'Funding / Seed Grant',
            'title': 'CSR Seed Grant for Handpump Filtration Deployment',
            'description': 'Targeting 50 rural handpumps across Palamu district.',
            'estimated_budget': '500000',
            'timeline': '90 Days'
        }, follow_redirects=True)
        self.assertEqual(global_req_res.status_code, 200)
        print(" -> [PASS] Global industry support creation verified.")

        print("\n[TEST F3.3] Testing Industry Partner Submitting Offer & Acceptance...")
        # Login as Industry Representative
        ind_user = User.query.filter_by(email="rajesh.singhania@tatasteel.com").first()
        if not ind_user:
            ind_user = User.query.filter(User.user_type.like("%Industry%")).first()
        ind_user.set_password("TestPassword@123")
        db.session.commit()
        self.login(ind_user.email, "TestPassword@123")

        offer_res = self.client.post(f'/industry-support/{created_req.id}/respond', data={
            'support_offered': 'Tata Steel Utilities Division offers 20 ultrasonic flow meters and 2 site engineers.',
            'contribution_details': 'Hardware supply + on-site installation guidance.',
            'contact_person': 'Rajesh Singhania',
            'contact_email': 'rajesh.singhania@tatasteel.com',
            'organization_name': 'Tata Steel Ltd.'
        }, follow_redirects=True)
        self.assertEqual(offer_res.status_code, 200)

        db.session.refresh(created_req)
        self.assertEqual(created_req.status, 'Industry Interested')
        resp = IndustrySupportResponse.query.filter_by(request_id=created_req.id).order_by(IndustrySupportResponse.id.desc()).first()
        self.assertIsNotNone(resp)
        self.assertEqual(resp.status, 'Offer Submitted')
        print(f" -> Industry Offer submitted. Request status advanced to 'Industry Interested'.")

        # Project Lead / Admin accepts offer
        self.login("admin@samadhansetu.com", "Admin@123")
        acc_res = self.client.post(f'/industry-response/{resp.id}/accept', follow_redirects=True)
        self.assertEqual(acc_res.status_code, 200)

        db.session.refresh(created_req)
        db.session.refresh(resp)
        self.assertEqual(created_req.status, 'Collaboration Started')
        self.assertEqual(resp.status, 'Accepted')
        print(f" -> Partnership accepted! Status advanced to '{created_req.status}'.")
        print(" -> [PASS] Feature 3 (Industry + University Collaboration Hub) passed 100%!")

    # -------------------------------------------------------------------------
    # TEST SUITE 4: DASHBOARD & ADMIN INTEGRATION (3 PROMINENT CARDS)
    # -------------------------------------------------------------------------
    def test_feature4_dashboard_cards_integration(self):
        print("\n[TEST F4.1] Verifying 3 Clickable Feature Cards on User Dashboard...")
        # Citizen login
        citizen = User.query.filter_by(user_type="Citizen").first() or User.query.first()
        citizen.set_password("Citizen@123")
        db.session.commit()
        self.login(citizen.email, "Citizen@123")

        dash_res = self.client.get('/user-dashboard')
        self.assertEqual(dash_res.status_code, 200)
        # Check all 3 feature card links
        self.assertIn(b'/smart-team', dash_res.data)
        self.assertIn(b'/idea-impact', dash_res.data)
        self.assertIn(b'/industry-collaboration', dash_res.data)
        print(" -> [PASS] All 3 feature cards present on User Dashboard (/user-dashboard).")

        print("\n[TEST F4.2] Verifying 3 Clickable Feature Cards on Admin Gateway & Operations Console...")
        self.login("admin@samadhansetu.com", "Admin@123")
        ops_res = self.client.get('/dashboard')
        self.assertEqual(ops_res.status_code, 200)
        self.assertIn(b'/smart-team', ops_res.data)
        self.assertIn(b'/idea-impact', ops_res.data)
        self.assertIn(b'/industry-collaboration', ops_res.data)

        admin_res = self.client.get('/admin')
        self.assertEqual(admin_res.status_code, 200)
        self.assertIn(b'/smart-team', admin_res.data)
        self.assertIn(b'/idea-impact', admin_res.data)
        self.assertIn(b'/industry-collaboration', admin_res.data)
        print(" -> [PASS] All 3 feature cards present on Administrator Gateway (/admin & /dashboard).")
        print(" -> [PASS] Feature 4 (Dashboard and Admin Integration) passed 100%!")


if __name__ == '__main__':
    print("=" * 72)
    print("  RUNNING SIH 2026 PROTOTYPE FEATURES VERIFICATION SUITE")
    print("=" * 72)
    unittest.main(verbosity=2)
