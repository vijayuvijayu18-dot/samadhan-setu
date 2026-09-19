"""
Samadhan AI — Complete Professional AI Problem Intake & Structuring Agent
Provides:
- Intent Detection (Greetings, General Questions, Problem Reports, Multiple Problems, Corrections, Uncertainty, Skips)
- Context & Multi-Turn Session Memory (Preserves all verified facts, avoids repeating known info)
- Structured Extraction (24 Jharkhand districts, villages, populations, timelines, 10 thematic domains)
- Dynamic Missing Information Engine (Information gap detection, problem before metadata, sufficiency evaluation)
- Conversational Response Generation (Acknowledge, explain, clarify, summarize, conversational checkpoints)
- Challenge Draft Builder with Field-Level Source Attribution (Citizen provided, AI suggested, Needs verification)
- Resilient Service Architecture with Gemini API integration & deterministic local fallback
"""

import os
import re
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# =====================================================================
# 1. THE 10 MANDATED THEMATIC DOMAIN SPECIFICATIONS
# =====================================================================
DOMAIN_SPECS = {
    "Water Resources": {
        "subdomains": [
            "Groundwater Quality & Fluoride/Arsenic Contamination",
            "Drinking Water Supply & Pipe Infrastructure",
            "Borewell & Community Well Maintenance",
            "Monsoon Waterlogging & Drainage"
        ],
        "keywords": ["water", "drinking", "fluoride", "arsenic", "groundwater", "pipeline", "borewell", "well", "contamination", "potable", "aquifer", "purification", "tap", "filter", "handpump"],
        "clarify_question": "What specifically is happening with the water? Is it related to drinking water quality, lack of water availability, contamination, or broken infrastructure?",
        "default_subdomain": "Groundwater Quality & Potable Water Supply",
        "population_question": "Who relies on this water source (e.g. students, families, or farmers), and approximately how many people are affected?"
    },
    "Agriculture": {
        "subdomains": [
            "Crop Disease & Pest Infestation",
            "Post-Harvest Storage & Cold Chain",
            "Irrigation & Soil Health",
            "Farm-to-Market Access & Distress Sales"
        ],
        "keywords": ["farmer", "crop", "agriculture", "soil", "harvest", "tomato", "paddy", "vegetable", "cold storage", "irrigation", "pesticide", "fertilizer", "yield", "farm", "field", "pest"],
        "clarify_question": "What crop is affected, and what specific damage or difficulty are farmers experiencing?",
        "default_subdomain": "Crop Protection & Agricultural Productivity",
        "population_question": "Which crop is affected, and are multiple farming families or an entire village facing this difficulty?"
    },
    "Healthcare": {
        "subdomains": [
            "Primary Health Center Diagnostic Infrastructure",
            "Maternal & Child Nutrition / Anemia",
            "Seasonal Waterborne / Vector-Borne Illness",
            "Emergency Telemedicine & Medical Logistics"
        ],
        "keywords": ["health", "medical", "hospital", "doctor", "disease", "patient", "sick", "illness", "fever", "malnutrition", "anemia", "phc", "chc", "clinic", "medicine"],
        "clarify_question": "What health difficulty or symptoms are community members facing?",
        "default_subdomain": "Community Healthcare & Primary Diagnostics",
        "population_question": "Who is mainly experiencing these health difficulties, and has a local healthcare center or doctor examined the situation?"
    },
    "Education": {
        "subdomains": [
            "Digital Learning Infrastructure & STEM Labs",
            "Vernacular & Multilingual Pedagogy (Santhali/Ho/Mundari)",
            "Classroom Sanitation & Student Retention",
            "Teacher Training & Learning Aids"
        ],
        "keywords": ["school", "education", "student", "teacher", "classroom", "learning", "study", "books", "tablet", "bench", "children", "college", "hostel", "toilet", "toilets", "sanitation"],
        "clarify_question": "Which educational facility is affected, and what specific barrier or shortage are students experiencing?",
        "default_subdomain": "School Infrastructure & Inclusive Education",
        "population_question": "Approximately how many students or teachers are affected at this school?"
    },
    "Rural Livelihoods": {
        "subdomains": [
            "Non-Timber Forest Produce (NTFP) & Lac Processing",
            "Tussar Silk & Handloom Value Addition",
            "SHG Micro-Enterprise Scaling",
            "Artisan Direct Marketing"
        ],
        "keywords": ["livelihood", "tribal", "lac", "forest", "shg", "artisan", "handicraft", "handloom", "tussar", "silk", "income", "cottage", "cultivation"],
        "clarify_question": "What traditional craft, forest produce, or livelihood activity is facing challenges?",
        "default_subdomain": "Rural Enterprise & Forest Produce Value Addition",
        "population_question": "How many artisans, SHG members, or rural workers are affected by this issue?"
    },
    "Accessibility": {
        "subdomains": [
            "Physical Mobility & Public Facility Ramps",
            "Assistive Devices for Visual & Hearing Impairment",
            "Accessible Public Transport & Signage",
            "Inclusive Digital Public Services"
        ],
        "keywords": ["access", "accessible", "accessibility", "disabled", "disability", "wheelchair", "blind", "ramp", "elderly", "hearing", "barrier", "inclusive"],
        "clarify_question": "Which facility or public area is difficult to access, and what specific barrier exists?",
        "default_subdomain": "Public Infrastructure Accessibility & Inclusion",
        "population_question": "Who is having difficulty accessing this facility (e.g. elderly citizens, wheelchair users, students)?"
    },
    "Urban Development": {
        "subdomains": [
            "Solid Waste Segregation & Processing",
            "Road Quality, Potholes & Stormwater Drains",
            "Traffic Bottlenecks & Smart Transit",
            "Street Lighting & Municipal Amenities"
        ],
        "keywords": ["urban", "road", "traffic", "municipal", "waste", "garbage", "drain", "drainage", "pothole", "street", "light", "bridge", "city", "town"],
        "clarify_question": "What is happening with the road or civic facility? Is it unusable during rain, broken, or lacking drainage?",
        "default_subdomain": "Urban Civic Amenities & Road Infrastructure",
        "population_question": "Who is most affected by this—students, daily commuters, local residents, or transport vehicles?"
    },
    "Environment": {
        "subdomains": [
            "Industrial Effluent & River Ecology Protection",
            "Mining Dust & Air Quality Mitigation",
            "E-Waste & Hazardous Material Disposal",
            "Biodiversity & Watershed Restoration"
        ],
        "keywords": ["environment", "pollution", "river", "smoke", "effluent", "dust", "toxic", "mining", "air", "ecology", "dump"],
        "clarify_question": "What environmental hazard or pollution source is causing this issue?",
        "default_subdomain": "Environmental Conservation & Pollution Abatement",
        "population_question": "Which areas or neighborhoods are exposed to this environmental concern?"
    },
    "Energy": {
        "subdomains": [
            "Off-Grid Decentralized Solar Microgrids",
            "Agricultural Pump Energization",
            "Rural Grid Reliability & Transformer Uptime",
            "Clean Cooking Fuel Alternatives"
        ],
        "keywords": ["energy", "solar", "electricity", "power", "grid", "voltage", "blackout", "transformer", "battery", "meter"],
        "clarify_question": "Is the power issue related to low voltage, frequent blackouts, broken transformers, or complete lack of electricity?",
        "default_subdomain": "Renewable Clean Energy & Rural Power Supply",
        "population_question": "How many households or agricultural pumps are impacted by this power difficulty?"
    },
    "Public Administration": {
        "subdomains": [
            "PDS Ration Delivery Transparency",
            "Gram Panchayat Grievance Tracking",
            "Land & Caste Certificate Delivery",
            "Public Welfare Scheme Last-Mile Access"
        ],
        "keywords": ["administration", "panchayat", "ration", "pds", "scheme", "certificate", "grievance", "portal", "transparency", "bdo", "delivery"],
        "clarify_question": "Which public service, certificate, or welfare scheme delivery is facing delays?",
        "default_subdomain": "Public Service Delivery & Civic Governance",
        "population_question": "How many community members or beneficiaries are unable to access this service?"
    }
}

