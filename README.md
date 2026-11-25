# ONECOUNTRY FITNESS — Gym Trainer Management

A simple app for an independent gym trainer to keep client records: who the clients are, who came today, who has paid, and what exercises they did.

Only the trainer signs in. Clients are records, not user accounts.

---

## ⚡ Tech Stack

- **Backend:** FastAPI (Python 3.10+), SQLAlchemy 2.x, Pydantic v2, PostgreSQL
- **Database driver:** `pg8000` (pure-Python, no C dependencies)
- **Migrations:** Alembic
- **Frontend:** React 19, TypeScript, Vite, Tailwind CSS 4, TanStack Query v5, Lucide React, Axios
- **Authentication:** JWT + bcrypt, trainer accounts only

---

## 🏋️ Features

### 1. Dashboard
Active clients, today's attendance, pending and overdue fees, fees due in the next 7 days, and recently added clients.

### 2. Clients (`/clients`)
- Add, search (name, phone, email), filter by status and goal, edit, archive. Email is optional.
- Each client's page has tabs for **Details**, **Attendance**, **Membership & Fees**, **Exercises** and **Notes** (private trainer notes).
- Archiving never deletes history.

### 3. Attendance (`/attendance`)
- Daily sheet: mark each client Present, Late or Absent.
- Monthly overview with days attended per client, plus a per-client calendar to mark or correct any day.

### 4. Fees & Memberships (`/fees`)
- **Plans** (e.g. Monthly ₹1500, Quarterly ₹4000) managed from **Manage plans**.
- **Assign a plan** to a client (optionally at a custom rate) from the client's *Membership & Fees* tab or the *Memberships* list. Each cycle's fee is due on its start date and is created automatically.
- **Payments:** amount, date, method (Cash / UPI / Card / Bank transfer), optional reference. Partial payments, waivers and payment history are supported.
- **Statuses:** Upcoming, Due, Partially paid, Overdue (after a 5-day grace period), Paid, Waived.
- **WhatsApp reminder** button with a pre-filled message (a `wa.me` link, so no paid service is needed).

### 5. Exercise Log (`/exercise-log`)
- Record the exercises a client did (sets, reps, weight) and view past entries. The exercise list is editable.

### 6. Alerts (`/notifications`)
- The trainer is alerted when a client misses **3 sessions in a row** or **6 in a month**, and when a fee becomes **overdue**. Each alert has a WhatsApp follow-up button.
- Alerts are raised once per condition, never duplicated.

---

## 🛠️ Operational CLI (`app.cli`)

A dedicated operational command-line tool is included for system maintenance and gym owner administration:

```powershell
cd backend

# 1. Inspect System Status (User count, Athlete count, Trainer profile)
python -m app.cli status

# 2. Reset Trainer Password (Emergency recovery)
python -m app.cli reset-trainer-password --email trainer@example.com --password "NewSecurePassword123!"

# 3. Create Trainer Account (Headless initialization)
python -m app.cli create-trainer --name "Coach Alex" --email trainer@onecountryfitness.com --password "StrongPass123!" --phone "+1-555-0100"

# 4. Populate Standard Library Exercises (Zero fake accounts created)
python -m app.cli seed-exercises

# 5. Create due fees and raise absence/overdue alerts (safe to run any time)
python -m app.cli run-daily-jobs
```

### Background jobs

By default the API runs these jobs itself every `SCHEDULER_INTERVAL_MINUTES` (60). With several workers, a PostgreSQL advisory lock makes sure only one runs per tick. To use cron instead, set `SCHEDULER_ENABLED=false` and schedule:

```bash
# Linux cron: every hour
0 * * * * cd /srv/gym/backend && ./venv/bin/python -m app.cli run-daily-jobs >> /var/log/gym-jobs.log 2>&1
```

On Windows, create a Task Scheduler task that runs `venv\Scripts\python.exe -m app.cli run-daily-jobs` hourly with `backend` as the working directory.

---

## 🚀 Local Setup & Running Instructions

### 1. Environment Configuration

Copy `.env.example` to `.env` in the root directory:

```env
ENVIRONMENT=development
DATABASE_URL=postgresql+pg8000://postgres:postgres@localhost:5433/gym_db
JWT_SECRET_KEY=supersecretjwtkeyforgymtrainerv1appdevelopmentonly
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
ADMIN_RECOVERY_KEY=your_emergency_admin_recovery_key
CORS_ORIGINS=http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173
PORT=8000
```

### 2. Backend Startup

```powershell
cd backend

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Run database migrations
alembic upgrade head

# (Optional) Seed standard exercise catalog without demo users
python -m app.cli seed-exercises

# Start FastAPI server
uvicorn app.main:app --reload --port 8000
```

- Health check: `http://localhost:8000/health` or `http://localhost:8000/api/health`
- Swagger API documentation: `http://localhost:8000/docs`

### 3. Frontend Startup

```powershell
cd frontend

# Install dependencies (if needed)
npm install

# Start Vite development server
npm run dev
```

Frontend application is live at: `http://localhost:5173`

---

## 🛡️ First-Time Setup

1. Open `http://localhost:5173/setup` and create the trainer account (name, email, password of at least 8 characters).
2. Go to **Fees → Manage plans** and add your membership plans.
3. Add clients under **Clients → Add Client**, then assign each one a plan from their **Membership & Fees** tab.

---

## 🚢 Production Checklist

1. `ENVIRONMENT=production`. The API **refuses to start** with the default/placeholder `JWT_SECRET_KEY`, a secret shorter than 32 characters, or a SQLite database. Swagger docs (`/docs`) are disabled in production.
2. Generate a secret: `python -c "import secrets; print(secrets.token_hex(32))"`.
3. Run `alembic upgrade head` on every deploy (this release adds revision `f2b7c9d41a10`: membership plans, fee records, payments, notifications, trainer settings).
4. Set `CORS_ORIGINS` to your real domain and `TIMEZONE` to the gym's timezone.
5. Run the API behind HTTPS (e.g. `uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2` behind Nginx/Caddy). Build the frontend with `npm run build` and serve `frontend/dist` with `/api` proxied to the backend.
6. Schedule the database backups below.

---

## 💾 Database Backup & Disaster Recovery

### Backup Database (PostgreSQL)

```powershell
pg_dump -h localhost -p 5433 -U postgres -F c -b -v -f "gym_db_backup_$(Get-Date -Format 'yyyyMMdd_HHmmss').dump" gym_db
```

### Restore Database

```powershell
pg_restore -h localhost -p 5433 -U postgres -d gym_db -v "gym_db_backup_filename.dump"
```

---

## 🧪 Automated Tests

58 tests cover authentication (including refusing client logins), trainer data isolation, clients, attendance, fees and payments, alerts, the exercise log and the dashboard. They run on an in-memory SQLite database and never touch your real data:

```powershell
cd backend
.\venv\Scripts\python.exe -m pytest tests -q
```
