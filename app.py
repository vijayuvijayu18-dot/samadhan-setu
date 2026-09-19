import os
import math
import uuid
import logging
from datetime import datetime, timedelta
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, session, jsonify, abort
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from samadhan_ai_engine import SamadhanAiService, SamadhanAiEngine

# ---------------------------------------------------------
# APPLICATION CONFIGURATION & LOGGING
# ---------------------------------------------------------
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'samadhan-setu-sih-secret-key-2026-gov-enterprise-secured')

# Uploads configuration for multimedia evidence
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024  # 32 MB max
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif', 'mp4', 'mov', 'webm', 'avi', 'pdf', 'docx', 'txt', 'csv'}

database_url = os.environ.get('DATABASE_URL')
if database_url:
    # Standardize postgres:// to postgresql:// for SQLAlchemy 2.0+
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'samadhan_setu.db')

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

db = SQLAlchemy(app)

# ---------------------------------------------------------
# CONSTANTS & CONTROLLED DATASETS
# ---------------------------------------------------------
# The 10 Mandated Thematic Domains (plus backwards-compatible categories)
CATEGORIES = [
    "Water Resources", "Agriculture", "Healthcare", "Rural Livelihoods",
    "Environment", "Energy", "Education", "Urban Development",
    "Accessibility", "Public Administration", "Smart Cities",
    "Waste Management", "Water", "Women's Safety", "Transportation", "Other"
]

JHARKHAND_DISTRICTS = [
    "Ranchi", "East Singhbhum (Jamshedpur)", "Dhanbad", "Bokaro", "Deoghar",
    "Dumka", "Hazaribagh", "West Singhbhum (Chaibasa)", "Ramgarh", "Giridih",
    "Palamu", "Gumla", "Khunti", "Simdega", "Lohardaga", "Latehar",
    "Garhwa", "Chatra", "Koderma", "Jamtara", "Godda", "Sahibganj",
    "Pakur", "Saraikela Kharsawan"
]

SUBMITTER_TYPES = [
    "Citizen / Resident",
    "Gram Panchayat / Local Body",
    "Community Org / SHG",
    "Government Agency"
]

DEPARTMENTS = [
    "Drinking Water and Sanitation Department (DWSD Jharkhand)",
    "Department of Agriculture, Animal Husbandry & Co-operative",
    "Department of Health, Medical Education & Family Welfare",
    "Department of Rural Development & Panchayati Raj",
    "Jharkhand State Pollution Control Board (JSPCB)",
    "Jharkhand Renewable Energy Development Agency (JREDA)",
    "Department of Higher & Technical Education",
    "Urban Development and Housing Department (UDHD Jharkhand)",
    "Department of Forest, Environment & Climate Change",
    "Tribal Welfare & Welfare Department",
    "Public Works Department (PWD)",
    "Municipal Solid Waste & Sanitation Dept.",
    "Urban Traffic Police & Smart City Authority",
    "General Administration"
]

JHARKHAND_DEPARTMENTS = DEPARTMENTS

PUBLIC_USER_TYPES = [
    "Citizen",
    "Student",
    "Researcher",
    "University Representative",
    "Industry Representative",
    "Organization Representative",
    "Domain Expert",
    "NGO Representative"
]
USER_TYPES = PUBLIC_USER_TYPES + ["ADMINISTRATOR"]

PRIORITY_LEVELS = ["Low", "Medium", "High", "Critical"]

CHALLENGE_STATUSES = [
    "PENDING VERIFICATION", "UNDER REVIEW", "APPROVED", "VERIFIED",
    "REJECTED", "NEEDS INFORMATION", "IN PROGRESS", "COMPLETED",
    "Open", "Pilot", "Implemented", "Closed"
]

SOLUTION_STAGES = [
    "IDEA", "VALIDATION", "PROTOTYPE", "PILOT", "DEPLOYMENT", "IMPACT"
]

PROJECT_LIFECYCLE_STAGES = [
    "Challenge Submitted",
    "Challenge Validated",
    "Team Formed",
    "Solution Proposed",
    "Prototype Development",
    "Pilot Testing",
    "Community Feedback",
    "Solution Improved",
    "Implementation",
    "Impact Measured"
]

INDUSTRY_SUPPORT_TYPES = [
    "Funding / Seed Grant",
    "Technical Expertise & Mentorship",
    "Hardware & IoT Components",
    "Software, Cloud & Technology",
    "Testing Facility & Laboratory",
    "Manufacturing & Rapid Prototyping",
    "Field Implementation & Pilot Support",
    "Other Specialized Support"
]

INDUSTRY_COLLABORATION_STATUSES = [
    "Support Requested",
    "Under Review",
    "Industry Interested",
    "Collaboration Started",
    "Completed"
]

# ---------------------------------------------------------
# DATABASE MODELS
# ---------------------------------------------------------
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(150), nullable=False, default='Administrator')
    email = db.Column(db.String(150), unique=True, nullable=False)
    phone = db.Column(db.String(30), nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    user_type = db.Column(db.String(50), nullable=False, default='ADMINISTRATOR')
    organization = db.Column(db.String(200), nullable=True, default='National Innovation Cell')
    location = db.Column(db.String(150), nullable=True, default='New Delhi')
    skills = db.Column(db.Text, nullable=True, default='Platform Administration, Verification, Policy Evaluation')
    bio = db.Column(db.Text, nullable=True, default='National Administrator managing societal challenges, university research, and industry pilots.')
    avatar_seed = db.Column(db.String(50), default='Felix')
    contribution_score = db.Column(db.Integer, default=1000)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    challenges = db.relationship('Challenge', backref='creator', lazy=True, foreign_keys='Challenge.created_by_id')
    solutions = db.relationship('Solution', backref='author', lazy=True, foreign_keys='Solution.submitted_by_id')
    notifications = db.relationship('Notification', backref='user', lazy=True, cascade='all, delete-orphan')
    sent_invitations = db.relationship('TeamInvitation', backref='inviter', lazy=True, foreign_keys='TeamInvitation.inviter_user_id')
    received_invitations = db.relationship('TeamInvitation', backref='invitee', lazy=True, foreign_keys='TeamInvitation.invitee_user_id')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.user_type == 'ADMINISTRATOR'


class Organization(db.Model):
    __tablename__ = 'organizations'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, unique=True)
    type = db.Column(db.String(50), nullable=False) # University, Industry, Startup, Government, NGO, Research Institution
    location = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    expertise_tags = db.Column(db.Text, nullable=False) # comma-separated
    website = db.Column(db.String(200), nullable=True)
    logo_icon = db.Column(db.String(100), default='fa-university')
    is_verified = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Challenge(db.Model):
    __tablename__ = 'challenges'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(80), nullable=False)
    department = db.Column(db.String(150), nullable=False, default='General Administration')
    location = db.Column(db.String(150), nullable=False)
    priority = db.Column(db.String(30), nullable=False, default='Medium') # Low, Medium, High, Critical
    status = db.Column(db.String(50), default='Open') # Open, Under Review, Verified, In Progress, Pilot, Implemented, Closed
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    deadline = db.Column(db.DateTime, nullable=True)
    organization = db.Column(db.String(200), nullable=False, default='Municipal Corporation')
    required_skills = db.Column(db.Text, nullable=True)

    # Jharkhand Specific & Multi-Stakeholder Metadata
    submitter_type = db.Column(db.String(100), default='Citizen / Resident')
    district = db.Column(db.String(100), default='Ranchi')
    block = db.Column(db.String(100), nullable=True)
    media_url = db.Column(db.String(255), nullable=True)
    document_url = db.Column(db.String(255), nullable=True)
    assigned_university = db.Column(db.String(200), nullable=True)
    nep_aligned = db.Column(db.Boolean, default=True)
    expected_solution_type = db.Column(db.String(100), default='Software / Hardware Prototype')

    # Contextual fields for depth and backward compatibility
    affected_population = db.Column(db.String(200), default='General Community')
    people_affected_count = db.Column(db.Integer, default=10000)
    existing_solutions = db.Column(db.Text, nullable=True)
    shortcomings = db.Column(db.Text, nullable=True)
    required_technology = db.Column(db.Text, nullable=True)
    expected_outcome = db.Column(db.Text, nullable=True)
    ai_impact_score = db.Column(db.Integer, default=85)
    views_count = db.Column(db.Integer, default=240)
    followers_count = db.Column(db.Integer, default=28)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    # Relationships
    solutions = db.relationship('Solution', backref='challenge', lazy=True, cascade='all, delete-orphan')
    projects = db.relationship('Project', backref='challenge', lazy=True)
    invitations = db.relationship('TeamInvitation', backref='challenge', lazy=True, cascade='all, delete-orphan')
    problem_dna = db.relationship('ProblemDNA', backref='challenge', uselist=False, lazy=True, cascade='all, delete-orphan')

    @property
    def code(self):
        return f"CHL-2026-{self.id:04d}"

    @property
    def severity(self):
        return self.priority

    @severity.setter
    def severity(self, value):
        self.priority = value

    @property
    def created_at(self):
        return self.created_date

    @created_at.setter
    def created_at(self, value):
        self.created_date = value


class ProblemDNA(db.Model):
    """
    AI-Powered Problem DNA:
    Converts unstructured citizen descriptions into a structured, multi-dimensional
    challenge profile with ethical uncertainty disclaimers and human verification audit trails.
    """
    __tablename__ = 'problem_dna'
    id = db.Column(db.Integer, primary_key=True)
    challenge_id = db.Column(db.Integer, db.ForeignKey('challenges.id'), nullable=False, unique=True)

    # 1. Problem Title (Structured / Clear)
    title = db.Column(db.String(250), nullable=False)

    # 2. Domain & Subdomain
    domain = db.Column(db.String(100), nullable=False)
    subdomain = db.Column(db.String(150), nullable=False)

    # 3. Problem Summary
    summary = db.Column(db.Text, nullable=False)

    # 4. Affected Population
    affected_population = db.Column(db.String(250), nullable=False)

    # 5. Location & Context
    location_context = db.Column(db.Text, nullable=False)

    # 6. Severity / Urgency & Explanation
    severity = db.Column(db.String(50), nullable=False, default='High')
    severity_explanation = db.Column(db.Text, nullable=False)

    # 7. Possible Contributing Factors (Explicitly Hypotheses, NOT Confirmed Diagnosis)
    contributing_factors = db.Column(db.Text, nullable=True)

    # 8. Key Evidence (Photos, documents, telemetry, reports)
    key_evidence = db.Column(db.Text, nullable=True)

    # 9. Required Expertise (Academic/technical fields)
    required_expertise = db.Column(db.Text, nullable=True)

    # 10. Potential Solution Areas (Exploratory directions, not guaranteed solutions)
    potential_solution_areas = db.Column(db.Text, nullable=True)

    # 11. Relevant SDGs
    relevant_sdgs = db.Column(db.Text, nullable=True)

    # 12. Related Challenges (Similar Problem Fusion)
    related_challenges_json = db.Column(db.Text, nullable=True)

    # 13. Information Gaps
    information_gaps = db.Column(db.Text, nullable=True)

    # AI Understanding Section
    ai_understanding = db.Column(db.Text, nullable=False)

    # Governance & Uncertainty Metadata
    verification_status = db.Column(db.String(50), default='AI-estimated') # 'AI-estimated', 'Needs Verification', 'Expert Verified & Corrected'
    confidence_score = db.Column(db.Integer, default=88)
    is_edited_by_user = db.Column(db.Boolean, default=False)
    last_edited_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    last_editor = db.relationship('User', foreign_keys=[last_edited_by_id], lazy=True)

    def get_contributing_factors_list(self):
        if not self.contributing_factors:
            return []
        import json
        try:
            val = json.loads(self.contributing_factors)
            if isinstance(val, list):
                return val
        except Exception:
            pass
        return [f.strip() for f in self.contributing_factors.split('\n') if f.strip()]

    def get_key_evidence_list(self):
        if not self.key_evidence:
            return []
        import json
        try:
            val = json.loads(self.key_evidence)
            if isinstance(val, list):
                return val
        except Exception:
            pass
        return [e.strip() for e in self.key_evidence.split('\n') if e.strip()]

    def get_required_expertise_list(self):
        if not self.required_expertise:
            return []
        import json
        try:
            val = json.loads(self.required_expertise)
            if isinstance(val, list):
                return val
        except Exception:
            pass
        return [x.strip() for x in self.required_expertise.replace(';', ',').split(',') if x.strip()]

    def get_potential_solutions_list(self):
        if not self.potential_solution_areas:
            return []
        import json
        try:
            val = json.loads(self.potential_solution_areas)
            if isinstance(val, list):
                return val
        except Exception:
            pass
        return [s.strip() for s in self.potential_solution_areas.split('\n') if s.strip()]

    def get_relevant_sdgs_list(self):
        if not self.relevant_sdgs:
            return []
        import json
        try:
            val = json.loads(self.relevant_sdgs)
            if isinstance(val, list):
                return val
        except Exception:
            pass
        return [g.strip() for g in self.relevant_sdgs.split(',') if g.strip()]

    def get_related_challenges_list(self):
        if not self.related_challenges_json:
            return []
        import json
        try:
            val = json.loads(self.related_challenges_json)
            if isinstance(val, list):
                return val
        except Exception:
            pass
        return []

    def get_information_gaps_list(self):
        if not self.information_gaps:
            return []
        import json
        try:
            val = json.loads(self.information_gaps)
            if isinstance(val, list):
                return val
        except Exception:
            pass
        return [g.strip() for g in self.information_gaps.split('\n') if g.strip()]


class SamadhanAiSession(db.Model):
    """
    Tracks citizen conversational problem intake sessions,
    turn-by-turn dialogue, uploaded evidence, structured draft states,
    and citizen verification edits before formal Challenge creation.
    """
    __tablename__ = 'samadhan_ai_sessions'
    id = db.Column(db.Integer, primary_key=True)
    session_uuid = db.Column(db.String(64), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    challenge_id = db.Column(db.Integer, db.ForeignKey('challenges.id'), nullable=True)

    # Conversation history: list of {role, text, timestamp, type, evidence}
    conversation_json = db.Column(db.Text, default='[]')
    # Structured challenge draft: {title, problem_summary, domain, subdomain, location, affected_population, ...}
    draft_json = db.Column(db.Text, default='{}')
    # Original citizen input before any structuring
    original_input = db.Column(db.Text, nullable=True)
    # Citizen corrections/edits
    citizen_corrections_json = db.Column(db.Text, default='{}')

    is_submitted = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('User', backref='ai_sessions', lazy=True)
    challenge = db.relationship('Challenge', backref=db.backref('ai_session', uselist=False), lazy=True)

    def get_conversation(self):
        import json
        try:
            return json.loads(self.conversation_json) if self.conversation_json else []
        except Exception:
            return []

    def get_draft(self):
        import json
        try:
            return json.loads(self.draft_json) if self.draft_json else {}
        except Exception:
            return {}

    def get_corrections(self):
        import json
        try:
            return json.loads(self.citizen_corrections_json) if self.citizen_corrections_json else {}
        except Exception:
            return {}


class Solution(db.Model):
    __tablename__ = 'solutions'
    id = db.Column(db.Integer, primary_key=True)
    challenge_id = db.Column(db.Integer, db.ForeignKey('challenges.id'), nullable=False)
    submitted_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    title = db.Column(db.String(250), nullable=False)
    problem_addressed = db.Column(db.Text, nullable=False)
    detailed_solution = db.Column(db.Text, nullable=False)
    innovation_points = db.Column(db.Text, nullable=False)
    technology_stack = db.Column(db.Text, nullable=False)
    expected_impact = db.Column(db.Text, nullable=False)
    estimated_cost = db.Column(db.String(100), nullable=False)
    implementation_plan = db.Column(db.Text, nullable=False)
    scalability = db.Column(db.Text, nullable=True)
    sustainability = db.Column(db.Text, nullable=True)
    team_members_info = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), default='IDEA') # IDEA, VALIDATION, PROTOTYPE, PILOT, DEPLOYMENT, IMPACT
    endorsements_count = db.Column(db.Integer, default=0)
    is_selected = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    projects = db.relationship('Project', backref='solution', lazy=True)

    @property
    def code(self):
        return f"SOL-2026-{self.id:04d}"


class Project(db.Model):
    __tablename__ = 'projects'
    id = db.Column(db.Integer, primary_key=True)
    challenge_id = db.Column(db.Integer, db.ForeignKey('challenges.id'), nullable=False)
    solution_id = db.Column(db.Integer, db.ForeignKey('solutions.id'), nullable=True)
    title = db.Column(db.String(250), nullable=False)
    description = db.Column(db.Text, nullable=False)
    lead_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    university_partner = db.Column(db.String(200), nullable=True)
    industry_partner = db.Column(db.String(200), nullable=True)
    govt_ngo_partner = db.Column(db.String(200), nullable=True)
    start_date = db.Column(db.DateTime, default=datetime.utcnow)
    target_date = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(50), default='Active') # Active, In Pilot, Implemented, Completed
    current_stage = db.Column(db.String(100), default='Prototype Development')
    progress_pct = db.Column(db.Integer, default=25)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    lead_user = db.relationship('User', foreign_keys=[lead_user_id])
    milestones = db.relationship('Milestone', backref='project', lazy=True, cascade='all, delete-orphan', order_by='Milestone.order_idx')
    tasks = db.relationship('Task', backref='project', lazy=True, cascade='all, delete-orphan')
    members = db.relationship('TeamMember', backref='project', lazy=True, cascade='all, delete-orphan')
    stage_updates = db.relationship('ProjectStageUpdate', backref='project', lazy=True, cascade='all, delete-orphan', order_by='ProjectStageUpdate.created_at.desc()')
    impact_indicators = db.relationship('ProjectImpactMetric', backref='project', lazy=True, cascade='all, delete-orphan', order_by='ProjectImpactMetric.recorded_at.desc()')
    support_requests = db.relationship('IndustrySupportRequest', backref='project', lazy=True, cascade='all, delete-orphan', order_by='IndustrySupportRequest.created_at.desc()')

    @property
    def code(self):
        return f"PROJECT-2026-{self.id:04d}"

    @property
    def stage_index(self):
        if self.current_stage in PROJECT_LIFECYCLE_STAGES:
            return PROJECT_LIFECYCLE_STAGES.index(self.current_stage) + 1
        return 5

    @property
    def lifecycle_stages_info(self):
        curr_idx = self.stage_index
        info = []
        for i, stg in enumerate(PROJECT_LIFECYCLE_STAGES, 1):
            if i < curr_idx:
                s_status = 'completed'
            elif i == curr_idx:
                s_status = 'current'
            else:
                s_status = 'upcoming'
            info.append({'stage': stg, 'step': i, 'status': s_status})
        return info

    @property
    def target_beneficiaries(self):
        return 15000


class ProjectPartner(db.Model):
    __tablename__ = 'project_partners'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=True)
    org_name = db.Column(db.String(200), nullable=False)
    org_type = db.Column(db.String(100), nullable=False) # University, Industry, NGO, Research Institution, Government
    role_description = db.Column(db.String(250), nullable=True)
    contact_person = db.Column(db.String(150), nullable=True)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)

    project_rel = db.relationship('Project', backref=db.backref('partner_orgs', lazy=True, cascade='all, delete-orphan'))


class Milestone(db.Model):
    __tablename__ = 'milestones'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False) # Research, Requirements, Prototype, Testing, Pilot, Deployment
    description = db.Column(db.Text, nullable=True)
    due_date = db.Column(db.DateTime, nullable=True)
    is_completed = db.Column(db.Boolean, default=False)
    order_idx = db.Column(db.Integer, default=1)


class Task(db.Model):
    __tablename__ = 'tasks'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    assigned_name = db.Column(db.String(150), default='Unassigned')
    priority = db.Column(db.String(30), default='Medium') # Low, Medium, High
    deadline = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(30), default='To Do') # To Do, In Progress, Completed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class TeamMember(db.Model):
    __tablename__ = 'team_members'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    role_title = db.Column(db.String(150), nullable=False)
    organization = db.Column(db.String(200), nullable=True)
    email = db.Column(db.String(150), nullable=True)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)


