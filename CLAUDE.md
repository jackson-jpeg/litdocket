# LitDocket - AI Docketing Assistant

## Project Overview

Enterprise legal docketing software that combines CompuLaw-style rules-based deadline calculation with AI document analysis. Built for attorneys managing complex litigation with fatal deadlines.

**Production URLs:**
- Frontend: https://frontend-five-azure-58.vercel.app
- Backend API: https://litdocket-production.up.railway.app
- API Docs: https://litdocket-production.up.railway.app/api/docs

## Technology Stack

### Frontend
- **Framework:** Next.js 14.1.0 (App Router)
- **Language:** TypeScript 5.3.3 (strict mode)
- **Styling:** Tailwind CSS 3.4.1 with enterprise legal aesthetic
- **State:** React hooks + context for auth
- **Auth:** Firebase Auth 12.7.0 (ID tokens exchanged for backend JWT)
- **Calendar:** React Big Calendar 1.19.4
- **PDF:** pdfjs-dist 4.4.168
- **Charts:** Recharts 3.6.0
- **Animations:** Framer Motion 12.26.2
- **Hosting:** Vercel

### Backend
- **Framework:** FastAPI 0.128.0
- **Language:** Python 3.11+
- **ORM:** SQLAlchemy 2.0.36+
- **Database:** PostgreSQL (Supabase/Railway)
- **Auth:** JWT tokens via `python-jose`, Firebase Admin 6.4.0
- **AI:** Anthropic Claude API (claude-sonnet-4-20250514)
- **Validation:** Pydantic 2.10.0+
- **Rate Limiting:** slowapi
- **Email:** SendGrid
- **Hosting:** Railway

## Directory Structure

```
litdocket/
├── frontend/                    # Next.js 14 App Router
│   ├── app/                     # Pages and layouts
│   │   ├── (auth)/             # Auth pages (login, signup, complete-profile)
│   │   ├── (protected)/        # Authenticated pages
│   │   │   ├── dashboard/      # Morning report
│   │   │   ├── cases/          # Case management + [caseId]/triggers
│   │   │   ├── calendar/       # Deadline calendar view
│   │   │   ├── ai-assistant/   # AI chat interface
│   │   │   ├── tools/          # deadline-calculator, document-analyzer, jurisdiction-selector
│   │   │   ├── settings/       # User settings
│   │   │   └── rules/          # Rules management
│   │   ├── (public)/           # Public pages (terms, privacy)
│   │   └── layout.tsx          # Root layout
│   ├── components/             # React components (20+)
│   │   ├── cases/              # Case-specific components
│   │   ├── calendar/           # Calendar components
│   │   ├── chat/               # Chat interface
│   │   ├── audit/              # Audit trail display
│   │   ├── jurisdiction/       # Jurisdiction selector
│   │   ├── rules/              # Rules display
│   │   └── layout/             # Layout components
│   ├── hooks/                  # Custom React hooks
│   ├── lib/                    # Utilities and services
│   │   ├── api-client.ts       # Axios instance with auth
│   │   ├── auth/               # Auth context and Firebase
│   │   └── config.ts           # Environment config
│   ├── types/                  # TypeScript type definitions
│   │   └── index.ts            # All interfaces (Case, Deadline, Document, etc.)
│   └── public/                 # Static assets
│
├── backend/
│   ├── app/
│   │   ├── api/v1/            # API route handlers (16 routers)
│   │   │   ├── auth.py        # Login/signup/token
│   │   │   ├── cases.py       # Case CRUD
│   │   │   ├── documents.py   # Document upload/viewing
│   │   │   ├── deadlines.py   # Deadline CRUD
│   │   │   ├── triggers.py    # Trigger events → deadline generation
│   │   │   ├── chat.py        # Non-streaming chat
│   │   │   ├── chat_stream.py # SSE streaming chat
│   │   │   ├── dashboard.py   # Morning report data
│   │   │   ├── search.py      # Case/deadline search
│   │   │   ├── insights.py    # Analytics
│   │   │   ├── verification.py # Deadline verification gate
│   │   │   ├── jurisdictions.py # Jurisdiction & rules
│   │   │   ├── rag_search.py  # Semantic search
│   │   │   ├── workload.py    # Workload optimization
│   │   │   ├── notifications.py # Notification management
│   │   │   └── rules.py       # User rule templates
│   │   ├── models/            # SQLAlchemy models (20+)
│   │   │   ├── enums.py       # Centralized enums (TriggerType, DeadlinePriority, etc.)
│   │   │   ├── user.py        # User model
│   │   │   ├── case.py        # Case model
│   │   │   ├── deadline.py    # Deadline model (80+ fields)
│   │   │   ├── document.py    # Document model
│   │   │   └── ...            # Additional models
│   │   ├── schemas/           # Pydantic request/response schemas
│   │   ├── services/          # Business logic (20+ services)
│   │   │   ├── rules_engine.py      # CompuLaw-style deadline calculation
│   │   │   ├── ai_service.py        # Claude API integration
│   │   │   ├── document_service.py  # PDF processing
│   │   │   ├── streaming_chat_service.py  # SSE chat
│   │   │   ├── rag_service.py       # Semantic search
│   │   │   ├── morning_report_service.py  # Dashboard data
│   │   │   └── ...                  # Additional services
│   │   ├── auth/              # JWT & Firebase auth
│   │   ├── middleware/        # Security middleware
│   │   ├── constants/         # Legal rules constants
│   │   ├── utils/             # Utilities (auth, deadline_calculator)
│   │   ├── seed/              # Database seeding
│   │   ├── config.py          # Settings and configuration
│   │   ├── database.py        # Database connection
│   │   └── main.py            # FastAPI app entry
│   ├── supabase/migrations/   # SQL migrations (010 versions)
│   ├── scripts/               # Utility scripts
│   ├── tests/                 # Test suite
│   └── requirements.txt       # Python dependencies
│
└── docs/archive/              # Historical documentation
```

