# Authentra AI

**AI-powered employee background verification platform for modern HR teams.**

Upload a resume → AI extracts candidate data → Consent email sent → Employment & education verified → Fraud detection → Risk score → PDF report.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI, SQLAlchemy Async, Alembic |
| Database | PostgreSQL (files stored as BYTEA) |
| Queue | Celery + Redis |
| AI/LLM | Google Gemini Flash (free) + OpenRouter fallback |
| Frontend | Next.js 15, TypeScript, Tailwind CSS |
| Auth | JWT + Refresh Tokens + bcrypt |
| Email | SMTP (Gmail / SendGrid / Resend compatible) |
| PDF | ReportLab |
| OCR | Tesseract + PyMuPDF + pdfplumber |

---

## Quick Start (Docker)

### 1. Clone and configure

```bash
git clone https://github.com/yourusername/authentra.git
cd authentra
cp .env.example backend/.env
```

### 2. Edit `backend/.env`

At minimum, set:

```env
# Generate secure keys:
# python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=<32-char-hex>
JWT_SECRET_KEY=<32-char-hex>
ENCRYPTION_KEY=<exactly-32-characters!!>

# Gmail app password (Settings → Security → 2FA → App Passwords)
SMTP_USER=your@gmail.com
SMTP_PASSWORD=your_app_password

# Get free key at https://aistudio.google.com
GEMINI_API_KEY=your_gemini_key

# Frontend URL
FRONTEND_URL=http://localhost:3000
CORS_ORIGINS=http://localhost:3000
```

### 3. Run

```bash
docker compose up --build
```

### 4. Access

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| Celery Flower | http://localhost:5555 |

---

## How It Works

### Candidate Verification Flow

```
Recruiter uploads resume
        ↓
PDF/DOCX text extracted (+ OCR for scanned pages)
        ↓
Gemini AI parses: name, email, phone, employment, education, skills
        ↓
Consent email sent to candidate
        ↓
Candidate clicks Accept
        ↓
Recruiter adds HR contact emails per employer/institution
        ↓
Verification emails sent with unique response links
        ↓
Fraud detection runs (overlapping jobs, impossible dates, etc.)
        ↓
AI risk scoring (0–100, Low/Moderate/High/Critical)
        ↓
PDF report generated
        ↓
Recruiter notified, report downloadable
```

### Risk Scoring

| Score | Level | Verdict |
|---|---|---|
| 0–25 | Low | Clear |
| 26–50 | Moderate | Review Required |
| 51–75 | High | Review Required |
| 76–100 | Critical | Reject |

### Fraud Detection

Automatically detects:
- Overlapping employment (>2 months concurrent jobs)
- Impossible date ranges (end before start)
- Future employment claims
- Suspicious education durations
- Excessive job hopping (<3 months per role × 3+)
- Keyword stuffing

---

## Pages

| Route | Description |
|---|---|
| `/login` | Sign in |
| `/register` | Company registration |
| `/dashboard` | Stats, charts, activity |
| `/candidates` | Upload resume, list candidates |
| `/candidates/:id` | Candidate detail, add contacts, trigger verifications |
| `/verifications` | All verification requests |
| `/reports` | Download PDF reports |
| `/settings` | SMTP, LLM, retention config |
| `/admin` | User management |
| `/consent/:token` | Public — candidate consent page |
| `/verify-response/:token` | Public — employer verification form |
| `/verify-email` | Email verification callback |

---

## API Endpoints

### Auth
- `POST /api/v1/auth/register` — Register organization
- `GET  /api/v1/auth/verify-email?token=` — Verify email
- `POST /api/v1/auth/login` — Login
- `POST /api/v1/auth/refresh` — Refresh token

### Candidates
- `POST   /api/v1/candidates/` — Upload resume
- `GET    /api/v1/candidates/` — List candidates
- `GET    /api/v1/candidates/:id` — Candidate detail
- `PATCH  /api/v1/candidates/:id/employment/:rid/contact` — Set HR email
- `PATCH  /api/v1/candidates/:id/education/:rid/contact` — Set registrar email
- `POST   /api/v1/candidates/:id/send-verifications` — Trigger verification emails
- `GET    /api/v1/candidates/:id/report` — Download PDF report
- `DELETE /api/v1/candidates/:id` — GDPR erasure
- `GET    /api/v1/candidates/:id/export` — GDPR data export

