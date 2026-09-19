import unittest
import json
from app import app, db, User, Challenge, ProblemDNA, generate_problem_dna

class TestProblemDNA(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()

    def test_01_dna_generation_all_13_dimensions(self):
        """Test that generate_problem_dna produces all 13 required fields + AI Understanding."""
        with app.app_context():
            ch = Challenge.query.first()
            self.assertIsNotNone(ch, "Challenge #1 should exist")
            dna = generate_problem_dna(ch)

            # 1. Problem Title
            self.assertTrue(len(dna.title) > 5)
            # 2. Domain & Subdomain
            self.assertTrue(len(dna.domain) > 2)
            self.assertTrue(len(dna.subdomain) > 2)
            # 3. Problem Summary
            self.assertTrue(len(dna.summary) > 15)
            # 4. Affected Population
            self.assertTrue(len(dna.affected_population) > 5)
            # 5. Location & Context
            self.assertTrue(len(dna.location_context) > 5)
            # 6. Severity / Urgency & Explanation
            self.assertIn(dna.severity, ['Critical', 'High', 'Medium', 'Low'])
            self.assertTrue(len(dna.severity_explanation) > 10)
            # 7. Contributing Factors (Hypotheses)
            factors = dna.get_contributing_factors_list()
            self.assertTrue(len(factors) >= 1)
            self.assertTrue(any("Hypothesis" in f for f in factors))
            # 8. Key Evidence
            evidence = dna.get_key_evidence_list()
            self.assertTrue(len(evidence) >= 1)
            # 9. Required Expertise
            expertise = dna.get_required_expertise_list()
            self.assertTrue(len(expertise) >= 1)
            # 10. Potential Solution Areas
            solutions = dna.get_potential_solutions_list()
            self.assertTrue(len(solutions) >= 1)
            # 11. Relevant SDGs
            sdgs = dna.get_relevant_sdgs_list()
            self.assertTrue(len(sdgs) >= 1)
            self.assertTrue(any("SDG" in s for s in sdgs))
            # 12. Related Challenges (Similar Problem Fusion)
            self.assertIsInstance(dna.get_related_challenges_list(), list)
            # 13. Information Gaps
            gaps = dna.get_information_gaps_list()
            self.assertTrue(len(gaps) >= 1)

            # AI Understanding Section
            self.assertTrue(len(dna.ai_understanding) > 30)

            # Ethical Uncertainty Badges
            self.assertEqual(dna.verification_status, 'AI-estimated')

    def test_02_challenge_detail_renders_problem_dna(self):
        """Test that /challenge/<id> renders the Problem DNA card with badges and citizen report."""
        with app.app_context():
            # Test with Challenge #2 to ensure clean unedited state
            ch = Challenge.query.get(2) or Challenge.query.first()
            ch_id = ch.id
            raw_desc = ch.description

        res = self.client.get(f'/challenge/{ch_id}')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')

        # Check visual card & badges
        self.assertIn('AI PROBLEM DNA', html)
        self.assertIn('Structured Challenge Profile', html)
        self.assertIn('Ethical AI Guardrail Notice', html)
        self.assertIn('AI Understanding', html)

        # Check key dimensions present
        self.assertIn('Problem Summary', html)
        self.assertIn('Affected Population', html)
        self.assertIn('Location', html)
        self.assertIn('Severity &', html)
        self.assertIn('Possible Contributing Factors', html)
        self.assertIn('Key Evidence', html)
        self.assertIn('Required Technical Expertise', html)
        self.assertIn('Potential Solution Areas', html)
        self.assertIn('Relevant UN SDGs', html)
        self.assertIn('Information Gaps', html)
        self.assertIn('Similar Problem Fusion', html)

        # Check Original Citizen Report Tab
        self.assertIn('Original Citizen Report (Preserved)', html)
        self.assertIn('Original Citizen Report Preserved (Immutable)', html)
        self.assertIn(raw_desc[:30], html)

    def test_03_authorized_edit_and_citizen_preservation(self):
        """Test authorized edit updates Problem DNA while preserving citizen report intact."""
        with app.app_context():
            ch = Challenge.query.get(1)
            ch_id = ch.id
            orig_desc = ch.description
            orig_loc = ch.location

            # Login as Administrator
            admin = User.query.filter_by(user_type='ADMINISTRATOR').first()
            with self.client.session_transaction() as sess:
                sess['user_id'] = admin.id
                sess['user_role'] = 'ADMINISTRATOR'

            # Submit Problem DNA Edit
            edit_data = {
                'title': 'Refined Water Treatment Project (Human Verified)',
                'domain': 'Water Resources',
                'subdomain': 'Groundwater Quality & Fluoride Remediation',
                'summary': 'Refined summary verified by academic researcher squad.',
                'affected_population': '3,500 residents across 3 Panchayats',
                'location_context': 'Baghmara, Dhanbad, Jharkhand',
                'severity': 'Critical',
                'severity_explanation': 'Critical urgency confirmed due to high fluoride levels.',
                'contributing_factors': 'Hypothesis: Mining pit seepage\nHypothesis: Subsurface mineral dissolution',
                'key_evidence': 'BIT Mesra lab assay #42\nSite inspection photo',
                'required_expertise': 'Chemical Engineering, IoT Telemetry',
                'potential_solution_areas': 'Solar membrane filtration skid\nActivated alumina adsorption',
                'relevant_sdgs': 'SDG 6: Clean Water, SDG 3: Good Health',
                'information_gaps': 'Certified flow rate\nBorewell GPS census',
                'ai_understanding': 'The AI synthesized citizen report and researchers confirmed parameters.'
            }

            res = self.client.post(f'/challenge/{ch_id}/problem-dna/edit', data=edit_data, follow_redirects=True)
            self.assertEqual(res.status_code, 200)

            # Verify Problem DNA updated
            dna = ProblemDNA.query.filter_by(challenge_id=ch_id).first()
            self.assertEqual(dna.title, 'Refined Water Treatment Project (Human Verified)')
            self.assertTrue(dna.is_edited_by_user)
            self.assertEqual(dna.verification_status, 'Expert Verified & Corrected')
            self.assertEqual(dna.last_edited_by_id, admin.id)

            # CRITICAL: Verify original citizen report is completely untouched!
            ch_after = Challenge.query.get(ch_id)
            self.assertEqual(ch_after.description, orig_desc, "Citizen description must remain 100% intact")
            self.assertEqual(ch_after.location, orig_loc, "Citizen location must remain 100% intact")

    def test_04_unauthorized_edit_blocked(self):
        """Test that unauthenticated users cannot edit Problem DNA."""
        with app.app_context():
            ch = Challenge.query.first()
            ch_id = ch.id

        # Anonymous user attempt
        res = self.client.post(f'/challenge/{ch_id}/problem-dna/edit', data={'title': 'Hacked Title'}, follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertIn('/login', res.headers.get('Location', ''))

    def test_05_new_challenge_submission_creates_dna(self):
        """Test that submitting a new challenge immediately synthesizes its Problem DNA."""
        with app.app_context():
            admin = User.query.filter_by(user_type='ADMINISTRATOR').first()
            with self.client.session_transaction() as sess:
                sess['user_id'] = admin.id
                sess['user_role'] = 'ADMINISTRATOR'

            post_data = {
                'title': 'Severe Fluorosis in Dumka Wells',
                'description': 'Villagers and cattle in Dumka report white chalky deposits and bone aches from drinking water.',
                'category': 'Water Resources',
                'department': 'Drinking Water and Sanitation',
                'location': 'Shikaripara, Dumka, Jharkhand',
                'district': 'Dumka',
                'block': 'Shikaripara',
                'priority': 'High',
                'status': 'Open'
            }

            res = self.client.post('/challenge/new', data=post_data, follow_redirects=True)
            self.assertEqual(res.status_code, 200)

            # Check new challenge has synthesized DNA
            created_ch = Challenge.query.filter_by(title='Severe Fluorosis in Dumka Wells').first()
            self.assertIsNotNone(created_ch)
            self.assertIsNotNone(created_ch.problem_dna)
            self.assertEqual(created_ch.problem_dna.domain, 'Water Resources')
            self.assertTrue(len(created_ch.problem_dna.ai_understanding) > 20)

if __name__ == '__main__':
    unittest.main()