## Security Standards (CRITICAL - LegalTech)

### Backend Security Rules
1. **Ownership Verification:** EVERY endpoint that accesses user data MUST filter by `user_id == str(current_user.id)`
2. **IDOR Prevention:** Never trust client-provided IDs without ownership check
3. **Input Validation:** All inputs validated via Pydantic schemas
4. **Error Handling:** Never expose stack traces to clients - use `detail` field with safe messages
5. **Secrets:** No secrets in code - use environment variables via `app.config.settings`
6. **Rate Limiting:** 5/min auth endpoints, 100/min default, 20/min AI endpoints

### Frontend Security Rules
1. **Auth Tokens:** JWT stored in localStorage with proper handling
2. **API Calls:** Always use `apiClient` from `lib/api-client.ts` (handles auth headers)
3. **User Input:** Sanitize before rendering (React handles most XSS)

### Example: Correct Ownership Check
```python
# CORRECT
deadline = db.query(Deadline).filter(
    Deadline.id == deadline_id,
    Deadline.user_id == str(current_user.id)  # Always filter by user
).first()

if not deadline:
    raise HTTPException(status_code=404, detail="Deadline not found")

# WRONG - IDOR vulnerability
deadline = db.query(Deadline).filter(Deadline.id == deadline_id).first()
```

## Coding Standards

### TypeScript (Frontend)
- **Strict Mode:** No `any` types - use proper interfaces from `types/index.ts`
- **Error Handling:** Use `catch (err: unknown)` with type narrowing, not `catch (err: any)`
- **Components:** Prefer Server Components, use `'use client'` only when needed
- **Imports:** Use `@/` alias for absolute imports
- **Styling:** Tailwind CSS with enterprise legal aesthetic (IBM-blue, serif fonts)

### Python (Backend)
- **Type Hints:** All function parameters and returns must be typed
- **Pydantic:** Use Pydantic models for request/response schemas
- **Async:** Use `async def` for all route handlers and I/O operations
- **Logging:** Use `logger = logging.getLogger(__name__)` - never print()
- **Enums:** Import from `app.models.enums` - single source of truth

### Database
- **UUIDs:** All primary keys are UUIDs stored as VARCHAR(36)
- **Soft Delete:** Prefer `status = 'archived'` over hard deletes for legal audit trails
- **Timestamps:** All models must have `created_at` and `updated_at` (server-side defaults)
- **Foreign Keys:** Use CASCADE delete for owned resources

## Key Business Logic

### Trigger-Based Deadline Calculation
The rules engine (`services/rules_engine.py`) implements CompuLaw-style deadline chains:
1. User enters a **trigger event** (trial date, complaint served, etc.)
2. System calculates **50+ dependent deadlines** automatically
3. If trigger date changes, all dependents cascade-update
4. Manually overridden deadlines are protected from auto-recalculation

### Trigger Types (from `models/enums.py`)
- `case_filed`, `complaint_served`, `answer_filed`
- `discovery_served`, `discovery_deadline`
- `motion_filed`, `motion_hearing`
- `trial_date`, `pretrial_conference`
- `mediation`, `arbitration`
- `appeal_filed`, `judgment_entered`
- `custom`

### Deadline Priorities
- **FATAL:** Jurisdictional deadlines - missing = case dismissal
- **CRITICAL:** Court-ordered deadlines
- **IMPORTANT:** Procedural deadlines with consequences
- **STANDARD:** Best practice deadlines
- **INFORMATIONAL:** Internal reminders

### Calculation Methods
- **calendar_days:** Standard calendar day calculation
- **business_days:** Excludes weekends and holidays
- **court_days:** Court-specific calculation rules

## Database Models

### Core Models
- **User** - Firebase + JWT auth, firm info, subscription tiers
- **Case** - Core case data with metadata JSON
- **Deadline** - Comprehensive deadline tracking (80+ fields)
- **Document** - PDF documents with extracted metadata
- **ChatMessage** - Conversation history

### Jurisdiction System
- **Jurisdiction** - State/federal/local courts (14 seeded)
- **RuleSet** - Court rules grouped by jurisdiction
- **RuleTemplate** - Trigger → Dependent Deadlines mapping
- **RuleTemplateDeadline** - Individual deadline templates
- **CourtLocation** - Court locations
- **LocalRule** - Local court-specific rules

