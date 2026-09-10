# SamadhanSetu (समाधान सेतु)
### National Societal Innovation & Industry-Academia Collaborative Platform
**Smart India Hackathon (SIH) Enterprise Ready**

> *"Turn Societal Challenges Into Real-World Solutions."*

---

## 🏛️ Overview
**SamadhanSetu** is a comprehensive, production-ready enterprise/government web application built to crowdsource grassroots societal challenges and facilitate multi-stakeholder collaboration among **Citizens, Students, Faculty Researchers, Premier Universities (IITs/NITs), Corporate Industry R&D/CSR, Startups, NGOs, and Government Bodies**.

The platform operationalizes the full lifecycle pipeline:
$$\text{Societal Problem} \rightarrow \text{Crowdsource} \rightarrow \text{Verify} \rightarrow \text{Academia-Industry Match} \rightarrow \text{Proposal} \rightarrow \text{Workspace} \rightarrow \text{Pilot} \rightarrow \text{Social Impact}$$

---

## 🚀 Technology Stack
- **Backend:** Python 3, Flask 3.1+, Flask-SQLAlchemy 3.1+
- **Database:** SQLite with SQLAlchemy ORM (auto-migrating & auto-seeding)
- **Security:** Werkzeug secure salted password hashing (`generate_password_hash`, `check_password_hash`), role-based session authorization
- **Frontend:** HTML5, CSS3, JavaScript (Vanilla ES6+), Bootstrap 5.3, Font Awesome 6
- **Analytics & Data Visualizations:** Chart.js 4.4 (Impact timelines, Sector breakdown, Category distribution, Pipeline health)

---

## 🔑 Authentication Credentials
Access is strictly restricted to a single **ADMINISTRATOR** account. All demo quick-accounts have been removed for enterprise security.

| Role | Email / Admin ID | Password | Access Level |
| :--- | :--- | :--- | :--- |
| **ADMINISTRATOR** | `admin@samadhansetu.com` | `Admin@123` | Full Administrative & CRUD Access |

*Note: Authentication is enforced on the Python backend using Flask sessions and salted PBKDF2:SHA256 password hashing. Unauthenticated users are redirected to `/login`.*

---

## ⚡ Quick Start & Execution

### Option 1: Direct Python Execution
Open PowerShell or Command Prompt in the project folder:
```bash
cd "c:\Users\Nandini M\OneDrive\Desktop\societal_innovation_platform"
.venv\Scripts\python.exe app.py
```
*(Or if Python is on your PATH: `python app.py`)*

### Option 2: Windows 1-Click Launcher
Double-click `run.bat` inside the project folder.

Open your browser and navigate to:
👉 **`http://127.0.0.1:5000/`** (or directly **`http://127.0.0.1:5000/login`**)

---

## 🧪 Automated Specification Test Suite
Run the test suite verifying all 10 specification requirements:
```bash
.venv\Scripts\python.exe test_admin_suite.py
```
This tests:
1. Valid admin login (`admin@samadhansetu.com` / `Admin@123`)
2. Wrong email rejection with *"Invalid admin email or password."*
3. Correct email + wrong password rejection
4. Direct unauthenticated access redirection to `/login`
5. Session persistence across dashboard refreshes
6. Logout clears session and revokes access
7. Verification that demo account buttons are completely absent from HTML
8. Verification of controlled, permanent challenges with zero reload randomness
9. Admin add challenge saved to SQLite
10. Admin edit and delete challenge CRUD operations

---

## 🔄 End-to-End Demonstration Workflow
1. **Public Discovery (`/`)**:
   - Inspect the National Innovation Grid hero, official tricolor banner, live impact counters, and the 8-step workflow.
2. **Citizen Submits a Problem (`/challenge/new`)**:
   - Log in as Citizen (`anita.deshmukh@gmail.com`) or Student.
   - Fill in details: Category (e.g., *Water* or *Waste Management*), Location, Affected Population, Severity, Shortcomings of current attempts, Required Skills.
   - Notice the automated **AI Impact Score pre-calculation** (0–100) generated using our rule-based algorithm.
