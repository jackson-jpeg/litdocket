# LitDocket - AI Legal Docketing Assistant

Enterprise legal docketing software combining CompuLaw-style rules-based deadline calculation with AI document analysis.

**Status:** ✅ Production Ready | Database Seeded | Backend & Frontend Deployed

---

## Quick Links

- **Frontend:** https://frontend-five-azure-58.vercel.app
- **Backend API:** https://litdocket-production.up.railway.app
- **API Docs:** https://litdocket-production.up.railway.app/api/docs

---

## Current System Status

### ✅ Production Environment
- **Backend:** Railway (FastAPI + PostgreSQL)
- **Frontend:** Vercel (Next.js 14)
- **Database:** Supabase PostgreSQL (14 jurisdictions seeded)
- **Auth:** Firebase Authentication
- **AI:** Anthropic Claude API

### ✅ Features Working
- Case management
- Deadline tracking and calculation
- Trigger-based deadline generation (Florida + Federal rules active)
- PDF document upload and viewing
- AI-powered document analysis
- Calendar view
- Morning report dashboard

---

## Tech Stack

### Frontend
- **Framework:** Next.js 14 (App Router)
- **Styling:** Tailwind CSS (enterprise legal aesthetic)
- **Auth:** Firebase Auth → Backend JWT
- **State:** React hooks + context

### Backend
- **Framework:** FastAPI (Python 3.12)
- **ORM:** SQLAlchemy 2.0
- **Database:** PostgreSQL via Supabase
- **AI:** Anthropic Claude API
- **Auth:** JWT (python-jose)

---

## Getting Started

### Prerequisites
- Node.js 18+
- Python 3.12+
- PostgreSQL (or use Supabase)

### Local Development

```bash
# Clone the repo
git clone https://github.com/jackson-jpeg/litdocket.git
cd docketassist-v3

# Backend setup
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env  # Configure your env vars
uvicorn app.main:app --reload

# Frontend setup (new terminal)
cd frontend
npm install
cp .env.example .env.local  # Configure your env vars
npm run dev
```

### Environment Variables

**Backend (.env):**
```bash
DATABASE_URL=postgresql://...
JWT_SECRET_KEY=your-secret-key-here
ANTHROPIC_API_KEY=sk-ant-...
FIREBASE_SERVICE_ACCOUNT={"type":"service_account"...}
```

**Frontend (.env.local):**
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_FIREBASE_API_KEY=...
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=...
```

---

## Project Structure

```
docketassist-v3/
├── frontend/               # Next.js frontend
│   ├── app/               # App router pages
│   ├── components/        # React components
│   ├── lib/               # Utilities, API client, auth
│   └── types/             # TypeScript types
│
├── backend/               # FastAPI backend
│   ├── app/
│   │   ├── api/v1/        # API routes
│   │   ├── models/        # SQLAlchemy models
│   │   ├── schemas/       # Pydantic schemas
│   │   ├── services/      # Business logic
│   │   │   ├── rules_engine.py      # Deadline calculation
│   │   │   └── ai_service.py        # Claude integration
│   │   └── seed/          # Database seeding
│   ├── scripts/           # Utility scripts
│   │   └── seed_production.py  # Database seeding
│   └── supabase/migrations/    # Database migrations
│
└── docs/                  # Documentation
    └── archive/           # Historical docs