### Supporting Models
- **DeadlineChain** - Trigger-dependent deadline chains
- **DeadlineDependency** - Explicit dependency relationships
- **DeadlineHistory** - Audit trail of changes
- **DocumentEmbedding** - RAG semantic search embeddings
- **AIExtractionFeedback** - Feedback for AI quality improvement
- **Notification** / **NotificationPreferences** - Alert system
- **CaseTemplate** - Quick case creation templates

## API Patterns

### Response Format
```python
# Success
return {"success": True, "data": {...}, "message": "..."}

# Error (via HTTPException)
raise HTTPException(status_code=404, detail="Resource not found")
```

### Pagination
```python
@router.get("/items")
async def list_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    ...
)
```

### Authentication
```python
@router.get("/resource")
async def get_resource(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Always filter by user_id
    items = db.query(Resource).filter(
        Resource.user_id == str(current_user.id)
    ).all()
```

## Testing

### Running Tests
```bash
# Backend
cd backend && pytest

# Frontend
cd frontend && npm run test
```

### Test Files
- `test_auth.py` - Authentication and JWT validation
- `test_deadline_calculator.py` - Deadline calculation logic
- `test_document_upload.py` - Document upload flow
- `test_florida_rule_2514.py` - Florida-specific rule testing

### Test Requirements
- All API endpoints must have ownership verification tests
- All business logic must have unit tests
- Integration tests for document upload → deadline extraction flow

## Development Setup

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## Environment Variables

### Backend
```
DATABASE_URL=postgresql://...
SUPABASE_DB_URL=postgresql://...  # Takes priority if set
JWT_SECRET_KEY=...
ANTHROPIC_API_KEY=...
FIREBASE_SERVICE_ACCOUNT=...  # JSON string
SENDGRID_API_KEY=...  # Optional
```

### Frontend
```
NEXT_PUBLIC_API_URL=...
NEXT_PUBLIC_FIREBASE_API_KEY=...
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=...
NEXT_PUBLIC_FIREBASE_PROJECT_ID=...
NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET=...
NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=...
NEXT_PUBLIC_FIREBASE_APP_ID=...
```

## Deployment

### Backend (Railway)
- Builder: NIXPACKS
- Deploy command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Restart policy: ON_FAILURE (max 10 retries)

### Frontend (Vercel)
- Framework: Next.js (auto-detected)
- Build command: `npm run build`
- Region: iad1 (US)

## Common Tasks

### Adding a New API Endpoint
1. Create route in `backend/app/api/v1/<resource>.py`
2. Add Pydantic schemas in `backend/app/schemas/<resource>.py`
3. Include `current_user: User = Depends(get_current_user)` for auth
4. Filter ALL queries by `user_id == str(current_user.id)`
5. Register router in `backend/app/main.py`

### Adding a New Frontend Page
1. Create page in `frontend/app/(protected)/<path>/page.tsx`
2. Use Server Components where possible
3. Add TypeScript interfaces to `types/index.ts`
4. Use `apiClient` for data fetching

### Adding a New Database Model
1. Create model in `backend/app/models/<model>.py`
2. Add necessary enums to `backend/app/models/enums.py`
3. Import in `backend/app/models/__init__.py`
4. Create migration in `backend/supabase/migrations/`
5. Add Pydantic schemas for API serialization

### Adding New Trigger Types or Rules
1. Update `TriggerType` enum in `backend/app/models/enums.py`
2. Add rule templates via the jurisdiction system
3. Update `services/rules_engine.py` if custom logic needed
4. Test with `test_deadline_calculator.py`

## Feature Status

### Implemented
- Case management (CRUD)
- Document upload & PDF viewing
- AI document analysis (Claude API)
- Trigger-based deadline generation (Florida + Federal rules)
- Calendar view with deadline visualization
- Morning report dashboard
- Chat with Claude
- Deadline verification (Case OS)
- Workload analytics
- Multi-jurisdiction support (14 jurisdictions seeded)

### Disabled/Incomplete
- WebSocket real-time collaboration (commented out in main.py)
- Pinecone vector database (not implemented)

### Future (Phase 3)
- Multi-user case access (models exist: CaseAccess, ActiveSession)
- Real-time collaboration
- Advanced RAG search

## Known Issues / Tech Debt
1. Some `any` types remain in event handlers - migrate to proper types
2. Calendar DnD library typing issues - use type assertion as workaround
3. Firebase auth bypass exists for local dev - ensure DEV_AUTH_BYPASS is never true in production
4. WebSocket routes disabled pending production testing

## Key Documentation Files
- `UPDATED_RULES_ARCHITECTURE.md` - Rules engine deep dive
- `DATABASE_SEEDED_CONFIRMATION.md` - Database seeding status
- `backend/LEGAL_DEFENSIBILITY_GUIDE.md` - Legal accuracy standards
- `frontend/PAPER_STEEL_DESIGN_SYSTEM.md` - Design system and typography