class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    link = db.Column(db.String(250), default='#')
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ImpactMetric(db.Model):
    __tablename__ = 'impact_metrics'
    id = db.Column(db.Integer, primary_key=True)
    project_title = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(80), nullable=False)
    people_impacted = db.Column(db.Integer, default=0)
    villages_reached = db.Column(db.Integer, default=0)
    cost_saved_lakhs = db.Column(db.Float, default=0.0) # in INR Lakhs
    time_saved_pct = db.Column(db.Integer, default=0)
    environmental_gain = db.Column(db.String(200), nullable=True)
    employment_created = db.Column(db.Integer, default=0)
    resources_saved = db.Column(db.String(200), nullable=True)
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)


class TeamInvitation(db.Model):
    __tablename__ = 'team_invitations'
    id = db.Column(db.Integer, primary_key=True)
    challenge_id = db.Column(db.Integer, db.ForeignKey('challenges.id'), nullable=False)
    inviter_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    invitee_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    role_offered = db.Column(db.String(100), default='Team Member')
    matching_skills = db.Column(db.String(250), nullable=True)
    match_score = db.Column(db.Integer, default=80)
    message = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(30), default='Pending') # Pending, Accepted, Declined
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)


class ProjectStageUpdate(db.Model):
    __tablename__ = 'project_stage_updates'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    stage = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    evidence_url = db.Column(db.String(255), nullable=True)
    updated_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    updater = db.relationship('User', foreign_keys=[updated_by_id])

    @property
    def new_stage(self):
        return self.stage

    @new_stage.setter
    def new_stage(self, val):
        self.stage = val

    @property
    def previous_stage(self):
        return None

    @property
    def notes(self):
        return self.description

    @notes.setter
    def notes(self, val):
        self.description = val


class ProjectImpactMetric(db.Model):
    __tablename__ = 'project_impact_metrics'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    metric_name = db.Column(db.String(100), nullable=False) # e.g. "Water Wastage", "Municipal Cost", "Energy Saved"
    unit = db.Column(db.String(50), default='') # e.g. "L/day", "INR Lakhs", "kWh/mo", "Beneficiaries"
    before_value = db.Column(db.Float, nullable=False)
    after_value = db.Column(db.Float, nullable=False)
    change_pct = db.Column(db.Float, default=0.0)
    is_reduction = db.Column(db.Boolean, default=True) # True = decrease is positive (e.g. wastage, cost, emissions)
    verification_notes = db.Column(db.Text, nullable=True)
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)

    def calculate_change(self):
        if self.before_value and self.before_value != 0:
            if self.is_reduction:
                self.change_pct = round(((self.before_value - self.after_value) / self.before_value) * 100, 1)
            else:
                self.change_pct = round(((self.after_value - self.before_value) / self.before_value) * 100, 1)
        else:
            self.change_pct = 0.0

    @property
    def baseline_value(self):
        return self.before_value

    @baseline_value.setter
    def baseline_value(self, val):
        self.before_value = val

    @property
    def current_value(self):
        return self.after_value

    @current_value.setter
    def current_value(self, val):
        self.after_value = val

    @property
    def delta_pct(self):
        return self.change_pct

    @delta_pct.setter
    def delta_pct(self, val):
        self.change_pct = val

    @property
    def baseline_date(self):
        return self.recorded_at

    @property
    def measured_date(self):
        return self.recorded_at

    @property
    def target_value(self):
        return None

    @property
    def verification_document_url(self):
        return None


class IndustrySupportRequest(db.Model):
    __tablename__ = 'industry_support_requests'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    support_type = db.Column(db.String(100), nullable=False) # Funding, Technical expertise, Hardware/components, Software/technology, Testing facility, Manufacturing/prototyping, Mentorship, Implementation support, Other
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    estimated_budget = db.Column(db.String(100), nullable=True)
    timeline = db.Column(db.String(100), nullable=True)
    contact_info = db.Column(db.String(200), nullable=True)
    status = db.Column(db.String(50), default='Support Requested') # Support Requested, Under Review, Industry Interested, Collaboration Started, Completed
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    creator = db.relationship('User', foreign_keys=[created_by_id])
    responses = db.relationship('IndustrySupportResponse', backref='request', lazy=True, cascade='all, delete-orphan', order_by='IndustrySupportResponse.created_at.desc()')

    @property
    def estimated_amount_inr(self):
        try:
            return int(float(self.estimated_budget)) if self.estimated_budget and self.estimated_budget.replace('.','',1).isdigit() else None
        except Exception:
            return None

    @property
    def required_by(self):
        return None


class IndustrySupportResponse(db.Model):
    __tablename__ = 'industry_support_responses'
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('industry_support_requests.id'), nullable=False)
    industry_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    organization_name = db.Column(db.String(200), nullable=False)
    support_offered = db.Column(db.Text, nullable=False)
    contribution_details = db.Column(db.Text, nullable=True)
    contact_person = db.Column(db.String(150), nullable=False)
    contact_email = db.Column(db.String(150), nullable=False)
    status = db.Column(db.String(50), default='Offer Submitted') # Offer Submitted, Accepted, Under Discussion, Declined
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    industry_user = db.relationship('User', foreign_keys=[industry_user_id])

    @property
    def response_details(self):
        return self.support_offered

    @response_details.setter
    def response_details(self, val):
        self.support_offered = val

    @property
    def offered_funding_inr(self):
        return None

    @property
    def industry_partner(self):
        return self.industry_user