```

---

## Key Documentation

### Essential Docs (Root)
- **CLAUDE.md** - Project instructions and coding standards ⭐
- **UPDATED_RULES_ARCHITECTURE.md** - Current rules engine architecture
- **DATABASE_SEEDED_CONFIRMATION.md** - Database seeding status and next steps
- **SCRIPTS_CLEANUP_SUMMARY.md** - Backend scripts cleanup summary

### Backend Docs
- **backend/scripts/README.md** - Available backend scripts
- **backend/LEGAL_DEFENSIBILITY_GUIDE.md** - Legal accuracy standards
- **backend/SYSTEM_STATUS.md** - System status and fixes log

### Frontend Docs
- **frontend/PAPER_STEEL_DESIGN_SYSTEM.md** - Design system
- **frontend/FIXES_APPLIED.md** - Frontend fixes log

### Archived Docs
- **docs/archive/** - Historical planning and old status docs

---

## Rules Engine Overview

LitDocket uses a **trigger-based deadline calculation system** inspired by CompuLaw:

1. **User enters a trigger event** (e.g., "Complaint Served on Jan 15")
2. **System calculates 30+ dependent deadlines** automatically
3. **If trigger date changes, all deadlines cascade-update**
4. **Manual overrides are preserved** from auto-recalculation

### Current Coverage
- **14 Jurisdictions** seeded and active
- **Florida State Courts** - Full civil procedure rules
- **Federal Courts** - FRCP rules
- **2 Rule Templates:**
  - FL Complaint Served → 3 deadlines
  - FL Trial Date → 30+ deadlines

### Architecture
- **Jurisdiction** → **RuleSet** → **RuleTemplate** → **RuleTemplateDeadline**
- Supports service method extensions (mail, personal, etc.)
- Priority levels: FATAL, CRITICAL, IMPORTANT, STANDARD, INFORMATIONAL

See `UPDATED_RULES_ARCHITECTURE.md` for full details.

---

## Testing the System

### Test Trigger-Based Deadline Generation

1. **Login:** https://frontend-five-azure-58.vercel.app
2. **Open a case** (or create new one)
3. **Click "Add Trigger"**
4. **Select:**
   - Jurisdiction: Florida
   - Trigger Type: Complaint Served
   - Date: Any date
   - Service Method: Mail
5. **Click "Generate Deadlines"**

**Expected:** 3 deadlines appear automatically with correct dates calculated!

---

## Deployment

### Backend (Railway)
```bash
# Deploy via git push
git push origin main
# Railway auto-deploys from main branch

# Or manual deploy
railway up
```

### Frontend (Vercel)
```bash
# Deploy via git push
git push origin main
# Vercel auto-deploys from main branch

# Or manual deploy
vercel --prod
```

---

## Security Notes

**CRITICAL - LegalTech Security Standards:**

1. **Ownership Verification:** ALL endpoints filter by `user_id`
2. **IDOR Prevention:** Never trust client IDs without ownership check
3. **Input Validation:** All inputs validated via Pydantic
4. **No Secrets in Code:** Use environment variables only
5. **Audit Trail:** Soft deletes, timestamps on all models

See `CLAUDE.md` for full security standards.

---

## Database Seeding

**Status:** ✅ Production database already seeded (14 jurisdictions)

If you need to re-seed:
```bash
railway ssh --service litdocket
python scripts/seed_production.py
```

See `DATABASE_SEEDED_CONFIRMATION.md` for details.

---

## Recent Changes

### January 27, 2026
- ✅ Fixed backend 502 errors (deleted obsolete model files)
- ✅ Confirmed database seeded (14 jurisdictions)
- ✅ Cleaned up backend scripts directory
- ✅ Consolidated documentation (archived 18 obsolete .md files)

See commit history for full changelog.

---

## Contributing

### Code Style
- **TypeScript:** Strict mode, no `any` types
- **Python:** Type hints required, use Pydantic for validation
- **Testing:** Write tests for all business logic
- **Security:** Follow ownership verification patterns

See `CLAUDE.md` for full coding standards.

---

## Support

### Common Issues

**"Can't login"**
- Check Firebase config in frontend `.env.local`
- Verify backend JWT_SECRET_KEY is set

**"No jurisdictions in dropdown"**
- Database may not be seeded - see `DATABASE_SEEDED_CONFIRMATION.md`

**"Deadlines not generating"**
- Check browser console for errors
- Verify backend `/api/v1/triggers` endpoint is working

**"Railway deployment failing"**
- Check Railway logs for errors
- Verify all environment variables are set

---

## License

Proprietary - LitDocket

---

## Project History

LitDocket started as a deadline calculation tool and evolved into a comprehensive legal docketing system with:
- CompuLaw-style trigger-based deadline chains
- AI document analysis via Claude
- Enterprise-grade security and audit trails
- Multi-jurisdiction support

For historical planning docs and development notes, see `docs/archive/`.

---

**Last Updated:** January 27, 2026
**Version:** 1.0.0
**Status:** Production Ready ✅
