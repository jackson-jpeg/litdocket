# LitDocket - AI Docketing Assistant

## Project Overview
Enterprise legal docketing software that combines CompuLaw-style rules-based deadline calculation with AI document analysis. Built for attorneys managing complex litigation with fatal deadlines.

## Technology Stack

### Frontend
- **Framework:** Next.js 14+ (App Router)
- **Styling:** Tailwind CSS with enterprise legal aesthetic (IBM-blue, serif fonts, dense data)
- **State:** React hooks + context for auth
- **Auth:** Firebase Auth (ID tokens exchanged for backend JWT)
- **Hosting:** Vercel

### Backend
- **Framework:** FastAPI (Python 3.11+)
- **ORM:** SQLAlchemy 2.0
- **Database:** PostgreSQL (Railway)
- **Auth:** JWT tokens via `python-jose`
- **AI:** Anthropic Claude API
- **Hosting:** Railway

## Directory Structure

```
/frontend
├── app/                    # Next.js App Router pages
│   ├── (auth)/            # Auth pages (login, signup)
│   ├── (protected)/       # Authenticated pages
│   │   ├── cases/         # Case management
│   │   ├── calendar/      # Deadline calendar
│   │   └── dashboard/     # Morning report
├── components/            # React components
├── hooks/                 # Custom React hooks
├── lib/                   # Utilities and services
│   ├── api-client.ts     # Axios instance with auth
│   ├── auth/             # Auth context and Firebase
│   └── config.ts         # Environment config
├── types/                 # TypeScript type definitions
└── tailwind.config.ts    # Tailwind with enterprise colors

/backend
├── app/
│   ├── api/v1/           # API route handlers
│   ├── models/           # SQLAlchemy models
│   ├── schemas/          # Pydantic schemas
│   ├── services/         # Business logic
│   │   ├── rules_engine.py    # CompuLaw-style deadline calculation
│   │   ├── ai_service.py      # Claude API integration
│   │   └── document_service.py # PDF processing
│   └── utils/            # Utilities (auth, PDF parsing)
├── alembic/              # Database migrations
└── main.py               # FastAPI app entry
```

## Security Standards (CRITICAL - LegalTech)

### Backend Security Rules
1. **Ownership Verification:** EVERY endpoint that accesses user data MUST filter by `user_id == str(current_user.id)`
2. **IDOR Prevention:** Never trust client-provided IDs without ownership check
3. **Input Validation:** All inputs validated via Pydantic schemas
4. **Error Handling:** Never expose stack traces to clients - use `detail` field with safe messages
5. **Secrets:** No secrets in code - use environment variables via `app.config.settings`

### Frontend Security Rules
1. **Auth Tokens:** Never store JWT in localStorage - use httpOnly cookies or memory
2. **API Calls:** Always use `apiClient` from `lib/api-client.ts` (handles auth headers)
3. **User Input:** Sanitize before rendering (React handles most XSS, but be careful with `dangerouslySetInnerHTML`)

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

### Python (Backend)
- **Type Hints:** All function parameters and returns must be typed
- **Pydantic:** Use Pydantic models for request/response schemas
- **Async:** Use `async def` for all route handlers and I/O operations
- **Logging:** Use `logger = logging.getLogger(__name__)` - never print()

### Database
- **UUIDs:** All primary keys are UUIDs stored as strings
- **Soft Delete:** Prefer `status = 'archived'` over hard deletes for legal audit trails
- **Timestamps:** All models must have `created_at` and `updated_at`

## Key Business Logic

### Trigger-Based Deadline Calculation
The rules engine (`services/rules_engine.py`) implements CompuLaw-style deadline chains:
1. User enters a **trigger event** (trial date, complaint served, etc.)
2. System calculates **50+ dependent deadlines** automatically
3. If trigger date changes, all dependents cascade-update
4. Manually overridden deadlines are protected from auto-recalculation

### Deadline Priorities
- **FATAL:** Jurisdictional deadlines - missing = case dismissal
- **CRITICAL:** Court-ordered deadlines
- **IMPORTANT:** Procedural deadlines with consequences
- **STANDARD:** Best practice deadlines
- **INFORMATIONAL:** Internal reminders

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

## Testing

### Running Tests
```bash
# Backend
cd backend && pytest

# Frontend
cd frontend && npm run test
```

### Test Requirements
- All API endpoints must have ownership verification tests
- All business logic must have unit tests
- Integration tests for document upload → deadline extraction flow

## Deployment

### Environment Variables Required
```
# Backend
DATABASE_URL=postgresql://...
JWT_SECRET_KEY=...
ANTHROPIC_API_KEY=...
FIREBASE_SERVICE_ACCOUNT=...

# Frontend
NEXT_PUBLIC_API_URL=...
NEXT_PUBLIC_FIREBASE_*=...
```

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

## Known Issues / Tech Debt
1. Some `any` types remain in event handlers - migrate to proper types
2. Calendar DnD library typing issues - use type assertion as workaround
3. Firebase auth bypass exists for local dev - ensure DEV_AUTH_BYPASS is never true in production