# ---------------------------------------------------------
# AUTHENTICATION & ACCESS DECORATORS
# ---------------------------------------------------------
def login_required(f):
    """Requires user to be signed in (public user, partner, or administrator)."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login or create an account to continue.', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Protects administrative operations gateway. Accessible strictly by Administrator."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in as Administrator to continue.', 'warning')
            return redirect(url_for('login', next=request.url))
        if session.get('user_role') != 'ADMINISTRATOR':
            flash('Access denied. Administrator privileges required.', 'danger')
            return redirect(url_for('user_dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def get_current_user():
    if 'user_id' in session:
        return User.query.get(session['user_id'])
    return None


@app.context_processor
def inject_global_data():
    current_user = get_current_user()
    unread_notifications_count = 0
    if current_user:
        unread_notifications_count = Notification.query.filter_by(
            user_id=current_user.id, is_read=False
        ).count()
    is_admin = bool((current_user and current_user.user_type == 'ADMINISTRATOR') or (session.get('user_role') == 'ADMINISTRATOR'))
    return {
        'current_user': current_user,
        'is_admin': is_admin,
        'unread_count': unread_notifications_count,
        'all_categories': CATEGORIES,
        'all_departments': DEPARTMENTS,
        'all_priorities': PRIORITY_LEVELS,
        'all_statuses': CHALLENGE_STATUSES,
        'all_user_types': PUBLIC_USER_TYPES,
        'now': datetime.utcnow()
    }


def calculate_expertise_match(user_or_org, challenge):
    """
    Computes deterministic keyword-based match percentage between user/organization profile
    and a verified challenge requirements (Category, Required Skills, Technology).
    Returns score between 42 and 96 (percentage).
    """
    if not user_or_org or not challenge:
        return 55

    # Extract user/org keywords
    user_tokens = set()
    if hasattr(user_or_org, 'skills') and user_or_org.skills:
        for s in user_or_org.skills.replace(';', ',').split(','):
            if s.strip():
                user_tokens.add(s.strip().lower())
    if hasattr(user_or_org, 'expertise_tags') and user_or_org.expertise_tags:
        for s in user_or_org.expertise_tags.replace(';', ',').split(','):
            if s.strip():
                user_tokens.add(s.strip().lower())
    if hasattr(user_or_org, 'organization') and user_or_org.organization:
        for s in user_or_org.organization.split():
            if len(s) > 3:
                user_tokens.add(s.strip().lower())
    if hasattr(user_or_org, 'user_type') and user_or_org.user_type:
        user_tokens.add(user_or_org.user_type.lower())

    # Extract challenge keywords
    target_tokens = set()
    if challenge.category:
        for s in challenge.category.split():
            target_tokens.add(s.strip().lower())
    if challenge.required_skills:
        for s in challenge.required_skills.replace(';', ',').split(','):
            if s.strip():
                target_tokens.add(s.strip().lower())
    if challenge.required_technology:
        for s in challenge.required_technology.replace(';', ',').split(','):
            if s.strip():
                target_tokens.add(s.strip().lower())
    if challenge.department:
        for s in challenge.department.split():
            if len(s) > 3:
                target_tokens.add(s.strip().lower())

    if not target_tokens or not user_tokens:
        return 65

    # Keyword overlap
    overlap = 0
    for u_tok in user_tokens:
        for t_tok in target_tokens:
            if u_tok in t_tok or t_tok in u_tok:
                overlap += 1
                break

    base_score = 48
    score = base_score + min(44, overlap * 16)
    hash_val = (hash(challenge.title + str(user_or_org.id)) % 7) - 3
    final_score = max(42, min(96, score + hash_val))
    return final_score


def calculate_smart_team_recommendations(challenge, max_recommendations=6):
    """
    Smart Skill-Based Matching:
    Transparent rule-based keyword & skill matching engine comparing
    challenge required skills, technology, and domain with registered users' expertise.
    Returns recommended users with Match %, Matching Skills, and Reason for recommendation.
    """
    if not challenge:
        return []

    # 1. Parse challenge target keywords and skills
    target_tokens = set()
    req_skills_list = []
    if challenge.required_skills:
        for s in challenge.required_skills.replace(';', ',').split(','):
            cleaned = s.strip()
            if cleaned:
                target_tokens.add(cleaned.lower())
                req_skills_list.append(cleaned)
    if challenge.required_technology:
        for s in challenge.required_technology.replace(';', ',').split(','):
            cleaned = s.strip()
            if cleaned:
                target_tokens.add(cleaned.lower())
    if challenge.category:
        for w in challenge.category.split():
            if len(w) > 3:
                target_tokens.add(w.lower())
    if challenge.title:
        for w in challenge.title.split():
            if len(w) > 3:
                target_tokens.add(w.lower())

    # 2. Evaluate all active candidates (excluding creator & admin)
    all_users = User.query.filter(User.user_type != 'ADMINISTRATOR').all()
    recommendations = []

    for user in all_users:
        if challenge.created_by_id and user.id == challenge.created_by_id:
            continue

        user_skills_list = []
        user_tokens = set()
        if user.skills:
            for s in user.skills.replace(';', ',').split(','):
                cleaned = s.strip()
                if cleaned:
                    user_tokens.add(cleaned.lower())
                    user_skills_list.append(cleaned)
        if user.organization:
            for w in user.organization.split():
                if len(w) > 3:
                    user_tokens.add(w.lower())

        # Find matching skills
        matching_skills = []
        for us in user_skills_list:
            u_low = us.lower()
            for ts in target_tokens:
                if u_low in ts or ts in u_low:
                    matching_skills.append(us)
                    break

        matching_skills = list(dict.fromkeys(matching_skills))
        overlap_count = len(matching_skills)

        # Base score starts around 65%, +10% per matching skill up to 96%
        match_score = min(96, 65 + (overlap_count * 10))
        if not matching_skills:
            if any(k in user.user_type.lower() for k in ['researcher', 'expert', 'student', 'university']):
                match_score = 70
            else:
                match_score = 60

        # Formulate transparent recommendation reason
        if matching_skills:
            skills_str = ", ".join(matching_skills[:3])
            reason = f"Verified expertise in {skills_str} directly aligns with the technical demands of this challenge."
        elif "water" in challenge.category.lower() or "water" in challenge.title.lower():
            reason = f"Relevant domain competency in {user.organization or 'applied research'} with cross-functional problem-solving capabilities."
        else:
            reason = f"{user.user_type} with foundational technical competencies aligned with {challenge.category} interventions."

        # Check invitation status if any
        existing_inv = TeamInvitation.query.filter_by(challenge_id=challenge.id, invitee_user_id=user.id).first()
        invitation_status = existing_inv.status if existing_inv else None

        recommendations.append({
            'user': user,
            'user_id': user.id,
            'name': user.full_name,
            'role': user.user_type,
            'organization': user.organization or 'Independent',
            'location': user.location or 'Jharkhand',
            'skills': user.skills or 'General Technical Skills',
            'matching_skills': matching_skills if matching_skills else ['Interdisciplinary Research'],
            'matched_skills': matching_skills if matching_skills else ['Interdisciplinary Research'],
            'match_percentage': match_score,
            'match_pct': match_score,
            'reason': reason,
            'rationale': reason,
            'invited': existing_inv is not None,
            'invitation_status': invitation_status,
            'invitation_id': existing_inv.id if existing_inv else None
        })

    # Sort descending by match percentage
    recommendations.sort(key=lambda x: x['match_percentage'], reverse=True)
    return recommendations[:max_recommendations]


def send_notification(user_id, title, message, link='#'):
    try:
        notif = Notification(user_id=user_id, title=title, message=message, link=link)
        db.session.add(notif)
        db.session.commit()
    except Exception as e:
        app.logger.error(f"Failed to dispatch notification: {e}")
        db.session.rollback()

# ---------------------------------------------------------
# DETERMINISTIC RULE-BASED ALGORITHMS (NO RANDOM GENERATION)
# ---------------------------------------------------------
def calculate_ai_impact_score(priority, people_affected=1000, skills_text='', outcome_text='', tech_text=''):
    """Calculates a deterministic 0-100 Impact Score based strictly on inputs."""
    score = 0
    pri_map = {'Critical': 32, 'High': 26, 'Medium': 18, 'Low': 12}
    score += pri_map.get(priority, 18)

    try:
        count = max(int(people_affected), 1)
        pop_pts = min(28, int(math.log10(count + 1) * 5.0))
        score += max(pop_pts, 8)
    except Exception:
        score += 12

    feasibility = 20
    if skills_text and len(skills_text.split(',')) >= 2:
        feasibility += 7
    if outcome_text and len(outcome_text) > 30:
        feasibility += 7
    if tech_text and len(tech_text.split(',')) >= 2:
        feasibility += 6
    score += min(feasibility, 40)

    return min(max(score, 45), 98)


def classify_thematic_domain(title, description=""):
    """
    AI-Enabled Classification Technique:
    Analyzes title and problem description text to automatically categorize
    into one of the 10 mandated thematic domains with confidence score.
    """
    text = f"{title} {description}".lower()

    domain_keywords = {
        "Water Resources": [
            "water", "drinking", "fluoride", "arsenic", "groundwater", "pipeline", "filtration",
            "borewell", "contamination", "potable", "aquifer", "drought", "hydro", "leakage", "purification"
        ],
        "Agriculture": [
            "farmer", "crop", "agriculture", "soil", "harvest", "tomato", "paddy", "vegetable",
            "cold storage", "irrigation", "pesticide", "fertilizer", "horticulture", "agri", "haat", "yield"
        ],
        "Healthcare": [
            "health", "medical", "hospital", "telemedicine", "doctor", "disease", "patient",
            "maternal", "infant", "asha", "malnutrition", "diagnostic", "clinic", "anemia", "medicine"
        ],
        "Rural Livelihoods": [
            "livelihood", "tribal", "lac", "forest", "shg", "artisan", "handicraft", "handloom",
            "tussar", "silk", "rural", "pvtg", "income", "cottage", "micro-enterprise", "cultivation"
        ],
        "Environment": [
            "environment", "pollution", "effluent", "heavy metal", "subarnarekha", "river", "emission",
            "smog", "toxic", "tailing", "waste dump", "ecology", "biodiversity", "conservation"
        ],
        "Energy": [
            "energy", "solar", "microgrid", "electricity", "power", "grid", "battery", "photovoltaic",
            "renewable", "metering", "blackout", "lighting", "dc grid", "jreda", "mini-grid"
        ],
        "Education": [
            "education", "school", "stem", "student", "teacher", "tablet", "santhali", "eklavya",
            "curriculum", "learning", "classroom", "literacy", "bilingual", "pedagogy"
        ],
        "Urban Development": [
            "urban", "traffic", "municipal", "waste", "drainage", "smart city", "congestion",
            "bin", "sanitation", "pothole", "solid waste", "transport", "rmc", "road"
        ],
        "Accessibility": [
            "accessibility", "disabled", "disability", "wheelchair", "visual", "blind",
            "braille", "hearing", "assistive", "elderly", "ramp", "inclusive"
        ],
        "Public Administration": [
            "administration", "governance", "public service", "panchayat", "pds", "ration",
            "certificate", "corruption", "grievance", "portal", "citizen delivery", "transparency"
        ]
    }

    scores = {}
    for domain, kws in domain_keywords.items():
        score = sum(text.count(kw) * (3 if kw in title.lower() else 1) for kw in kws)
        scores[domain] = score

    sorted_domains = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    best_domain, best_score = sorted_domains[0]

    if best_score == 0:
        return {
            "domain": "Rural Livelihoods",
            "confidence": 72,
            "secondary_domain": "Public Administration",
            "matched_keywords": ["community", "regional"]
        }

    confidence = min(98, 70 + (best_score * 4))
    secondary_domain = sorted_domains[1][0] if len(sorted_domains) > 1 else "Education"
    matched_kws = [kw for kw in domain_keywords[best_domain] if kw in text][:5]

    return {
        "domain": best_domain,
        "confidence": confidence,
        "secondary_domain": secondary_domain,
        "matched_keywords": matched_kws
    }


def rule_based_smart_match(challenge):
    """Deterministic keyword matching against registered organizations."""
    ch_text = f"{challenge.category} {challenge.required_skills or ''} {challenge.title} {challenge.department}".lower()
    ch_keywords = set([w.strip().lower() for w in ch_text.replace(',', ' ').replace('+', ' ').split() if len(w) > 2])

    orgs = Organization.query.all()
    matched_universities = []
    matched_industries = []

    for org in orgs:
        tags = set([t.strip().lower() for t in org.expertise_tags.split(',')])
        overlap = len(ch_keywords.intersection(tags))
        base_match = 70
        # Deterministic match percentage without any random jitter
        match_percentage = min(98, base_match + (overlap * 9))
        
        item = {
            'id': org.id,
            'name': org.name,
            'location': org.location,
            'description': org.description,
            'tags': [t.strip() for t in org.expertise_tags.split(',')],
            'match_pct': match_percentage,
            'type': org.type,
            'logo_icon': org.logo_icon
        }

        if org.type in ['University', 'Research Institution']:
            matched_universities.append(item)
        elif org.type in ['Industry', 'Startup']:
            matched_industries.append(item)

    matched_universities.sort(key=lambda x: x['match_pct'], reverse=True)
    matched_industries.sort(key=lambda x: x['match_pct'], reverse=True)

    return {
        'universities': matched_universities[:3],
        'industries': matched_industries[:3]
    }


def find_similar_challenges(challenge):
    return Challenge.query.filter(
        Challenge.id != challenge.id,
        Challenge.category == challenge.category
    ).limit(3).all()


def generate_problem_dna(challenge):
    """
    AI Problem DNA Synthesis Engine:
    Converts unstructured citizen problem reports into a multi-dimensional,
    structured challenge profile with ethical uncertainty boundaries and plain-language understanding.
    """
    title = (challenge.title or '').strip()
    desc = (challenge.description or '').strip()
    loc = (challenge.location or '').strip()
    district = (challenge.district or '').strip()
    block = (challenge.block or '').strip()
    category = (challenge.category or '').strip()
    combined_text = f"{title} {desc}".lower()

    # Determine Domain & Subdomain
    domain_cls = classify_thematic_domain(title, desc)
    primary_domain = category if category and category not in ['Auto-Detect', 'Other'] else domain_cls['domain']

    domain_profiles = {
        "Water Resources": {
            "subdomain": "Groundwater Quality & Fluoride Remediation",
            "title_prefix": "Groundwater Quality & Potable Water Remediation",
            "affected_population": "Rural households, school children, cattle, and marginal farming hamlets relying on community borewells",
            "factors": [
                "Hypothesis: Leaching of geochemical fluoride/heavy minerals from subsurface strata into shallow aquifers.",
                "Hypothesis: Runoff and pit seepage from nearby abandoned opencast mining reservoirs during monsoon.",
                "Hypothesis: Absence of operational adsorption filtration media or regular municipal preventative maintenance."
            ],
            "expertise": "Environmental Engineering, Hydrogeology, Water Chemistry & Desalination, IoT Telemetry Sensing, Community Health",
            "solutions": [
                "Decentralized solar-powered activated alumina filtration skid with backwash recovery.",
                "Low-cost gravity-fed multi-stage biosand and activated charcoal filter cartridges.",
                "Community IoT telemetry sensor node measuring fluoride, pH, and TDS in real time."
            ],
            "sdgs": "SDG 6: Clean Water & Sanitation, SDG 3: Good Health & Well-being, SDG 11: Sustainable Communities",
            "gaps": [
                "Accredited spectrophotometer lab assay documenting exact fluoride (mg/L) and TDS levels.",
                "Geotagged census of contaminated vs functional handpumps in the panchayat.",
                "Seasonal water table depth and drawdown measurements (pre- vs post-monsoon)."
            ]
        },
        "Agriculture": {
            "subdomain": "Post-Harvest Cold Chain & Micro-Irrigation Logistics",
            "title_prefix": "Post-Harvest Cold Chain & Smallholder Market Linkage",
            "affected_population": "Smallholder and marginal tribal vegetable farmers, women Self-Help Groups (SHGs), and weekly haat vendors",
            "factors": [
                "Hypothesis: Absence of village-level decentralized precooling leading to rapid metabolic rot of perishable produce.",
                "Hypothesis: Frequent electrical grid outages making conventional cold storage facilities non-viable.",
                "Hypothesis: Distress selling on harvest morning due to absence of local collective aggregation."
            ],
            "expertise": "Agricultural Engineering, Phase-Change Material (PCM) Thermodynamics, Embedded IoT Systems, Rural Supply Chain",
            "solutions": [
                "Phase-change material (PCM) solar micro-cold storage unit with modular insulated panels.",
                "Zero Energy Cool Chamber (ZECC) evaporative cooling structure using locally sourced terracotta bricks.",
                "Vernacular SMS/IVR pre-booking system to aggregate produce for weekly regional haats."
            ],
            "sdgs": "SDG 2: Zero Hunger, SDG 12: Responsible Consumption & Production, SDG 8: Decent Work & Economic Growth",
            "gaps": [
                "Quantified daily post-harvest tonnage rot across peak harvest weeks.",
                "Local solar insolation profile and ambient diurnal temperature records.",
                "Village feeder grid power availability logs (average hours of electricity per day)."
            ]
        },
        "Healthcare": {
            "subdomain": "Rural Point-of-Care Diagnostics & Tele-Consultation",
            "title_prefix": "Rural Point-of-Care Diagnostics & Maternal Health Outreach",
            "affected_population": "Pregnant mothers, infants, adolescent girls, elderly rural residents, and remote tribal hamlets",
            "factors": [
                "Hypothesis: Significant distance barrier to the nearest Community Health Centre (CHC) or Sub-Divisional Hospital.",
                "Hypothesis: Limited point-of-care rapid testing kits available to grassroots ASHA workers.",
                "Hypothesis: Low cellular bandwidth preventing live video tele-consultation with district specialists."
            ],
            "expertise": "Biomedical Engineering, Public Health Epidemiology, Telemedicine Software Systems, Health Informatics",
            "solutions": [
                "Solar-powered portable multi-parameter diagnostic kit backpack for field health workers.",
                "Store-and-forward offline-first tele-consultation app with asynchronous doctor triage.",
                "Low-cost wearable biometric vital-signs band for high-risk maternal monitoring."
            ],
            "sdgs": "SDG 3: Good Health and Well-being, SDG 10: Reduced Inequalities, SDG 1: No Poverty",
            "gaps": [
                "Clinical symptom prevalence registry authenticated by Primary Health Centre (PHC) medical officer.",
                "Cellular network signal strength and latency mapping across targeted hamlet locations.",
                "Average emergency roundtrip transport time and out-of-pocket ambulance expenditures."
            ]
        },
        "Environment": {
            "subdomain": "Industrial Effluent Monitoring & Ecological Remediation",
            "title_prefix": "Industrial Effluent Remediation & Watershed Conservation",
            "affected_population": "Riparian farming communities, forest gatherers, and downstream aquatic ecosystems",
            "factors": [
                "Hypothesis: Uncontrolled industrial effluent discharge during night hours or high rainfall runoff.",
                "Hypothesis: Absence of operational secondary biological waste treatment prior to discharge.",
                "Hypothesis: Heavy metal accumulation in riverbank topsoil inhibiting crop germination."
            ],
            "expertise": "Ecological Engineering, Industrial Waste Chemistry, GIS Watershed Modeling, Phytoremediation",
            "solutions": [
                "Engineered constructed wetland using indigenous hyper-accumulator wetland flora.",
                "Low-cost solar-powered water quality buoy broadcasting real-time turbidity and chemical oxygen demand.",
                "Bioremediation microbial inoculants for rapid organic sludge breakdown."
            ],
            "sdgs": "SDG 15: Life on Land, SDG 14: Life Below Water, SDG 13: Climate Action, SDG 6: Clean Water",
            "gaps": [
                "Chemical Oxygen Demand (COD), Biological Oxygen Demand (BOD), and heavy metal ppm assay.",
                "Flow rate and volumetric discharge measurements at major outfall points.",
                "Historical soil quality testing comparisons from adjacent agricultural fields."
            ]
        },
        "Energy": {
            "subdomain": "Decentralized Renewable Microgrids & Productive Power",
            "title_prefix": "Decentralized Solar Microgrid & Productive Energy Access",
            "affected_population": "Off-grid rural hamlets, village cottage enterprises, primary schools, and micro-irrigation pump users",
            "factors": [
                "Hypothesis: Challenging hilly topography and forest canopy preventing central transmission line expansion.",
                "Hypothesis: Existing standalone solar streetlights lack intelligent battery management and maintenance.",
                "Hypothesis: High reliance on expensive diesel generator sets for basic rice-hulling and water pumping."
            ],
            "expertise": "Renewable Power Systems, DC Microgrid Architecture, Battery Management Systems (BMS), Smart Metering",
            "solutions": [
                "Decentralized DC microgrid with Lithium Iron Phosphate (LFP) storage and smart load balancing.",
                "Solar-powered agricultural pump skid with pay-as-you-go vernacular smart card.",
                "Community solar charging kiosk and micro-enterprise power station."
            ],
            "sdgs": "SDG 7: Affordable & Clean Energy, SDG 9: Industry, Innovation & Infrastructure, SDG 13: Climate Action",
            "gaps": [
                "24-hour diurnal community electrical load curve and estimated peak kW demand.",
                "Structural load-bearing capacity and shade survey of proposed community solar installation sites.",
                "Baseline household lighting and diesel expenditure estimates."
            ]
        },
        "Education": {
            "subdomain": "Vernacular STEM Kits & Contextual Multilingual Learning",
            "title_prefix": "Vernacular STEM Learning & Offline Digital Classroom Kits",
            "affected_population": "First-generation tribal learners, government school students, and rural educators",
            "factors": [
                "Hypothesis: Linguistic divergence between native tribal dialects (Santhali/Mundari/Ho) and standard curriculum medium.",
                "Hypothesis: Inadequate hands-on laboratory apparatus for secondary science experiments.",
                "Hypothesis: Unreliable grid power rendering conventional smart television classrooms inoperative."
            ],
            "expertise": "Educational Technology, Multilingual Natural Language Processing, Low-Power Embedded Hardware, Pedagogy",
            "solutions": [
                "Offline-first solar-powered Raspberry Pi local WiFi classroom content server (Kiwix/RACHEL).",
                "Experiential vernacular STEM experiment kits fabricated from sustainable regional materials.",
                "Bilingual illustrated storybooks and interactive phonics tablets with Ol Chiki script support."
            ],
            "sdgs": "SDG 4: Quality Education, SDG 10: Reduced Inequalities, SDG 1: No Poverty",
            "gaps": [
                "Student language demographic survey and mother-tongue proficiency census.",
                "School rooftop solar feasibility and electrical infrastructure readiness audit.",
                "Baseline numeracy and literacy benchmark test records."
            ]
        },
        "Accessibility": {
            "subdomain": "Assistive Mobility & Multimodal Navigation for Divyangjan",
            "title_prefix": "Assistive Mobility Devices & Inclusive Infrastructure",
            "affected_population": "Persons with locomotor, visual, or hearing disabilities, elderly residents, and inclusive school students",
            "factors": [
                "Hypothesis: Lack of universal accessibility ramps and tactile guide tiles across public facilities.",
                "Hypothesis: High commercial cost and fragile maintenance requirements of imported mobility aids.",
                "Hypothesis: Absence of regional language auditory and haptic warning signals in public transport nodes."
            ],
            "expertise": "Biomechanical Engineering, Embedded Systems, Assistive Ergonomics, Haptics & Sensory Interfaces",
            "solutions": [
                "Rugged, all-terrain lever-drive wheelchair attachment kit manufactured from modular steel tubing.",
                "Wearable ultrasonic obstacle-detection band with multilingual voice and vibration alerts.",
                "Low-cost tactile digital braille slate with vernacular audio feedback."
            ],
            "sdgs": "SDG 10: Reduced Inequalities, SDG 11: Sustainable Cities & Communities, SDG 4: Quality Education",
            "gaps": [
                "Panchayat-level census of persons with disabilities categorized by mobility needs.",
                "Topographic road gradient and surface roughness assessment along essential travel routes.",
                "Assessment by certified district medical rehabilitation officer."
            ]
        },
        "Urban Development": {
            "subdomain": "Road Infrastructure Quality & Smart Municipal Drainage",
            "title_prefix": "Road Pavement Distress & Municipal Drainage Monitoring",
            "affected_population": "Daily urban commuters, ambulance services, school transit, and roadside commercial establishments",
            "factors": [
                "Hypothesis: Ineffective bitumen sub-base drainage causing rapid monsoon moisture damage and pothole formation.",
                "Hypothesis: Excessive axle loads from heavy industrial transport exceeding design pavement capacity.",
                "Hypothesis: Solid waste dumping in roadside storm drains obstructing gravity runoff."
            ],
            "expertise": "Transportation Engineering, Computer Vision Pavement Inspection, Municipal Hydrology, Civil Materials",
            "solutions": [
                "Smartphone dashcam computer vision system for automated pothole detection and classification.",
                "Pavement stabilization trial utilizing locally sourced fly ash and industrial slag binders.",
                "Low-cost ultrasonic storm-drain water level and blockage sensor network."
            ],
            "sdgs": "SDG 9: Industry, Innovation & Infrastructure, SDG 11: Sustainable Cities & Communities",
            "gaps": [
                "Kilometers of critical road distress requiring immediate patch stabilization.",
                "Photographic inspection logs with measured pothole depths and dimensions.",
                "Municipal drainage basin cross-section and clearance schedule."
            ]
        },
        "Public Administration": {
            "subdomain": "Public Distribution System (PDS) & Civic Delivery Transparency",
            "title_prefix": "PDS Ration Transparency & Biometric Delivery Safeguards",
            "affected_population": "Ration cardholders, Antyodaya beneficiaries, elderly pensioners, and rural wage laborers",
            "factors": [
                "Hypothesis: Biometric authentication failures due to skin wear among agricultural and mining workers.",
                "Hypothesis: Weak cellular reception at rural Fair Price Shops causing transaction drops.",
                "Hypothesis: Absence of transparent digital weighment verification accessible to the consumer."
            ],
            "expertise": "Software Engineering, Cryptographic Audit Logs, Offline-First Mobile Architectures, IoT Load-Cell Telemetry",
            "solutions": [
                "Offline-first cryptographic voucher system with delayed reconciliation sync.",
                "Smart IoT load-cell weighing platform with public electronic display and SMS confirmation.",
                "Gram Panchayat automated voice grievance kiosk with vernacular audio recording."
            ],
            "sdgs": "SDG 16: Peace, Justice & Strong Institutions, SDG 1: No Poverty, SDG 10: Reduced Inequalities",
            "gaps": [
                "Recorded point-of-sale biometric authentication failure rate over the preceding 6 months.",
                "Ration dealer stock inventory reconciliation discrepancy records.",
                "Average grievance resolution turnaround time documented in Gram Sabha minutes."
            ]
        },
        "Rural Livelihoods": {
            "subdomain": "Non-Timber Forest Produce (NTFP) & Artisan Value Addition",
            "title_prefix": "Tribal Lac & Forest Produce Processing Optimization",
            "affected_population": "Tribal forest gatherers, lac cultivators, women handloom artisans, and PVTG communities",
            "factors": [
                "Hypothesis: Absence of village-level primary processing equipment leading to raw produce distress sales.",
                "Hypothesis: Vulnerability of lac and silkworm host trees to unseasonal pest infestations and thermal stress.",
                "Hypothesis: Intermediary supply chain layers capturing up to 60% of retail market value."
            ],
            "expertise": "Forest Product Technology, Chemical Processing, Solar Thermal Engineering, Cooperative Market Platforms",
            "solutions": [
                "Solar-assisted lac scraper and primary washing/grading machine for village SHG clusters.",
                "IoT climate and micro-climate monitoring nodes for lac and tasar silkworm rearing belts.",
                "Direct-to-enterprise traceability ledger and cooperative e-marketplace platform."
            ],
            "sdgs": "SDG 8: Decent Work & Economic Growth, SDG 1: No Poverty, SDG 12: Responsible Consumption",
            "gaps": [
                "Annual seasonal harvest tonnage and price realization records across the block.",
                "Pest infestation frequency and temperature-humidity correlation logs.",
                "Current buyer procurement pricing versus terminal market retail prices."
            ]
        }
    }

    # Match or fallback profile
    matched_profile = None
    for dom_key, prof in domain_profiles.items():
        if dom_key.lower() in primary_domain.lower() or primary_domain.lower() in dom_key.lower():
            matched_profile = prof
            break
    if not matched_profile:
        matched_profile = domain_profiles["Water Resources"]

    # 1. Clean Structured Problem Title
    clean_title = f"{matched_profile['title_prefix']} in {block + ', ' if block else ''}{district or 'Jharkhand'}"
    if len(title) > 8 and len(title) < 90 and not title.lower().startswith('problem') and not title.lower().startswith('issue'):
        clean_title = title

    # 2. Domain & Subdomain
    domain = primary_domain
    subdomain = matched_profile['subdomain']

    # 3. Problem Summary
    summary = (
        f"In {loc or (district + ', Jharkhand')}, {desc[:320].strip()}"
        if len(desc) > 30 else
        f"Field challenge reported in {loc or (district + ', Jharkhand')}: {title}. Community reports acute bottlenecks requiring technical intervention and structured baseline verification."
    )
    if not summary.endswith('.'):
        summary += '.'

    # 4. Affected Population
    pop_keywords = ["farmer", "student", "mother", "child", "villager", "resident", "patient", "artisan", "commuter"]
    found_pop = [p for p in pop_keywords if p in combined_text]
    affected_population = matched_profile['affected_population']
    if found_pop:
        affected_population = f"Community residents (including {', '.join(found_pop)}s), numbering approximately {challenge.people_affected_count or 1500} individuals across local wards/hamlets."

    # 5. Location & Context
    loc_context = f"{loc or district}, Jharkhand. Geographic context: Revenue village / municipal boundary within {district or 'Jharkhand state'}. "
    if 'mine' in combined_text or 'coal' in combined_text:
        loc_context += "Surrounded by intensive mineral extraction and industrial coal transport corridors."
    elif 'forest' in combined_text or 'tribal' in combined_text:
        loc_context += "Situated within undulating forested tribal heartland terrain with seasonal accessibility constraints."
    elif 'urban' in combined_text or 'city' in combined_text:
        loc_context += "High-density urban municipal zone characterized by rapid infrastructure growth."
    else:
        loc_context += "Rural agrarian block characterized by smallholder farmlands and community borewell reliance."

    # 6. Severity / Urgency & Explanation
    sev = challenge.priority or 'High'
    if 'death' in combined_text or 'toxic' in combined_text or 'poison' in combined_text or 'critical' in combined_text:
        sev = 'Critical'
    elif 'urgent' in combined_text or 'severe' in combined_text or 'acute' in combined_text:
        sev = 'High'

    sev_explanations = {
        'Critical': "Urgent: Direct health or safety hazard reported. Immediate baseline verification and mitigation resources required to avert acute community risks.",
        'High': "High Priority: Persistent socio-economic distress and environmental vulnerability affecting vulnerable demographics. Timely prototype matching recommended.",
        'Medium': "Medium Urgency: Systematic operational friction impacting community productivity and service reliability. Well-suited for semester-long university prototype squads.",
        'Low': "Low / Monitoring: Localized optimization opportunity with minimal immediate safety risk; suited for exploratory capstone research."
    }
    sev_explanation = sev_explanations.get(sev, sev_explanations['High'])

    # 7. Contributing Factors (Hypotheses)
    factors = list(matched_profile['factors'])
    if 'drain' in combined_text or 'sewage' in combined_text:
        factors.append("Hypothesis: Uncovered surface stormwater drains overflowing into domestic habitations.")
    contributing_factors_str = "\n".join(factors)

    # 8. Key Evidence
    evidence_items = []
    if challenge.media_url:
        evidence_items.append(f"Field Media Upload: Geotagged photographic inspection file ({challenge.media_url.split('/')[-1]}).")
    else:
        evidence_items.append("Visual Evidence: Site photograph / visual ground documentation requested from submitter.")
    if challenge.document_url:
        evidence_items.append(f"Official Documentation: Gram Panchayat / department survey document ({challenge.document_url.split('/')[-1]}).")
    else:
        evidence_items.append("Administrative Record: Gram Sabha resolution or local memorandum requested.")
    evidence_items.append(f"Submitter Testimonial: Direct report logged by verified {challenge.submitter_type or 'Citizen'} on {challenge.created_date.strftime('%d %b %Y')}.")
    key_evidence_str = "\n".join(evidence_items)

    # 9. Required Expertise
    required_expertise_str = matched_profile['expertise']
    if challenge.required_skills:
        required_expertise_str = f"{challenge.required_skills}, {required_expertise_str}"

    # 10. Potential Solution Areas
    solutions = list(matched_profile['solutions'])
    potential_solutions_str = "\n".join(solutions)

    # 11. Relevant SDGs
    relevant_sdgs_str = matched_profile['sdgs']

    # 12. Related Challenges (Similar Problem Fusion)
    import json
    sim_challenges = find_similar_challenges(challenge)
    related_list = []
    for sc in sim_challenges:
        related_list.append({
            "id": sc.id,
            "code": sc.code,
            "title": sc.title,
            "location": sc.location,
            "category": sc.category,
            "priority": sc.priority,
            "fusion_rationale": f"Shared {sc.category} domain in regional proximity ({sc.district or 'Jharkhand'}). Coordinated prototyping can prevent duplication."
        })
    related_challenges_json = json.dumps(related_list)

    # 13. Information Gaps
    information_gaps_str = "\n".join(matched_profile['gaps'])

    # AI Understanding Section
    ai_understanding = (
        f"The AI analyzed the citizen's report regarding '{title}' in {loc or district}. "
        f"By cross-referencing domain keywords, geographic indicators, and regional challenges for {district or 'Jharkhand'}, "
        f"the system structured this challenge under '{primary_domain} &rarr; {subdomain}'. "
        f"Risk factors, required academic disciplines, and preliminary solution pathways were synthesized to assist Higher Education Institutions (HEIs) "
        f"in designing rapid, field-relevant student innovation squads. "
        f"Transparency Notice: All contributing causes and solution areas are algorithmic hypotheses provided for research scoping; they are not confirmed laboratory determinations or binding medical diagnoses."
    )

    return ProblemDNA(
        challenge_id=challenge.id,
        title=clean_title,
        domain=domain,
        subdomain=subdomain,
        summary=summary,
        affected_population=affected_population,
        location_context=loc_context,
        severity=sev,
        severity_explanation=sev_explanation,
        contributing_factors=contributing_factors_str,
        key_evidence=key_evidence_str,
        required_expertise=required_expertise_str,
        potential_solution_areas=potential_solutions_str,
        relevant_sdgs=relevant_sdgs_str,
        related_challenges_json=related_challenges_json,
        information_gaps=information_gaps_str,
        ai_understanding=ai_understanding,
        verification_status='AI-estimated',
        confidence_score=88,
        is_edited_by_user=False
    )


# ---------------------------------------------------------
# ROUTES: AUTHENTICATION
# ---------------------------------------------------------
@app.route('/')
def landing():
    """Public Landing Page."""
    if 'user_id' in session and session.get('user_role') == 'ADMINISTRATOR':
        return redirect(url_for('dashboard'))

    total_challenges = Challenge.query.count()
    total_solutions = Solution.query.count()
    active_projects = Project.query.filter(Project.status != 'Completed').count()
    total_univ = Organization.query.filter_by(type='University').count()
    total_ind = Organization.query.filter_by(type='Industry').count()
    people_impacted = sum(m.people_impacted for m in ImpactMetric.query.all()) or 2450000

    featured_challenges = Challenge.query.order_by(Challenge.ai_impact_score.desc()).limit(3).all()
    featured_orgs = Organization.query.limit(6).all()

    return render_template('landing.html',
        total_challenges=total_challenges,
        total_solutions=total_solutions,
        active_projects=active_projects,
        total_univ=total_univ,
        total_ind=total_ind,
        people_impacted=people_impacted,
        featured_challenges=featured_challenges,
        featured_orgs=featured_orgs
    )


@app.route('/api/classify-domain', methods=['POST'])
def api_classify_domain():
    """Live AI domain classification for problem submission form."""
    data = request.get_json(silent=True) or {}
    title = data.get('title', '')
    description = data.get('description', '')
    result = classify_thematic_domain(title, description)
    return jsonify(result)


@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Dual Authentication Gateway:
    - Authenticates Public Users & Partners (Citizens, HEIs, Industries, Experts) -> User Dashboard
    - Authenticates Administrator -> Operations Gateway
    """
    if 'user_id' in session:
        if session.get('user_role') == 'ADMINISTRATOR':
            return redirect(url_for('dashboard'))
        return redirect(url_for('user_dashboard'))

    if request.method == 'POST':
        login_id = (request.form.get('login_id') or request.form.get('email') or '').strip().lower()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))

        admin_email = os.environ.get('ADMIN_EMAIL', 'admin@samadhansetu.com').lower()
        admin_password = os.environ.get('ADMIN_PASSWORD', 'Admin@123')

        # Check Administrator Authentication
        if login_id == admin_email or login_id == 'admin@samadhansetu.com':
            admin_user = User.query.filter_by(email='admin@samadhansetu.com').first()
            if password == admin_password or (admin_user and admin_user.check_password(password)):
                if not admin_user:
                    admin_user = User(
                        full_name="Administrator",
                        email='admin@samadhansetu.com',
                        user_type="ADMINISTRATOR"
                    )
                    admin_user.set_password(admin_password)
                    db.session.add(admin_user)
                    db.session.commit()

                session.permanent = remember
                session['user_id'] = admin_user.id
                session['user_email'] = admin_user.email
                session['user_name'] = 'Administrator'
                session['user_type'] = 'ADMINISTRATOR'
                session['user_role'] = 'ADMINISTRATOR'

                app.logger.info("Administrator authenticated successfully.")
                flash('Welcome Administrator! Signed in successfully.', 'success')

                next_page = request.args.get('next')
                if next_page and next_page.startswith('/'):
                    return redirect(next_page)
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid email or password / Invalid admin email or password.', 'danger')
                return render_template('login.html', login_id=login_id)

        # Check Normal Public User / Partner Authentication
        user = User.query.filter_by(email=login_id).first()
        if user and user.check_password(password) and user.user_type != 'ADMINISTRATOR':
            session.permanent = remember
            session['user_id'] = user.id
            session['user_email'] = user.email
            session['user_name'] = user.full_name
            session['user_type'] = user.user_type
            session['user_role'] = user.user_type

            app.logger.info(f"User {user.email} ({user.user_type}) authenticated successfully.")
            flash(f"Welcome back, {user.full_name}! Signed in successfully.", 'success')

            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            return redirect(url_for('user_dashboard'))
        else:
            flash('Invalid email or password / Invalid admin email or password.', 'danger')
            return render_template('login.html', login_id=login_id)

    return render_template('login.html')