3. **Admin Verifies Challenge (`/admin`)**:
   - Sign in as Admin (`admin@samadhansetu.gov.in`).
   - Open the **Challenge Verification Queue**. Click **Verify** to officially approve and publish the challenge to the national marketplace.
4. **Academia-Industry Smart Matchmaking (`/challenge/<id>`)**:
   - Open the verified challenge.
   - Observe the **AI-Recommended Universities** (e.g. IIT Bombay with matching IoT/Water tags) and **Recommended Industry Partners** (e.g. Tata Social Innovations) calculated via rule-based keyword cross-referencing.
5. **Student Proposes Solution (`/challenge/<id>/propose-solution`)**:
   - Submit technical architecture, innovation points, technology stack, estimated budget, and team structure.
6. **Solution Lifecycle Stepper & Selection (`/solution/<id>`)**:
   - Observe the 6-stage lifecycle stepper: `IDEA → VALIDATION → PROTOTYPE → PILOT → DEPLOYMENT → IMPACT`.
   - Click **Select & Launch Project** to automatically generate a dedicated **Project Workspace** linking the Student Lead, University Partner, and Industry Sponsor!
7. **Interactive Project Workspace (`/project/<id>`)**:
   - Interactive **Milestones Tracker**: Click milestone checkboxes to update overall delivery % in real-time.
   - **Kanban Task Board**: Add work packages, move tasks seamlessly between *To Do*, *In Progress*, and *Completed*.
8. **National Impact Analytics (`/impact`)**:
   - Explore the 8 national KPI cards (2.45M+ People Impacted, ₹14.2 Cr Saved, 1,480 MT CO2 avoided, 180M Ltr Water Conserved) and Chart.js analytics graphs.

---

## 📂 Project Structure
```
societal_innovation_platform/
│
├── app.py                     # Main backend entry point, models, routes, intelligent algorithms, seed data
├── requirements.txt           # Python dependencies (Flask, Flask-SQLAlchemy, Werkzeug)
├── run.bat                    # Windows 1-click launcher
├── README.md                  # Complete documentation
│
├── templates/
│   ├── base.html              # Enterprise layout with tricolor banner, header, navbar, footer
│   ├── landing.html           # Landing page with workflow visualization & stats
│   ├── login.html             # Split-screen enterprise login with show/hide password
│   ├── register.html          # Professional role-based registration
│   ├── forgot_password.html   # Password recovery flow
│   ├── dashboard.html         # User dashboard with sidebar, KPI cards, Chart.js
│   ├── challenges.html        # Marketplace with search & multi-filters
│   ├── submit_challenge.html  # Crowdsourcing challenge submission form
│   ├── challenge_detail.html  # Problem deep dive with AI recommendations & solutions
│   ├── solutions.html         # Solution repository
│   ├── propose_solution.html  # Solution proposal form
│   ├── solution_detail.html   # Lifecycle progress stepper & project launcher
│   ├── projects.html          # Active collaborative projects directory
│   ├── project_detail.html    # Workspace with Milestones & Kanban Tasks
│   ├── organizations.html     # Directory of Universities, Industries, Startups, NGOs
│   ├── impact.html            # National impact analytics with Chart.js
│   ├── admin.html             # Administrative governance & verification queue
│   ├── profile.html           # User profile with contribution ledger
│   ├── notifications.html     # Real-time alert feed
│   ├── 403.html               # 403 Forbidden page
│   ├── 404.html               # 404 Not Found page
│   └── 500.html               # 500 Server Error page
│
└── static/
    ├── css/
    │   └── style.css          # Government/Enterprise custom styling, cards, stepper, Kanban
    └── js/
        └── script.js          # Password toggle, live search, notifications, flash handlers
```

---
*Built for Smart India Hackathon (SIH) 2026. Ministry of Education Innovation Cell & AICTE.*

