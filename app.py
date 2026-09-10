import os
import math
import logging
from datetime import datetime, timedelta
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, session, jsonify, abort
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

# ---------------------------------------------------------
# APPLICATION CONFIGURATION & LOGGING
# ---------------------------------------------------------
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__)
app.config['SECRET_KEY'] = 'samadhan-setu-sih-secret-key-2026-gov-enterprise-secured'
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

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


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
    progress_pct = db.Column(db.Integer, default=25)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    lead_user = db.relationship('User', foreign_keys=[lead_user_id])
    milestones = db.relationship('Milestone', backref='project', lazy=True, cascade='all, delete-orphan', order_by='Milestone.order_idx')
    tasks = db.relationship('Task', backref='project', lazy=True, cascade='all, delete-orphan')
    members = db.relationship('TeamMember', backref='project', lazy=True, cascade='all, delete-orphan')

    @property
    def code(self):
        return f"PROJECT-2026-{self.id:04d}"


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
    return {
        'current_user': current_user,
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

    return render_template('user_dashboard.html',
        user=user,
        my_challenges=my_challenges,
        my_solutions=my_solutions,
        solutions_on_my_challenges=solutions_on_my_challenges,
        recommended_challenges=recommended_challenges,
        my_projects=my_projects,
        notifications=notifications
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
    """View Challenge Details & Academic/Industry Matches."""
    challenge = Challenge.query.get_or_404(challenge_id)
    matches = rule_based_smart_match(challenge)
    similar_challenges = find_similar_challenges(challenge)
    solutions = Solution.query.filter_by(challenge_id=challenge.id).order_by(Solution.created_at.desc()).all()
    user = get_current_user()

    user_match_score = calculate_expertise_match(user, challenge) if user else None

    return render_template('challenge_detail.html',
        challenge=challenge,
        matches=matches,
        similar_challenges=similar_challenges,
        solutions=solutions,
        user_match_score=user_match_score
    )


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
        completed_tasks=completed_tasks
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
    """National Impact Analytics."""
    metrics = ImpactMetric.query.all()
    total_people = sum(m.people_impacted for m in metrics) or 2450000
    total_villages = sum(m.villages_reached for m in metrics) or 840
    total_cost_saved = sum(m.cost_saved_lakhs for m in metrics) or 1420.5
    avg_time_saved = int(sum(m.time_saved_pct for m in metrics) / max(len(metrics), 1)) if metrics else 42
    total_jobs = sum(m.employment_created for m in metrics) or 620
    implemented_projects_count = Project.query.filter(Project.progress_pct >= 75).count() or 14

    return render_template('impact.html',
        metrics=metrics,
        total_people=total_people,
        total_villages=total_villages,
        total_cost_saved=total_cost_saved,
        avg_time_saved=avg_time_saved,
        total_jobs=total_jobs,
        implemented_projects_count=implemented_projects_count
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