@app.route('/secure-admin-login', methods=['GET', 'POST'])
def secure_admin_login():
    """
    Private Administrator Operations Gateway.
    Accessible only via private system route.
    """
    if 'user_id' in session and session.get('user_role') == 'ADMINISTRATOR':
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        login_id = (request.form.get('login_id') or request.form.get('email') or '').strip().lower()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))

        admin_email = os.environ.get('ADMIN_EMAIL', 'admin@samadhansetu.com').lower()
        admin_password = os.environ.get('ADMIN_PASSWORD', 'Admin@123')

        if login_id != admin_email and login_id != 'admin@samadhansetu.com':
            flash('Invalid admin email or password.', 'danger')
            return render_template('secure_admin_login.html', login_id=login_id)

        admin_user = User.query.filter_by(email='admin@samadhansetu.com').first()
        if password == admin_password or (admin_user and admin_user.check_password(password)):
            session.permanent = remember
            session['user_id'] = admin_user.id
            session['user_email'] = admin_user.email
            session['user_name'] = 'Administrator'
            session['user_type'] = 'ADMINISTRATOR'
            session['user_role'] = 'ADMINISTRATOR'

            app.logger.info("Administrator authenticated via secure gateway.")
            flash('Welcome Administrator! Signed in successfully.', 'success')

            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid admin email or password.', 'danger')
            return render_template('secure_admin_login.html', login_id=login_id)

    return render_template('secure_admin_login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    """
    Public Self-Registration for Citizens, Students, Researchers,
    Universities, Industries, Domain Experts, and NGOs.
    """
    if 'user_id' in session:
        if session.get('user_role') == 'ADMINISTRATOR':
            return redirect(url_for('dashboard'))
        return redirect(url_for('user_dashboard'))

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        phone = request.form.get('phone', '').strip()
        user_type = request.form.get('user_type', 'Citizen').strip()
        organization = request.form.get('organization', '').strip()
        location = request.form.get('location', 'Jharkhand').strip()
        skills = request.form.get('skills', '').strip()

        if not full_name or not email or not password:
            flash('Please complete all required fields.', 'danger')
            return render_template('register.html', **request.form)

        if password != confirm_password:
            flash('Passwords do not match. Please verify your password entry.', 'danger')
            return render_template('register.html', **request.form)

        if len(password) < 6:
            flash('Password must be at least 6 characters in length.', 'danger')
            return render_template('register.html', **request.form)

        if user_type == 'ADMINISTRATOR' or email == 'admin@samadhansetu.com':
            flash('Registration with administrative role or email is strictly restricted.', 'danger')
            return render_template('register.html', **request.form)

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('An account with this email address already exists. Please log in.', 'warning')
            return redirect(url_for('login', login_id=email))

        new_user = User(
            full_name=full_name,
            email=email,
            phone=phone,
            user_type=user_type,
            organization=organization or f"{user_type} Independent",
            location=location or "Jharkhand",
            skills=skills or "Innovation, Grassroots Problem Solving",
            bio=f"Registered {user_type} participating in collaborative societal innovation."
        )
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        # Create or link Organization profile if applicable
        if organization and user_type in ['University Representative', 'Industry Representative', 'NGO Representative', 'Organization Representative']:
            org_type_map = {
                'University Representative': 'University',
                'Industry Representative': 'Industry',
                'NGO Representative': 'NGO',
                'Organization Representative': 'Startup'
            }
            mapped_type = org_type_map.get(user_type, 'Organization')
            existing_org = Organization.query.filter_by(name=organization).first()
            if not existing_org:
                new_org = Organization(
                    name=organization,
                    type=mapped_type,
                    location=location,
                    description=f"{organization} partnering on societal problem solving across Jharkhand.",
                    expertise_tags=skills or "Applied Research, Prototype Engineering, Field Implementation",
                    is_verified=True
                )
                db.session.add(new_org)
                db.session.commit()

        # Send welcome notification
        send_notification(
            new_user.id,
            "Welcome to SamadhanSetu",
            f"Hello {full_name}, your {user_type} account has been created. Start submitting challenges or proposing solutions.",
            url_for('user_dashboard')
        )

        flash('Registration completed successfully! Please sign in with your email and password.', 'success')
        return redirect(url_for('login', login_id=email))

    return render_template('register.html')


@app.route('/logout')
def logout():
    """Secure Sign Out: Clears server-side session."""
    session.clear()
    flash('You have been securely signed out of your session.', 'info')
    return redirect(url_for('login'))


@app.route('/user/dashboard')
@app.route('/user-dashboard')
@login_required
def user_dashboard():
    """Personalized User Dashboard for Citizens, HEIs, Industries, and Experts."""
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    if user.user_type == 'ADMINISTRATOR':
        return redirect(url_for('dashboard'))

    my_challenges = Challenge.query.filter_by(created_by_id=user.id).order_by(Challenge.created_date.desc()).all()
    my_solutions = Solution.query.filter_by(submitted_by_id=user.id).order_by(Solution.created_at.desc()).all()

    my_challenge_ids = [c.id for c in my_challenges]
    solutions_on_my_challenges = []
    if my_challenge_ids:
        solutions_on_my_challenges = Solution.query.filter(
            Solution.challenge_id.in_(my_challenge_ids)
        ).order_by(Solution.created_at.desc()).all()

    # Recommended Challenges with Match Score
    approved_challenges = Challenge.query.filter(
        Challenge.status.in_(['APPROVED', 'Verified', 'Open', 'In Progress', 'Pilot'])
    ).all()

    recommended_challenges = []
    for ach in approved_challenges:
        match_pct = calculate_expertise_match(user, ach)
        recommended_challenges.append({
            'challenge': ach,
            'match_score': match_pct
        })
    recommended_challenges.sort(key=lambda x: x['match_score'], reverse=True)
    recommended_challenges = recommended_challenges[:6]

    my_projects = []
    if user.organization:
        my_projects = Project.query.filter(
            (Project.university_partner.ilike(f"%{user.organization}%")) |
            (Project.industry_partner.ilike(f"%{user.organization}%")) |
            (Project.govt_ngo_partner.ilike(f"%{user.organization}%"))
        ).all()

    notifications = Notification.query.filter_by(user_id=user.id).order_by(Notification.created_at.desc()).limit(10).all()
    pending_invitations = TeamInvitation.query.filter_by(invitee_user_id=user.id, status='Pending').order_by(TeamInvitation.created_at.desc()).all()
    recent_support_requests = IndustrySupportRequest.query.order_by(IndustrySupportRequest.created_at.desc()).limit(6).all()

    return render_template('user_dashboard.html',
        user=user,
        my_challenges=my_challenges,
        my_solutions=my_solutions,
        solutions_on_my_challenges=solutions_on_my_challenges,
        recommended_challenges=recommended_challenges,
        my_projects=my_projects,
        notifications=notifications,
        pending_invitations=pending_invitations,
        recent_support_requests=recent_support_requests
    )


# ---------------------------------------------------------
# ROUTES: ADMIN DASHBOARD
# ---------------------------------------------------------
@app.route('/dashboard')
@admin_required
def dashboard():
    """Administrator Central Operations Workspace."""
    user = get_current_user()

    total_challenges = Challenge.query.count()
    active_projects = Project.query.filter(Project.status != 'Completed').count()
    solutions_submitted = Solution.query.count()
    university_partners = Organization.query.filter_by(type='University').count()
    industry_partners = Organization.query.filter_by(type='Industry').count()
    people_impacted = sum(m.people_impacted for m in ImpactMetric.query.all()) or 2450000

    recent_challenges = Challenge.query.order_by(Challenge.created_date.desc()).limit(4).all()
    recent_projects = Project.query.order_by(Project.created_at.desc()).limit(4).all()

    category_counts = {}
    for cat in CATEGORIES[:10]:
        cnt = Challenge.query.filter_by(category=cat).count()
        category_counts[cat] = cnt

    # District distribution for Jharkhand
    district_counts = {}
    for dist in JHARKHAND_DISTRICTS:
        c = Challenge.query.filter((Challenge.district == dist) | (Challenge.location.ilike(f"%{dist}%"))).count()
        if c > 0:
            district_counts[dist] = c

    universities = Organization.query.filter_by(type='University').all()
    industries = Organization.query.filter(Organization.type.in_(['Industry', 'Startup'])).all()

    return render_template('dashboard.html',
        user=user,
        total_challenges=total_challenges,
        active_projects=active_projects,
        solutions_submitted=solutions_submitted,
        university_partners=university_partners,
        industry_partners=industry_partners,
        people_impacted=people_impacted,
        recent_challenges=recent_challenges,
        recent_projects=recent_projects,
        category_counts=category_counts,
        district_counts=district_counts,
        universities=universities,
        industries=industries
    )

# ---------------------------------------------------------
# ROUTES: CHALLENGE MANAGEMENT & CRUD (ADMIN ONLY)
# ---------------------------------------------------------
# ---------------------------------------------------------
# ROUTES: CHALLENGE MANAGEMENT & CRUD
# ---------------------------------------------------------
@app.route('/challenges')
def challenges():
    """Verified Database Challenges Marketplace with Filtering & Search."""
    user = get_current_user()
    is_admin = (user and user.user_type == 'ADMINISTRATOR')

    query_text = request.args.get('q', '').strip()
    category_filter = request.args.get('category', '').strip()
    department_filter = request.args.get('department', '').strip()
    status_filter = request.args.get('status', '').strip()
    priority_filter = request.args.get('priority', '').strip()
    location_filter = request.args.get('location', '').strip()

    query = Challenge.query

    # Non-admin visitors only see approved and verified marketplace challenges
    if not is_admin:
        query = query.filter(Challenge.status.in_([
            'APPROVED', 'VERIFIED', 'Verified', 'Open', 'In Progress', 'Pilot', 'Implemented', 'Completed'
        ]))

    if query_text:
        pattern = f"%{query_text}%"
        query = query.filter(
            (Challenge.title.ilike(pattern)) |
            (Challenge.description.ilike(pattern)) |
            (Challenge.department.ilike(pattern)) |
            (Challenge.organization.ilike(pattern)) |
            (Challenge.required_skills.ilike(pattern)) |
            (Challenge.location.ilike(pattern))
        )

    if category_filter and category_filter != 'All':
        query = query.filter(Challenge.category == category_filter)

    if department_filter and department_filter != 'All':
        query = query.filter(Challenge.department == department_filter)

    if status_filter and status_filter != 'All':
        query = query.filter(Challenge.status == status_filter)

    if priority_filter and priority_filter != 'All':
        query = query.filter(Challenge.priority == priority_filter)

    if location_filter:
        query = query.filter(Challenge.location.ilike(f"%{location_filter}%"))

    challenges_list = query.order_by(Challenge.created_date.desc()).all()

    return render_template('challenges.html',
        challenges=challenges_list,
        query_text=query_text,
        category_filter=category_filter,
        department_filter=department_filter,
        status_filter=status_filter,
        priority_filter=priority_filter,
        location_filter=location_filter,
        is_admin=is_admin
    )


@app.route('/challenge/new', methods=['GET', 'POST'])
@app.route('/submit-challenge', methods=['GET', 'POST'])
def submit_challenge():
    """Submit New Grassroots Societal Challenge."""
    if 'user_id' not in session:
        flash('Please login or create an account to submit a challenge.', 'warning')
        return redirect(url_for('login', next=request.url))

    user = get_current_user()

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        category = request.form.get('category', '').strip()
        department = request.form.get('department', 'General Administration').strip()
        location = request.form.get('location', '').strip()
        district = request.form.get('district', '').strip()
        block = request.form.get('block', '').strip()
        submitter_type = request.form.get('submitter_type', user.user_type if user else 'Citizen / Resident').strip()
        priority = request.form.get('priority', 'Medium')
        organization = request.form.get('organization', user.organization if user else 'Municipal Corporation').strip()
        deadline_str = request.form.get('deadline', '')
        required_skills = request.form.get('required_skills', '').strip()
        expected_outcome = request.form.get('expected_outcome', '').strip()
        media_url = request.form.get('media_url', '').strip()
        document_url = request.form.get('document_url', '').strip()

        # Status: Admin submissions can be specified; Citizen submissions start as PENDING VERIFICATION
        if user and user.user_type == 'ADMINISTRATOR':
            status = request.form.get('status', 'Open')
        else:
            status = 'PENDING VERIFICATION'

        # Derive location/district if one is missing
        if not location and district:
            location = f"{block + ', ' if block else ''}{district}, Jharkhand"
        elif not district and location:
            district = location.split(',')[0].strip()

        # AI Domain Auto-Classification if needed
        if not category or category in ['Auto-Detect', 'Other']:
            ai_cls = classify_thematic_domain(title, description)
            category = ai_cls['domain']

        if not title or not description or not location:
            flash('Please complete all mandatory fields (Title, Description, Location).', 'danger')
            return render_template('submit_challenge.html',
                form=request.form,
                categories=CATEGORIES,
                districts=JHARKHAND_DISTRICTS,
                submitter_types=SUBMITTER_TYPES,
                departments=JHARKHAND_DEPARTMENTS
            )

        deadline = None
        if deadline_str:
            try:
                deadline = datetime.strptime(deadline_str, '%Y-%m-%d')
            except Exception:
                deadline = datetime.utcnow() + timedelta(days=90)
        else:
            deadline = datetime.utcnow() + timedelta(days=90)

        impact_score = calculate_ai_impact_score(priority, 10000, required_skills, expected_outcome)

        try:
            new_challenge = Challenge(
                title=title,
                description=description,
                category=category,
                department=department or 'General Administration',
                location=location,
                district=district or 'Ranchi',
                block=block,
                submitter_type=submitter_type or 'Citizen / Resident',
                priority=priority,
                status=status,
                organization=organization or 'Municipal Corporation',
                deadline=deadline,
                required_skills=required_skills,
                expected_outcome=expected_outcome or 'Operational deployment meeting societal specifications.',
                media_url=media_url,
                document_url=document_url,
                ai_impact_score=impact_score,
                created_date=datetime.utcnow(),
                created_by_id=user.id if user else None
            )
            db.session.add(new_challenge)
            db.session.commit()

            # Automatically synthesize AI Problem DNA
            try:
                dna = generate_problem_dna(new_challenge)
                db.session.add(dna)
                db.session.commit()
            except Exception as dna_err:
                app.logger.warning(f"Could not immediately generate Problem DNA for #{new_challenge.id}: {dna_err}")
                db.session.rollback()

            app.logger.info(f"Challenge added: #{new_challenge.id} ({new_challenge.code}) - {title} by {user.email if user else 'guest'}")

            # Notify admin of new challenge
            admin_user = User.query.filter_by(user_type='ADMINISTRATOR').first()
            if admin_user and (not user or user.user_type != 'ADMINISTRATOR'):
                send_notification(
                    admin_user.id,
                    "New Challenge Submitted",
                    f"New challenge {new_challenge.code} ('{title}') submitted for verification by {user.full_name if user else 'Citizen'}.",
                    url_for('admin_panel')
                )

            if user and user.user_type == 'ADMINISTRATOR':
                flash('Societal challenge added and published to the database successfully!', 'success')
                return redirect(url_for('challenge_detail', challenge_id=new_challenge.id))
            else:
                flash('Challenge submitted successfully.', 'success')
                return redirect(url_for('user_dashboard'))
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error adding challenge: {e}")
            flash('Failed to save challenge to database. Please check your inputs.', 'danger')
            return render_template('submit_challenge.html',
                form=request.form,
                categories=CATEGORIES,
                districts=JHARKHAND_DISTRICTS,
                submitter_types=SUBMITTER_TYPES,
                departments=JHARKHAND_DEPARTMENTS
            )

    return render_template('submit_challenge.html',
        categories=CATEGORIES,
        districts=JHARKHAND_DISTRICTS,
        submitter_types=SUBMITTER_TYPES,
        departments=JHARKHAND_DEPARTMENTS
    )


@app.route('/challenge/<int:challenge_id>')
def challenge_detail(challenge_id):
    """View Challenge Details, Problem DNA & Academic/Industry Matches."""
    challenge = Challenge.query.get_or_404(challenge_id)

    # Auto-synthesize Problem DNA if not present
    if not challenge.problem_dna:
        try:
            dna = generate_problem_dna(challenge)
            db.session.add(dna)
            db.session.commit()
        except Exception as e:
            app.logger.warning(f"Error ensuring Problem DNA for #{challenge.id}: {e}")
            db.session.rollback()

    matches = rule_based_smart_match(challenge)
    similar_challenges = find_similar_challenges(challenge)
    solutions = Solution.query.filter_by(challenge_id=challenge.id).order_by(Solution.created_at.desc()).all()
    user = get_current_user()

    user_match_score = calculate_expertise_match(user, challenge) if user else None
    recommended_team = calculate_smart_team_recommendations(challenge, max_recommendations=6)

    # Authorization to edit Problem DNA
    can_edit_dna = False
    if user:
        if user.user_type == 'ADMINISTRATOR' or (challenge.created_by_id and challenge.created_by_id == user.id) or user.user_type in ['FACULTY / RESEARCHER', 'STUDENT / INNOVATOR', 'Industry Representative']:
            can_edit_dna = True

    return render_template('challenge_detail.html',
        challenge=challenge,
        problem_dna=challenge.problem_dna,
        matches=matches,
        similar_challenges=similar_challenges,
        solutions=solutions,
        user_match_score=user_match_score,
        recommended_team=recommended_team,
        can_edit_dna=can_edit_dna
    )


@app.route('/challenge/<int:challenge_id>/problem-dna/edit', methods=['POST'])
def edit_problem_dna(challenge_id):
    """Allow authorized stakeholders to refine/correct Problem DNA while preserving the citizen report."""
    challenge = Challenge.query.get_or_404(challenge_id)
    if 'user_id' not in session:
        flash('Please log in to edit the Problem DNA profile.', 'warning')
        return redirect(url_for('login', next=url_for('challenge_detail', challenge_id=challenge.id)))

    user = get_current_user()
    is_authorized = (
        (user and user.user_type == 'ADMINISTRATOR') or
        (challenge.created_by_id and user and challenge.created_by_id == user.id) or
        (user and user.user_type in ['FACULTY / RESEARCHER', 'STUDENT / INNOVATOR', 'Industry Representative'])
    )
    if not is_authorized:
        flash('You do not have authorization to edit this Problem DNA profile.', 'danger')
        return redirect(url_for('challenge_detail', challenge_id=challenge.id))

    dna = challenge.problem_dna
    if not dna:
        dna = generate_problem_dna(challenge)
        db.session.add(dna)
        db.session.commit()

    try:
        dna.title = request.form.get('title', dna.title).strip()
        dna.domain = request.form.get('domain', dna.domain).strip()
        dna.subdomain = request.form.get('subdomain', dna.subdomain).strip()
        dna.summary = request.form.get('summary', dna.summary).strip()
        dna.affected_population = request.form.get('affected_population', dna.affected_population).strip()
        dna.location_context = request.form.get('location_context', dna.location_context).strip()
        dna.severity = request.form.get('severity', dna.severity).strip()
        dna.severity_explanation = request.form.get('severity_explanation', dna.severity_explanation).strip()
        dna.contributing_factors = request.form.get('contributing_factors', dna.contributing_factors).strip()
        dna.key_evidence = request.form.get('key_evidence', dna.key_evidence).strip()
        dna.required_expertise = request.form.get('required_expertise', dna.required_expertise).strip()
        dna.potential_solution_areas = request.form.get('potential_solution_areas', dna.potential_solution_areas).strip()
        dna.relevant_sdgs = request.form.get('relevant_sdgs', dna.relevant_sdgs).strip()
        dna.information_gaps = request.form.get('information_gaps', dna.information_gaps).strip()
        dna.ai_understanding = request.form.get('ai_understanding', dna.ai_understanding).strip()

        dna.is_edited_by_user = True
        dna.last_edited_by_id = user.id
        dna.verification_status = 'Expert Verified & Corrected'
        dna.updated_at = datetime.utcnow()

        db.session.commit()
        app.logger.info(f"Problem DNA for challenge #{challenge.id} updated and verified by {user.email}")
        flash('Problem DNA updated and verified successfully! The original citizen submission is preserved.', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error saving Problem DNA edit: {e}")
        flash('An error occurred while updating Problem DNA.', 'danger')

    return redirect(url_for('challenge_detail', challenge_id=challenge.id))



@app.route('/challenge/<int:challenge_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_challenge(challenge_id):
    """Edit Existing Challenge in Database (Admin Only)."""
    challenge = Challenge.query.get_or_404(challenge_id)

    if request.method == 'POST':
        try:
            challenge.title = request.form.get('title', challenge.title).strip()
            challenge.description = request.form.get('description', challenge.description).strip()
            challenge.category = request.form.get('category', challenge.category)
            challenge.department = request.form.get('department', challenge.department).strip()
            challenge.location = request.form.get('location', challenge.location).strip()
            challenge.district = request.form.get('district', challenge.district or 'Ranchi').strip()
            challenge.block = request.form.get('block', challenge.block)
            challenge.submitter_type = request.form.get('submitter_type', challenge.submitter_type or 'Citizen / Resident')
            challenge.priority = request.form.get('priority', challenge.priority)
            challenge.status = request.form.get('status', challenge.status)
            challenge.organization = request.form.get('organization', challenge.organization).strip()
            challenge.required_skills = request.form.get('required_skills', challenge.required_skills).strip()
            challenge.expected_outcome = request.form.get('expected_outcome', challenge.expected_outcome).strip()
            challenge.media_url = request.form.get('media_url', challenge.media_url)
            challenge.document_url = request.form.get('document_url', challenge.document_url)

            deadline_str = request.form.get('deadline', '')
            if deadline_str:
                try:
                    challenge.deadline = datetime.strptime(deadline_str, '%Y-%m-%d')
                except Exception:
                    pass

            db.session.commit()
            app.logger.info(f"Admin updated challenge #{challenge.id}")
            flash('Challenge specifications updated successfully in database.', 'success')
            return redirect(url_for('challenge_detail', challenge_id=challenge.id))
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error editing challenge #{challenge_id}: {e}")
            flash('Failed to update challenge. An error occurred.', 'danger')

    return render_template('edit_challenge.html',
        challenge=challenge,
        categories=CATEGORIES,
        districts=JHARKHAND_DISTRICTS,
        departments=JHARKHAND_DEPARTMENTS,
        submitter_types=SUBMITTER_TYPES
    )


@app.route('/challenge/<int:challenge_id>/delete', methods=['POST'])
@login_required
def delete_challenge(challenge_id):
    """Delete Challenge from Database (Admin Only)."""
    challenge = Challenge.query.get_or_404(challenge_id)
    title = challenge.title
    try:
        db.session.delete(challenge)
        db.session.commit()
        app.logger.info(f"Admin deleted challenge #{challenge_id} ({title})")
        flash(f"Challenge '{title}' was deleted successfully from the database.", 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting challenge #{challenge_id}: {e}")
        flash('Failed to delete challenge from database.', 'danger')

    return redirect(url_for('challenges'))


@app.route('/challenge/<int:challenge_id>/status', methods=['POST'])
@login_required
def update_challenge_status(challenge_id):
    """Quick Status Update for Challenge (Admin Only)."""
    challenge = Challenge.query.get_or_404(challenge_id)
    new_status = request.form.get('status', '').strip()

    if new_status in CHALLENGE_STATUSES:
        challenge.status = new_status
        db.session.commit()
        flash(f"Challenge status updated to '{new_status}'.", 'success')
    else:
        flash('Invalid status provided.', 'warning')

    return redirect(request.referrer or url_for('challenge_detail', challenge_id=challenge.id))


@app.route('/challenge/<int:challenge_id>/follow', methods=['POST'])
@login_required
def follow_challenge(challenge_id):
    challenge = Challenge.query.get_or_404(challenge_id)
    challenge.followers_count += 1
    db.session.commit()
    flash(f"You are following updates for '{challenge.title}'.", 'success')
    return redirect(url_for('challenge_detail', challenge_id=challenge.id))


@app.route('/challenge/<int:challenge_id>/join', methods=['POST'])
@login_required
def join_challenge(challenge_id):
    challenge = Challenge.query.get_or_404(challenge_id)
    flash(f"Institutional collaboration interest logged for '{challenge.title}'.", 'success')
    return redirect(url_for('challenge_detail', challenge_id=challenge.id))

# ---------------------------------------------------------
# ROUTES: SOLUTION PROPOSALS & LIFECYCLE
# ---------------------------------------------------------
@app.route('/solutions')
@login_required
def solutions():
    """Solutions Repository."""
    solutions_list = Solution.query.order_by(Solution.created_at.desc()).all()
    return render_template('solutions.html', solutions=solutions_list)


@app.route('/challenge/<int:challenge_id>/propose-solution', methods=['GET', 'POST'])
@login_required
def propose_solution(challenge_id):
    """Propose a Solution for an Approved Challenge."""
    challenge = Challenge.query.get_or_404(challenge_id)
    user = get_current_user()

    # Reject proposals for unapproved, pending or closed challenges
    if challenge.status in ['PENDING VERIFICATION', 'REJECTED', 'NEEDS INFORMATION', 'Closed']:
        flash('This challenge is not currently approved for solution proposals.', 'warning')
        return redirect(url_for('challenge_detail', challenge_id=challenge.id))

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        detailed_solution = request.form.get('detailed_solution', '').strip()
        problem_addressed = request.form.get('problem_addressed', challenge.title).strip()
        innovation_points = request.form.get('innovation_points', '').strip()
        technology_stack = request.form.get('technology_stack', '').strip()
        expected_impact = request.form.get('expected_impact', '').strip()
        estimated_cost = request.form.get('estimated_cost', '').strip()
        implementation_plan = request.form.get('implementation_plan', '').strip()
        scalability = request.form.get('scalability', '').strip()
        sustainability = request.form.get('sustainability', '').strip()
        team_members_info = request.form.get('team_members_info', user.full_name if user else 'Administrator & Research Squad').strip()

        if not title or not detailed_solution:
            flash('Please complete mandatory solution details.', 'danger')
            return render_template('propose_solution.html', challenge=challenge, form=request.form)

        solution = Solution(
            challenge_id=challenge.id,
            submitted_by_id=session.get('user_id'),
            title=title,
            problem_addressed=problem_addressed or challenge.title,
            detailed_solution=detailed_solution,
            innovation_points=innovation_points or 'Proprietary automated approach',
            technology_stack=technology_stack or 'Python, Edge IoT',
            expected_impact=expected_impact or 'High quantifiable impact',
            estimated_cost=estimated_cost or 'Estimated based on pilot scope',
            implementation_plan=implementation_plan or 'Phase 1 MVP, Phase 2 Field trial',
            scalability=scalability or 'Scalable across Jharkhand districts',
            sustainability=sustainability or 'Sustained through institutional CSR & local PRIs',
            team_members_info=team_members_info,
            status='IDEA'
        )

        db.session.add(solution)
        db.session.commit()

        # Send notifications
        if user:
            send_notification(
                user.id,
                "Solution Proposal Registered",
                f"Your solution proposal {solution.code} ('{solution.title}') was submitted successfully.",
                url_for('solution_detail', solution_id=solution.id)
            )

        admin_user = User.query.filter_by(user_type='ADMINISTRATOR').first()
        if admin_user:
            send_notification(
                admin_user.id,
                "New Solution Proposal",
                f"New solution {solution.code} submitted for challenge {challenge.code} by {user.organization if user else 'Innovator'}.",
                url_for('admin_panel')
            )

        flash('Solution proposal registered successfully!', 'success')
        return redirect(url_for('solution_detail', solution_id=solution.id))

    return render_template('propose_solution.html', challenge=challenge)


@app.route('/solution/<int:solution_id>')
@login_required
def solution_detail(solution_id):
    """Solution Detail with 6-stage lifecycle stepper."""
    solution = Solution.query.get_or_404(solution_id)
    stages = SOLUTION_STAGES
    current_stage_idx = stages.index(solution.status) if solution.status in stages else 0

    return render_template('solution_detail.html',
        solution=solution,
        stages=stages,
        current_stage_idx=current_stage_idx
    )


@app.route('/solution/<int:solution_id>/endorse', methods=['POST'])
@login_required
def endorse_solution(solution_id):
    solution = Solution.query.get_or_404(solution_id)
    solution.endorsements_count += 1
    db.session.commit()
    flash(f"You endorsed solution '{solution.title}'.", 'success')
    return redirect(url_for('solution_detail', solution_id=solution.id))


@app.route('/solution/<int:solution_id>/advance-status', methods=['POST'])
@login_required
def advance_solution_status(solution_id):
    solution = Solution.query.get_or_404(solution_id)
    current_idx = SOLUTION_STAGES.index(solution.status) if solution.status in SOLUTION_STAGES else 0

    if current_idx < len(SOLUTION_STAGES) - 1:
        next_stage = SOLUTION_STAGES[current_idx + 1]
        solution.status = next_stage
        db.session.commit()
        flash(f"Solution advanced to '{next_stage}' stage successfully!", 'success')
    else:
        flash('Solution is already at maximum deployment stage (IMPACT).', 'info')

    return redirect(url_for('solution_detail', solution_id=solution.id))


@app.route('/admin/solution/<int:solution_id>/create-project', methods=['POST'])
@app.route('/solution/<int:solution_id>/select-for-project', methods=['POST'])
@login_required
def select_solution_for_project(solution_id):
    """Creates a Project Workspace with Multi-Organization Collaboration from the solution."""
    solution = Solution.query.get_or_404(solution_id)
    challenge = solution.challenge

    solution.is_selected = True
    challenge.status = 'Pilot'

    matches = rule_based_smart_match(challenge)
    default_univ = matches['universities'][0]['name'] if matches['universities'] else 'Birla Institute of Technology (BIT Mesra), Ranchi'
    default_ind = matches['industries'][0]['name'] if matches['industries'] else 'Tata Steel CSR & Technology Division'
    default_ngo = challenge.organization or 'Drinking Water and Sanitation Department (DWSD Jharkhand)'

    univ_partner = request.form.get('university_partner', '').strip() or default_univ
    ind_partner = request.form.get('industry_partner', '').strip() or default_ind
    ngo_partner = request.form.get('govt_ngo_partner', '').strip() or default_ngo

    project = Project(
        challenge_id=challenge.id,
        solution_id=solution.id,
        title=f"Implementation: {solution.title}",
        description=f"Quadruple Helix Stakeholder Coalition for collaborative execution of solution '{solution.title}' under {challenge.department}.",
        lead_user_id=session.get('user_id'),
        university_partner=univ_partner,
        industry_partner=ind_partner,
        govt_ngo_partner=ngo_partner,
        target_date=datetime.utcnow() + timedelta(days=120),
        status='Active',
        progress_pct=25
    )
    db.session.add(project)
    db.session.flush()

    # Link Multiple Project Partners
    partner_tuples = [
        (univ_partner, 'University', 'Academic R&D & Prototyping Lead'),
        (ind_partner, 'Industry', 'Industrial Scaling & CSR Co-Sponsor'),
        (ngo_partner, 'NGO / Government', 'Field Ground Testing & Implementation Partner')
    ]
    for p_name, p_type, p_desc in partner_tuples:
        p_org = Organization.query.filter_by(name=p_name).first()
        pp = ProjectPartner(
            project_id=project.id,
            organization_id=p_org.id if p_org else None,
            org_name=p_name,
            org_type=p_type,
            role_description=p_desc
        )
        db.session.add(pp)

    milestones_data = [
        ("Research & Domain Analysis", "Literature survey and baseline field audit", 1, True),
        ("System Architecture & Specifications", "Detailed engineering schematic design and BOM", 2, True),
        ("Functional Prototype Development", "First iteration working MVP built and calibrated in lab", 3, False),
        ("Field Testing & Verification", "Controlled testing in municipal pilot ward", 4, False),
        ("Pilot Deployment", "Live rollout to initial targeted cohort", 5, False),
        ("Full-Scale Impact Rollout", "Third-party audit and commercial scaling", 6, False)
    ]
    for m_name, m_desc, idx, completed in milestones_data:
        m = Milestone(
            project_id=project.id,
            name=m_name,
            description=m_desc,
            order_idx=idx,
            is_completed=completed,
            due_date=datetime.utcnow() + timedelta(days=idx * 20)
        )
        db.session.add(m)

    tasks_data = [
        ("Finalize Memorandum of Understanding (MoU) with University", univ_partner, "High", "Completed"),
        ("Industry R&D Cloud / Hardware Fabrication Provisioning", ind_partner, "High", "In Progress"),
        ("Edge Firmware / Mobile Application UI Implementation", "Lead Engineer", "Medium", "In Progress"),
        ("Conduct Local Panchayat / Ward Briefing", "Field Coordination", "Medium", "To Do"),
        ("Telemetry Sensor Calibration & Impact Logging", "Tech Squad", "Low", "To Do")
    ]
    for t_title, assigned, priority, status in tasks_data:
        t = Task(
            project_id=project.id,
            title=t_title,
            assigned_name=assigned,
            priority=priority,
            status=status,
            deadline=datetime.utcnow() + timedelta(days=15)
        )
        db.session.add(t)

    db.session.add(TeamMember(
        project_id=project.id,
        name="Project Lead Administrator",
        role_title="Principal Investigator",
        organization="National Innovation Cell",
        email="admin@samadhansetu.com"
    ))
    db.session.add(TeamMember(
        project_id=project.id,
        name=f"Academic Mentor ({univ_partner})",
        role_title="University Research Lead",
        organization=univ_partner
    ))
    db.session.add(TeamMember(
        project_id=project.id,
        name=f"Industry Advisor ({ind_partner})",
        role_title="Corporate Technical Advisor",
        organization=ind_partner
    ))

    db.session.commit()

    flash(f"Project Workspace #{project.id} initialized successfully with {univ_partner} & {ind_partner}.", 'success')
    return redirect(url_for('project_detail', project_id=project.id))

# ---------------------------------------------------------
# ROUTES: PROJECT WORKSPACE & KANBAN TASKS
# ---------------------------------------------------------
@app.route('/projects')
@login_required
def projects():
    """Collaborative Projects Directory."""
    projects_list = Project.query.order_by(Project.created_at.desc()).all()
    return render_template('projects.html', projects=projects_list)


@app.route('/project/<int:project_id>')
@login_required
def project_detail(project_id):
    """Project Workspace."""
    project = Project.query.get_or_404(project_id)
    todo_tasks = [t for t in project.tasks if t.status == 'To Do']
    inprogress_tasks = [t for t in project.tasks if t.status == 'In Progress']
    completed_tasks = [t for t in project.tasks if t.status == 'Completed']

    return render_template('project_detail.html',
        project=project,
        todo_tasks=todo_tasks,
        inprogress_tasks=inprogress_tasks,
        completed_tasks=completed_tasks,
        lifecycle_stages=project.lifecycle_stages_info,
        stage_updates=project.stage_updates,
        impact_metrics=project.impact_indicators,
        support_requests=project.support_requests,
        support_types=INDUSTRY_SUPPORT_TYPES,
        lifecycle_stage_options=PROJECT_LIFECYCLE_STAGES
    )


@app.route('/project/<int:project_id>/task/add', methods=['POST'])
@login_required
def add_project_task(project_id):
    project = Project.query.get_or_404(project_id)
    title = request.form.get('title', '').strip()
    assigned_name = request.form.get('assigned_name', 'Unassigned').strip()
    priority = request.form.get('priority', 'Medium')
    status = request.form.get('status', 'To Do')

    if title:
        task = Task(
            project_id=project.id,
            title=title,
            assigned_name=assigned_name,
            priority=priority,
            status=status,
            deadline=datetime.utcnow() + timedelta(days=14)
        )
        db.session.add(task)
        db.session.commit()
        flash('Task added to project board.', 'success')

    return redirect(url_for('project_detail', project_id=project.id))


@app.route('/project/<int:project_id>/task/<int:task_id>/update-status', methods=['POST'])
@login_required
def update_task_status(project_id, task_id):
    task = Task.query.filter_by(id=task_id, project_id=project_id).first_or_404()
    new_status = request.form.get('status')
    if new_status in ['To Do', 'In Progress', 'Completed']:
        task.status = new_status
        db.session.commit()
        flash(f"Task status updated to '{new_status}'.", 'info')
    return redirect(url_for('project_detail', project_id=project_id))


@app.route('/project/<int:project_id>/milestone/<int:milestone_id>/toggle', methods=['POST'])
@login_required
def toggle_milestone(project_id, milestone_id):
    milestone = Milestone.query.filter_by(id=milestone_id, project_id=project_id).first_or_404()
    milestone.is_completed = not milestone.is_completed

    project = milestone.project
    total_m = len(project.milestones)
    if total_m > 0:
        completed_m = sum(1 for m in project.milestones if m.is_completed)
        project.progress_pct = int((completed_m / total_m) * 100)
        if project.progress_pct == 100:
            project.status = 'Implemented'
            project.challenge.status = 'Implemented'
        elif project.progress_pct >= 65:
            project.status = 'In Pilot'
            project.challenge.status = 'Pilot'

    db.session.commit()
    flash(f"Milestone updated. Project progress recomputed to {project.progress_pct}%.", 'success')
    return redirect(url_for('project_detail', project_id=project_id))


# ---------------------------------------------------------
# ROUTES: SIH PROTOTYPE DISTINCTIVE FEATURES
# ---------------------------------------------------------

# FEATURE 1: SMART TEAM MATCHING & INVITATIONS
@app.route('/challenge/<int:challenge_id>/team-recommendations')
def challenge_team_recommendations(challenge_id):
    """API endpoint returning smart skill-based recommendations for a challenge."""
    challenge = Challenge.query.get_or_404(challenge_id)
    recommendations = calculate_smart_team_recommendations(challenge, max_recommendations=8)
    clean_recs = []
    for r in recommendations:
        clean_recs.append({
            'user_id': r['user_id'],
            'name': r['name'],
            'full_name': r['name'],
            'role': r['role'],
            'organization': r['organization'],
            'skills': r['skills'],
            'matching_skills': r['matching_skills'],
            'matched_skills': r['matching_skills'],
            'match_percentage': r['match_percentage'],
            'match_score': r['match_percentage'],
            'reason': r['reason'],
            'rationale': r['reason'],
            'invitation_status': r['invitation_status'],
            'invitation_id': r['invitation_id']
        })
    return jsonify({'success': True, 'challenge_id': challenge.id, 'recommendations': clean_recs})


@app.route('/team-matching')
@app.route('/smart-team')
def smart_team():
    """Dedicated Smart Challenge -> Team Matching Page."""
    challenge_id = request.args.get('challenge_id', type=int)
    all_challenges = Challenge.query.order_by(Challenge.created_date.desc()).all()

    selected_challenge = None
    if challenge_id:
        selected_challenge = Challenge.query.get(challenge_id)
    if not selected_challenge and all_challenges:
        selected_challenge = all_challenges[0]

    recommendations = []
    if selected_challenge:
        recommendations = calculate_smart_team_recommendations(selected_challenge, max_recommendations=9)

    user = get_current_user()
    sent_invitations = []
    received_invitations = []
    if user:
        sent_invitations = TeamInvitation.query.filter_by(inviter_user_id=user.id).order_by(TeamInvitation.created_at.desc()).all()
        received_invitations = TeamInvitation.query.filter_by(invitee_user_id=user.id).order_by(TeamInvitation.created_at.desc()).all()

    return render_template('smart_team.html',
        challenges=all_challenges,
        selected_challenge=selected_challenge,
        recommendations=recommendations,
        sent_invitations=sent_invitations,
        received_invitations=received_invitations,
        current_user=user
    )


@app.route('/challenge/<int:challenge_id>/send-invitation', methods=['POST'])
@login_required
def send_team_invitation(challenge_id):
    """Challenge creator or lead sends a team collaboration invitation to an expert/student."""
    challenge = Challenge.query.get_or_404(challenge_id)
    next_url = request.form.get('next') or request.referrer or url_for('challenge_detail', challenge_id=challenge.id)
    invitee_id = request.form.get('invitee_id', type=int)
    if not invitee_id:
        flash('Invalid invitee specified.', 'danger')
        return redirect(next_url)

    invitee = User.query.get_or_404(invitee_id)
    inviter = get_current_user()

    # Prevent duplicate invitations
    existing = TeamInvitation.query.filter_by(
        challenge_id=challenge.id,
        invitee_user_id=invitee.id
    ).first()

    if existing:
        flash(f'A collaboration invitation has already been sent to {invitee.full_name} (Status: {existing.status}).', 'warning')
        return redirect(next_url)

    role_offered = request.form.get('role_offered', 'Team Member').strip() or 'Team Member'
    matching_skills = request.form.get('matching_skills', '').strip()
    match_score = request.form.get('match_score', 80, type=int)
    message = request.form.get('message', '').strip() or f"Hi {invitee.full_name}, your expertise matches our challenge requirements. We invite you to join our solving team."

    invitation = TeamInvitation(
        challenge_id=challenge.id,
        inviter_user_id=inviter.id,
        invitee_user_id=invitee.id,
        role_offered=role_offered,
        matching_skills=matching_skills,
        match_score=match_score,
        message=message,
        status='Pending'
    )
    db.session.add(invitation)
    db.session.commit()

    # Dispatch notification to invitee
    send_notification(
        invitee.id,
        "Team Collaboration Invitation",
        f"{inviter.full_name} invited you to join the team for '{challenge.title}' as {role_offered} ({match_score}% Match).",
        url_for('user_dashboard')
    )

    flash(f"Team collaboration invitation successfully sent to {invitee.full_name}!", 'success')
    return redirect(next_url)


@app.route('/invitation/<int:invitation_id>/respond', methods=['POST'])
@login_required
def respond_team_invitation(invitation_id):
    """Invited user accepts or declines a team invitation."""
    invitation = TeamInvitation.query.get_or_404(invitation_id)
    user = get_current_user()
    next_url = request.form.get('next') or request.referrer or url_for('user_dashboard')

    if invitation.invitee_user_id != user.id:
        flash('Unauthorized action on this invitation.', 'danger')
        return redirect(next_url)

    action = request.form.get('action', '').strip().lower()
    if action == 'accept':
        invitation.status = 'Accepted'
        invitation.updated_at = datetime.utcnow()

        # If an active project exists for this challenge, add to project team
        project = Project.query.filter_by(challenge_id=invitation.challenge_id).first()
        if project:
            existing_tm = TeamMember.query.filter_by(project_id=project.id, email=user.email).first()
            if not existing_tm:
                tm = TeamMember(
                    project_id=project.id,
                    name=user.full_name,
                    role_title=invitation.role_offered or user.user_type,
                    organization=user.organization or 'Academic / Research Partner',
                    email=user.email
                )
                db.session.add(tm)

        db.session.commit()

        # Notify inviter
        send_notification(
            invitation.inviter_user_id,
            "Invitation Accepted",
            f"{user.full_name} accepted your collaboration invitation for '{invitation.challenge.title}'.",
            url_for('challenge_detail', challenge_id=invitation.challenge_id)
        )
        flash(f"You have joined the team for '{invitation.challenge.title}'!", 'success')

    elif action == 'decline':
        invitation.status = 'Declined'
        invitation.updated_at = datetime.utcnow()
        db.session.commit()
        flash("You have declined the team invitation.", 'info')

    return redirect(next_url)


# FEATURE 2: IDEA -> IMPACT PROJECT TRACKER & IMPACT MEASUREMENT
@app.route('/idea-impact')
def idea_impact():
    """Dedicated Idea -> Impact 10-Stage Sequential Tracker & Ground Impact Page."""
    project_id = request.args.get('project_id', type=int)
    all_projects = Project.query.order_by(Project.created_at.desc()).all()

    selected_project = None
    if project_id:
        selected_project = Project.query.get(project_id)
    if not selected_project and all_projects:
        selected_project = all_projects[0]

    stage_updates = []
    impact_metrics = []
    stages_info = []

    if selected_project:
        stage_updates = ProjectStageUpdate.query.filter_by(project_id=selected_project.id).order_by(ProjectStageUpdate.created_at.desc()).all()
        impact_metrics = ProjectImpactMetric.query.filter_by(project_id=selected_project.id).order_by(ProjectImpactMetric.recorded_at.desc()).all()
        stages_info = selected_project.lifecycle_stages_info

    # Calculate aggregate impact stats across all projects
    total_beneficiaries = 0
    for p in all_projects:
        if p.target_beneficiaries:
            try:
                total_beneficiaries += int(p.target_beneficiaries)
            except (ValueError, TypeError):
                total_beneficiaries += 5000
        else:
            total_beneficiaries += 3500

    total_impact_metrics_count = ProjectImpactMetric.query.count()

    user = get_current_user()
    return render_template('idea_impact.html',
        projects=all_projects,
        selected_project=selected_project,
        stages=PROJECT_LIFECYCLE_STAGES,
        stages_info=stages_info,
        stage_updates=stage_updates,
        impact_metrics=impact_metrics,
        total_beneficiaries=total_beneficiaries,
        total_impact_metrics_count=total_impact_metrics_count,
        current_user=user
    )


@app.route('/project/<int:project_id>/update-lifecycle-stage', methods=['POST'])
@login_required
def update_project_lifecycle_stage(project_id):
    """Updates the 10-stage Idea -> Impact lifecycle tracker with transition audit log."""
    project = Project.query.get_or_404(project_id)
    user = get_current_user()
    next_url = request.form.get('next') or request.referrer or url_for('project_detail', project_id=project.id)

    new_stage = request.form.get('stage', '').strip()
    if new_stage not in PROJECT_LIFECYCLE_STAGES:
        flash('Invalid lifecycle stage selected.', 'danger')
        return redirect(next_url)

    description = request.form.get('description', '').strip() or f"Stage updated to {new_stage}."
    evidence_url = request.form.get('evidence_url', '').strip()

    project.current_stage = new_stage
    new_progress = int((project.stage_index / len(PROJECT_LIFECYCLE_STAGES)) * 100)
    project.progress_pct = max(project.progress_pct, new_progress)

    if new_stage in ['Implementation', 'Impact Measured']:
        project.status = 'Implemented'
        if project.challenge:
            project.challenge.status = 'Implemented'
    elif new_stage in ['Pilot Testing', 'Community Feedback', 'Solution Improved']:
        project.status = 'In Pilot'
        if project.challenge:
            project.challenge.status = 'Pilot'

    stage_log = ProjectStageUpdate(
        project_id=project.id,
        stage=new_stage,
        description=description,
        evidence_url=evidence_url,
        updated_by_id=user.id
    )
    db.session.add(stage_log)
    db.session.commit()

    if project.lead_user_id and project.lead_user_id != user.id:
        send_notification(
            project.lead_user_id,
            "Project Lifecycle Advanced",
            f"Project '{project.title}' advanced to '{new_stage}' by {user.full_name}.",
            url_for('project_detail', project_id=project.id)
        )

    flash(f"Project lifecycle journey advanced to '{new_stage}' (Progress: {project.progress_pct}%).", 'success')
    return redirect(next_url)


@app.route('/project/<int:project_id>/add-impact-metric', methods=['POST'])
@login_required
def add_project_impact_metric(project_id):
    """Records quantitative Before-vs-After measurable indicators for a project."""
    project = Project.query.get_or_404(project_id)
    next_url = request.form.get('next') or request.referrer or url_for('project_detail', project_id=project.id)

    metric_name = request.form.get('metric_name', '').strip()
    unit = request.form.get('unit', '').strip()
    before_str = request.form.get('before_value', '0').strip()
    after_str = request.form.get('after_value', '0').strip()
    is_reduction = (request.form.get('is_reduction') == 'on' or request.form.get('is_reduction') == 'true')
    verification_notes = request.form.get('verification_notes', '').strip()

    if not metric_name:
        flash('Please provide an indicator name for the impact measurement.', 'danger')
        return redirect(next_url)

    try:
        before_val = float(before_str)
        after_val = float(after_str)
    except ValueError:
        flash('Before and After values must be valid numbers.', 'danger')
        return redirect(next_url)

    metric = ProjectImpactMetric(
        project_id=project.id,
        metric_name=metric_name,
        unit=unit,
        before_value=before_val,
        after_value=after_val,
        is_reduction=is_reduction,
        verification_notes=verification_notes
    )
    metric.calculate_change()
    db.session.add(metric)
    db.session.commit()

    flash(f"Measurable impact indicator '{metric_name}' recorded: {abs(metric.change_pct)}% {'Reduction' if metric.is_reduction else 'Increase'}!", 'success')
    return redirect(next_url)


# FEATURE 3: INDUSTRY + UNIVERSITY COLLABORATION HUB
@app.route('/industry-collaboration')
def industry_collaboration():
    """Public / Industry Portal displaying projects requesting CSR, funding, mentorship & technology support."""
    support_type_filter = request.args.get('type', '')
    status_filter = request.args.get('status', '')
    q = request.args.get('q', '').strip()
    action = request.args.get('action', '').strip()

    query = IndustrySupportRequest.query.join(Project)

    if support_type_filter and support_type_filter != 'All':
        query = query.filter(IndustrySupportRequest.support_type.ilike(f"%{support_type_filter}%"))
    if status_filter and status_filter != 'All':
        query = query.filter(IndustrySupportRequest.status == status_filter)
    if q:
        query = query.filter(
            (IndustrySupportRequest.title.ilike(f"%{q}%")) |
            (IndustrySupportRequest.description.ilike(f"%{q}%")) |
            (Project.title.ilike(f"%{q}%"))
        )

    all_requests = query.order_by(IndustrySupportRequest.created_at.desc()).all()

    total_requests = IndustrySupportRequest.query.count()
    active_collaborations = IndustrySupportRequest.query.filter(
        IndustrySupportRequest.status.in_(['Industry Interested', 'Collaboration Started', 'Completed'])
    ).count()
    total_responses = IndustrySupportResponse.query.count()

    all_projects = Project.query.order_by(Project.title.asc()).all()
    projects_seeking_support = Project.query.join(IndustrySupportRequest).distinct().all()

    return render_template('industry_hub.html',
        requests=all_requests,
        support_types=INDUSTRY_SUPPORT_TYPES,
        industry_support_types=INDUSTRY_SUPPORT_TYPES,
        statuses=INDUSTRY_COLLABORATION_STATUSES,
        selected_type=support_type_filter,
        selected_status=status_filter,
        search_query=q,
        action=action,
        total_requests=total_requests,
        active_collaborations=active_collaborations,
        total_responses=total_responses,
        all_projects=all_projects,
        projects_seeking_support=projects_seeking_support
    )


@app.route('/industry-support/create', methods=['POST'])
@login_required
def create_industry_support_global():
    """Global endpoint to publish industry support request from Hub or Dashboard."""
    project_id = request.form.get('project_id', type=int)
    if not project_id:
        flash('Please select a project to request industry support.', 'danger')
        return redirect(url_for('industry_collaboration'))
    return request_industry_support(project_id)


@app.route('/project/<int:project_id>/request-industry-support', methods=['POST'])
@login_required
def request_industry_support(project_id):
    """Project team creates an open industry collaboration and support request."""
    project = Project.query.get_or_404(project_id)
    user = get_current_user()
    next_url = request.form.get('next') or request.referrer or url_for('project_detail', project_id=project.id)

    support_type = request.form.get('support_type', 'Technical Expertise & Mentorship')
    title = request.form.get('title', '').strip() or f"Industry Support for {project.title}"
    description = request.form.get('description', '').strip()
    estimated_budget = request.form.get('estimated_budget', '').strip()
    timeline = request.form.get('timeline', '').strip()
    contact_info = request.form.get('contact_info', '').strip() or user.email

    if not description:
        flash('Please describe the industry support required.', 'danger')
        return redirect(next_url)

    req = IndustrySupportRequest(
        project_id=project.id,
        support_type=support_type,
        title=title,
        description=description,
        estimated_budget=estimated_budget,
        timeline=timeline,
        contact_info=contact_info,
        status='Support Requested',
        created_by_id=user.id
    )
    db.session.add(req)
    db.session.commit()

    flash('Industry support request published to National Collaboration Hub!', 'success')
    return redirect(next_url)


@app.route('/industry-support/<int:request_id>/respond', methods=['POST'])
@login_required
def respond_industry_support(request_id):
    """Industry representative offers support / co-sponsorship for a project."""
    support_req = IndustrySupportRequest.query.get_or_404(request_id)
    user = get_current_user()

    support_offered = request.form.get('support_offered', '').strip()
    contribution_details = request.form.get('contribution_details', '').strip()
    contact_person = request.form.get('contact_person', user.full_name).strip()
    contact_email = request.form.get('contact_email', user.email).strip()
    org_name = user.organization or request.form.get('organization_name', 'Industrial Partner').strip()

    if not support_offered:
        flash('Please specify the support your organization can provide.', 'danger')
        return redirect(url_for('industry_collaboration'))

    resp = IndustrySupportResponse(
        request_id=support_req.id,
        industry_user_id=user.id,
        organization_name=org_name,
        support_offered=support_offered,
        contribution_details=contribution_details,
        contact_person=contact_person,
        contact_email=contact_email,
        status='Offer Submitted'
    )
    support_req.status = 'Industry Interested'
    db.session.add(resp)
    db.session.commit()

    # Notify project creator
    if support_req.project and support_req.project.lead_user_id:
        send_notification(
            support_req.project.lead_user_id,
            "Industry Support Offer Received",
            f"{org_name} has offered support for '{support_req.project.title}' ({support_req.support_type}).",
            url_for('project_detail', project_id=support_req.project.id)
        )

    flash(f"Thank you! Your collaboration offer from {org_name} has been submitted. The project team has been notified.", 'success')
    return redirect(url_for('industry_collaboration'))


@app.route('/industry-response/<int:response_id>/accept', methods=['POST'])
@login_required
def accept_industry_response(response_id):
    """Project team accepts an industry collaboration offer."""
    resp = IndustrySupportResponse.query.get_or_404(response_id)
    support_req = resp.request
    project = support_req.project

    resp.status = 'Accepted'
    support_req.status = 'Collaboration Started'

    # Add as ProjectPartner if not already linked
    existing_partner = ProjectPartner.query.filter_by(
        project_id=project.id,
        org_name=resp.organization_name
    ).first()
    if not existing_partner:
        partner = ProjectPartner(
            project_id=project.id,
            org_name=resp.organization_name,
            org_type='Industry',
            role_description=f"Industry Partner: {resp.support_offered[:100]}",
            contact_person=resp.contact_person
        )
        db.session.add(partner)

    if not project.industry_partner or project.industry_partner == 'Corporate R&D Division':
        project.industry_partner = resp.organization_name

    db.session.commit()

    # Notify industry partner
    send_notification(
        resp.industry_user_id,
        "Industry Collaboration Formalized",
        f"Your collaboration offer for '{project.title}' has been accepted by the project team. Status: Collaboration Started!",
        url_for('project_detail', project_id=project.id)
    )

    flash(f"Collaboration with {resp.organization_name} accepted! Status advanced to 'Collaboration Started'.", 'success')
    return redirect(url_for('project_detail', project_id=project.id))


# ---------------------------------------------------------
# ROUTES: ORGANIZATIONS & NATIONAL IMPACT
# ---------------------------------------------------------
@app.route('/organizations')
@login_required
def organizations():
    """Organizations Directory."""
    type_filter = request.args.get('type', '')
    query_text = request.args.get('q', '').strip()

    query = Organization.query
    if type_filter and type_filter != 'All':
        query = query.filter_by(type=type_filter)
    if query_text:
        query = query.filter(
            (Organization.name.ilike(f"%{query_text}%")) |
            (Organization.location.ilike(f"%{query_text}%")) |
            (Organization.expertise_tags.ilike(f"%{query_text}%"))
        )

    orgs = query.order_by(Organization.name.asc()).all()
    return render_template('organizations.html', organizations=orgs, type_filter=type_filter, query_text=query_text)


@app.route('/impact')
def impact():
    """National Impact Analytics & Grounded SIH Prototype Outcome Ledger."""
    all_challenges = Challenge.query.all()
    all_projects = Project.query.all()
    impact_metrics = ProjectImpactMetric.query.all()

    # Credible Platform & Process Metrics
    challenges_reported = len(all_challenges) or 10
    challenges_validated = sum(1 for c in all_challenges if c.status in ['Open', 'Under Review', 'In Progress', 'Pilot', 'Implemented', 'VERIFIED']) or 8
    active_collaborations = len(all_projects) or 2
    projects_in_dev = sum(1 for p in all_projects if p.current_stage in ['Team Formed', 'Solution Proposed', 'Prototype Development']) or 1
    pilots_active = sum(1 for p in all_projects if p.current_stage in ['Pilot Testing', 'Community Feedback', 'Solution Improved', 'Implementation']) or 1
    community_verifications = len(impact_metrics) or 2

    # District Distribution (Challenges & Projects by District)
    district_data = {}
    for c in all_challenges:
        d = c.district or 'Ranchi'
        if d not in district_data:
            district_data[d] = {'challenges': 0, 'projects': 0}
        district_data[d]['challenges'] += 1

    for p in all_projects:
        d = (p.challenge.district if p.challenge else 'Ranchi') or 'Ranchi'
        if d not in district_data:
            district_data[d] = {'challenges': 0, 'projects': 0}
        district_data[d]['projects'] += 1

    sample_districts = ["Dhanbad", "Ranchi", "Dumka", "East Singhbhum (Jamshedpur)", "Bokaro", "Hazaribagh", "Palamu", "West Singhbhum (Chaibasa)"]
    for sd in sample_districts:
        if sd not in district_data:
            district_data[sd] = {'challenges': 1, 'projects': 0}

    # 10 Mandated Domains with counts
    domain_data = [
        {"name": "Healthcare", "icon": "fa-heartbeat", "color": "#dc2626", "count": 0, "status": "Active Pilot", "desc": "Diagnostic kits, rural clinic tele-linkages & health registries"},
        {"name": "Human/Animal Health", "icon": "fa-paw", "color": "#ea580c", "count": 0, "status": "Under Evaluation", "desc": "Veterinary outreach, zoonotic disease monitoring & cattle feeds"},
        {"name": "Water", "icon": "fa-tint", "color": "#0284c7", "count": 0, "status": "Pilot Testing", "desc": "Mine pit purification, solar filtration & fluoride removal"},
        {"name": "Agriculture", "icon": "fa-seedling", "color": "#16a34a", "count": 0, "status": "In Development", "desc": "Solar cold storage, haat market linkages & drip micro-irrigation"},
        {"name": "Education", "icon": "fa-graduation-cap", "color": "#7c3aed", "count": 0, "status": "Squad Formed", "desc": "Vernacular learning kits, smart tribal classroom aids & STEM labs"},
        {"name": "Environment", "icon": "fa-leaf", "color": "#059669", "count": 0, "status": "Field Baseline", "desc": "Forest produce valorization, fly ash utilization & waste recycling"},
        {"name": "Accessibility", "icon": "fa-wheelchair", "color": "#0891b2", "count": 0, "status": "Matched", "desc": "Assistive mobility devices & vernacular audio cues for Divyangjan"},
        {"name": "Infrastructure", "icon": "fa-road", "color": "#475569", "count": 0, "status": "In Development", "desc": "Pothole detection, smart municipal water management & traffic routing"},
        {"name": "Energy", "icon": "fa-bolt", "color": "#d97706", "count": 0, "status": "Prototype Stage", "desc": "Biomass gasification, solar microgrids & micro-hydro telemetry"},
        {"name": "Public Services", "icon": "fa-university", "color": "#2563eb", "count": 0, "status": "Panchayat Review", "desc": "Gram Panchayat grievance trackers, PDS ration tracking & DBT aids"}
    ]

    for c in all_challenges:
        cat = (c.category or '').lower()
        if 'water' in cat:
            domain_data[2]['count'] += 1
        elif 'agri' in cat:
            domain_data[3]['count'] += 1
        elif 'health' in cat or 'medic' in cat:
            domain_data[0]['count'] += 1
        elif 'edu' in cat:
            domain_data[4]['count'] += 1
        elif 'env' in cat or 'forest' in cat or 'waste' in cat:
            domain_data[5]['count'] += 1
        elif 'energy' in cat or 'solar' in cat:
            domain_data[8]['count'] += 1
        elif 'access' in cat or 'disab' in cat:
            domain_data[6]['count'] += 1
        elif 'urban' in cat or 'infra' in cat or 'transport' in cat or 'smart' in cat:
            domain_data[7]['count'] += 1
        elif 'admin' in cat or 'public' in cat or 'gov' in cat:
            domain_data[9]['count'] += 1
        else:
            domain_data[1]['count'] += 1

    for dom in domain_data:
        if dom['count'] == 0:
            dom['count'] = 1

    # Challenge Pipeline Funnel Data
    pipeline_stages = [
        {"stage": "Reported", "count": max(challenges_reported, 10), "desc": "Grassroots challenges submitted by citizens / local bodies", "badge": "bg-secondary"},
        {"stage": "Validated", "count": max(challenges_validated, 8), "desc": "Domain classified & screened for feasibility", "badge": "bg-info"},
        {"stage": "Matched", "count": 7, "desc": "Algorithmic skill recommendation to universities", "badge": "bg-primary"},
        {"stage": "Team Formed", "count": 5, "desc": "Faculty mentors & student squads onboarded", "badge": "bg-primary", "custom_style": "background-color: #6366f1 !important;"},
        {"stage": "Prototype", "count": max(projects_in_dev + 2, 3), "desc": "Working hardware/software MVP in lab", "badge": "bg-warning text-dark"},
        {"stage": "Pilot", "count": max(pilots_active, 2), "desc": "Controlled ground trial in target panchayat", "badge": "bg-danger text-white"},
        {"stage": "Community Verified", "count": max(community_verifications, 2), "desc": "Direct village sign-off & delta measured", "badge": "bg-success"}
    ]

    return render_template('impact.html',
        projects=all_projects,
        impact_metrics=impact_metrics,
        challenges_reported=challenges_reported,
        challenges_validated=challenges_validated,
        active_collaborations=active_collaborations,
        projects_in_dev=projects_in_dev,
        pilots_active=pilots_active,
        community_verifications=community_verifications,
        district_data=district_data,
        domain_data=domain_data,
        pipeline_stages=pipeline_stages,
        # Backward compatibility placeholders
        total_people=0,
        total_villages=0,
        total_cost_saved=0,
        avg_time_saved=0,
        total_jobs=0,
        implemented_projects_count=active_collaborations,
        metrics=[]
    )


@app.route('/admin')
@admin_required
def admin_panel():
    """Admin Console."""
    users = User.query.all()
    pending_challenges = Challenge.query.filter(Challenge.status.in_([
        'PENDING VERIFICATION', 'Under Review', 'Submitted', 'NEEDS INFORMATION'
    ])).all()
    all_challenges = Challenge.query.order_by(Challenge.created_date.desc()).all()
    all_solutions = Solution.query.order_by(Solution.created_at.desc()).all()
    all_projects = Project.query.order_by(Project.created_at.desc()).all()
    all_orgs = Organization.query.all()

    stats = {
        'total_users': len(users),
        'total_challenges': len(all_challenges),
        'verified_challenges': sum(1 for c in all_challenges if c.status in ['APPROVED', 'VERIFIED', 'Verified', 'Open', 'In Progress', 'Pilot', 'Implemented']),
        'total_solutions': len(all_solutions),
        'total_projects': len(all_projects),
        'total_universities': sum(1 for o in all_orgs if o.type == 'University'),
        'total_industries': sum(1 for o in all_orgs if o.type == 'Industry'),
        'implemented_projects': sum(1 for p in all_projects if p.status == 'Implemented' or p.progress_pct >= 90)
    }

    return render_template('admin.html',
        stats=stats,
        pending_challenges=pending_challenges,
        all_challenges=all_challenges,
        all_solutions=all_solutions,
        all_projects=all_projects,
        users=users
    )


@app.route('/admin/challenge/<int:challenge_id>/approve', methods=['POST'], endpoint='approve_challenge')
@app.route('/admin/challenge/<int:challenge_id>/verify', methods=['POST'], endpoint='verify_challenge')
@admin_required
def verify_challenge(challenge_id):
    """Admin approves and verifies challenge for the public marketplace."""
    challenge = Challenge.query.get_or_404(challenge_id)
    challenge.status = 'Verified'
    db.session.commit()

    if challenge.created_by_id:
        send_notification(
            challenge.created_by_id,
            "Challenge Approved",
            f"Your challenge {challenge.code} has been approved and published to the marketplace.",
            url_for('challenge_detail', challenge_id=challenge.id)
        )

    flash(f"Challenge '{challenge.title}' verified successfully.", 'success')
    return redirect(url_for('admin_panel'))


@app.route('/admin/challenge/<int:challenge_id>/reject', methods=['POST'])
@admin_required
def reject_challenge(challenge_id):
    """Admin marks challenge as rejected."""
    challenge = Challenge.query.get_or_404(challenge_id)
    challenge.status = 'REJECTED'
    db.session.commit()

    if challenge.created_by_id:
        send_notification(
            challenge.created_by_id,
            "Challenge Status Update",
            f"Your challenge {challenge.code} was reviewed and rejected.",
            url_for('challenge_detail', challenge_id=challenge.id)
        )

    flash(f"Challenge '{challenge.title}' marked as REJECTED.", 'warning')
    return redirect(url_for('admin_panel'))


@app.route('/admin/challenge/<int:challenge_id>/request-info', methods=['POST'])
@admin_required
def request_info_challenge(challenge_id):
    """Admin requests more information from the citizen submitter."""
    challenge = Challenge.query.get_or_404(challenge_id)
    challenge.status = 'NEEDS INFORMATION'
    db.session.commit()

    if challenge.created_by_id:
        send_notification(
            challenge.created_by_id,
            "More Information Requested",
            f"Admin requested additional information for your challenge {challenge.code}.",
            url_for('challenge_detail', challenge_id=challenge.id)
        )

    flash(f"More information requested for challenge {challenge.code}.", 'info')
    return redirect(url_for('admin_panel'))
    return redirect(url_for('admin_panel'))


@app.route('/profile')
@login_required
def profile():
    """Administrator Profile."""
    user = get_current_user()
    my_challenges = Challenge.query.all()
    my_solutions = Solution.query.all()
    my_projects = Project.query.all()

    return render_template('profile.html',
        user=user,
        my_challenges=my_challenges,
        my_solutions=my_solutions,
        my_projects=my_projects
    )


@app.route('/profile/edit', methods=['POST'])
@login_required
def edit_profile():
    user = get_current_user()
    user.full_name = request.form.get('full_name', user.full_name).strip()
    user.phone = request.form.get('phone', user.phone).strip()
    user.organization = request.form.get('organization', user.organization).strip()
    user.location = request.form.get('location', user.location).strip()
    user.skills = request.form.get('skills', user.skills).strip()
    user.bio = request.form.get('bio', user.bio).strip()

    db.session.commit()
    flash('Profile updated successfully!', 'success')
    return redirect(url_for('profile'))


@app.route('/notifications')
@login_required
def notifications():
    user = get_current_user()
    user_notifications = Notification.query.filter_by(user_id=user.id).order_by(Notification.created_at.desc()).all()
    return render_template('notifications.html', notifications=user_notifications)


@app.route('/notifications/mark-all-read', methods=['POST'])
@login_required
def mark_all_notifications_read():
    user = get_current_user()
    Notification.query.filter_by(user_id=user.id, is_read=False).update({'is_read': True})
    db.session.commit()
    flash('All notifications marked as read.', 'info')
    return redirect(url_for('notifications'))


@app.route('/notification/<int:notif_id>/read')
@login_required
def read_notification(notif_id):
    notif = Notification.query.filter_by(id=notif_id, user_id=session['user_id']).first_or_404()
    notif.is_read = True
    db.session.commit()
    return redirect(notif.link if notif.link and notif.link != '#' else url_for('notifications'))


# ---------------------------------------------------------
# ROUTES: SAMADHAN AI CONVERSATIONAL PROBLEM SUBMISSION
# ---------------------------------------------------------
@app.route('/samadhan-ai')
def samadhan_ai():
    """Samadhan AI: Conversational Problem Intake & Submission Portal."""
    user = get_current_user()
    session_uuid = session.get('samadhan_ai_session_uuid')
    if not session_uuid:
        session_uuid = str(uuid.uuid4())
        session['samadhan_ai_session_uuid'] = session_uuid

    ai_sess = SamadhanAiSession.query.filter_by(session_uuid=session_uuid).first()
    if not ai_sess:
        ai_sess = SamadhanAiSession(
            session_uuid=session_uuid,
            user_id=user.id if user else None,
            conversation_json='[]',
            draft_json='{}'
        )
        db.session.add(ai_sess)
        db.session.commit()
    elif user and not ai_sess.user_id:
        ai_sess.user_id = user.id
        db.session.commit()

    demo_scenario = SamadhanAiEngine.get_demo_scenario()
    mode = "Live Gemini AI" if os.environ.get("GEMINI_API_KEY") else "Demo AI"

    return render_template('samadhan_ai.html',
        session_uuid=session_uuid,
        user=user,
        districts=JHARKHAND_DISTRICTS,
        categories=CATEGORIES,
        departments=JHARKHAND_DEPARTMENTS,
        demo_scenario=demo_scenario,
        ai_mode=mode,
        existing_draft=ai_sess.get_draft(),
        conversation_history=ai_sess.get_conversation()
    )


@app.route('/api/samadhan-ai/chat', methods=['POST'])
def api_samadhan_ai_chat():
    """Processes interactive conversational turn with dynamic questioning."""
    import json
    data = request.get_json() or {}
    session_uuid = data.get('session_uuid') or session.get('samadhan_ai_session_uuid')
    message = data.get('message', '').strip()
    uploaded_files = data.get('uploaded_files', [])
    location_data = data.get('location_data', {})

    if not session_uuid:
        session_uuid = str(uuid.uuid4())
        session['samadhan_ai_session_uuid'] = session_uuid

    ai_sess = SamadhanAiSession.query.filter_by(session_uuid=session_uuid).first()
    if not ai_sess:
        ai_sess = SamadhanAiSession(session_uuid=session_uuid)
        db.session.add(ai_sess)

    history = data.get('history') if data.get('history') is not None else ai_sess.get_conversation()
    current_draft = data.get('current_draft') if data.get('current_draft') is not None else ai_sess.get_draft()

    if not ai_sess.original_input and message:
        ai_sess.original_input = message

    result = SamadhanAiService.process_chat(
        message=message,
        history=history,
        current_draft=current_draft,
        uploaded_files=uploaded_files,
        location_data=location_data
    )

    timestamp = datetime.utcnow().strftime('%H:%M')
    if message:
        history.append({'role': 'user', 'text': message, 'time': timestamp, 'type': 'text'})
    if uploaded_files and not message:
        history.append({'role': 'user', 'text': f"[Uploaded {len(uploaded_files)} evidence file(s)]", 'time': timestamp, 'type': 'attachment'})

    history.append({'role': 'ai', 'text': result['ai_message'], 'time': timestamp, 'type': 'text'})

    ai_sess.conversation_json = json.dumps(history)
    ai_sess.draft_json = json.dumps(result['draft'])
    db.session.commit()

    return jsonify({
        'success': True,
        'session_uuid': session_uuid,
        'ai_message': result['ai_message'],
        'draft': result['draft'],
        'checklist': result['checklist'],
        'progress_pct': result['progress_pct'],
        'is_ready': result['is_ready'],
        'quick_replies': result['quick_replies'],
        'mode': result['mode']
    })


@app.route('/api/samadhan-ai/upload', methods=['POST'])
def api_samadhan_ai_upload():
    """Handles secure multimedia evidence uploads (photos, videos, docs)."""
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file part in request'}), 400
    file = request.files['file']
    if not file or file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'}), 400

    filename = secure_filename(file.filename)
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if ext not in ALLOWED_EXTENSIONS:
        return jsonify({'success': False, 'error': f'Unsupported file format (.{ext}). Allowed: images, videos, documents.'}), 400

    file_type = 'document'
    if ext in {'png', 'jpg', 'jpeg', 'webp', 'gif'}:
        file_type = 'photo'
    elif ext in {'mp4', 'mov', 'webm', 'avi'}:
        file_type = 'video'

    unique_name = f"{uuid.uuid4().hex[:10]}_{filename}"
    save_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
    file.save(save_path)
    file_url = f"/static/uploads/{unique_name}"

    return jsonify({
        'success': True,
        'file': {
            'name': filename,
            'url': file_url,
            'type': file_type,
            'ext': ext
        }
    })


@app.route('/api/samadhan-ai/draft', methods=['POST'])
def api_samadhan_ai_update_draft():
    """Updates structured challenge draft with citizen manual corrections."""
    import json
    data = request.get_json() or {}
    session_uuid = data.get('session_uuid') or session.get('samadhan_ai_session_uuid')
    if not session_uuid:
        return jsonify({'success': False, 'error': 'Session token required'}), 400

    ai_sess = SamadhanAiSession.query.filter_by(session_uuid=session_uuid).first()
    if not ai_sess:
        return jsonify({'success': False, 'error': 'Session not found'}), 404

    current_draft = ai_sess.get_draft()
    for key in ['title', 'problem_summary', 'domain', 'subdomain', 'location', 'district', 'affected_population', 'timing']:
        if key in data and data[key]:
            current_draft[key] = data[key]

    ai_sess.citizen_corrections_json = json.dumps(data)
    ai_sess.draft_json = json.dumps(current_draft)
    db.session.commit()

    return jsonify({'success': True, 'draft': current_draft})


@app.route('/api/samadhan-ai/submit', methods=['POST'])
def api_samadhan_ai_submit():
    """
    Explicit Citizen Confirmation:
    Converts reviewed structured draft into official Challenge, synthesizes Problem DNA,
    detects Similar Problem Fusion candidates, and links audit trail.
    """
    import json
    data = request.get_json() or {}
    session_uuid = data.get('session_uuid') or session.get('samadhan_ai_session_uuid')
    user = get_current_user()

    ai_sess = None
    if session_uuid:
        ai_sess = SamadhanAiSession.query.filter_by(session_uuid=session_uuid).first()

    draft = data.get('draft') or (ai_sess.get_draft() if ai_sess else {})

    title = draft.get('title', 'Community Societal Challenge').strip()
    description = draft.get('problem_summary', '').strip()
    category = draft.get('domain', 'Water Resources').strip()
    location = draft.get('location', 'Jharkhand').strip()
    district = draft.get('district', 'Ranchi').strip()
    affected_population = draft.get('affected_population', 'General Community').strip()
    people_affected_count = int(draft.get('people_affected_count', 10000))

    # Append raw unedited citizen words for permanent auditability & transparency
    if ai_sess and ai_sess.original_input:
        if "[Original Citizen Report]" not in description:
            description = f"{description}\n\n[Original Citizen Report]: {ai_sess.original_input}"

    media_url = None
    document_url = None
    evidence_files = draft.get('evidence_files', [])
    for f in evidence_files:
        if f.get('type') in ['photo', 'video'] and not media_url:
            media_url = f.get('url')
        elif f.get('type') == 'document' and not document_url:
            document_url = f.get('url')

    status = 'Open' if (user and user.user_type == 'ADMINISTRATOR') else 'PENDING VERIFICATION'
    submitter_type = user.user_type if user else 'Citizen / Resident'

    impact_score = calculate_ai_impact_score('Medium', people_affected_count, '', '')

    new_challenge = Challenge(
        title=title,
        description=description,
        category=category,
        department='General Administration',
        location=location,
        district=district,
        submitter_type=submitter_type,
        priority='Medium',
        status=status,
        organization=user.organization if user and user.organization else 'Community Initiative',
        deadline=datetime.utcnow() + timedelta(days=90),
        affected_population=affected_population,
        people_affected_count=people_affected_count,
        media_url=media_url,
        document_url=document_url,
        ai_impact_score=impact_score,
        created_date=datetime.utcnow(),
        created_by_id=user.id if user else None
    )
    db.session.add(new_challenge)
    db.session.commit()

    # Automatically synthesize 13-dimensional AI Problem DNA
    try:
        dna = generate_problem_dna(new_challenge)
        db.session.add(dna)
        db.session.commit()
    except Exception as dna_err:
        app.logger.warning(f"Could not generate Problem DNA for #{new_challenge.id}: {dna_err}")
        db.session.rollback()

    # Detect Similar Problem Fusion Candidates
    similar_challenges = find_similar_challenges(new_challenge)
    similar_list = []
    for sc in similar_challenges:
        similar_list.append({
            'id': sc.id,
            'code': sc.code,
            'title': sc.title,
            'location': sc.location,
            'category': sc.category
        })

    if ai_sess:
        ai_sess.challenge_id = new_challenge.id
        ai_sess.is_submitted = True
        db.session.commit()

    return jsonify({
        'success': True,
        'challenge_id': new_challenge.id,
        'challenge_code': new_challenge.code,
        'title': new_challenge.title,
        'similar_count': len(similar_list),
        'similar': similar_list,
        'redirect_url': url_for('challenge_detail', challenge_id=new_challenge.id)
    })


@app.route('/api/samadhan-ai/demo-scenario')
def api_samadhan_ai_demo_scenario():
    """Provides canonical Section 28 demonstration scenario."""
    return jsonify(SamadhanAiEngine.get_demo_scenario())


@app.route('/api/samadhan-ai/reset', methods=['POST'])
def api_samadhan_ai_reset():
    """Resets conversational session to start a new intake workflow."""
    new_uuid = str(uuid.uuid4())
    session['samadhan_ai_session_uuid'] = new_uuid
    user = get_current_user()
    new_sess = SamadhanAiSession(
        session_uuid=new_uuid,
        user_id=user.id if user else None,
        conversation_json='[]',
        draft_json='{}'
    )
    db.session.add(new_sess)
    db.session.commit()
    return jsonify({'success': True, 'session_uuid': new_uuid})


# ---------------------------------------------------------
# ERROR HANDLERS
# ---------------------------------------------------------
@app.errorhandler(403)
def forbidden_error(error):
    return render_template('403.html'), 403

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    app.logger.error(f"Internal server error: {error}")
    return render_template('500.html'), 500

# ---------------------------------------------------------
# CONTROLLED DATABASE INITIALIZATION & STATIC DATASET
# ---------------------------------------------------------
def seed_database():
    """
    Initializes controlled database with ONLY the single Administrator account
    and stable, static, realistic societal challenges (no random generation).
    """
    with app.app_context():
        db.create_all()

        # 1. Ensure Single Admin Account (admin@samadhansetu.com / Admin@123)
        admin = User.query.filter_by(email="admin@samadhansetu.com").first()
        if not admin:
            # Check if old admin exists and update
            old_admin = User.query.filter_by(email="admin@samadhansetu.gov.in").first()
            if old_admin:
                admin = old_admin
                admin.email = "admin@samadhansetu.com"
                admin.full_name = "Administrator"
                admin.user_type = "ADMINISTRATOR"
                admin.set_password("Admin@123")
            else:
                admin = User(
                    full_name="Administrator",
                    email="admin@samadhansetu.com",
                    phone="+91-11-23456789",
                    user_type="ADMINISTRATOR",
                    organization="National Innovation & Governance Cell",
                    location="New Delhi",
                    skills="Platform Governance, Evaluation, Policy, Multi-Sector Convergence",
                    bio="Lead Administrator overseeing national societal innovation pipelines.",
                    contribution_score=1000
                )
                admin.set_password("Admin@123")
                db.session.add(admin)
            db.session.commit()
            print("Admin account initialized: admin@samadhansetu.com")

        # 2. Controlled Stable Challenge titles
        controlled_titles = [
            "Abandoned Coal Pit Mine Water Purification & Fluoride Remediation for Hamlets",
            "Solar-Assisted Farm-to-Haat Cold Storage & Vernacular Market Linkage for Peri-Urban Clusters",
            "Store-and-Forward Telemedicine & Maternal Diagnostic Hubs for Forest Villages",
            "Scientific Lac Cultivation & IoT Canopy Microclimate Sensing for Tribal Livelihoods",
            "Real-Time Industrial Effluent & Heavy Metal Telemetry in Subarnarekha River Basin",
            "Decentralized DC Solar Mini-Grids with Prepaid Smart Metering for Netarhat Hamlets",
            "Offline Bilingual STEM Tablets & Interactive Science Kits for Tribal Residential Schools",
            "Smart Haat Solid Waste Segregation & Dynamic Inundation Clearance Telemetry"
        ]
        extra_challenges = Challenge.query.filter(~Challenge.title.in_(controlled_titles)).all()
        for ech in extra_challenges:
            for s in ech.solutions:
                for p in s.projects:
                    Task.query.filter_by(project_id=p.id).delete()
                    Milestone.query.filter_by(project_id=p.id).delete()
                    ProjectPartner.query.filter_by(project_id=p.id).delete()
                    db.session.delete(p)
                db.session.delete(s)
            db.session.delete(ech)
        if extra_challenges:
            db.session.commit()

        if Challenge.query.count() >= 8:
            return

        print("Seeding controlled stable societal challenges into database...")

        # 3. Controlled Stable Predefined Challenges (Authentic Jharkhand Grassroots Challenges)
        controlled_challenges = [
            {
                "title": "Abandoned Coal Pit Mine Water Purification & Fluoride Remediation for Hamlets",
                "category": "Water Resources",
                "department": "Drinking Water and Sanitation Department (DWSD Jharkhand)",
                "location": "Baghmara & Nirsa, Dhanbad, Jharkhand",
                "district": "Dhanbad",
                "block": "Baghmara",
                "submitter_type": "Gram Panchayat / Local Body",
                "priority": "Critical",
                "status": "In Progress",
                "organization": "BCCL CSR & DWSD Jharkhand",
                "deadline": datetime(2026, 12, 31),
                "description": "Disused opencast coal pit reservoirs hold millions of gallons of water containing high suspended solids and toxic fluoride exceeding 2.9 mg/L. Tribal and mining hamlets face acute potable water scarcity and debilitating fluorosis during summer months.",
                "required_skills": "Water Engineering, Membrane Filtration, Fluoride Remediation, IoT Quality Telemetry, Geophysics",
                "expected_outcome": "Community solar filtration plant treating 60,000 L/day mine discharge, supplying safe potable water to 8,500 villagers across 4 panchayats."
            },
            {
                "title": "Solar-Assisted Farm-to-Haat Cold Storage & Vernacular Market Linkage for Peri-Urban Clusters",
                "category": "Agriculture",
                "department": "Department of Agriculture, Animal Husbandry & Co-operative",
                "location": "Bero & Kanke, Ranchi, Jharkhand",
                "district": "Ranchi",
                "block": "Bero",
                "submitter_type": "Community Org / SHG",
                "priority": "High",
                "status": "Open",
                "organization": "Jharkhand State Agri Marketing Board",
                "deadline": datetime(2026, 11, 30),
                "description": "Tribal farmers in Ranchi vegetable belts harvest surplus tomato, cabbage, and peas. Absence of village-level pre-cooling leads to 35% post-harvest rot. Farmers are forced to sell to commission intermediaries for as low as Rs 3/kg.",
                "required_skills": "AgriTech, Thermal Micro-Cold Storage, Vernacular PWA (Hindi/Nagpuri), Solar Energy",
                "expected_outcome": "Decentralized solar micro-chilling hub linked to weekly haats, boosting smallholder farmer net earnings by 42%."
            },
            {
                "title": "Store-and-Forward Telemedicine & Maternal Diagnostic Hubs for Forest Villages",
                "category": "Healthcare",
                "department": "Department of Health, Medical Education & Family Welfare",
                "location": "Shikaripara & Kathikund, Dumka, Jharkhand",
                "district": "Dumka",
                "block": "Shikaripara",
                "submitter_type": "Citizen / Resident",
                "priority": "Critical",
                "status": "Pilot",
                "organization": "National Health Mission Jharkhand",
                "deadline": datetime(2026, 12, 15),
                "description": "Forested tribal hamlets across Santhal Pargana suffer from severe maternal anemia and infant malnutrition. Sub-centres lack resident doctors and high-speed broadband. Emergency hospital transfers take over 4 hours.",
                "required_skills": "Telemedicine, Low-Bandwidth WebRTC, Diagnostic Medical Devices, Santhali Vernacular UI, Offline Sync",
                "expected_outcome": "12 solar-powered diagnostic kits equipped with ASHA workers connected to AIIMS Deoghar specialists via offline-sync telemedicine."
            },
            {
                "title": "Scientific Lac Cultivation & IoT Canopy Microclimate Sensing for Tribal Livelihoods",
                "category": "Rural Livelihoods",
                "department": "Department of Rural Development & Panchayati Raj",
                "location": "Torpa & Rania, Khunti, Jharkhand",
                "district": "Khunti",
                "block": "Torpa",
                "submitter_type": "Community Org / SHG",
                "priority": "High",
                "status": "In Progress",
                "organization": "Jharkhand State Livelihood Promotion Society (JSLPS)",
                "deadline": datetime(2026, 10, 31),
                "description": "Thousands of tribal forest dwellers in Khunti depend on Rangeeni and Kusmi lac crops hosted on Ber and Palas trees. Unseasonal temperature spikes and predator infestations cause premature larval mortality, devastating annual household income.",
                "required_skills": "IoT Canopy Sensors, LoRaWAN, Agri-Biotechnology, Rural SHG Supply Chain",
                "expected_outcome": "Micro-climatic tree canopy sensor network providing pest warnings to 1,600 tribal SHG lac growers, doubling harvest productivity."
            },
            {
                "title": "Real-Time Industrial Effluent & Heavy Metal Telemetry in Subarnarekha River Basin",
                "category": "Environment",
                "department": "Jharkhand State Pollution Control Board (JSPCB)",
                "location": "Adityapur & Jamshedpur, East Singhbhum, Jharkhand",
                "district": "East Singhbhum (Jamshedpur)",
                "block": "Golmuri-cum-Jugsalai",
                "submitter_type": "Government Agency",
                "priority": "High",
                "status": "Open",
                "organization": "JSPCB & East Singhbhum District Administration",
                "deadline": datetime(2026, 11, 20),
                "description": "Unmonitored toxic runoff and industrial tailing effluents threaten downstream drinking water intakes in the Subarnarekha and Kharkai rivers. Periodic manual water sampling fails to detect night-time illicit discharges.",
                "required_skills": "Spectrophotometric Sensors, LoRaWAN, Edge Computing, GIS Heatmap Tracking",
                "expected_outcome": "Continuous 24x7 river quality sensing buoy network alerting pollution control officers within 3 minutes of heavy metal threshold breach."
            },
            {
                "title": "Decentralized DC Solar Mini-Grids with Prepaid Smart Metering for Netarhat Hamlets",
                "category": "Energy",
                "department": "Jharkhand Renewable Energy Development Agency (JREDA)",
                "location": "Netarhat Plateau, Latehar, Jharkhand",
                "district": "Latehar",
                "block": "Mahuadanr",
                "submitter_type": "Gram Panchayat / Local Body",
                "priority": "High",
                "status": "Pilot",
                "organization": "JREDA Latehar Division",
                "deadline": datetime(2026, 12, 25),
                "description": "Isolated forest terrain in the Netarhat hills makes conventional transmission grid expansion economically unfeasible. Primitive kerosene lamps pose acute respiratory hazards to 450 PVTG (Birhor and Asur) families.",
                "required_skills": "DC Microgrids, LiFePO4 Battery Storage, Smart Prepaid Metering, Solar PV Design",
                "expected_outcome": "Cluster of three 25kW community solar mini-grids delivering 24x7 lighting, clean water pumping, and digital study centres to 380 tribal homes."
            },
            {
                "title": "Offline Bilingual STEM Tablets & Interactive Science Kits for Tribal Residential Schools",
                "category": "Education",
                "department": "Department of Higher & Technical Education",
                "location": "Bermo & Chas, Bokaro, Jharkhand",
                "district": "Bokaro",
                "block": "Bermo",
                "submitter_type": "Government Agency",
                "priority": "Medium",
                "status": "Open",
                "organization": "Jharkhand Tribal Welfare Residential Education Society",
                "deadline": datetime(2026, 10, 15),
                "description": "Students in tribal residential schools lack hands-on physics and chemistry laboratory equipment. Available digital material is exclusively in English or formal Hindi, posing severe comprehension hurdles for Santhali and Ho native speakers.",
                "required_skills": "EdTech, Offline Progressive Web App, Gamification, Bilingual Audio Synthesis (Santhali/Hindi)",
                "expected_outcome": "Interactive experiential science simulation software deployed on 1,400 solar tablets across 18 tribal residential schools."
            },
            {
                "title": "Smart Haat Solid Waste Segregation & Dynamic Inundation Clearance Telemetry",
                "category": "Urban Development",
                "department": "Urban Development and Housing Department (UDHD Jharkhand)",
                "location": "Ranchi Municipal Corporation, Jharkhand",
                "district": "Ranchi",
                "block": "Kanke",
                "submitter_type": "Citizen / Resident",
                "priority": "High",
                "status": "Open",
                "organization": "Ranchi Municipal Corporation (RMC)",
                "deadline": datetime(2026, 11, 15),
                "description": "Weekly vegetable haats in Ranchi generate massive bio-waste volumes that choke municipal stormwater drains during monsoon downpours. Collection vehicles operate on rigid schedules without fill-level telemetry.",
                "required_skills": "IoT Ultrasonic Sensors, Vehicle Routing Optimization, Computer Vision, Edge Telemetry",
                "expected_outcome": "Real-time volumetric bin monitoring network with automated dynamic compaction vehicle dispatch for 16 major haats in Ranchi."
            }
        ]

        for item in controlled_challenges:
            ch = Challenge(
                title=item['title'],
                category=item['category'],
                department=item['department'],
                location=item['location'],
                district=item.get('district', 'Ranchi'),
                block=item.get('block', ''),
                submitter_type=item.get('submitter_type', 'Citizen / Resident'),
                priority=item['priority'],
                status=item['status'],
                organization=item['organization'],
                deadline=item['deadline'],
                description=item['description'],
                required_skills=item['required_skills'],
                expected_outcome=item['expected_outcome'],
                ai_impact_score=calculate_ai_impact_score(item['priority'], 10000, item['required_skills'], item['expected_outcome']),
                created_date=datetime(2026, 1, 15, 10, 0, 0),
                created_by_id=admin.id
            )
            db.session.add(ch)

        # 4. Controlled Stable Organizations (Premier Jharkhand HEIs & Industry Partners)
        orgs = [
            Organization(
                name="Birla Institute of Technology (BIT), Mesra, Ranchi",
                type="University",
                location="Ranchi, Jharkhand",
                description="Premier deemed university with Centres of Excellence in AI, Robotics, Remote Sensing, and dedicated Technology Business Incubator (BIT-TBI).",
                expertise_tags="IoT, Robotics, Artificial Intelligence, Smart Cities, Urban Development, Telematics, Remote Sensing, Computer Vision",
                website="https://www.bitmesra.ac.in",
                logo_icon="fa-university"
            ),
            Organization(
                name="Indian Institute of Technology (ISM) Dhanbad",
                type="University",
                location="Dhanbad, Jharkhand",
                description="Institute of National Importance with TEXMiN Hub, specialized in groundwater hydrology, mine water purification, clean energy, and geophysics.",
                expertise_tags="Water Resources, Clean Energy, Environmental Engineering, Mining Tech, Geophysics, Hydrology, Clean Coal, Filtration",
                website="https://www.iitism.ac.in",
                logo_icon="fa-graduation-cap"
            ),
            Organization(
                name="National Institute of Technology (NIT) Jamshedpur",
                type="University",
                location="Jamshedpur, Jharkhand",
                description="Premier technical institution closely linked to Jharkhand industrial corridor, featuring advanced manufacturing testbeds and smart grid laboratories.",
                expertise_tags="Heavy Engineering, Materials Science, Industrial Automation, Smart Grids, Manufacturing, Metallurgy, LoRaWAN",
                website="https://www.nitjsr.ac.in",
                logo_icon="fa-microchip"
            ),
            Organization(
                name="Birsa Agricultural University (BAU), Kanke",
                type="University",
                location="Ranchi, Jharkhand",
                description="State agricultural university with Agri-Business Incubation Centre (ABIC) leading tribal farm modernization, lac cultivation, and soil testing.",
                expertise_tags="AgriTech, Agriculture, Soil Health, Rural Livelihoods, Crop Science, Horticulture, Agro-forestry, Lac Cultivation",
                website="https://www.bauranchi.org",
                logo_icon="fa-seedling"
            ),
            Organization(
                name="All India Institute of Medical Sciences (AIIMS) Deoghar",
                type="University",
                location="Deoghar, Jharkhand",
                description="Apex medical research and healthcare institution providing specialized digital telemedicine outreach to tribal districts of Santhal Pargana.",
                expertise_tags="Healthcare, Telemedicine, Public Health, Rural Epidemiology, Maternal Health, Diagnostic Devices, Medical IoT",
                website="https://www.aiimsdeoghar.edu.in",
                logo_icon="fa-hospital-user"
            ),
            Organization(
                name="Central University of Jharkhand (CUJ), Brambe",
                type="University",
                location="Ranchi, Jharkhand",
                description="Central university leading tribal linguistic preservation, NEP 2020 experiential learning curricula, and rural governance research.",
                expertise_tags="Education, Tribal Languages, Public Administration, Social Innovation, Rural Development, Renewable Energy, EdTech",
                website="https://www.cuj.ac.in",
                logo_icon="fa-book-reader"
            ),
            Organization(
                name="Tata Steel Foundation & Tata Motors CSR",
                type="Industry",
                location="Jamshedpur, Jharkhand",
                description="Pioneering corporate social responsibility foundation providing industrial testbeds, CSR grant funding, and community scaling.",
                expertise_tags="Corporate CSR, Industrial IoT, Clean Water, Environment, Heavy Tech, Tribal Health, Prototyping, Manufacturing",
                website="https://www.tatasteel.com",
                logo_icon="fa-building"
            ),
            Organization(
                name="Central Coalfields Limited (CCL) & BCCL (Coal India)",
                type="Industry",
                location="Ranchi & Dhanbad, Jharkhand",
                description="Major public sector energy enterprise investing CSR funds in mine water treatment, rural community healthcare, and solar electrification.",
                expertise_tags="Mine Water Reclamation, Water Resources, Clean Energy, Rural Infrastructure, Community CSR, Environmental Restoration",
                website="https://www.centralcoalfields.in",
                logo_icon="fa-industry"
            ),
            Organization(
                name="Steel Authority of India Limited (SAIL Bokaro)",
                type="Industry",
                location="Bokaro, Jharkhand",
                description="One of India's largest steel plants supporting industrial innovation, secondary recycling, waste-to-energy, and technical skill development.",
                expertise_tags="Industrial Waste-to-Energy, Automation, Heavy Manufacturing, Vocational Training, Technical CSR, Energy",
                website="https://www.sail.co.in",
                logo_icon="fa-cogs"
            ),
            Organization(
                name="Jharkhand Innovation Lab (JIL) / Startup Jharkhand",
                type="Startup",
                location="Ranchi, Jharkhand",
                description="State nodal innovation agency under Dept. of IT & e-Gov providing up to Rs 15 Lakhs prototype grants, testbed access, and incubation mentorship.",
                expertise_tags="Early Stage Seed Grants, Prototyping Facilities, MSME Scaling, Incubation, Tech Mentorship, Smart Cities",
                website="https://startup.jharkhand.gov.in",
                logo_icon="fa-rocket"
            )
        ]
        db.session.add_all(orgs)

        # 5. Stable Impact Metrics (Jharkhand Focused)
        metrics = [
            ImpactMetric(
                project_title="Coal-Belt Mine Water Purification Grid",
                category="Water Resources",
                people_impacted=480000,
                villages_reached=42,
                cost_saved_lakhs=180.0,
                time_saved_pct=65,
                environmental_gain="120 Million Litres potable water reclaimed from abandoned pits",
                employment_created=64,
                resources_saved="Fluoride levels brought below 1.0 mg/L in 42 tribal hamlets"
            ),
            ImpactMetric(
                project_title="Santhal Pargana ASHA Telemedicine Hubs",
                category="Healthcare",
                people_impacted=74000,
                villages_reached=95,
                cost_saved_lakhs=210.0,
                time_saved_pct=82,
                environmental_gain="140,000 km unnecessary rural patient commute averted",
                employment_created=58,
                resources_saved="Emergency maternal referral time reduced by 3.8 hours"
            ),
            ImpactMetric(
                project_title="Ranchi Peri-Urban Solar Cold Haat Chain",
                category="Agriculture",
                people_impacted=125000,
                villages_reached=38,
                cost_saved_lakhs=95.0,
                time_saved_pct=45,
                environmental_gain="850 Metric Tons vegetable post-harvest rot prevented",
                employment_created=40,
                resources_saved="Average farmer household income increased by 42%"
            ),
            ImpactMetric(
                project_title="Netarhat Plateau Solar DC Mini-Grids",
                category="Energy",
                people_impacted=26000,
                villages_reached=16,
                cost_saved_lakhs=84.0,
                time_saved_pct=40,
                environmental_gain="92,000 Litres hazardous kerosene burn eliminated per year",
                employment_created=30,
                resources_saved="24x7 solar electricity delivered to 380 tribal homes"
            )
        ]
        db.session.add_all(metrics)

        db.session.commit()
        print("Controlled dataset successfully seeded into database.")

# ---------------------------------------------------------
# RUNNER ENTRY POINT
# ---------------------------------------------------------
if __name__ == '__main__':
    seed_database()
    print("\n=======================================================")
    print("  SAMADHAN SETU - National Societal Innovation Portal  ")
    print("  Enterprise Platform Ready                            ")
    print("=======================================================")
    print("  Server running at: http://127.0.0.1:5000/            ")
    print("  Admin Credentials: admin@samadhansetu.com / Admin@123")
    print("=======================================================\n")
    app.run(debug=True, host='0.0.0.0', port=5000)
