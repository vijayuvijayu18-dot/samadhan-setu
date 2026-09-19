"""
Unit and Integration Test Suite for Samadhan AI: Conversational Problem Submission
Tests route accessibility, top navigation presence, dynamic questioning,
evidence upload, "I don't know" handling, explicit confirmation,
Problem DNA synthesis, Similar Problem Fusion, and audit preservation.
"""

import os
import io
import json
import unittest
from app import app, db, User, Challenge, ProblemDNA, SamadhanAiSession


class TestSamadhanAi(unittest.TestCase):

    def setUp(self):
        self.client = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def test_01_samadhan_ai_route_and_navigation(self):
        """Verify /samadhan-ai renders HTTP 200 and navbar contains Samadhan AI."""
        resp = self.client.get('/samadhan-ai')
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)

        # Intro titles & buttons
        self.assertIn("Tell us your problem. We'll help structure it.", html)
        self.assertIn("You don't need to know how to write a formal problem statement.", html)
        self.assertIn("Start Reporting", html)
        self.assertIn("Samadhan AI", html)

        # Top navbar test
        self.assertIn('/samadhan-ai', html)
        self.assertIn('Samadhan AI', html)

        # Dashboard sidebar check
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['user_role'] = 'ADMINISTRATOR'
        dash_resp = self.client.get('/dashboard')
        self.assertEqual(dash_resp.status_code, 200)
        dash_html = dash_resp.get_data(as_text=True)
        self.assertIn('Samadhan AI', dash_html)

    def test_02_dynamic_questioning_missing_info(self):
        """Verify AI asks only for missing information and does not repeat known facts."""
        # Citizen provides problem statement without location or population
        resp = self.client.post('/api/samadhan-ai/chat',
            data=json.dumps({
                "message": "There is a severe water problem near our village school.",
                "history": [],
                "current_draft": {}
            }),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['draft']['domain'], 'Water Resources')
        # AI should ask for location because it is missing
        self.assertTrue(any(word in data['ai_message'].lower() for word in ['which village', 'district', 'town', 'where', 'location', 'area']))

    def test_03_dynamic_questioning_already_provided_facts(self):
        """Verify AI does NOT ask for location or population if citizen already provided them."""
        # Citizen provides location AND affected people in first message
        message = "There is no drinking water in our village school in Dumka, and around 100 students are affected."
        resp = self.client.post('/api/samadhan-ai/chat',
            data=json.dumps({
                "message": message,
                "history": [],
                "current_draft": {}
            }),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['success'])
        # Draft should capture location and population
        self.assertIn('Dumka', data['draft']['location'])
        self.assertIn('students', data['draft']['affected_population'])

        # AI should NOT ask "Which village" or "Who is affected"
        ai_msg = data['ai_message'].lower()
        self.assertNotIn("which village, town, or district", ai_msg)
        self.assertNotIn("who is mainly affected", ai_msg)

    def test_04_uncertainty_handling_i_dont_know(self):
        """Verify 'I don't know' responses are accepted gracefully without repeating."""
        resp = self.client.post('/api/samadhan-ai/chat',
            data=json.dumps({
                "message": "I don't have that information",
                "history": [
                    {"role": "user", "text": "Water pipeline is leaking in Ranchi."},
                    {"role": "ai", "text": "When did you first notice this issue?"}
                ],
                "current_draft": {
                    "domain": "Water Resources",
                    "location": "Ranchi, Jharkhand",
                    "affected_population": "Local residents"
                }
            }),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['success'])
        # Field should be marked for field verification rather than failing
        self.assertIn("Requires field verification", data['draft']['timing'])

    def test_05_evidence_upload(self):
        """Verify multimedia evidence upload endpoint securely saves files."""
        fake_image = (io.BytesIO(b"FAKE_IMAGE_DATA_BYTES"), "test_evidence.jpg")
        resp = self.client.post('/api/samadhan-ai/upload',
            data={"file": fake_image},
            content_type='multipart/form-data'
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['file']['type'], 'photo')
        self.assertIn('/static/uploads/', data['file']['url'])

        # Document upload test
        fake_doc = (io.BytesIO(b"LAB_TEST_REPORT_PDF"), "water_lab_report.pdf")
        resp_doc = self.client.post('/api/samadhan-ai/upload',
            data={"file": fake_doc},
            content_type='multipart/form-data'
        )
        self.assertEqual(resp_doc.status_code, 200)
        data_doc = resp_doc.get_json()
        self.assertTrue(data_doc['success'])
        self.assertEqual(data_doc['file']['type'], 'document')

    def test_06_explicit_confirmation_and_challenge_creation(self):
        """Verify explicit citizen confirmation creates Challenge, Problem DNA, and Similar Fusion links."""
        session_uuid = "test-session-uuid-12345"
        # Seed draft
        draft_payload = {
            "title": "Severe Fluoride Outflow at Dumka School Well",
            "domain": "Water Resources",
            "subdomain": "Groundwater Quality & Fluoride Remediation",
            "location": "Dumka Village School, Dumka, Jharkhand",
            "district": "Dumka",
            "affected_population": "120 students and 45 rural families",
            "people_affected_count": 500,
            "problem_summary": "Borewell water has high mineral salinity and reddish turbidity causing dental fluorosis symptoms.",
            "evidence_files": [
                {"name": "test_evidence.jpg", "url": "/static/uploads/test_evidence.jpg", "type": "photo"}
            ]
        }

        # Call submit endpoint
        resp = self.client.post('/api/samadhan-ai/submit',
            data=json.dumps({
                "session_uuid": session_uuid,
                "draft": draft_payload
            }),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['success'])
        challenge_id = data['challenge_id']

        # Verify challenge exists in DB
        ch = Challenge.query.get(challenge_id)
        self.assertIsNotNone(ch)
        self.assertEqual(ch.title, "Severe Fluoride Outflow at Dumka School Well")
        self.assertEqual(ch.district, "Dumka")
        self.assertEqual(ch.category, "Water Resources")
        self.assertEqual(ch.media_url, "/static/uploads/test_evidence.jpg")

        # Verify Problem DNA was automatically synthesized
        dna = ProblemDNA.query.filter_by(challenge_id=challenge_id).first()
        self.assertIsNotNone(dna)
        self.assertEqual(dna.domain, "Water Resources")
        self.assertIn("Fluoride", dna.subdomain)

        # Verify similar fusion detection
        self.assertIn('similar_count', data)

    def test_07_demo_scenario_endpoint(self):
        """Verify Section 28 demo scenario returns rural water dialogue and draft."""
        resp = self.client.get('/api/samadhan-ai/demo-scenario')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("Unsafe Drinking Water Near Rural School", data['title'])
        self.assertEqual(data['domain'], "Water Resources")
        self.assertTrue(len(data['dialogue']) >= 8)

    def test_section16_case1_greeting_hi(self):
        """Test 1: User enters 'hi' -> AI greets, asks for problem. No location query. No premature draft."""
        resp = self.client.post('/api/samadhan-ai/chat',
            data=json.dumps({"message": "hi", "history": [], "current_draft": {}}),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['success'])
        msg = data['ai_message'].lower()
        self.assertIn("namaste", msg)
        self.assertNotIn("which village", msg)
        self.assertNotIn("which district", msg)
        self.assertEqual(data['draft'], {})
        self.assertEqual(data['progress_pct'], 0)
        self.assertFalse(data['is_ready'])

    def test_section16_case2_consecutive_greetings(self):
        """Test 2: User enters 'hello' after 'hi' -> AI acknowledges warmly, no repeated question."""
        h1 = [
            {"role": "user", "text": "hi"},
            {"role": "ai", "text": "Namaste! Tell me about a problem..."}
        ]
        resp = self.client.post('/api/samadhan-ai/chat',
            data=json.dumps({"message": "hello", "history": h1, "current_draft": {}}),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['success'])
        msg = data['ai_message'].lower()
        self.assertNotIn("which village", msg)
        self.assertEqual(data['draft'], {})
        self.assertEqual(data['progress_pct'], 0)

    def test_section16_case3_water_problem_intake(self):
        """Test 3: User enters 'Water is dirty in our village' -> identifies water issue, asks for location."""
        resp = self.client.post('/api/samadhan-ai/chat',
            data=json.dumps({"message": "Water is dirty in our village", "history": [], "current_draft": {}}),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['draft']['domain'], 'Water Resources')
        msg = data['ai_message'].lower()
        self.assertTrue(any(w in msg for w in ['which village', 'district', 'town', 'where']))

    def test_section16_case4_location_provided(self):
        """Test 4: User enters 'In Murhu village, Khunti district' -> captures location, asks population."""
        h3 = [
            {"role": "user", "text": "Water is dirty in our village"},
            {"role": "ai", "text": "Which village, town, or district in Jharkhand is this occurring in?"}
        ]
        resp = self.client.post('/api/samadhan-ai/chat',
            data=json.dumps({
                "message": "In Murhu village, Khunti district",
                "history": h3,
                "current_draft": {"domain": "Water Resources"}
            }),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['success'])
        self.assertIn("Murhu", data['draft']['location'])
        self.assertIn("Khunti", data['draft']['district'])
        msg = data['ai_message'].lower()
        self.assertNotIn("which village", msg)
        self.assertTrue(any(w in msg for w in ["who is mainly affected", "how many", "who is affected"]))

    def test_section16_case5_i_dont_know_handling(self):
        """Test 5: User enters 'I don't know' -> noted for field verification, moves to timing/evidence without repeating."""
        h4 = [
            {"role": "user", "text": "Water is dirty in our village"},
            {"role": "ai", "text": "Which village, town, or district in Jharkhand is this occurring in?"},
            {"role": "user", "text": "In Murhu village, Khunti district"},
            {"role": "ai", "text": "Who is mainly affected by this issue, and approximately how many?"}
        ]
        draft = {
            "domain": "Water Resources",
            "location": "Murhu village, Khunti, Jharkhand",
            "district": "Khunti"
        }
        resp = self.client.post('/api/samadhan-ai/chat',
            data=json.dumps({"message": "I don't know", "history": h4, "current_draft": draft}),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['success'])
        self.assertIn("field survey", data['draft']['affected_population'].lower())
        msg = data['ai_message'].lower()
        self.assertNotIn("who is mainly affected", msg)
        self.assertTrue(any(w in msg for w in ["when did you first notice", "constantly", "seasonally"]))

    def test_section16_case6_skip_handling(self):
        """Test 6: User enters 'skip' -> advances without re-asking."""
        h5 = [
            {"role": "user", "text": "Water is dirty in our village"},
            {"role": "ai", "text": "Which village, town, or district in Jharkhand is this occurring in?"},
            {"role": "user", "text": "In Murhu village, Khunti district"},
            {"role": "ai", "text": "Who is mainly affected by this issue?"},
            {"role": "user", "text": "I don't know"},
            {"role": "ai", "text": "When did you first notice this issue?"}
        ]
        draft = {
            "domain": "Water Resources",
            "location": "Murhu village, Khunti, Jharkhand",
            "district": "Khunti",
            "affected_population": "Local community members"
        }
        resp = self.client.post('/api/samadhan-ai/chat',
            data=json.dumps({"message": "skip", "history": h5, "current_draft": draft}),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['success'])
        self.assertIn("verification", data['draft']['timing'].lower())
        msg = data['ai_message'].lower()
        self.assertTrue(any(w in msg for w in ["photo", "video", "document", "evidence"]))

    def test_section16_case7_vague_road_problem(self):
        """Test 7: User enters 'There is a road problem' -> clarifies road problem before asking location."""
        resp = self.client.post('/api/samadhan-ai/chat',
            data=json.dumps({"message": "There is a road problem", "history": [], "current_draft": {}}),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['success'])
        msg = data['ai_message'].lower()
        self.assertTrue(any(w in msg for w in ["road", "rain", "broken", "drainage", "what specifically", "what is happening"]))
        self.assertNotIn("which village, town, or district", msg)

    def test_section16_case8_complete_description(self):
        """Test 8: Complete description in one message -> extracts all facts, asks only for evidence/readiness."""
        msg_in = "Handpump water is red and smells bad in Karra village, Khunti district. Around 200 people are affected since last month."
        resp = self.client.post('/api/samadhan-ai/chat',
            data=json.dumps({"message": msg_in, "history": [], "current_draft": {}}),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['success'])
        draft = data['draft']
        self.assertIn("Karra", draft['location'])
        self.assertIn("Khunti", draft['district'])
        self.assertIn("200", draft['affected_population'])
        self.assertIn("last month", draft['timing'])
        msg = data['ai_message'].lower()
        self.assertNotIn("which village", msg)
        self.assertNotIn("who is mainly affected", msg)
        self.assertNotIn("when did you first notice", msg)
        self.assertTrue(any(w in msg for w in ["photo", "video", "document", "evidence", "prepare your challenge"]))

    def test_section16_case9_mid_conversation_greeting(self):
        """Test 9: User enters 'hello' in the middle of a problem discussion -> responds naturally and redirects back."""
        h4 = [
            {"role": "user", "text": "Water is dirty in our village"},
            {"role": "ai", "text": "Which village, town, or district in Jharkhand is this occurring in?"},
            {"role": "user", "text": "In Murhu village, Khunti district"},
            {"role": "ai", "text": "Who is mainly affected by this issue?"}
        ]
        draft = {
            "title": "Groundwater Quality in Murhu, Khunti",
            "domain": "Water Resources",
            "location": "Murhu village, Khunti, Jharkhand",
            "district": "Khunti"
        }
        resp = self.client.post('/api/samadhan-ai/chat',
            data=json.dumps({"message": "hello", "history": h4, "current_draft": draft}),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['success'])
        msg = data['ai_message'].lower()
        self.assertIn("hello", msg)
        self.assertNotIn("which village, town, or district", msg)

    def test_section16_case10_general_questions(self):
        """Test 10: General inquiries (name, platform, evidence) answered gracefully without forcing location."""
        # 10a. Identity question
        resp = self.client.post('/api/samadhan-ai/chat',
            data=json.dumps({"message": "What is your name?", "history": [], "current_draft": {}}),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['success'])
        self.assertIn("Samadhan AI", data['ai_message'])
        self.assertNotIn("which village", data['ai_message'].lower())

        # 10b. Platform question
        resp2 = self.client.post('/api/samadhan-ai/chat',
            data=json.dumps({"message": "What is Samadhan Setu?", "history": [], "current_draft": {}}),
            content_type='application/json'
        )
        self.assertEqual(resp2.status_code, 200)
        data2 = resp2.get_json()
        self.assertTrue(data2['success'])
        self.assertIn("Samadhan Setu", data2['ai_message'])
        self.assertTrue(any(w in data2['ai_message'].lower() for w in ["innovators", "universities", "community challenges", "solutions"]))

        # 10c. Evidence question
        resp3 = self.client.post('/api/samadhan-ai/chat',
            data=json.dumps({"message": "Can I upload a photo?", "history": [], "current_draft": {}}),
            content_type='application/json'
        )
        self.assertEqual(resp3.status_code, 200)
        data3 = resp3.get_json()
        self.assertTrue(data3['success'])
        self.assertTrue(any(w in data3['ai_message'].lower() for w in ["yes", "attachment", "photos", "paperclip"]))

    def test_section16_case11_short_problem_keyword(self):
        """Test 11: Single keyword 'road' triggers domain clarification instead of raw location query."""
        resp = self.client.post('/api/samadhan-ai/chat',
            data=json.dumps({"message": "road", "history": [], "current_draft": {}}),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['success'])
        msg = data['ai_message'].lower()
        self.assertTrue(any(w in msg for w in ["road", "rain", "potholes", "maintenance", "damaged"]))
        self.assertNotIn("which village", msg)
        self.assertEqual(data['draft']['domain'], 'Urban Development')

    def test_section16_case12_multiple_problems_handling(self):
        """Test 12: Multiple problems in one message asks user to combine or separate."""
        multi_msg = "we have poor roads, no proper waste collection and water shortages"
        resp = self.client.post('/api/samadhan-ai/chat',
            data=json.dumps({"message": multi_msg, "history": [], "current_draft": {}}),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['success'])
        msg = data['ai_message'].lower()
        self.assertTrue("multiple issues" in msg or "combine" in msg)
        self.assertTrue(any("combine" in qr.lower() for qr in data['quick_replies']))

    def test_section16_case13_self_correction_handling(self):
        """Test 13: Citizen correction 'Actually I meant Dumka, not Ranchi' updates location cleanly."""
        h = [
            {"role": "user", "text": "Dirty water in our school"},
            {"role": "ai", "text": "Which village, town, or district in Jharkhand is this occurring in?"},
            {"role": "user", "text": "Ranchi"},
            {"role": "ai", "text": "Who is mainly affected by this issue?"}
        ]
        draft = {
            "title": "Water problem in Ranchi",
            "domain": "Water Resources",
            "location": "Ranchi, Jharkhand",
            "district": "Ranchi",
            "source_attribution": {"location": "Citizen provided"}
        }
        resp = self.client.post('/api/samadhan-ai/chat',
            data=json.dumps({"message": "Actually I meant Dumka, not Ranchi", "history": h, "current_draft": draft}),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['success'])
        self.assertIn("Dumka", data['draft']['location'])
        self.assertEqual(data['draft']['district'], "Dumka")
        self.assertNotIn("Ranchi", data['draft']['location'])
        self.assertIn("Dumka", data['ai_message'])

    def test_section16_case14_source_attribution_in_draft(self):
        """Test 14: Draft includes field-level source attribution badges."""
        msg = "Dirty drinking water in Khunti village affecting 200 people"
        resp = self.client.post('/api/samadhan-ai/chat',
            data=json.dumps({"message": msg, "history": [], "current_draft": {}}),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['success'])
        attrs = data['draft'].get('source_attribution', {})
        self.assertEqual(attrs.get('problem'), "Citizen provided")
        self.assertEqual(attrs.get('location'), "Citizen provided")
        self.assertEqual(attrs.get('affected_population'), "Citizen provided")
        self.assertIn(attrs.get('domain'), ["AI suggested", "AI classified"])

    def test_section16_case15_clean_empty_initial_state(self):
        """Test 15: Initial page load shows clean empty draft state without placeholder groundwater data."""
        resp = self.client.get('/samadhan-ai')
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)
        self.assertIn("No problem has been described yet. Explain your situation in natural words.", html)
        self.assertIn("id=\"draftEmptyState\"", html)
        self.assertIn("id=\"draftContentArea\" class=\"d-none\"", html)

    def test_section16_case16_gibberish_handling(self):
        """Test 16: User typing 'gg' or keymash when asked for location does not jump to population."""
        h = [
            {"role": "user", "text": "There is dirty water in our village"},
            {"role": "ai", "text": "Which village, town, or district in Jharkhand is this occurring in?"}
        ]
        draft = {
            "problem_summary": "There is dirty water in our village",
            "domain": "Water Resources",
            "subdomain": "Groundwater Quality & Potable Water Supply"
        }
        resp = self.client.post('/api/samadhan-ai/chat',
            data=json.dumps({"message": "gg", "history": h, "current_draft": draft}),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['success'])
        msg = data['ai_message'].lower()
        # Must re-prompt for location / district, NOT advance to population or timing
        self.assertTrue(any(w in msg for w in ["which village", "district", "town", "understand", "not sure"]))
        self.assertNotIn("who is mainly affected", msg)
        self.assertNotIn("how many people are affected", msg)
        self.assertNotIn("when did you first notice", msg)
        # Location must remain unset (not filled with 'gg')
        self.assertFalse(data['draft'].get('location'))
        self.assertFalse(data['draft'].get('affected_population'))

    def test_section16_case17_informal_whats_ur_name_redirect(self):
        """Test 17: User asking 'whats ur name' answers identity and redirects to active missing dimension without skipping."""
        h = [
            {"role": "user", "text": "There is dirty water in our village"},
            {"role": "ai", "text": "Which village, town, or district in Jharkhand is this occurring in?"}
        ]
        draft = {
            "problem_summary": "There is dirty water in our village",
            "domain": "Water Resources",
            "subdomain": "Groundwater Quality & Potable Water Supply"
        }
        resp = self.client.post('/api/samadhan-ai/chat',
            data=json.dumps({"message": "whats ur name", "history": h, "current_draft": draft}),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['success'])
        msg = data['ai_message']
        # Answers identity
        self.assertIn("Samadhan AI", msg)
        # Reminds of location
        self.assertTrue(any(w in msg.lower() for w in ["village", "district", "town", "where"]))
        # Does NOT advance to timing
        self.assertNotIn("when did you first notice", msg.lower())
        # Draft is not corrupted
        self.assertFalse(data['draft'].get('location'))
        self.assertFalse(data['draft'].get('affected_population'))


if __name__ == '__main__':
    unittest.main()

