# Seyal API Backend 🚀

> **One backend · Multi-tenant · PostgreSQL & Redis · Built to scale to 1 Lakh+ Users**

The backend powering **Seyal** — a Notion-style collaborative workspace platform with hierarchical task delegation, approval flows, personal workspace privacy, connected Google Workspace integrations, and Anthropic Claude AI copilot.

---

## 🛠️ Tech Stack

- **Framework:** Python 3.12, Django 5.x, Django REST Framework
- **Authentication:** SimpleJWT (JWT Access & Refresh Tokens), Email OTP (Passwordless), Mobile Phone OTP, Social OAuth (Google, Facebook, Apple)
- **Database:** PostgreSQL 16 (JSONB, Row-Level-Security, Cursor Pagination)
- **Caching & Broker:** Redis 7
- **WSGI Server:** Gunicorn with multi-worker concurrency
- **Containerization:** Docker & Docker Compose

---

## 📂 Architecture & Apps

| App | Purpose | Main Models / APIs |
| :--- | :--- | :--- |
| `accounts` | Identity, Auth & Users | `User`, `AuthIdentity`, `OTPRequest`, `LoginAudit`, `RefreshTokenRecord` |
| `workspaces` | Multi-Tenant Workspaces | `Workspace` (Personal/Team/Org), `WorkspaceMember`, `Department`, `WorkspaceInvite` |
| `content` | Notion-style Pages & Blocks | `Page`, `Block` (Fractional indexing), `Database`, `DatabaseRow`, `DatabaseView` |
| `tasks` | Hierarchy & Approvals | `Task`, `TaskSubmission`, `TaskComment`, `TaskAttachment`, Assign down / Submit / Review |
| `notifications`| In-App & Activity Feeds | `Notification`, `ActivityLog` |
| `billing` | Plans & Subscriptions | `Plan`, `Subscription`, `Payment`, Razorpay integration |
| `common` | Connected Integrations & AI | Google Drive, Gmail Task Converter, Anthropic Claude Copilot, Birthday Reminders, API Settings |

---

## 🚀 Quick Start with Docker

```bash
# Clone the repository
git clone https://github.com/From-update/seyal--BE.git
cd seyal--BE

# Start Postgres, Redis, and Django API
docker compose up -d

# Check live logs
docker compose logs -f api
```

The API service runs on `http://localhost:8000/api/v1/`.

---

## 💻 Local Development Setup (Native Python)

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Or `.\venv\Scripts\Activate.ps1` on Windows

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Seed initial demo accounts and college department hierarchy
python seed_data.py

# Run local dev server
python manage.py runserver 8000
```

---

## 🔑 Pre-Configured Demo Accounts

| Role | Email | Password | Scope |
| :--- | :--- | :--- | :--- |
| **Owner / GM** | `gm@seyal.app` | `password123` | Institutional Admin & Executive Sign-off |
| **HOD / Manager** | `manager@seyal.app` | `password123` | Department Manager & Task Reviewer |
| **Faculty / Staff** | `staff@seyal.app` | `password123` | Department Faculty & Submissions |
| **Student / Personal** | `student@seyal.app` | `password123` | Private Personal Workspace |

*All accounts also support 1-click passwordless login via **Email OTP**.*

---

## 🔌 API Endpoints Summary

- **Authentication:**
  - `POST /api/v1/auth/login` - Email & Password login
  - `POST /api/v1/auth/register` - Create new user account
  - `POST /api/v1/auth/otp/request` - Send 6-digit numeric OTP to Email or Phone
  - `POST /api/v1/auth/otp/verify` - Verify OTP and generate JWT tokens
  - `POST /api/v1/auth/social/<provider>` - Google, Facebook, Apple token exchange
  - `GET /api/v1/me` - Current authenticated user profile
- **Workspaces & Hierarchy:**
  - `GET /api/v1/workspaces` - List accessible workspaces
  - `POST /api/v1/workspaces/{id}/convert` - Convert Personal workspace to Team workspace
  - `GET /api/v1/workspaces/{id}/departments` - List department structure
  - `GET /api/v1/workspaces/{id}/members` - Manage members & roles
- **Tasks & Approvals:**
  - `GET /api/v1/tasks` - List tasks with status/priority/department filters
  - `POST /api/v1/tasks/{id}/submit` - Staff submit proof of work
  - `POST /api/v1/tasks/{id}/review` - Manager approve or reject submission
- **Integrations & AI:**
  - `POST /api/v1/ai/claude/generate` - Claude 3.5 Sonnet workspace intelligence
  - `GET /api/v1/integrations/google/drive` - Google Drive explorer
  - `GET /api/v1/integrations/google/gmail` - Gmail inbox reader
  - `POST /api/v1/integrations/google/gmail/create-task` - Convert email to workspace card
  - `GET /api/v1/integrations/settings` - Manage live API credentials (encrypted & masked)
  - `POST /api/v1/integrations/test` - Test live connectivity to Anthropic, Google, and Razorpay
  - `GET/POST /api/v1/reminders/birthdays` - Birthday & occasion reminder hub
