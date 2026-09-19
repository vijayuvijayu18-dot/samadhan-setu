"""
=============================================================================
SAMADHAN SETU - SIH Prototype Features Demonstration Seeder
Smart India Hackathon 2026 Showcase Data Loader
=============================================================================
This script seeds rich, realistic demonstration data for the 3 distinctive
SIH prototype features:
1. Smart Skill-Based Team Matching
2. Idea -> Impact 10-Stage Project Lifecycle Tracker with Before-After Metrics
3. Industry + University Collaboration Hub Support Requests & Corporate Offers
=============================================================================
"""

import sys
from datetime import datetime, date, timedelta
from app import (
    app, db, User, Challenge, Solution, Project,
    Milestone, Task, TeamMember,
    ProjectStageUpdate, ProjectImpactMetric,
    IndustrySupportRequest, IndustrySupportResponse,
    TeamInvitation, PROJECT_LIFECYCLE_STAGES
)

def seed_sih_features():
    print("=" * 70)
    print("  SEEDING SIH PROTOTYPE DEMONSTRATION DATA")
    print("=" * 70)

    with app.app_context():
        # 1. Fetch Key Users
        admin_user = User.query.filter_by(email="admin@samadhansetu.com").first()
        if not admin_user:
            print("[ERROR] Admin user not found. Run standard seed first.")
            return

        # Ensure demo candidate innovators with diverse skills exist
        innovators_spec = [
            {
                "full_name": "Aakash Verma",
                "email": "aakash.iot@bitmesra.ac.in",
                "user_type": "Student",
                "organization": "Birla Institute of Technology, Mesra",
                "location": "Ranchi, Jharkhand",
                "skills": "IoT, Embedded Systems, LoRaWAN, Water Sensors, Microcontrollers"
            },
            {
                "full_name": "Dr. Sunita Murmu",
                "email": "sunita.env@iitism.ac.in",
                "user_type": "Researcher",
                "organization": "IIT (ISM) Dhanbad",
                "location": "Dhanbad, Jharkhand",
                "skills": "Environmental Engineering, Water Quality, Fluoride Removal, Filtration"
            },
            {
                "full_name": "Rajesh Singhania",
                "email": "rajesh.singhania@tatasteel.com",
                "user_type": "Industry Representative",
                "organization": "Tata Steel CSR & Sustainability",
                "location": "Jamshedpur, Jharkhand",
                "skills": "CSR Funding, Industrial Scaling, SCADA, Project Governance"
            },
            {
                "full_name": "Pooja Kumari",
                "email": "pooja.ai@iiitranchi.ac.in",
                "user_type": "Student",
                "organization": "IIIT Ranchi",
                "location": "Ranchi, Jharkhand",
                "skills": "Python, Machine Learning, Data Analytics, GIS Mapping, Cloud Backend"
            }
        ]

        seeded_users = {}
        for spec in innovators_spec:
            user = User.query.filter_by(email=spec["email"]).first()
            if not user:
                user = User(
                    full_name=spec["full_name"],
                    email=spec["email"],
                    user_type=spec["user_type"],
                    organization=spec["organization"],
                    location=spec["location"],
                    skills=spec["skills"]
                )
                user.set_password("Innovator@123")
                db.session.add(user)
                db.session.flush()
                print(f"[+] Created Innovator Profile: {user.full_name} ({user.skills})")
            else:
                user.skills = spec["skills"]
                user.organization = spec["organization"]
                user.location = spec["location"]
            seeded_users[spec["email"]] = user

        db.session.commit()

        # 2. Ensure Feature Showcase Challenge exists
        demo_chal_code = "CHL-2026-0008"
        challenge = Challenge.query.filter_by(code=demo_chal_code).first()
        if not challenge:
            challenge = Challenge.query.filter(Challenge.category.like("%Water%")).first()

        if challenge:
            challenge.required_skills = "IoT, Embedded Systems, Water Sensors, Python, LoRaWAN, Water Quality"
            challenge.expected_solution_type = "Hardware + IoT Edge Telemetry + Cloud Dashboard"
            db.session.commit()
            print(f"[+] Updated Challenge {challenge.code} with rich required skills for team matching.")

        # 3. Ensure a Showcase Project with 10-Stage Lifecycle and Impact Metrics
        project = Project.query.filter(Project.title.like("%Water%")).first()
        if not project:
            project = Project.query.first()
        if not project:
            sol = Solution.query.first()
            chal = Challenge.query.first()
            project = Project(
                title="Smart Water Distribution & Fluoride Filtration Network",
                description="Community-scale water testing and automated filtration nodes deployed across rural Jharkhand.",
                challenge_id=chal.id if chal else 1,
                solution_id=sol.id if sol else None,
                lead_user_id=admin_user.id,
                university_partner="Birla Institute of Technology, Mesra",
                industry_partner="Tata Steel CSR & Sustainability",
                current_stage="Pilot Testing",
                status="In Pilot"
            )
            db.session.add(project)
            db.session.commit()
            print(f"[+] Created New Showcase Project #{project.id}: {project.title}")

        if project:
            # Advance to Stage: Pilot Testing
            project.current_stage = "Pilot Testing"
            print(f"[+] Setting Project #{project.id} ({project.title}) to Stage: {project.current_stage}")

            # Add Stage Updates History if empty
            if len(project.stage_updates) == 0:
                stage_history = [
                    ("Challenge Submitted", "Citizen telemetry data verified by Ranchi Municipal Corporation water division.", None, -25),
                    ("Challenge Validated", "Field ground inspection and water laboratory testing confirmed high contaminants.", None, -20),
                    ("Team Formed", "Multidisciplinary squad with BIT Mesra, IIT Dhanbad and Tata Steel engineers formed.", None, -15),
                    ("Prototype Development", "Benchtop LoRaWAN sensor node assembled and calibrated against lab standards.", "https://drive.google.com/sample-lab-calibration-cert", -10),
                    ("Pilot Testing", "Deploying 12 field telemetry nodes across Ward 8 ground borewells.", "https://drive.google.com/sample-field-trial-log", -2)
                ]
                for stg, desc, evidence, days_ago in stage_history:
                    upd = ProjectStageUpdate(
                        project_id=project.id,
                        stage=stg,
                        description=desc,
                        evidence_url=evidence,
                        updated_by_id=admin_user.id,
                        created_at=datetime.utcnow() + timedelta(days=days_ago)
                    )
                    db.session.add(upd)
                print(f"[+] Created 5 sequential stage transition logs for Project #{project.id}")

            # Add Before-vs-After Impact Metrics if empty
            if len(project.impact_indicators) == 0:
                metrics_data = [
                    {
                        "name": "Groundwater Arsenic & Heavy Metal Concentration",
                        "unit": "ppm",
                        "before_val": 3.8,
                        "after_val": 0.4,
                        "is_red": True,
                        "notes": "Verified via spectrophotometric analysis by IIT (ISM) Dhanbad Environmental Lab."
                    },
                    {
                        "name": "Daily Non-Revenue Physical Water Wastage",
                        "unit": "Litres / Day",
                        "before_val": 48500.0,
                        "after_val": 16200.0,
                        "is_red": True,
                        "notes": "Acoustic line leak detectors detected and patched 14 underground pipeline fissures."
                    },
                    {
                        "name": "Households Receiving Verified Safe Potable Water",
                        "unit": "Households",
                        "before_val": 320.0,
                        "after_val": 1480.0,
                        "is_red": False,
                        "notes": "Door-to-door community survey validated across 4 rural Panchayats."
                    }
                ]
                for md in metrics_data:
                    pim = ProjectImpactMetric(
                        project_id=project.id,
                        metric_name=md["name"],
                        unit=md["unit"],
                        before_value=md["before_val"],
                        after_value=md["after_val"],
                        is_reduction=md["is_red"],
                        verification_notes=md["notes"]
                    )
                    pim.calculate_change()
                    db.session.add(pim)
                print(f"[+] Created 3 Before-vs-After Ground Impact Metrics for Project #{project.id}")

            # Add Industry Support Request & Response
            if len(project.support_requests) == 0:
                tata_rep = seeded_users.get("rajesh.singhania@tatasteel.com")
                req = IndustrySupportRequest(
                    project_id=project.id,
                    support_type="Funding / Seed Grant",
                    title=f"Industrial IoT Telemetry Gateways & Solar Kits for {project.title}",
                    description="Seeking corporate CSR seed funding of Rs 3,50,000 for 25 LoRaWAN telemetry gateways and industrial solar power kits for remote rural borewells.",
                    estimated_budget="350000",
                    timeline="3 Months",
                    contact_info="project.office@samadhansetu.com",
                    status="Industry Interested",
                    created_by_id=project.lead_user_id or admin_user.id
                )
                db.session.add(req)
                db.session.flush()

                if tata_rep:
                    resp = IndustrySupportResponse(
                        request_id=req.id,
                        industry_user_id=tata_rep.id,
                        organization_name="Tata Steel CSR & Sustainability",
                        support_offered="Tata Steel Rural Development Society (TSRDS) approves in-principle CSR co-funding of Rs 2,50,000 along with telemetry hardware kits and technical mentorship from our water utilities engineering division.",
                        contribution_details="Rs 2,50,000 CSR Grant + 15 Industrial Sensor Enclosures + 2 Senior Engineers Advisory",
                        contact_person="Rajesh Singhania, Head of CSR Initiatives",
                        contact_email="rajesh.singhania@tatasteel.com",
                        status="Offer Submitted"
                    )
                    db.session.add(resp)
                print(f"[+] Created Industry Support Request & Tata Steel CSR Offer on Project #{project.id}")

            db.session.commit()

        # 4. Seed a Team Invitation for testing
        if challenge:
            aakash_user = seeded_users.get("aakash.iot@bitmesra.ac.in")
            if aakash_user:
                existing_inv = TeamInvitation.query.filter_by(
                    challenge_id=challenge.id,
                    invitee_user_id=aakash_user.id
                ).first()
                if not existing_inv:
                    inv = TeamInvitation(
                        challenge_id=challenge.id,
                        inviter_user_id=admin_user.id,
                        invitee_user_id=aakash_user.id,
                        role_offered="Lead IoT Hardware Specialist",
                        matching_skills="IoT, Embedded Systems, Water Sensors, LoRaWAN",
                        match_score=92,
                        message="Your specialized background in LoRaWAN sensors and microcontrollers matches this challenge requirements perfectly. We would like you to join our innovation squad.",
                        status="Pending"
                    )
                    db.session.add(inv)
                    db.session.commit()
                    print(f"[+] Created Demo Team Invitation for {aakash_user.full_name} on Challenge #{challenge.id}")

    print("=" * 70)
    print("  SIH PROTOTYPE DEMONSTRATION DATA SEEDING COMPLETE")
    print("=" * 70)

if __name__ == '__main__':
    seed_sih_features()