# =====================================================================
# 2. VOCABULARY & INTENT LEXICONS
# =====================================================================
GREETING_WORDS = {
    "hi", "hello", "hey", "namaste", "namaskar", "pranam", "good morning",
    "good afternoon", "good evening", "hola", "kese ho", "hi samadhan",
    "hello samadhan", "hey there", "start", "help"
}

NON_ANSWER_WORDS = {
    "i don't know", "i dont know", "not sure", "don't know", "dont know",
    "no idea", "cannot say", "not known", "skip", "pass", "no info",
    "i don't have that information", "i dont have that information", "no information",
    "idk", "no", "nahi pata", "pata nahi", "leave it", "later", "maybe", "can't say", "cant say"
}

AFFIRMATION_WORDS = {
    "yes", "yeah", "yep", "ok", "okay", "sure", "haan", "ha", "fine", "alright",
    "looks good", "correct", "confirm", "submit", "ready", "yes submit"
}

JHARKHAND_DISTRICTS_LIST = [
    "Ranchi", "East Singhbhum", "Jamshedpur", "Dhanbad", "Bokaro", "Deoghar",
    "Dumka", "Hazaribagh", "West Singhbhum", "Chaibasa", "Ramgarh", "Giridih",
    "Palamu", "Gumla", "Khunti", "Simdega", "Lohardaga", "Latehar",
    "Garhwa", "Chatra", "Koderma", "Jamtara", "Godda", "Sahibganj",
    "Pakur", "Saraikela"
]


# =====================================================================
# 3. INTENT DETECTOR
# =====================================================================
class IntentDetector:
    """
    Interprets citizen message in context without blindly assuming it
    is an answer to the previous question.
    """

    @classmethod
    def is_gibberish(cls, text):
        clean = text.strip().lower()
        if not clean:
            return True
        valid_shorts = {
            "hi", "ok", "no", "yes", "idk", "road", "dam", "well", "tap", "crop", "farm", "none",
            "skip", "pass", "ha", "hey", "ranchi", "dumka", "water", "drain", "lamp", "pipe", "bore",
            "pothole", "river", "soil", "dust", "smoke", "tree", "plant", "pond", "canal", "waste",
            "school", "health", "power", "light", "pds", "ration", "solar", "seed", "wheat", "paddy"
        }
        if clean in valid_shorts:
            return False

        # If length <= 3 and not in valid_shorts, it's non-responsive or random (e.g. "gg", "aa", "zzz", "xd", "lol", "k", "a")
        if len(clean) <= 3:
            return True

        # Repeated identical characters e.g. "aaaaa", ".....", "????"
        if re.match(r'^(.)\1+$', clean):
            return True

        # Keyboard mashing
        if any(km in clean for km in ["asdf", "sdkjf", "qwer", "zxcv", "ghjk", "lkjh", "poiu"]):
            return True

        # Long strings without any vowels
        letters = re.findall(r'[a-z]', clean)
        vowels = re.findall(r'[aeiouy]', clean)
        if len(letters) >= 4 and len(vowels) == 0:
            return True

        return False

    @classmethod
    def detect(cls, message, history=None, state=None):
        clean = message.strip().lower()
        clean_norm = re.sub(r'[^a-zA-Z0-9\s]', '', clean).strip()
        words = clean_norm.split()

        # 1. Greeting
        if clean_norm in GREETING_WORDS or clean in GREETING_WORDS:
            return {"intent": "greeting"}

        for gw in GREETING_WORDS:
            if clean_norm == gw or clean_norm.startswith(gw + " "):
                if len(words) <= 3:
                    return {"intent": "greeting"}

        # 2. General Questions about Samadhan AI, Samadhan Setu, or Process
        # 2a. Name / Identity (handles "whats ur name", "who are you", "who r u", "kya naam hai", etc.)
        if re.search(r"\b(?:what(?:'s|\s+is|\s+are)?|who|tell\s+me\s+about)\s+(?:ur|your|u|the)\s+(?:name|identity|bot|assistant|details)\b", clean) \
           or re.search(r"\b(?:whats?\s+(?:ur|your)\s+name)\b", clean) \
           or re.search(r"\b(?:who\s+(?:are\s+you|r\s+u|are\s+u))\b", clean) \
           or re.search(r"\b(?:who\s+(?:made|created)\s+(?:you|u))\b", clean) \
           or re.search(r"\b(?:tell\s+me\s+about\s+(?:yourself|urself))\b", clean) \
           or re.search(r"\b(?:aapka\s+naam|kya\s+naam\s+hai)\b", clean):
            return {"intent": "general_question", "sub_type": "identity"}

        # 2b. Platform / Purpose
        if re.search(r'\b(?:what\s+(?:is|does)\s+(?:this|samadhan|setu|samadhansetu|platform))\b', clean) \
           or re.search(r'\b(?:what\s+do\s+(?:you|u)\s+do|what\s+can\s+(?:you|u)\s+do|how\s+can\s+(?:you|u)\s+help)\b', clean) \
           or re.search(r'\b(?:tell\s+me\s+about\s+samadhan\s+setu)\b', clean) \
           or re.search(r'\b(?:kya\s+kaam\s+hai|ye\s+kya\s+hai)\b', clean):
            return {"intent": "general_question", "sub_type": "platform"}

        # 2c. Rationale / Why asking
        if re.search(r'\b(?:why\s+(?:are\s+you\s+asking|do\s+you\s+need|asking))\b', clean) \
           or re.search(r'\b(?:why\s+(?:location|district|village|details))\b', clean):
            return {"intent": "general_question", "sub_type": "why_asking"}

        # 2d. Evidence Inquiry
        if re.search(r'\b(?:can\s+(?:i|we)\s+(?:upload|attach)|how\s+(?:do\s+i|to)\s+upload|upload\s+(?:photo|pic|video|doc|image|evidence))\b', clean):
            if not any(w in clean for w in ["have photo", "attached", "here is", "i have photos", "i have photo"]):
                return {"intent": "general_question", "sub_type": "evidence_inquiry"}

        # 2e. Location Inquiry / Change Request
        if re.search(r'\b(?:can\s+i\s+change\s+(?:the\s+)?location|change\s+location|wrong\s+location)\b', clean):
            return {"intent": "location_change_inquiry"}

        # 2f. Help Inquiry
        if re.search(r'\b(?:help(?:\s+me)?|how\s+does\s+this\s+work|what\s+should\s+i\s+do|guide\s+me)\b', clean):
            return {"intent": "general_question", "sub_type": "help"}

        # 3. Corrections (e.g. "actually I meant Dumka", "sorry I meant Khunti", "it's not Ranchi")
        correction_patterns = [
            r'(?:actually|sorry|no)\s+(?:i\s+meant|it\s+is|it\'s|meant)\s+([A-Za-z0-9\s]+?)(?:,\s*not|\s+not|\s+instead of|\.|$)',
            r'change\s+(?:location|village|district|area)\s+to\s+([A-Za-z0-9\s]+?)(?:,\s*not|\s+not|\.|$)',
            r'(?:not\s+[A-Za-z0-9\s]+,\s*(?:in|it is|meant|actually)?\s*([A-Za-z0-9\s]+))',
            r'(?:actually|sorry|no)\s+(?:i\s+meant|it\s+is|it\'s|meant)\s+([A-Za-z0-9\s,]+)'
        ]
        for pat in correction_patterns:
            m = re.search(pat, message, re.IGNORECASE)
            if m:
                return {"intent": "correction", "corrected_value": m.group(1).strip()}

        # 4. Uncertainty & Non-answers
        for nw in NON_ANSWER_WORDS:
            if clean_norm == nw:
                return {"intent": "uncertainty"}
            if len(nw.split()) > 1 and nw in clean_norm:
                return {"intent": "uncertainty"}
            if len(nw.split()) == 1 and len(words) <= 3:
                if re.search(r'\b' + re.escape(nw) + r'\b', clean_norm):
                    return {"intent": "uncertainty"}

        # 5. Affirmations / Confirmations
        if clean_norm in AFFIRMATION_WORDS or (len(words) <= 2 and any(clean_norm == aw for aw in AFFIRMATION_WORDS)):
            return {"intent": "affirmation"}

        # 6. Ultra-short problem keyword (e.g. "road", "water", "school", "crop", "waste")
        if len(words) <= 2 and clean_norm in {"road", "water", "school", "crop", "crops", "waste", "electricity", "hospital", "doctor"}:
            return {"intent": "short_problem_keyword", "keyword": clean_norm}

        # 7. Multiple Problems Detection (e.g. "poor roads, no waste collection and water shortages")
        issues_detected = []
        if re.search(r'\b(?:poor\s+roads?|bad\s+roads?|broken\s+roads?|no\s+roads?|potholes?|road\s+issue|road\s+problem)\b', clean):
            issues_detected.append("road infrastructure")
        elif re.search(r'\broads?\b', clean) and any(w in clean for w in ["damage", "broken", "unusable", "repair", "pothole"]):
            issues_detected.append("road infrastructure")

        if re.search(r'\b(?:waste|garbage|dump|drainage|sewage|sanitation)\b', clean) and any(w in clean for w in ["collection", "overflow", "dirty", "dump", "pile", "unhygienic", "clean", "problem", "issue"]):
            issues_detected.append("waste & sanitation")
        elif re.search(r'\b(?:waste\s+collection|garbage\s+dump|open\s+drainage|sewage\s+overflow)\b', clean):
            issues_detected.append("waste & sanitation")

        if re.search(r'\b(?:water\s+shortage|no\s+(?:drinking\s+)?water|dirty\s+water|water\s+contamination|water\s+problem|water\s+crisis)\b', clean):
            issues_detected.append("water supply")
        elif re.search(r'\bwater\b', clean) and any(w in clean for w in ["scarcity", "shortage", "leak", "dirty", "contamination", "pipeline"]):
            issues_detected.append("water supply")

        if re.search(r'\b(?:electricity\s+cut|no\s+power|power\s+cut|power\s+outage|transformer\s+burnt|load\s+shedding)\b', clean):
            issues_detected.append("electricity")

        if re.search(r'\b(?:no\s+teachers?|teacher\s+shortage|school\s+facility|school\s+infrastructure|broken\s+school|classroom\s+damage)\b', clean):
            issues_detected.append("school education")

        if re.search(r'\b(?:no\s+doctors?|doctor\s+shortage|hospital\s+closed|no\s+medicines?|health\s+center\s+closed)\b', clean):
            issues_detected.append("healthcare")

        if len(issues_detected) >= 2 and any(conn in clean for conn in [" and ", " as well as ", ", "]):
            return {"intent": "multiple_problems", "issues": issues_detected}

        # 8. Gibberish / Random Characters
        if cls.is_gibberish(clean):
            return {"intent": "gibberish", "raw": message}

        # 9. Standard problem report or follow-up detail
        return {"intent": "problem_report"}