### Dashboard & Other
- `GET  /api/v1/dashboard/stats` — Dashboard stats + chart data
- `GET  /api/v1/dashboard/activity` — Recent audit log
- `GET  /api/v1/notifications` — User notifications
- `POST /api/v1/notifications/:id/read` — Mark read
- `GET  /api/v1/settings` — Organization settings
- `PATCH /api/v1/settings` — Update settings
- `GET  /api/v1/users` — List users (admin)
- `POST /api/v1/users` — Create user (admin)

### Public (no auth)
- `GET  /api/v1/consent/:token` — Consent info
- `POST /api/v1/consent/:token/respond?action=accept|decline` — Respond
- `GET  /api/v1/verify-response/:token` — Verification form
- `POST /api/v1/verify-response/:token` — Submit response

---

## Deployment on Render.com

### Prerequisites
- GitHub repo with this code
- Render account (free tier)

### Steps

1. Push to GitHub
2. Go to Render → **New** → **Blueprint**
3. Connect your repo
4. Render reads `render.yaml` automatically
5. Set environment variables in the Render dashboard:
   - `ENCRYPTION_KEY` (exactly 32 chars)
   - `FRONTEND_URL` (your frontend service URL)
   - `SMTP_*` (your email settings)
   - `GEMINI_API_KEY`
   - `CORS_ORIGINS` (your frontend URL)
6. Deploy

**Note:** Free tier services spin down after inactivity. Upgrade to Starter ($7/mo) for always-on.

---

## Development

### Backend only

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your config

# Run migrations
alembic upgrade head

# Start API
uvicorn app.main:app --reload

# Start worker (separate terminal)
celery -A app.tasks.celery_app worker --loglevel=info
```

### Frontend only

```bash
cd frontend
npm install
# Create .env.local:
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
npm run dev
```

### Run tests

```bash
cd backend
pip install aiosqlite  # for in-memory test DB
pytest --cov=app tests/ -v
```

---

## Security

- Passwords hashed with bcrypt
- PII (email, phone) encrypted with AES-256 (Fernet) at rest
- JWT access tokens (30min) + refresh tokens (7 days)
- Role-based access: `super_admin`, `org_admin`, `recruiter`, `reviewer`
- Immutable audit logs for all actions
- GDPR: data export + erasure endpoints
- All consent records include timestamp, IP, user-agent, version

---

## GDPR Compliance

| Feature | Endpoint |
|---|---|
| Data Export | `GET /api/v1/candidates/:id/export` |
| Data Erasure | `DELETE /api/v1/candidates/:id` |
| Consent Record | Stored with IP, timestamp, version |
| Retention Policy | Configurable in Settings |

---

## Environment Variables Reference

| Variable | Description | Required |
|---|---|---|
| `DATABASE_URL` | PostgreSQL async URL | ✓ |
| `SECRET_KEY` | App secret (32+ chars) | ✓ |
| `JWT_SECRET_KEY` | JWT signing key | ✓ |
| `ENCRYPTION_KEY` | AES key (exactly 32 chars) | ✓ |
| `SMTP_HOST` | SMTP server | ✓ for email |
| `SMTP_USER` | SMTP username | ✓ for email |
| `SMTP_PASSWORD` | SMTP password | ✓ for email |
| `FRONTEND_URL` | Frontend base URL (for email links) | ✓ |
| `GEMINI_API_KEY` | Google Gemini API key | For AI |
| `OPENROUTER_API_KEY` | OpenRouter API key | Fallback AI |
| `REDIS_URL` | Redis connection URL | ✓ |
| `CELERY_BROKER_URL` | Celery broker (Redis) | ✓ |

---

## License

MIT — free to use, modify, and deploy.
