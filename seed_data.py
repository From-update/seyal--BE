import os
import sys
import django
from datetime import timedelta
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from accounts.models import User, AuthIdentity
from workspaces.models import Workspace, WorkspaceMember, Department, DepartmentMember
from content.models import Page, Block, Database, DatabaseRow, DatabaseView
from tasks.models import Task, TaskSubmission, Comment
from notifications.models import Notification, ActivityLog
from billing.models import Plan, Subscription
from billing.views import ensure_plans

def run_seed():
    print("🌱 Seeding Seyal database...")

    # 1. Ensure Plans
    ensure_plans()
    print("✅ Plans seeded.")

    # 2. Demo Users
    # GM / Owner
    owner, _ = User.objects.get_or_create(
        email="gm@seyal.app",
        defaults={
            "name": "Dr. Rajesh Sundaram (GM / Principal)",
            "email_verified": True,
            "language": "en",
            "usage_mode": "team"
        }
    )
    owner.set_password("password123")
    owner.save()
    AuthIdentity.objects.get_or_create(
        user=owner,
        provider='password',
        defaults={'provider_user_id': owner.email, 'is_verified': True}
    )

    # Department Manager
    manager, _ = User.objects.get_or_create(
        email="manager@seyal.app",
        defaults={
            "name": "Prof. Anitha Selvan (HOD / Manager)",
            "email_verified": True,
            "language": "en",
            "usage_mode": "team"
        }
    )
    manager.set_password("password123")
    manager.save()
    AuthIdentity.objects.get_or_create(
        user=manager,
        provider='password',
        defaults={'provider_user_id': manager.email, 'is_verified': True}
    )

    # Staff
    staff, _ = User.objects.get_or_create(
        email="staff@seyal.app",
        defaults={
            "name": "Karthik Subramanian (Faculty / Staff)",
            "email_verified": True,
            "language": "en",
            "usage_mode": "team"
        }
    )
    staff.set_password("password123")
    staff.save()
    AuthIdentity.objects.get_or_create(
        user=staff,
        provider='password',
        defaults={'provider_user_id': staff.email, 'is_verified': True}
    )

    # Personal user
    student, _ = User.objects.get_or_create(
        email="student@seyal.app",
        defaults={
            "name": "Priya Sharma (Student)",
            "email_verified": True,
            "language": "en",
            "usage_mode": "self"
        }
    )
    student.set_password("password123")
    student.save()
    AuthIdentity.objects.get_or_create(
        user=student,
        provider='password',
        defaults={'provider_user_id': student.email, 'is_verified': True}
    )

    print("✅ Demo users created (gm@seyal.app, manager@seyal.app, staff@seyal.app, student@seyal.app | password: password123).")

    # 3. Create Team Workspace
    team_ws, created = Workspace.objects.get_or_create(
        name="Apex College of Engineering",
        defaults={
            "type": "organization",
            "plan": "business",
            "owner": owner,
            "settings": {"icon": "🏛️", "theme": "default", "tagline": "Department tasks & workflow management"}
        }
    )

    # Memberships
    WorkspaceMember.objects.get_or_create(workspace=team_ws, user=owner, defaults={"role": "owner", "status": "active"})
    WorkspaceMember.objects.get_or_create(workspace=team_ws, user=manager, defaults={"role": "manager", "status": "active"})
    WorkspaceMember.objects.get_or_create(workspace=team_ws, user=staff, defaults={"role": "member", "status": "active"})

    owner.default_workspace_id = str(team_ws.id)
    owner.save(update_fields=['default_workspace_id'])
    manager.default_workspace_id = str(team_ws.id)
    manager.save(update_fields=['default_workspace_id'])
    staff.default_workspace_id = str(team_ws.id)
    staff.save(update_fields=['default_workspace_id'])

    # 4. Departments
    dept_cs, _ = Department.objects.get_or_create(
        workspace=team_ws,
        name="Computer Science & Engineering",
        defaults={"manager": manager}
    )
    DepartmentMember.objects.get_or_create(department=dept_cs, user=manager)
    DepartmentMember.objects.get_or_create(department=dept_cs, user=staff)

    dept_admin, _ = Department.objects.get_or_create(
        workspace=team_ws,
        name="Admissions & Administration",
        defaults={"manager": owner}
    )

    print("✅ Workspace & Hierarchy Departments configured.")

    # 5. Notion-style Pages & Blocks
    handbook_page, _ = Page.objects.get_or_create(
        workspace=team_ws,
        title="Department Operations Handbook 2026",
        defaults={
            "icon": "📘",
            "created_by": owner,
            "is_favorite": True
        }
    )

    if not handbook_page.blocks.exists():
        blocks = [
            ("heading1", {"text": "Department Operations & Hierarchy Flow"}),
            ("callout", {"text": "Welcome to Apex College Workspace! All faculty tasks must follow the Owner → HOD → Staff hierarchy approval workflow."}),
            ("heading2", {"text": "Key Guidelines"}),
            ("paragraph", {"text": "Every semester syllabus review and laboratory audit must be submitted directly through Seyal for review and approval."}),
            ("checklist", {"text": "Verify accreditation documentation", "checked": True}),
            ("checklist", {"text": "Complete curriculum feedback collection", "checked": False}),
            ("checklist", {"text": "Submit quarterly budget reports to Principal", "checked": False}),
            ("heading2", {"text": "Approval Pipeline"}),
            ("quote", {"text": "Work done diligently today ensures student excellence tomorrow."}),
            ("code", {"text": "# Weekly Review Cron\n0 9 * * 1 /scripts/weekly_department_audit.sh", "language": "bash"}),
        ]
        for idx, (b_type, b_content) in enumerate(blocks):
            Block.objects.create(
                page=handbook_page,
                type=b_type,
                content=b_content,
                position=float(idx + 1)
            )

    # 6. Database with Table and Board views
    db, _ = Database.objects.get_or_create(
        workspace=team_ws,
        name="Semester Accreditation Deliverables",
        defaults={
            "page": handbook_page,
            "schema": [
                {"id": "title", "name": "Deliverable", "type": "title"},
                {"id": "status", "name": "Status", "type": "select", "options": ["Not Started", "In Progress", "In Review", "Approved"]},
                {"id": "priority", "name": "Priority", "type": "select", "options": ["Low", "Medium", "High", "Urgent"]},
                {"id": "lead", "name": "Lead", "type": "text"},
                {"id": "due", "name": "Due Date", "type": "date"},
            ]
        }
    )

    DatabaseView.objects.get_or_create(database=db, name="Table View", defaults={"type": "table"})
    DatabaseView.objects.get_or_create(database=db, name="Kanban Board", defaults={"type": "board", "group_by": "status"})

    if not db.rows.exists():
        sample_rows = [
            {"title": "NBA Tier-1 Criteria 4 Document", "status": "In Review", "priority": "Urgent", "lead": "Prof. Anitha Selvan", "due": "2026-11-20"},
            {"title": "IoT Lab Equipment Calibration", "status": "In Progress", "priority": "High", "lead": "Karthik Subramanian", "due": "2026-11-15"},
            {"title": "Student Industry Internship Log", "status": "Not Started", "priority": "Medium", "lead": "Karthik Subramanian", "due": "2026-11-30"},
            {"title": "Faculty Research Publication Index", "status": "Approved", "priority": "Medium", "lead": "Dr. Rajesh Sundaram", "due": "2026-11-05"},
        ]
        for row_data in sample_rows:
            DatabaseRow.objects.create(
                database=db,
                properties=row_data,
                created_by=owner
            )

    print("✅ Databases and Views created.")

    # 7. Tasks with Hierarchy Approval Workflow
    now = timezone.now()

    # Task 1: Submitted for Manager review
    t1, _ = Task.objects.get_or_create(
        workspace=team_ws,
        title="Submit NAAC Criteria 3 Research Paper Compilation",
        defaults={
            "department": dept_cs,
            "description": "Consolidate all Scopus-indexed papers published by CSE department faculty during the odd semester.",
            "status": "submitted",
            "priority": "urgent",
            "assignee": staff,
            "assigned_by": manager,
            "due_date": now + timedelta(days=2),
            "labels": ["NAAC", "Accreditation", "Research"]
        }
    )
    if not t1.submissions.exists():
        TaskSubmission.objects.create(
            task=t1,
            submitted_by=staff,
            note="Completed verification of 24 journal papers and 18 conference proceedings. Attached summary sheet.",
            attachments=[{"name": "cse_scopus_papers_2026.pdf", "url": "https://example.com/cse_papers.pdf", "size": 1845000}],
            status="pending"
        )
        Notification.objects.create(
            user=manager,
            workspace=team_ws,
            type="submission",
            title="Task Submitted for Review",
            message=f"{staff.name} submitted 'Submit NAAC Criteria 3 Research Paper Compilation' for review.",
            link=f"/tasks?taskId={t1.id}"
        )

    # Task 2: Approved task
    t2, _ = Task.objects.get_or_create(
        workspace=team_ws,
        title="Department Syllabus Moderation Committee Minutes",
        defaults={
            "department": dept_cs,
            "description": "Draft minutes of meeting held on Nov 1st for AI & Data Science elective curriculum.",
            "status": "completed",
            "priority": "high",
            "assignee": staff,
            "assigned_by": manager,
            "due_date": now - timedelta(days=3),
            "labels": ["Curriculum", "Academic Council"]
        }
    )
    if not t2.submissions.exists():
        sub = TaskSubmission.objects.create(
            task=t2,
            submitted_by=staff,
            note="Minutes finalized and signed by all external board members.",
            status="approved",
            reviewed_by=manager,
            reviewed_at=now - timedelta(days=1),
            review_note="Excellent work. Minutes approved and archived."
        )

    # Task 3: In Progress assigned to Staff
    Task.objects.get_or_create(
        workspace=team_ws,
        title="Setup Cloud Computing Lab Virtual Machine Clusters",
        defaults={
            "department": dept_cs,
            "description": "Provision 40 AWS instances for final year Cloud Computing practical exam.",
            "status": "in_progress",
            "priority": "high",
            "assignee": staff,
            "assigned_by": manager,
            "due_date": now + timedelta(days=5),
            "labels": ["Lab Setup", "Infrastructure"]
        }
    )

    # Task 4: Overdue task
    Task.objects.get_or_create(
        workspace=team_ws,
        title="Mid-term Internal Marks Entry in ERP",
        defaults={
            "department": dept_cs,
            "description": "Upload third year assessment-1 grades before portal closes.",
            "status": "todo",
            "priority": "urgent",
            "assignee": staff,
            "assigned_by": manager,
            "due_date": now - timedelta(days=1),
            "labels": ["Grades", "ERP"]
        }
    )

    # Personal workspace for student
    from accounts.views import ensure_personal_workspace
    ensure_personal_workspace(student)
    ensure_personal_workspace(owner)

    print("✅ Hierarchy Tasks and Submissions populated successfully.")
    print("🚀 Database seeding complete!")

if __name__ == '__main__':
    run_seed()