# =====================================================================
# 4. STRUCTURED EXTRACTOR
# =====================================================================
class StructuredExtractor:
    """Extracts factual dimensions from citizen text without hallucination."""

    @classmethod
    def detect_domain(cls, text):
        """Identify the most relevant thematic domain using keyword density and boundaries."""
        text_lower = text.lower()
        best_domain = None
        max_hits = 0

        for domain, spec in DOMAIN_SPECS.items():
            hits = sum(1 for kw in spec["keywords"] if re.search(r'\b' + re.escape(kw) + r'\b', text_lower))
            if hits > max_hits:
                max_hits = hits
                best_domain = domain

        return best_domain

    @classmethod
    def extract(cls, text, current_state=None):
        extracted = {}
        text_lower = text.lower()

        # 1. Specific District Detection
        for dist in JHARKHAND_DISTRICTS_LIST:
            if re.search(r'\b' + re.escape(dist.lower()) + r'\b', text_lower):
                extracted["district"] = dist
                extracted["location"] = f"{dist}, Jharkhand"
                break

        # 2. Named Village / Area Detection
        village_cand = None
        v_match = re.search(r'\b(?:in|near|at|of)\s+([A-Za-z0-9\s]{2,25}?(?:village|tola|basti|block|colony|nagar|panchayat))\b', text, re.IGNORECASE)
        if not v_match:
            v_match = re.search(r'\b([A-Za-z0-9\s]{2,20}\s+(?:village|tola|basti|panchayat))\b', text, re.IGNORECASE)

        if v_match:
            candidate = v_match.group(1).strip()
            cand_lower = candidate.lower()
            generic_words = [
                "our village", "the village", "a village", "my village", "this village",
                "the school", "our school", "village school", "problem"
            ]
            if not any(cand_lower == gw for gw in generic_words) and len(candidate) > 2:
                village_cand = candidate.strip(",. ")

        if village_cand:
            if "district" in extracted:
                extracted["location"] = f"{village_cand}, {extracted['district']}, Jharkhand"
            else:
                extracted["location"] = village_cand

        # 3. Affected Population Detection
        pop_patterns = [
            (r'(\d+)\s*(?:students|children|families|people|farmers|villagers|residents|households)', 'count'),
            (r'(?:around|about|approximately)\s*(\d+)\s*(?:people|citizens|families|students|farmers)?', 'approx'),
            (r'(students|farmers|villagers|residents|school children|nearby families|daily commuters)', 'group')
        ]
        for pat, ptype in pop_patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                if ptype == 'count':
                    extracted["people_count"] = int(m.group(1))
                    extracted["affected_population"] = f"Approximately {m.group(1)} {m.group(0).split()[-1]} and surrounding community"
                elif ptype == 'approx':
                    extracted["people_count"] = int(m.group(1))
                    extracted["affected_population"] = f"Approximately {m.group(1)} community members"
                elif ptype == 'group' and "affected_population" not in extracted:
                    extracted["affected_population"] = f"{m.group(1).capitalize()} and local residents"
                break

        # 4. Timeline / Recurrence Detection
        time_matches = re.search(
            r'\b(?:about|since|for|around|from)\s+(\d+\s+(?:days|weeks|months|years)|recently|two weeks|three months|yesterday|last\s+(?:week|month|year|few\s+(?:days|weeks|months)))\b'
            r'|\b(?:last|past)\s+(?:week|month|year|few\s+(?:days|weeks|months|years))\b'
            r'|\b(?:since\s+last\s+(?:week|month|year))\b',
            text, re.IGNORECASE
        )
        if time_matches:
            extracted["timing"] = time_matches.group(0).strip()
        elif "monsoon" in text_lower or "rain" in text_lower:
            extracted["timing"] = "Recurring during monsoon rainfall"
        elif "everyday" in text_lower or "daily" in text_lower or "constant" in text_lower:
            extracted["timing"] = "Continuous daily difficulty"

        # 5. Evidence Mention
        if any(p in text_lower for p in ["have photo", "have photos", "i have photos", "attached photo", "upload photo"]):
            extracted["citizen_indicated_evidence"] = True

        return extracted


# =====================================================================
# 5. CONVERSATION & CONTEXT MANAGER
# =====================================================================
class ContextManager:
    """
    Maintains the persistent structured state of the reporting session,
    tracks asked/answered topics, and applies corrections.
    """

    @classmethod
    def initialize_state(cls, existing_draft=None):
        draft = dict(existing_draft or {})
        if "source_attribution" not in draft:
            draft["source_attribution"] = {}
        if "needs_verification" not in draft:
            draft["needs_verification"] = []
        if "asked_topics" not in draft:
            draft["asked_topics"] = []
        return draft

    @classmethod
    def determine_active_topic(cls, draft):
        """
        Determines the current active dimension based on what is genuinely
        resolved in the draft state.
        """
        if not draft.get("problem_summary"):
            return "problem"
        if not draft.get("location"):
            return "location"
        if not draft.get("affected_population"):
            return "population"
        if not draft.get("timing"):
            return "timing"
        if not (draft.get("evidence_summary") or draft.get("evidence_declined")):
            return "evidence"
        return "review_ready"

    @classmethod
    def get_asked_topics(cls, history):
        topics = set()
        for h in history:
            if h.get("role") == "ai":
                t = h.get("text", "").lower()
                if "which village" in t or "where is" in t or "district" in t or "which area" in t:
                    topics.add("location")
                if "who is mainly affected" in t or "how many" in t or "who relies" in t or "which students" in t:
                    topics.add("population")
                if "when did you first notice" in t or "frequently" in t or "how often" in t:
                    topics.add("timing")
                if "photo" in t or "video" in t or "document" in t or "evidence" in t:
                    topics.add("evidence")
                if "what specifically is happening" in t or "what is happening" in t:
                    topics.add("problem_clarify")
        return topics

    @classmethod
    def apply_correction(cls, state, corrected_value):
        """Applies a user self-correction (e.g. 'Actually I meant Dumka')."""
        corrected_clean = corrected_value.strip(",. ")
        # Filter out negated mentions like "not Ranchi" or "instead of Ranchi"
        clean_target = re.sub(r'\b(?:not|instead\s+of)\s+[A-Za-z0-9\s]+', '', corrected_clean, flags=re.IGNORECASE).strip(" ,.")
        eval_text = clean_target if clean_target else corrected_clean

        for dist in JHARKHAND_DISTRICTS_LIST:
            if re.search(r'\b' + re.escape(dist.lower()) + r'\b', eval_text.lower()):
                state["location"] = f"{dist}, Jharkhand"
                state["district"] = dist
                state["source_attribution"]["location"] = "Confirmed by citizen"
                return f"Got it! I've updated the location to {dist}, Jharkhand."

        # If it looks like a population count
        num_match = re.search(r'\b(\d+)\b', eval_text)
        if num_match:
            state["people_affected_count"] = int(num_match.group(1))
            state["affected_population"] = f"Approximately {num_match.group(1)} people"
            state["source_attribution"]["affected_population"] = "Confirmed by citizen"
            return f"Understood. I have updated the affected population to approximately {num_match.group(1)}."

        # Otherwise update general location
        state["location"] = eval_text
        state["source_attribution"]["location"] = "Confirmed by citizen"
        return f"Understood. I have updated the location to {eval_text}."


# =====================================================================
# 6. MISSING INFORMATION & GAP ENGINE
# =====================================================================
class MissingInformationEngine:
    """
    Evaluates what information is necessary for meaningful evaluation
    and selects the single most critical missing dimension next.
    """

    @classmethod
    def evaluate(cls, state, asked_topics=None, meaningful_user_turns_count=0):
        """
        Returns:
            - next_topic (str or None)
            - is_ready (bool)
            - information_gaps (list)
        """
        gaps = []

        has_problem = bool(state.get("problem_summary"))
        has_location = bool(state.get("location"))
        has_population = bool(state.get("affected_population"))
        has_timing = bool(state.get("timing"))
        has_evidence = bool(state.get("evidence_summary") or state.get("evidence_declined"))

        if not has_location: gaps.append("Exact location (Village / District)")
        if not has_population: gaps.append("Affected population / scale")
        if not has_timing: gaps.append("Timeline and frequency")
        if not has_evidence: gaps.append("Supporting photos / documents")

        state["information_gaps"] = gaps

        # Check information sufficiency:
        if has_problem and has_location and has_population and has_timing and has_evidence:
            return None, True, gaps

        # Priority 1: Location (Where is this happening?)
        if not has_location:
            return "location", False, gaps

        # Priority 2: Population (Who is affected?)
        if not has_population:
            return "population", False, gaps

        # Priority 3: Timing (When did it start / how often?)
        if not has_timing:
            return "timing", False, gaps

        # Priority 4: Evidence
        if not has_evidence:
            return "evidence", False, gaps

        # If all resolved:
        return None, True, gaps


# =====================================================================
# 7. SAMADHAN AI ENGINE (AGENT CORE)
# =====================================================================
class SamadhanAiEngine:
    """
    AI-powered Societal Problem Intake, Understanding and Challenge Creation Agent.
    Implements:
    LISTEN -> UNDERSTAND -> CLARIFY -> COLLECT -> STRUCTURE -> VERIFY -> CONFIRM -> SUBMIT.
    """

    @classmethod
    def classify_intent(cls, message):
        return IntentDetector.detect(message)["intent"]

    @classmethod
    def detect_domain(cls, text):
        return StructuredExtractor.detect_domain(text)

    @classmethod
    def extract_dimensions_from_text(cls, text, current_draft=None):
        return StructuredExtractor.extract(text, current_draft)

    @classmethod
    def get_last_asked_topic(cls, history):
        if not history: return None
        last_ai_msgs = [h["text"] for h in history if h.get("role") == "ai"]
        if not last_ai_msgs: return None
        last_ai_text = last_ai_msgs[-1].lower()

        if any(w in last_ai_text for w in ["which village", "town", "district", "where is", "which area"]):
            return "location"
        if any(w in last_ai_text for w in ["who is mainly affected", "how many", "who is affected", "who relies"]):
            return "population"
        if any(w in last_ai_text for w in ["when did you first notice", "how frequently", "how often", "constantly", "seasonally"]):
            return "timing"
        if any(w in last_ai_text for w in ["photo", "video", "document", "evidence", "upload"]):
            return "evidence"
        if any(w in last_ai_text for w in ["what specifically is happening", "what is happening"]):
            return "problem_clarify"
        return "general"

    @classmethod
    def is_vague_problem(cls, text):
        text_lower = text.lower().strip()
        words = text_lower.split()
        if len(words) <= 5:
            vague_indicators = ["problem", "issue", "kharab", "pareshani", "difficulty"]
            if any(vi in text_lower for vi in vague_indicators):
                return True
        return False

    @classmethod
    def process_turn(cls, message, history, current_draft, uploaded_files=None, location_data=None):
        uploaded_files = uploaded_files or []
        location_data = location_data or {}
        draft = ContextManager.initialize_state(current_draft)

        intent_info = IntentDetector.detect(message, history, draft)
        intent = intent_info["intent"]
        last_asked_topic = cls.get_last_asked_topic(history)
        asked_topics = ContextManager.get_asked_topics(history)

        user_messages_raw = [h["text"] for h in history if h.get("role") == "user"]
        meaningful_user_messages = [m for m in user_messages_raw if IntentDetector.detect(m)["intent"] in {"problem_report", "multiple_problems", "short_problem_keyword"}]

        # =================================================================
        # SCENARIO A: GREETING
        # =================================================================
        if intent == "greeting":
            greetings_count = sum(1 for m in user_messages_raw if IntentDetector.detect(m)["intent"] == "greeting")
            if not meaningful_user_messages and not draft.get("problem_summary"):
                if greetings_count > 0:
                    ai_response = "Hello again! 😊 Whenever you're ready, please tell me about what difficulty or challenge is happening in your area. You can explain it naturally."
                else:
                    ai_response = "👋 Namaste! I'm Samadhan AI. Tell me about a problem affecting your village, town, school, or community. You don't need to write it formally. Just explain it naturally."

                quick_replies = [
                    "💧 There is a drinking-water problem in my village.",
                    "🛣️ Our road becomes unusable during rain.",
                    "🏫 Our school needs better sanitation facilities.",
                    "🌾 Farmers in our area are facing a crop problem."
                ]
            else:
                ai_response = f"Hello! 😊 Let's continue with your problem report. You were telling me about: {draft.get('title') or draft.get('problem_summary') or 'your community issue'}."
                quick_replies = ["Continue reporting", "Review current draft"]

            return cls._package_response(ai_response, draft, False, quick_replies, meaningful_user_messages)

        # =================================================================
        # SCENARIO B: GIBBERISH / NON-RESPONSIVE / RANDOM INPUT (e.g. "gg", "asdf")
        # =================================================================
        if intent == "gibberish":
            active_topic = ContextManager.determine_active_topic(draft)
            if active_topic == "problem":
                ai_response = "I didn't quite catch that. 😊 Could you please describe what problem or difficulty is happening in your area? You can write it simply in your own words."
                quick_replies = [
                    "💧 Drinking water problem in village",
                    "🛣️ Road unusable during rainfall",
                    "🏫 School sanitation facilities",
                    "🌾 Crop difficulty in farm"
                ]
            elif active_topic == "location":
                ai_response = "I couldn't quite understand that. Could you please tell me which village, town, or district in Jharkhand this problem is occurring in? (Or reply 'not sure' if you'd like our field team to verify it on-site)."
                quick_replies = ["Ranchi", "Dumka", "Khunti", "East Singhbhum", "Dhanbad", "Not sure"]
            elif active_topic == "population":
                ai_response = "I couldn't quite understand that. Could you tell me who is mainly affected by this difficulty (e.g. students, families, or farmers), and approximately how many people? (Or reply 'not sure' to skip)."
                quick_replies = ["School students", "Village households", "Local farmers", "Not sure"]
            elif active_topic == "timing":
                ai_response = "I didn't catch that. When did you first notice this problem, and does it happen continuously or seasonally? (Or reply 'not sure' to continue)."
                quick_replies = ["About two weeks ago", "Ongoing for months", "During monsoon rainfall", "Not sure"]
            elif active_topic == "evidence":
                ai_response = "I didn't catch that. Do you have any photos, videos, or documents to upload, or would you like to proceed without uploading?"
                quick_replies = ["I have photos", "Proceed without photos"]
            else:
                ai_response = "I didn't catch that. Your challenge draft is ready for review. Would you like to confirm and submit it?"
                quick_replies = ["Confirm & Submit Challenge", "Edit Information"]

            return cls._package_response(ai_response, draft, False, quick_replies, meaningful_user_messages)

        # =================================================================
        # SCENARIO C: GENERAL QUESTIONS & EXPLANATIONS
        # =================================================================
        if intent == "general_question":
            sub = intent_info.get("sub_type")
            if sub == "identity":
                ans = "I'm **Samadhan AI**, the problem-reporting assistant for Samadhan Setu. I help turn your natural problem description into a structured challenge profile for innovators and universities."
            elif sub == "platform":
                ans = "**Samadhan Setu** connects ground-level community challenges with universities, student researchers, and industry partners to develop practical, scalable solutions."
            elif sub == "why_asking":
                ans = "Innovators and researchers need clear context—such as the exact location and affected group—to evaluate technical feasibility, verify ground conditions, and design effective solutions."
            elif sub == "evidence_inquiry":
                ans = "Yes, absolutely! You can upload photos, videos, or documents using the paperclip attachment button below the input bar."
            elif sub == "help":
                ans = "I am here to guide you step-by-step in reporting any community problem in Jharkhand. You just speak or type naturally, and I will structure it into an actionable challenge."
            else:
                ans = "I am here to assist you in reporting and structuring your community challenge."

            active_topic = ContextManager.determine_active_topic(draft)
            if active_topic == "problem":
                ai_response = f"{ans}\n\nWhen you're ready, tell me about any problem you would like to report in your area."
                quick_replies = [
                    "💧 Drinking water problem in village",
                    "🛣️ Road unusable during rainfall",
                    "🏫 School sanitation facilities"
                ]
            elif active_topic == "location":
                ai_response = f"{ans}\n\nTo continue with your report, **which village, town, or district in Jharkhand is this occurring in?**"
                quick_replies = ["Ranchi", "Dumka", "Khunti", "East Singhbhum", "Not sure"]
            elif active_topic == "population":
                ai_response = f"{ans}\n\nTo continue with your report, **who is mainly affected (e.g. students, families, or farmers), and approximately how many people?**"
                quick_replies = ["School students", "Village households", "Local farmers", "Not sure"]
            elif active_topic == "timing":
                ai_response = f"{ans}\n\nTo continue, **when did you first notice this problem, and does it happen continuously or seasonally?**"
                quick_replies = ["About two weeks ago", "Ongoing for months", "During heavy rains", "Not sure"]
            elif active_topic == "evidence":
                ai_response = f"{ans}\n\nDo you have any photos, videos, or documents to upload, or would you like to proceed without uploading?"
                quick_replies = ["I have photos", "Proceed without photos"]
            else:
                ai_response = f"{ans}\n\nYour challenge draft is ready for review. Would you like to review and submit it?"
                quick_replies = ["Review Challenge Draft", "Confirm & Submit"]

            return cls._package_response(ai_response, draft, False, quick_replies, meaningful_user_messages)

        # =================================================================
        # SCENARIO D: LOCATION CHANGE INQUIRY
        # =================================================================
        if intent == "location_change_inquiry":
            ai_response = "Yes, certainly! You can tell me the new village or district name here, or use the 📍 location pin button to select a Jharkhand district or share GPS coordinates."
            quick_replies = ["In Ranchi", "In Dumka", "In Khunti", "Use Device GPS"]
            return cls._package_response(ai_response, draft, False, quick_replies, meaningful_user_messages)

        # =================================================================
        # SCENARIO E: CORRECTIONS
        # =================================================================
        if intent == "correction":
            corrected_val = intent_info.get("corrected_value", "")
            confirm_msg = ContextManager.apply_correction(draft, corrected_val)
            # Check what's missing next
            next_topic, is_ready, _ = MissingInformationEngine.evaluate(draft, asked_topics, len(meaningful_user_messages))
            if is_ready:
                ai_response = f"{confirm_msg} I have enough information to prepare your challenge. Here is what I have understood. Would you like to review and submit it?"
            else:
                ai_response = f"{confirm_msg} Let's continue."
            return cls._package_response(ai_response, draft, is_ready, ["Review Challenge Draft", "Confirm & Submit"], meaningful_user_messages)

        # =================================================================
        # SCENARIO F: UNCERTAINTY & SKIP
        # =================================================================
        if intent == "uncertainty":
            active_topic = ContextManager.determine_active_topic(draft)
            target = last_asked_topic or active_topic
            if target == "location":
                draft["location"] = "Requires field verification (Location details to be determined on-site)"
                draft["district"] = "Jharkhand (Pending Verification)"
                draft["source_attribution"]["location"] = "Needs verification"
                ai_response = "No problem at all. You don't need the exact village name right now; our field team can verify the location. Who is mainly affected by this difficulty (e.g. students, families, or farmers)?"
                quick_replies = ["School students", "Village households", "Local farmers", "Not sure"]
            elif target == "population":
                draft["affected_population"] = "Requires field survey (Local community members, exact count pending on-site survey)"
                draft["people_affected_count"] = 1000
                draft["source_attribution"]["affected_population"] = "Needs verification"
                ai_response = "Understood. The exact number can be surveyed later. When did you first notice this issue, and does it happen constantly or seasonally?"
                quick_replies = ["About two weeks ago", "Ongoing for months", "During heavy rains"]
            elif target == "timing":
                draft["timing"] = "Requires field verification (Timeline to be confirmed on ground)"
                draft["source_attribution"]["timing"] = "Needs verification"
                ai_response = "That's completely fine. Do you happen to have any photos, videos, or documents, or would you like to proceed without uploading?"
                quick_replies = ["I have photos", "Proceed without photos"]
            elif target == "evidence":
                draft["evidence_declined"] = True
                draft["evidence_summary"] = "Physical evidence optional (to be verified on ground)"
                draft["source_attribution"]["evidence"] = "Needs verification"
                ai_response = "Understood. Physical evidence is optional. I have enough information to prepare your structured challenge."
                return cls._package_response(ai_response, draft, True, ["Review Challenge Draft", "Confirm & Submit"], meaningful_user_messages)
            else:
                ai_response = "No problem at all. We can leave that for field verification. Let's continue with your problem description."
                quick_replies = ["Continue", "Review Draft"]

            return cls._package_response(ai_response, draft, False, quick_replies, meaningful_user_messages)

        # =================================================================
        # SCENARIO G: EVIDENCE FILES UPLOADED
        # =================================================================
        if uploaded_files:
            draft["evidence_files"] = uploaded_files
            photo_count = sum(1 for f in uploaded_files if f.get("type") == "photo" or f.get("name", "").lower().endswith(('.png', '.jpg', '.jpeg', '.webp')))
            doc_count = sum(1 for f in uploaded_files if f.get("type") == "document" or f.get("name", "").lower().endswith(('.pdf', '.docx', '.txt', '.csv')))
            parts = []
            if photo_count: parts.append(f"{photo_count} photo{'s' if photo_count > 1 else ''}")
            if doc_count: parts.append(f"{doc_count} document{'s' if doc_count > 1 else ''}")
            draft["evidence_summary"] = ", ".join(parts) if parts else "Files attached"
            draft["source_attribution"]["evidence"] = "Citizen provided"

            ai_response = f"I have received your {draft['evidence_summary']}. I have enough information to prepare your challenge draft."
            return cls._package_response(ai_response, draft, True, ["Review Challenge Draft", "Confirm & Submit"], meaningful_user_messages)

        # =================================================================
        # SCENARIO H: MULTIPLE PROBLEMS RECOGNIZED
        # =================================================================
        if intent == "multiple_problems":
            issues = intent_info.get("issues", [])
            issues_str = ", ".join(issues[:-1]) + " and " + issues[-1] if len(issues) > 1 else issues[0]
            ai_response = f"I understand there are multiple issues here: {issues_str}. Would you like to report them as one combined community challenge, or focus on one first?"
            quick_replies = ["Combine into one challenge", f"Focus on {issues[0]}"]
            draft["problem_summary"] = message
            draft["domain"] = "Urban Development"
            draft["source_attribution"]["problem"] = "Citizen provided"
            return cls._package_response(ai_response, draft, False, quick_replies, meaningful_user_messages + [message])

        # =================================================================
        # SCENARIO I: SHORT PROBLEM KEYWORD ("road", "water", "school")
        # =================================================================
        if intent == "short_problem_keyword":
            kw = intent_info.get("keyword")
            if kw == "road":
                ai_response = "Sure. What is the problem with the road? Is it damaged, flooded during rain, or lacking maintenance?"
                draft["domain"] = "Urban Development"
                draft["subdomain"] = "Road Quality, Potholes & Stormwater Drains"
                quick_replies = ["Road unusable during rain", "Severe potholes", "Broken culvert / bridge"]
            elif kw in {"water", "drinking"}:
                ai_response = "I can help with that. What is happening with the water? Is it related to quality, availability, or broken supply infrastructure?"
                draft["domain"] = "Water Resources"
                draft["subdomain"] = "Groundwater Quality & Potable Water Supply"
                quick_replies = ["Water is dirty / discolored", "Handpump broken", "Acute water shortage"]
            elif kw == "school":
                ai_response = "What problem are students or staff facing at the school? Is it sanitation, drinking water, or damaged classrooms?"
                draft["domain"] = "Education"
                draft["subdomain"] = "School Infrastructure & Inclusive Education"
                quick_replies = ["Lack of clean toilets", "No drinking water", "Damaged building"]
            elif kw in {"crop", "crops"}:
                ai_response = "What difficulty are farmers facing with their crops? Is it pest damage, unseasonal disease, or lack of water?"
                draft["domain"] = "Agriculture"
                draft["subdomain"] = "Crop Protection & Agricultural Productivity"
                quick_replies = ["Pest infestation", "Crop drying / no irrigation", "Storage problem"]
            else:
                ai_response = f"I can help you report this {kw} problem. Can you tell me a little more about what is happening?"
                quick_replies = ["Explain problem details", "Provide location"]

            draft["problem_summary"] = f"Citizen reported {kw} issue"
            draft["source_attribution"]["problem"] = "Citizen provided"
            draft["source_attribution"]["domain"] = "AI suggested"
            return cls._package_response(ai_response, draft, False, quick_replies, meaningful_user_messages + [message])

        # =================================================================
        # SCENARIO J: FULL MEANINGFUL PROBLEM REPORT / FOLLOW-UP DETAILS
        # =================================================================
        active_topic = ContextManager.determine_active_topic(draft)

        # 1. Detect Domain & Subdomain
        detected_domain = cls.detect_domain(message) or draft.get("domain")
        if detected_domain:
            draft["domain"] = detected_domain
            domain_spec = DOMAIN_SPECS.get(detected_domain, DOMAIN_SPECS.get("Water Resources", {}))
            draft["subdomain"] = draft.get("subdomain") or domain_spec.get("default_subdomain", "")
            draft["source_attribution"]["domain"] = "AI suggested"
        else:
            domain_spec = None

        # 2. Extract Dimensions
        extracted = cls.extract_dimensions_from_text(message, draft)

        if location_data and "location" in location_data:
            draft["location"] = location_data["location"]
            if "district" in location_data:
                draft["district"] = location_data["district"]
            draft["source_attribution"]["location"] = "Citizen provided"
        elif "location" in extracted and not draft.get("location"):
            draft["location"] = extracted["location"]
            if "district" in extracted:
                draft["district"] = extracted["district"]
            draft["source_attribution"]["location"] = "Citizen provided"
        elif (last_asked_topic == "location" or active_topic == "location") and not draft.get("location"):
            clean_loc = message.strip(" ,.")
            if len(clean_loc.split()) <= 6:
                draft["location"] = f"{clean_loc}, Jharkhand"
                for d in JHARKHAND_DISTRICTS_LIST:
                    if d.lower() in clean_loc.lower():
                        draft["district"] = d
                        draft["location"] = clean_loc
                        break
                draft["source_attribution"]["location"] = "Citizen provided"

        if "affected_population" in extracted and not draft.get("affected_population"):
            draft["affected_population"] = extracted["affected_population"]
            if "people_count" in extracted:
                draft["people_affected_count"] = extracted["people_count"]
            draft["source_attribution"]["affected_population"] = "Citizen provided"
        elif (last_asked_topic == "population" or active_topic == "population") and not draft.get("affected_population"):
            clean_pop = message.strip()
            if len(clean_pop.split()) <= 10:
                draft["affected_population"] = clean_pop
                num_m = re.search(r'\b(\d+)\b', clean_pop)
                if num_m:
                    draft["people_affected_count"] = int(num_m.group(1))
                draft["source_attribution"]["affected_population"] = "Citizen provided"

        if "timing" in extracted and not draft.get("timing"):
            draft["timing"] = extracted["timing"]
            draft["source_attribution"]["timing"] = "Citizen provided"
        elif (last_asked_topic == "timing" or active_topic == "timing") and not draft.get("timing"):
            clean_time = message.strip()
            if len(clean_time.split()) <= 8:
                draft["timing"] = clean_time
                draft["source_attribution"]["timing"] = "Citizen provided"

        if "citizen_indicated_evidence" in extracted:
            draft["citizen_indicated_evidence"] = True

        if (last_asked_topic == "evidence" or active_topic == "evidence") and not draft.get("evidence_summary"):
            if any(w in message.lower() for w in ["no", "none", "don't have", "dont have", "proceed", "later", "without", "skip"]):
                draft["evidence_declined"] = True
                draft["evidence_summary"] = "Physical evidence optional (to be verified on ground)"
                draft["source_attribution"]["evidence"] = "Needs verification"

        # Problem summary
        if not draft.get("problem_summary"):
            draft["problem_summary"] = message.strip()
            draft["source_attribution"]["problem"] = "Citizen provided"
        elif last_asked_topic == "problem_clarify":
            draft["problem_summary"] = f"{draft['problem_summary']} - {message.strip()}"

        all_meaningful = meaningful_user_messages + [message]

        # 3. Check for ultra-vague statement (e.g. "There is a road problem") on turn 1
        is_vague = cls.is_vague_problem(message) and len(meaningful_user_messages) == 0

        # 4. Evaluate Dynamic Missing Information
        next_topic, is_ready, gaps = MissingInformationEngine.evaluate(draft, asked_topics, len(all_meaningful))

        quick_replies = []

        if is_vague and "problem_clarify" not in asked_topics:
            clarify_q = domain_spec.get("clarify_question", "What specifically is happening?") if domain_spec else "What specifically is happening?"
            dom_name = detected_domain.lower() if detected_domain else "your community"
            ai_response = f"I understand you are reporting a problem regarding {dom_name}. {clarify_q}"
            quick_replies = ["Road unusable during rain", "Damaged infrastructure", "Lack of maintenance"]

        elif next_topic == "location":
            ai_response = "I understand. Which village, town, or district in Jharkhand is this occurring in?"
            quick_replies = ["Ranchi", "Dumka", "Khunti", "East Singhbhum", "Dhanbad", "Use Device GPS"]

        elif next_topic == "population":
            pop_q = domain_spec.get("population_question", "Who is mainly affected by this issue, and approximately how many people?") if domain_spec else "Who is mainly affected by this issue, and approximately how many people?"
            ai_response = pop_q
            quick_replies = ["School students", "Local farming families", "Around 100 people", "Not sure"]

        elif next_topic == "timing":
            ai_response = "When did you first notice this problem, and does it happen continuously or seasonally?"
            quick_replies = ["About two weeks ago", "Ongoing for months", "During monsoon rainfall", "Not sure"]

        elif next_topic == "evidence":
            if draft.get("citizen_indicated_evidence") and not draft.get("evidence_summary"):
                ai_response = "Please upload your photo, video, or document using the attachment button below, or let me know if you prefer to proceed without uploading."
                quick_replies = ["Proceed without photos", "I will upload later"]
            else:
                ai_response = "Do you have any photos, videos, or documents showing the situation?"
                quick_replies = ["I have photos", "No evidence currently", "Will provide to field team"]

        else:
            # Sufficiency achieved: provide conversational summary checkpoint
            loc_disp = draft.get("location") or "Jharkhand"
            pop_disp = draft.get("affected_population") or "Local community"
            dom_name = detected_domain.lower() if detected_domain else "community"
            ai_response = f"Let me make sure I understood you correctly:\n\nYou are reporting {dom_name} difficulty in **{loc_disp}**, affecting **{pop_disp}**.\n\nI have enough information to prepare your challenge draft. Please review it before we submit."
            is_ready = True
            quick_replies = ["Confirm & Submit Challenge", "Edit Information"]

        return cls._package_response(ai_response, draft, is_ready, quick_replies, all_meaningful)

    @classmethod
    def _package_response(cls, ai_message, draft, is_ready, quick_replies, meaningful_messages):
        """Constructs standardized output payload with progress and attributions."""
        has_content = bool(draft.get("problem_summary") or draft.get("domain") or draft.get("location"))
        if not meaningful_messages and not has_content:
            return {
                "ai_message": ai_message,
                "draft": {},
                "checklist": {
                    "problem_core": False,
                    "domain_identified": False,
                    "location_provided": False,
                    "population_identified": False,
                    "timeline_recorded": False,
                    "evidence_attached": False
                },
                "progress_pct": 0,
                "is_ready": False,
                "quick_replies": quick_replies,
                "mode": "Live AI" if os.environ.get("GEMINI_API_KEY") else "Demo AI"
            }

        # Synthesize Title ONLY if domain or problem summary exists
        if not draft.get("title") and (draft.get("domain") or draft.get("problem_summary")):
            loc = draft.get("location") or (draft.get("district") + ", Jharkhand" if draft.get("district") else "Jharkhand")
            sub = draft.get("subdomain") or draft.get("domain") or "Community Challenge"
            draft["title"] = f"{sub} in {loc}"

        # Standard Ethical Verification Items
        needs_verif = []
        if not draft.get("location") or "Requires field verification" in draft.get("location", ""):
            needs_verif.append("Location details require on-site confirmation by field teams.")
        if not draft.get("affected_population") or "Requires field survey" in draft.get("affected_population", ""):
            needs_verif.append("Impacted population count requires ground census / household survey.")
        if not draft.get("evidence_summary"):
            needs_verif.append("Physical evidence optional (to be validated on ground).")
        needs_verif.append("Technical contributing factors are hypotheses for scoping, not binding findings.")

        draft["needs_verification"] = needs_verif

        checklist = {
            "problem_core": bool(draft.get("problem_summary")),
            "domain_identified": bool(draft.get("domain")),
            "location_provided": bool(draft.get("location")),
            "population_identified": bool(draft.get("affected_population")),
            "timeline_recorded": bool(draft.get("timing")),
            "evidence_attached": bool(draft.get("evidence_summary") or draft.get("evidence_declined"))
        }
        progress_pct = 0 if not meaningful_messages and not has_content else int((sum(1 for v in checklist.values() if v) / 6) * 100)

        return {
            "ai_message": ai_message,
            "draft": draft,
            "checklist": checklist,
            "progress_pct": progress_pct,
            "is_ready": is_ready,
            "quick_replies": quick_replies,
            "mode": "Live AI" if os.environ.get("GEMINI_API_KEY") else "Demo AI"
        }

    @classmethod
    def get_demo_scenario(cls):
        """Provides canonical demonstration scenario for 1-click evaluation."""
        return {
            "title": "Unsafe Drinking Water Near Rural School",
            "domain": "Water Resources",
            "subdomain": "Groundwater Quality & Fluoride Remediation",
            "location": "Dumka Village School, Dumka, Jharkhand",
            "affected_population": "Approximately 120 school students and 45 nearby rural families",
            "problem_summary": "School borewell water exhibits high turbidity, reddish discoloration, and suspected heavy mineral taste causing absenteeism.",
            "evidence": "2 Photos (borewell discolored outflow & school tank)",
            "needs_verification": "Water-quality condition and chemical ppm levels have not yet been independently laboratory tested.",
            "dialogue": [
                {"role": "user", "text": "There is a water problem near our village school."},
                {"role": "ai", "text": "I can help you report this problem. Is the main issue related to drinking-water quality, water availability, contamination, infrastructure, or something else?"},
                {"role": "user", "text": "Drinking water quality."},
                {"role": "ai", "text": "Which village, town, or area is affected?"},
                {"role": "user", "text": "Dumka village school area, Dumka district."},
                {"role": "ai", "text": "Who is mainly affected?"},
                {"role": "user", "text": "Around 120 students and 45 nearby families."},
                {"role": "ai", "text": "When did you first notice the problem, and does it happen constantly or seasonally?"},
                {"role": "user", "text": "About two weeks ago, and it is continuous whenever the borewell pump runs."},
                {"role": "ai", "text": "Do you have a photo, video, document, or other evidence?"},
                {"role": "user", "text": "Yes, I have photos."},
                {"role": "ai", "text": "Please upload them using the attachment button."},
                {"role": "user", "text": "[Attached 2 Photos: Borewell Outflow & Storage Tank]"},
                {"role": "ai", "text": "I have enough information to prepare your challenge."}
            ]
        }


# =====================================================================
# 8. SERVICE LAYER (GEMINI API INTEGRATION & LOCAL FALLBACK)
# =====================================================================
class SamadhanAiService:
    """
    Clean abstraction over LLM providers (Gemini) with automatic,
    lossless fallback to the deterministic SamadhanAiEngine.
    """

    @classmethod
    def process_chat(cls, message, history, current_draft, uploaded_files=None, location_data=None):
        api_key = os.environ.get("GEMINI_API_KEY")
        if api_key:
            try:
                import urllib.request
                import urllib.error

                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
                prompt = (
                    "You are Samadhan AI, a civic problem intake assistant for the SamadhanSetu Jharkhand platform. "
                    "A citizen is explaining a societal problem in natural words. "
                    "Rule 1: If citizen says 'hi' or 'hello', respond with a warm greeting and ask what problem they are facing in their community. Never ask for location on a greeting. "
                    "Rule 2: Never repeat a question you already asked. "
                    "Rule 3: If citizen says 'I don't know' or 'skip', accept it and move to another helpful question. "
                    "Rule 4: Understand the problem first before asking for location. "
                    "Rule 5: If citizen asks a general question (e.g. your name, what is Samadhan Setu), answer politely, then invite them back to reporting. "
                    "Rule 6: If citizen corrects themselves (e.g. 'Actually I meant Dumka'), confirm the update. "
                    "When enough information is gathered, summarize: 'Let me make sure I understood you correctly... I have enough information to prepare your challenge.'\n\n"
                    f"Current Draft Context: {json.dumps(current_draft or {})}\n"
                    f"Citizen's latest message: {message}"
                )
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}]
                }
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode('utf-8'),
                    headers={'Content-Type': 'application/json'},
                    method='POST'
                )
                with urllib.request.urlopen(req, timeout=5) as response:
                    res_body = json.loads(response.read().decode('utf-8'))
                    gemini_text = res_body['candidates'][0]['content']['parts'][0]['text']
                    result = SamadhanAiEngine.process_turn(message, history, current_draft, uploaded_files, location_data)
                    result["ai_message"] = gemini_text.strip()
                    result["mode"] = "Live Gemini AI"
                    return result
            except Exception as e:
                logger.warning(f"Gemini API request failed, falling back to local engine: {e}")

        # Local deterministic AI agent execution
        return SamadhanAiEngine.process_turn(message, history, current_draft, uploaded_files, location_data)
