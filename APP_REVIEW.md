# LitDocket Application Architecture Review

**Last Updated:** 2026-01-23
**Version:** 1.0
**Purpose:** Comprehensive technical documentation of the LitDocket application architecture, data flows, and integration points.

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [System Architecture Overview](#system-architecture-overview)
3. [Frontend Architecture](#frontend-architecture)
4. [Backend Architecture](#backend-architecture)
5. [Database Schema](#database-schema)
6. [Feature Deep Dives](#feature-deep-dives)
7. [Integration Points](#integration-points)
8. [Security & Compliance](#security--compliance)
9. [Data Flow Examples](#data-flow-examples)
10. [Development Workflows](#development-workflows)
11. [Deployment Architecture](#deployment-architecture)
12. [Known Issues & Tech Debt](#known-issues--tech-debt)

---

## Executive Summary

**LitDocket** is an enterprise legal docketing application that combines CompuLaw-style rules-based deadline calculation with AI-powered document analysis. The system is designed for attorneys managing complex litigation where missing a deadline can result in malpractice.

### Core Value Proposition
- **Trigger-Based Deadline Generation**: One event (trial date) generates 50+ dependent deadlines automatically
- **AI Document Analysis**: Upload court documents and auto-extract case metadata, dates, and deadlines
- **Legal Defensibility**: Complete audit trail with rule citations and calculation transparency
- **Professional UX**: Dense, data-rich interface optimized for power users (Sovereign Design System)

### Technology Stack
- **Frontend**: Next.js 14 (App Router), TypeScript, Tailwind CSS, Firebase Auth
- **Backend**: FastAPI, SQLAlchemy 2.0, PostgreSQL (Supabase), Claude AI
- **Infrastructure**: Vercel (frontend), Railway (backend), Supabase (database)

---

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENT TIER                              │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Next.js 14 Frontend (Vercel)                            │   │
│  │  - React Server Components + Client Components          │   │
│  │  - Tailwind CSS (Sovereign Design System)               │   │
│  │  - Firebase Auth Context                                │   │
│  │  - Event Bus for Real-Time Updates                      │   │
│  │  - Axios API Client with JWT Interceptors               │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              ↕ HTTPS/WSS
┌─────────────────────────────────────────────────────────────────┐
│                      APPLICATION TIER                            │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  FastAPI Backend (Railway)                               │   │
│  │  ┌────────────┬────────────┬──────────────┬───────────┐  │   │
│  │  │ API Routes │  Services  │ Rules Engine │ AI Service│  │   │
│  │  │            │            │              │           │  │   │
│  │  │ - Auth     │ - Deadline │ - Trigger    │ - Claude  │  │   │
│  │  │ - Cases    │ - Document │   Templates  │   API     │  │   │
│  │  │ - Deadlines│ - Calendar │ - Calculator │ - Streaming│ │   │
│  │  │ - Chat     │ - Dashboard│ - Confidence │ - Tools   │  │   │
│  │  └────────────┴────────────┴──────────────┴───────────┘  │   │
│  │  ┌────────────────────────────────────────────────────┐  │   │
│  │  │ Middleware: Security, Rate Limiting, Auth          │  │   │
│  │  └────────────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              ↕ SQL
┌─────────────────────────────────────────────────────────────────┐
│                         DATA TIER                                │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  PostgreSQL (Supabase)                                   │   │
│  │  - Users, Cases, Deadlines, Documents                    │   │
│  │  - Deadline Chains, Histories, Dependencies              │   │
│  │  - Chat Messages, Notifications, Calendar Events         │   │
│  │  - pgvector for RAG embeddings                           │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              ↕
┌─────────────────────────────────────────────────────────────────┐
│                    EXTERNAL SERVICES                             │
│  - Firebase Auth (User authentication)                           │
│  - Anthropic Claude API (Document analysis, Chat, Insights)      │
│  - AWS S3 (Document storage with presigned URLs)                 │
│  - SendGrid (Email notifications - optional)                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## Frontend Architecture

### Directory Structure

```
frontend/
├── app/                                    # Next.js App Router
│   ├── layout.tsx                          # Root layout
│   ├── (auth)/                             # Auth pages (unauthenticated)
│   │   ├── login/page.tsx
│   │   ├── signup/page.tsx
│   │   └── complete-profile/page.tsx
│   ├── (public)/                           # Public pages
│   │   ├── privacy/page.tsx
│   │   └── terms/page.tsx
│   └── (protected)/                        # Authenticated pages
│       ├── dashboard/page.tsx              # War Room Intelligence Dashboard
│       ├── cases/
│       │   ├── page.tsx                    # All Cases portfolio view
│       │   └── [caseId]/page.tsx           # Case Room (3-pane Cockpit)
│       ├── calendar/page.tsx               # Deadline calendar
│       ├── tools/                          # Standalone tools
│       │   ├── document-analyzer/
│       │   ├── jurisdiction-selector/
│       │   └── deadline-calculator/
│       └── settings/page.tsx               # User settings
│
├── components/                             # React components
│   ├── layout/
│   │   ├── CockpitLayout.tsx               # Fixed viewport container
│   │   ├── CockpitHeader.tsx               # Top navigation bar
│   │   ├── Sidebar.tsx                     # Left navigation
│   │   └── AITerminal.tsx                  # Bottom AI chat interface
│   ├── cases/
│   │   ├── deadlines/
│   │   │   ├── DeadlineTable.tsx           # Master data grid
│   │   │   ├── DeadlineDetailModal.tsx     # Detail inspector
│   │   │   ├── DeadlineChainView.tsx       # Dependency visualization
│   │   │   └── SimpleDeadlineModal.tsx     # Quick deadline creation
│   │   ├── triggers/
│   │   │   ├── AddTriggerModal.tsx
│   │   │   ├── EditTriggerModal.tsx
│   │   │   ├── TriggerCard.tsx
│   │   │   ├── SmartEventEntry.tsx         # Command bar input
│   │   │   └── TriggerAlertBar.tsx
│   │   ├── CaseQuickView.tsx               # Quick-view drawer
│   │   ├── ContextMenu.tsx                 # Right-click menu
│   │   └── JurisdictionSelector.tsx        # Jurisdiction picker
│   ├── GlobalSearch.tsx                    # Unified search
│   ├── DocumentViewer.tsx                  # PDF viewer
│   ├── MatterHealthCards.tsx               # Case health indicators
│   ├── CaseInsights.tsx                    # AI-generated insights
│   └── Toast.tsx                           # Notification system
│
├── hooks/                                  # Custom React hooks
│   ├── useCaseData.ts                      # Main case data fetching
│   ├── useCaseSync.ts                      # Event-based synchronization
│   ├── useStreamingChat.ts                 # SSE chat streaming
│   ├── useCaseDeadlineFilters.ts           # Deadline filtering logic
│   ├── useCalendarDeadlines.ts             # Calendar event management
│   ├── useRealTimeCase.ts                  # Real-time updates
│   ├── useNotifications.ts                 # Notification handling
│   └── useKeyboardShortcuts.ts             # Keyboard navigation
│
├── lib/                                    # Utilities and services
│   ├── api-client.ts                       # Axios instance with auth
│   ├── config.ts                           # API URL validation
│   ├── auth/
│   │   ├── auth-context.tsx                # Firebase auth context
│   │   └── firebase-config.ts              # Firebase config
│   ├── eventBus.ts                         # Event system
│   ├── formatters.ts                       # Date/time formatters
│   ├── sovereign-calculator.ts             # Deadline math library
│   └── validation.ts                       # Form validation
│
└── types/
    └── index.ts                            # TypeScript interfaces
```

### Key Frontend Technologies

| Technology | Purpose | Version |
|------------|---------|---------|
| Next.js | React framework with App Router | 14+ |
| TypeScript | Type safety | 5+ |
| Tailwind CSS | Utility-first styling | 3+ |
| Firebase Auth | User authentication | 10+ |
| Axios | HTTP client with interceptors | 1+ |
| react-big-calendar | Calendar component | 1+ |
| react-pdf | PDF viewing | 7+ |
| Recharts | Data visualization | 2+ |
| lucide-react | Icon library | Latest |

### State Management Architecture

LitDocket uses a **hybrid state management approach**:

1. **Server State**: React Server Components (default in Next.js 14)
2. **Client State**: React hooks + Context API
3. **Event-Driven Updates**: Custom Event Bus for cross-component communication

#### Event Bus Pattern

**Implementation** (`lib/eventBus.ts`):
```typescript
// Simple pub/sub pattern
const eventBus = {
  on: (event: string, callback: Function) => { /* subscribe */ },
  emit: (event: string, data?: any) => { /* publish */ },
  off: (event: string, callback: Function) => { /* unsubscribe */ }
};
```

**Key Events**:
- `deadline:created`, `deadline:updated`, `deadline:deleted`, `deadline:completed`
- `deadlines:bulk-updated`
- `trigger:created`, `trigger:deleted`
- `document:uploaded`, `document:analyzed`
- `case:updated`
- `chat:action-taken`
- `calendar:refresh`, `insights:refresh`

**Usage Pattern**:
```typescript
// Component A: Publishes event after API call
const handleCreateDeadline = async () => {
  await apiClient.post('/deadlines', data);
  eventBus.emit('deadline:created', { deadlineId });
};

// Component B: Subscribes to event
useEventBus('deadline:created', () => {
  refreshDeadlines();
});
```

### Authentication Flow (Frontend)

```
User enters credentials
    ↓
Firebase.signInWithEmailAndPassword(email, password)
    ↓
Firebase returns { user, idToken }
    ↓
POST /api/v1/auth/login/firebase { idToken }
    ↓
Backend returns { token: "jwt_token", user: {...} }
    ↓
Store JWT in localStorage
    ↓
Axios interceptor adds "Authorization: Bearer {jwt}" to all requests
    ↓
On 401 response → Clear localStorage → Redirect to /login
```

**Key Files**:
- `lib/auth/auth-context.tsx` - Firebase auth state management
- `lib/api-client.ts` - Axios interceptors for JWT injection

### UI/UX Design System (Sovereign Design)

**Philosophy**: "Density is Reliability" - CompuLaw-grade professional interface for power users

**Design Principles**:
1. **Information Density**: Show maximum data without scrolling
2. **Visual Hierarchy**: Color-coded priority indicators
3. **Contextual Actions**: Right-click menus, bulk actions, keyboard shortcuts
4. **Legal Aesthetics**: Serif fonts, legal pad yellow, IBM blue, professional feel

**Key Visual Patterns**:
- **Health Bar Indicators**: Left border colors (red = overdue, yellow = urgent, green = on track)
- **Legal Pad Zebra Stripes**: Alternating cream/white rows in tables
- **"DONE" Stamp Effect**: Visual indicator for completed items
- **Tabular Numerals**: Monospace numbers for date alignment
- **3-Pane Cockpit Layout**: Fixed viewport, no scrolling

**Color Palette**:
```css
--ibm-blue: #1f2937
--legal-pad-yellow: #fffbea
--fatal-red: #dc2626
--critical-orange: #f97316
--important-amber: #f59e0b
--standard-slate: #64748b
--done-green: #16a34a
```

---

## Backend Architecture

### Directory Structure

```
backend/
├── app/
│   ├── main.py                             # FastAPI entry point
│   ├── config.py                           # Configuration management
│   ├── database.py                         # SQLAlchemy setup
│   │
│   ├── models/                             # SQLAlchemy ORM models
│   │   ├── user.py                         # User model
│   │   ├── case.py                         # Case model
│   │   ├── deadline.py                     # Deadline model (most complex)
│   │   ├── document.py                     # Document model
│   │   ├── deadline_chain.py               # Deadline dependency chains
│   │   ├── deadline_history.py             # Audit trail
│   │   ├── deadline_dependency.py          # Dependency relationships
│   │   ├── chat_message.py                 # Chat history
│   │   ├── notification.py                 # Notifications
│   │   ├── jurisdiction.py                 # Jurisdiction rules
│   │   ├── calendar_event.py               # Calendar events
│   │   ├── case_access.py                  # Multi-user collaboration
│   │   └── enums.py                        # Centralized enums
│   │
│   ├── api/v1/                             # API route handlers
│   │   ├── router.py                       # Route registration
│   │   ├── auth.py                         # Authentication endpoints
│   │   ├── cases.py                        # Case CRUD + operations
│   │   ├── deadlines.py                    # Deadline management
│   │   ├── documents.py                    # Document upload/analysis
│   │   ├── triggers.py                     # Trigger-based deadline generation
│   │   ├── chat.py                         # Non-streaming chat
│   │   ├── chat_stream.py                  # SSE streaming chat
│   │   ├── dashboard.py                    # Dashboard intelligence
│   │   ├── calendar.py                     # Calendar data
│   │   ├── search.py                       # Global search
│   │   ├── insights.py                     # AI-generated case insights
│   │   ├── verification.py                 # Case OS verification gate
│   │   ├── notifications.py                # Notification management
│   │   └── jurisdictions.py                # Jurisdiction system
│   │
│   ├── services/                           # Business logic layer
│   │   ├── rules_engine.py                 # Trigger-based deadline calculation
│   │   ├── ai_service.py                   # Claude API integration
│   │   ├── document_service.py             # PDF parsing + AI analysis
│   │   ├── deadline_service.py             # Deadline operations
│   │   ├── dashboard_service.py            # Dashboard data aggregation
│   │   ├── streaming_chat_service.py       # SSE chat streaming
│   │   ├── chat_service.py                 # Non-streaming chat
│   │   ├── chat_tools.py                   # AI tool definitions
│   │   ├── calendar_service.py             # Calendar operations
│   │   ├── case_summary_service.py         # AI case summaries
│   │   ├── jurisdiction_detector.py        # Auto-detect court jurisdiction
│   │   ├── confidence_scoring.py           # Deadline confidence metrics
│   │   ├── notification_service.py         # Alert generation
│   │   ├── firebase_service.py             # Firebase integration
│   │   ├── approval_manager.py             # Tool approval workflow
│   │   ├── rag_service.py                  # Document embeddings (RAG)
│   │   ├── case_context_builder.py         # Build case context for AI
│   │   ├── morning_report_service.py       # Daily briefing generation
│   │   ├── rule_ingestion_service.py       # Jurisdiction rule loading
│   │   └── supabase_client.py              # Supabase connection
│   │
│   ├── utils/                              # Utilities
│   │   ├── auth.py                         # JWT creation/verification
│   │   ├── deadline_calculator.py          # Authoritative deadline math
│   │   ├── pdf_parser.py                   # PDF text extraction
│   │   ├── florida_holidays.py             # Court holiday calendar
│   │   └── db_backup.py                    # Database utilities
│   │
│   ├── constants/                          # Business constants
│   │   ├── legal_rules.py                  # Service extensions, rule citations
│   │   └── court_rules_knowledge.py        # Court rule templates
│   │
│   ├── middleware/                         # Middleware
│   │   ├── security.py                     # Rate limiting, security headers
│   │   └── __init__.py
│   │
│   ├── schemas/                            # Pydantic schemas
│   │   ├── deadline.py                     # Deadline request/response
│   │   └── [other schemas]
│   │
│   └── auth/                               # Authentication
│       ├── jwt_handler.py                  # JWT token management
│       ├── firebase_auth.py                # Firebase verification
│       └── middleware.py                   # Auth middleware
│
├── alembic/                                # Database migrations
│   ├── env.py
│   └── versions/
│
└── requirements.txt                        # Python dependencies
```

### Key Backend Technologies

| Technology | Purpose | Version |
|------------|---------|---------|
| FastAPI | Web framework | 0.128.0 |
| SQLAlchemy | ORM | 2.0+ |
| PostgreSQL | Database | 15+ |
| Anthropic SDK | Claude AI integration | Latest |
| PyPDF2 | PDF text extraction | 3+ |
| python-jose | JWT handling | 3+ |
| firebase-admin | Firebase auth verification | 6+ |
| sse-starlette | Server-Sent Events | 2+ |
| slowapi | Rate limiting | 0.1+ |

### API Architecture Patterns

#### 1. Ownership Verification (CRITICAL - IDOR Prevention)

**Every endpoint that accesses user-owned resources MUST filter by user_id:**

```python
# ✅ CORRECT - Always filter by user_id
@router.get("/deadlines/{deadline_id}")
async def get_deadline(
    deadline_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    deadline = db.query(Deadline).filter(
        Deadline.id == deadline_id,
        Deadline.user_id == str(current_user.id)  # CRITICAL
    ).first()

    if not deadline:
        raise HTTPException(status_code=404, detail="Deadline not found")

    return {"success": True, "data": deadline}

# ❌ WRONG - IDOR vulnerability
deadline = db.query(Deadline).filter(Deadline.id == deadline_id).first()
```

#### 2. Standard Response Format

```python
# Success response
{
    "success": True,
    "data": { ... },
    "message": "Operation completed successfully"
}

# Error response (via HTTPException)
{
    "detail": "Safe error message for client",
    "error": "specific_error_code"  # optional
}
```

#### 3. Pagination Pattern

```python
@router.get("/items")
async def list_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    items = db.query(Item).filter(
        Item.user_id == str(current_user.id)
    ).offset(skip).limit(limit).all()

    return {"success": True, "data": items}
```

### Security Implementation

#### Rate Limiting

**Configuration** (`middleware/security.py`):
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

# Default: 100 requests/minute
@limiter.limit("100/minute")
async def default_endpoint(): ...

# Auth: 5 requests/minute (brute force protection)
@limiter.limit("5/minute")
async def login(): ...

# Uploads: 10 requests/minute
@limiter.limit("10/minute")
async def upload_document(): ...

# AI: 20 requests/minute
@limiter.limit("20/minute")
async def chat(): ...
```

#### Security Headers

```python
headers = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()"
}
```

#### Input Validation

1. **Pydantic Schemas**: All request bodies validated via Pydantic models
2. **PDF Validation**: Magic number check (`%PDF-`) before processing
3. **SQL Injection**: Prevented by SQLAlchemy ORM (parameterized queries)
4. **XSS**: Frontend React handles escaping, backend returns JSON only

---

## Database Schema

### Entity Relationship Diagram

```
┌─────────────┐
│    User     │
│─────────────│
│ id (PK)     │──┐
│ firebase_uid│  │
│ email       │  │
│ firm_name   │  │
│ role        │  │
└─────────────┘  │
                 │
      ┌──────────┴───────────────┬──────────────┬────────────────┐
      │                          │              │                │
      ▼                          ▼              ▼                ▼
┌─────────────┐          ┌─────────────┐  ┌──────────┐  ┌──────────────┐
│    Case     │          │  Document   │  │ Deadline │  │ ChatMessage  │
│─────────────│          │─────────────│  │──────────│  │──────────────│
│ id (PK)     │──┐       │ id (PK)     │  │ id (PK)  │  │ id (PK)      │
│ user_id (FK)│  │       │ case_id (FK)│  │ case_id  │  │ case_id (FK) │
│ case_number │  │       │ user_id (FK)│  │ user_id  │  │ user_id (FK) │
│ court       │  │       │ file_type   │  │ ...      │  │ message      │
│ jurisdiction│  │       │ storage_path│  └──────────┘  │ role         │
│ ...         │  │       │ ai_summary  │                └──────────────┘
└─────────────┘  │       └─────────────┘
                 │
      ┌──────────┴──────────────────┬─────────────────┐
      │                             │                 │
      ▼                             ▼                 ▼
┌─────────────────┐        ┌──────────────────┐  ┌───────────────┐
│ DeadlineChain   │        │ DeadlineHistory  │  │ Notification  │
│─────────────────│        │──────────────────│  │───────────────│
│ id (PK)         │        │ id (PK)          │  │ id (PK)       │
│ case_id (FK)    │        │ deadline_id (FK) │  │ user_id (FK)  │
│ parent_deadline │        │ changed_by (FK)  │  │ deadline_id   │
│ trigger_event   │        │ field_changed    │  │ ...           │
│ ...             │        │ old_value        │  └───────────────┘
└─────────────────┘        │ new_value        │
                           └──────────────────┘
```

### Core Models

#### User Model

**Purpose**: User account and authentication
**File**: `backend/app/models/user.py`

```python
class User:
    id: str (UUID, PK)
    firebase_uid: str (unique)
    email: str (unique)
    first_name: str
    last_name: str
    firm_name: Optional[str]
    role: str (attorney, paralegal, admin)
    default_jurisdiction: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    # Relationships
    cases: List[Case]
    documents: List[Document]
    deadlines: List[Deadline]
    chat_messages: List[ChatMessage]
```

#### Case Model

**Purpose**: Legal matter container
**File**: `backend/app/models/case.py`

```python
class Case:
    id: str (UUID, PK)
    user_id: str (FK → User)
    case_number: str (unique per user)
    case_name: str
    court: Optional[str]
    jurisdiction: Optional[str]
    judge: Optional[str]
    case_type: Optional[str]
    status: str (active, archived, closed)
    parties_plaintiff: Optional[str]
    parties_defendant: Optional[str]
    lead_attorney: Optional[str]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    # Relationships
    documents: List[Document]
    deadlines: List[Deadline]
    chat_messages: List[ChatMessage]
    deadline_chains: List[DeadlineChain]
    access_grants: List[CaseAccess]

    # Unique constraint: (user_id, case_number)
```

#### Deadline Model (Most Complex)

**Purpose**: Legal deadlines with full audit trail and calculation transparency
**File**: `backend/app/models/deadline.py`

```python
class Deadline:
    # Primary keys and relationships
    id: str (UUID, PK)
    case_id: str (FK → Case)
    user_id: str (FK → User)
    document_id: Optional[str] (FK → Document)

    # Core deadline data
    title: str
    description: Optional[str]
    deadline_date: date
    priority: str (FATAL, CRITICAL, IMPORTANT, STANDARD, INFORMATIONAL)
    status: str (pending, completed, overdue, dismissed)

    # Trigger and calculation fields
    trigger_event: Optional[str]
    trigger_date: Optional[date]
    is_calculated: bool (auto-generated vs manual)
    is_dependent: bool (part of a chain)
    parent_deadline_id: Optional[str] (FK → Deadline)
    auto_recalculate: bool (update when trigger changes)

    # Legal defensibility
    rule_citation: Optional[str] (e.g., "FRCP 12(a)(1)(A)(i)")
    calculation_basis: Optional[str] (step-by-step calculation explanation)

    # Confidence scoring
    confidence_score: Optional[float] (0-100)
    verification_status: str (pending, approved, rejected, modified)
    source_page: Optional[int]
    source_text: Optional[str]

    # Manual override tracking
    is_manually_overridden: bool
    override_user_id: Optional[str] (FK → User)
    override_timestamp: Optional[datetime]
    override_reason: Optional[str]
    original_deadline_date: Optional[date] (preserved for audit)

    # Audit trail
    modified_by: Optional[str] (FK → User)
    modification_reason: Optional[str]
    verified_by: Optional[str] (FK → User)
    verified_at: Optional[datetime]
    verification_notes: Optional[str]

    # Timestamps
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    # Relationships
    case: Case
    document: Optional[Document]
    user: User
    override_user: Optional[User]
    verified_by_user: Optional[User]
    history: List[DeadlineHistory]
    chains: List[DeadlineChain]
    dependencies: List[DeadlineDependency]
```

#### Document Model

**Purpose**: Store uploaded documents with AI analysis
**File**: `backend/app/models/document.py`

```python
class Document:
    id: str (UUID, PK)
    case_id: str (FK → Case)
    user_id: str (FK → User)

    # File metadata
    filename: str
    file_type: str (pdf, docx, jpg, etc.)
    file_size_bytes: int
    storage_path: str (S3 key)
    presigned_url: Optional[str] (temporary download URL)
    presigned_url_expires_at: Optional[datetime]

    # AI analysis
    analysis_status: str (pending, processing, completed, failed)
    extracted_text: Optional[str]
    ai_summary: Optional[str]
    extracted_metadata: Optional[dict] (JSON)

    # Timestamps
    uploaded_at: datetime
    analyzed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    # Relationships
    case: Case
    user: User
    deadlines: List[Deadline]
    embeddings: List[DocumentEmbedding]
```

#### DeadlineChain Model

**Purpose**: Track trigger-based deadline dependencies
**File**: `backend/app/models/deadline_chain.py`

```python
class DeadlineChain:
    id: str (UUID, PK)
    case_id: str (FK → Case)
    parent_deadline_id: str (FK → Deadline) # The trigger
    dependent_deadline_id: str (FK → Deadline) # The generated deadline
    trigger_event: str (TRIAL_DATE, COMPLAINT_SERVED, etc.)
    rule_template_id: str
    created_at: datetime

    # Relationships
    case: Case
    parent_deadline: Deadline
    dependent_deadline: Deadline
```

#### DeadlineHistory Model

**Purpose**: Complete audit trail of all deadline changes
**File**: `backend/app/models/deadline_history.py`

```python
class DeadlineHistory:
    id: str (UUID, PK)
    deadline_id: str (FK → Deadline)
    changed_by: str (FK → User)
    change_type: str (created, updated, completed, dismissed, overridden)
    field_changed: Optional[str]
    old_value: Optional[str]
    new_value: Optional[str]
    reason: Optional[str]
    timestamp: datetime

    # Relationships
    deadline: Deadline
    user: User
```

---

## Feature Deep Dives

### 1. Trigger-Based Deadline Calculation

**Business Problem**: Manually entering 50+ dependent deadlines for each case is error-prone and time-consuming.

**Solution**: Trigger-based deadline generation where one event creates an entire deadline chain.

#### How It Works

```
User enters: "Trial Date: March 1, 2026"
                    ↓
Rules Engine loads rule template for jurisdiction + trigger type
                    ↓
Generates 47 dependent deadlines:
  - Expert Witness Disclosures (90 days before trial)
  - Pretrial Motions Deadline (30 days before trial)
  - Witness List Due (21 days before trial)
  - Motions in Limine (14 days before trial)
  - Final Pretrial Statement (7 days before trial)
  - ... and 42 more
                    ↓
All deadlines saved with:
  - parent_deadline_id → Trial Date deadline
  - is_dependent = True
  - auto_recalculate = True (default)
  - rule_citation (e.g., "FRCP 16(b)")
  - calculation_basis (step-by-step explanation)
```

#### Rule Template Structure

**File**: `backend/app/services/rules_engine.py`

```python
class RuleTemplate:
    rule_id: str
    trigger_type: str (TRIAL_DATE, COMPLAINT_SERVED, etc.)
    jurisdiction: str (florida_civil, federal_civil, etc.)
    dependent_deadlines: List[DependentDeadline]
    required_fields: List[RequiredField]
    clarification_questions: List[ClarificationQuestion]

class DependentDeadline:
    name: str
    description: str
    days_from_trigger: int (can be negative for "before" trigger)
    calculation_type: str (calendar_days, court_days)
    priority: str (FATAL, CRITICAL, etc.)
    rule_citation: str
    add_service_method_days: bool
    conditions: Optional[dict] (conditional logic)

class RequiredField:
    field_name: str
    display_label: str
    field_type: str (text, date, select, etc.)
    enum_options: Optional[List[str]]
    is_required: bool

class ClarificationQuestion:
    question_text: str
    affects_deadlines: List[str]
    answer_type: str (yes_no, multiple_choice, etc.)
```

#### Example: Florida Civil Complaint Served Trigger

```python
{
    "rule_id": "florida_civil_response",
    "trigger_type": "COMPLAINT_SERVED",
    "jurisdiction": "florida_civil",
    "dependent_deadlines": [
        {
            "name": "Defendant's Response Due",
            "description": "Answer, motion to dismiss, or other responsive pleading",
            "days_from_trigger": 20,
            "calculation_type": "calendar_days",
            "priority": "CRITICAL",
            "rule_citation": "Fla. R. Civ. P. 1.140(a)(1)",
            "add_service_method_days": True  # Add 5 days if served by mail
        },
        {
            "name": "Discovery Commencement",
            "description": "Earliest date discovery may begin",
            "days_from_trigger": 0,
            "calculation_type": "calendar_days",
            "priority": "STANDARD",
            "rule_citation": "Fla. R. Civ. P. 1.280(b)"
        }
    ],
    "required_fields": [
        {
            "field_name": "service_method",
            "display_label": "How was the complaint served?",
            "field_type": "select",
            "enum_options": ["personal", "mail", "email"],
            "is_required": True
        }
    ]
}
```

#### Authoritative Deadline Calculator

**File**: `backend/app/utils/deadline_calculator.py`

**Purpose**: Single source of truth for all deadline math.

**Features**:
1. **Calendar Days vs Court Days**: Handles both calculation types
2. **Business Day Rules**: Skips weekends and court holidays
3. **Service Method Extensions**: Adds days based on how document was served
   - Mail: +5 days (Florida), +3 days (Federal)
   - Email: +0 days (Florida), +3 days (Federal)
   - Personal: +0 days
4. **Roll Logic**: If deadline falls on weekend/holiday, rolls to next business day
5. **Full Transparency**: Returns detailed explanation of calculation

**Example Calculation**:
```python
from app.utils.deadline_calculator import AuthoritativeDeadlineCalculator

calculator = AuthoritativeDeadlineCalculator(jurisdiction="florida_civil")

result = calculator.calculate_deadline(
    trigger_date=date(2026, 1, 1),  # Thursday
    days_to_add=20,
    calculation_type="calendar_days",
    service_method="mail"
)

# Returns:
{
    "deadline_date": date(2026, 1, 27),  # Tuesday
    "calculation_basis": """
    1. Trigger date: January 1, 2026 (Thursday)
    2. Add 20 calendar days = January 21, 2026 (Wednesday)
    3. Service method: mail (+5 days per Fla. R. Civ. P. 1.090(e))
    4. After service extension: January 26, 2026 (Monday - MLK Day observed)
    5. Roll to next business day: January 27, 2026 (Tuesday)
    """,
    "rule_citation": "Fla. R. Civ. P. 1.140(a)(1); 1.090(e)",
    "service_extension_days": 5
}
```

#### Cascading Updates

**Scenario**: User changes trial date from March 1 to March 15

```python
# 1. Find all dependent deadlines
dependent_deadlines = db.query(Deadline).join(DeadlineChain).filter(
    DeadlineChain.parent_deadline_id == trial_deadline_id,
    Deadline.auto_recalculate == True,
    Deadline.is_manually_overridden == False  # Protect manual overrides
).all()

# 2. Recalculate each dependent deadline
for deadline in dependent_deadlines:
    new_date = calculator.calculate_deadline(
        trigger_date=new_trial_date,
        days_to_add=deadline.days_from_trigger,
        calculation_type=deadline.calculation_type,
        service_method=deadline.service_method
    )

    # 3. Log change in history
    history = DeadlineHistory(
        deadline_id=deadline.id,
        changed_by=current_user.id,
        change_type="auto_recalculated",
        field_changed="deadline_date",
        old_value=str(deadline.deadline_date),
        new_value=str(new_date),
        reason=f"Trigger date changed from {old_trial_date} to {new_trial_date}"
    )

    # 4. Update deadline
    deadline.deadline_date = new_date
```

### 2. Document Upload & AI Analysis

**Workflow**:

```
User drags PDF into Case Room
          ↓
Frontend validates file type
          ↓
POST /api/v1/documents/upload
          ↓
Backend: DocumentService.upload_document()
          ↓
1. Validate PDF magic number (%PDF-)
2. Extract text with PyPDF2
3. Normalize case number from text
4. Send to Claude for analysis
          ↓
Claude analyzes document and returns JSON:
{
  "case_number": "2025-CA-001234",
  "court": "Circuit Court, 11th Judicial Circuit",
  "judge": "Hon. Jane Smith",
  "document_type": "complaint",
  "parties_plaintiff": "John Doe",
  "parties_defendant": "Acme Corp",
  "filing_date": "2025-01-15",
  "service_date": "2025-01-16",
  "extracted_dates": [
    {
      "date": "2025-03-01",
      "type": "trial_date",
      "context": "Trial set for March 1, 2025 at 9:00 AM",
      "confidence": "high"
    }
  ],
  "jurisdiction": "florida_civil",
  "confidence_score": 92
}
          ↓
5. Smart Case Routing:
   - Normalize case number (strip judge initials, leading zeros)
   - Check if case exists for current user
          ↓
If case exists:
  - Attach document to existing case
  - Update case metadata if more complete
  - Regenerate deadline chains for extracted dates
          ↓
If case doesn't exist:
  - Create new case with extracted metadata
  - Attach document
  - Generate initial deadline chains
          ↓
6. Store PDF in S3
7. Generate presigned URL (expires in 24h)
8. Save document record to database
          ↓
Frontend receives response:
{
  "success": true,
  "data": {
    "document_id": "...",
    "case_id": "...",
    "analysis": { ... },
    "redirect_url": "/cases/{case_id}"
  }
}
          ↓
Event bus emits: "document:uploaded"
          ↓
Case Room refreshes and shows new document + deadlines
```

#### AI Service Implementation

**File**: `backend/app/services/ai_service.py`

**Key Features**:
1. **Resilience**: 3 retry attempts with exponential backoff
2. **System Prompt**: Specialized Florida Rules expert persona
3. **Structured Output**: JSON schema enforcement
4. **Confidence Scoring**: Returns confidence level for each extracted field
5. **API Key Safety**: Sanitizes keys from logs/errors

**Example System Prompt**:
```
You are a legal document analysis specialist with deep expertise in Florida
Rules of Civil Procedure, Federal Rules of Civil Procedure, and court
docketing systems.

Your task is to analyze uploaded court documents and extract:
1. Case metadata (case number, court, judge, parties)
2. Important dates (filing dates, service dates, hearing dates, trial dates)
3. Jurisdiction and applicable rules
4. Document type and purpose

Be extremely precise with dates. If a date is ambiguous, mark confidence as "low".
Always cite the page number and exact text where you found each piece of information.
```

### 3. Streaming Chat with Tool Calling

**Architecture**: Server-Sent Events (SSE) for real-time token streaming + tool approval workflow

#### Chat Flow

```
User types: "Create a deadline for the summary judgment hearing on Feb 15"
          ↓
Frontend: useStreamingChat.sendMessage(message)
          ↓
GET /api/v1/chat/stream?case_id=X&message=Y&session_id=Z
          ↓
Backend: StreamingChatService.stream_chat()
          ↓
1. Build case context:
   - Case metadata (court, judge, jurisdiction)
   - Active deadlines
   - Recent documents
   - Conversation history
          ↓
2. Add tool definitions:
   - create_deadline
   - update_case
   - search_documents
   - get_rule_citation
          ↓
3. Call Claude API with streaming=True
          ↓
Claude streams response:
  - "Thinking" tokens: "I'll create a deadline for..."
  - Tool use: {
      "type": "tool_use",
      "name": "create_deadline",
      "input": {
        "title": "Summary Judgment Hearing",
        "deadline_date": "2026-02-15",
        "priority": "CRITICAL"
      }
    }
          ↓
Backend detects tool_use → Pauses stream → Sends approval request
          ↓
Frontend receives SSE event:
  event: tool_approval_required
  data: {
    "tool_name": "create_deadline",
    "tool_input": { ... },
    "approval_id": "abc123"
  }
          ↓
Frontend shows approval dialog:
  "Claude wants to create a deadline:
   Title: Summary Judgment Hearing
   Date: February 15, 2026
   Priority: CRITICAL

   [Approve] [Modify] [Reject]"
          ↓
User clicks "Approve"
          ↓
POST /api/v1/chat/stream/approve
  {
    "approval_id": "abc123",
    "decision": "approve"
  }
          ↓
Backend executes tool:
  - Creates deadline in database
  - Emits event: deadline:created
  - Returns result to Claude
          ↓
Claude continues:
  "✓ I've created the deadline for February 15, 2026.
   Note: You should also file your response brief at least
   5 days before the hearing per FL R. Civ. P. 1.510(c)."
          ↓
Frontend:
  - Event bus refreshes deadline list
  - Chat shows final response
  - State returns to "idle"
```

#### SSE Event Types

**File**: `backend/app/api/v1/chat_stream.py`

```python
# Token event (streaming text)
event: token
data: {"content": "I'll create"}

# Status event (thinking, calling_tool, etc.)
event: status
data: {"status": "thinking"}

# Tool approval required
event: tool_approval_required
data: {
    "tool_name": "create_deadline",
    "tool_input": { ... },
    "approval_id": "abc123",
    "reasoning": "Creating deadline for summary judgment hearing"
}

# Tool execution result
event: tool_result
data: {
    "tool_name": "create_deadline",
    "result": "success",
    "deadline_id": "xyz789"
}

# Error
event: error
data: {"error": "Rate limit exceeded"}

# Stream complete
event: done
data: {"message_id": "msg_123", "tokens": 450}
```

#### Frontend State Machine

**File**: `frontend/hooks/useStreamingChat.ts`

```typescript
type ChatState =
  | 'idle'
  | 'connecting'
  | 'streaming'
  | 'awaiting_approval'
  | 'executing_tool'
  | 'error';

const [state, setState] = useState<ChatState>('idle');

// State transitions:
idle → connecting → streaming → awaiting_approval → executing_tool → streaming → idle
                              ↓
                            error → idle (after 3 retry attempts)
```

### 4. Dashboard Intelligence

**Purpose**: War Room dashboard showing high-risk cases, workload saturation, and productivity metrics

#### Dashboard Service

**File**: `backend/app/services/dashboard_service.py`

**Metrics Computed**:

1. **Case Statistics**:
   ```python
   {
       "total_cases": 42,
       "active_cases": 38,
       "by_jurisdiction": {
           "florida_civil": 25,
           "federal_civil": 10,
           "florida_family": 3
       },
       "by_type": {
           "civil_litigation": 30,
           "family_law": 8,
           "probate": 4
       }
   }
   ```

2. **Deadline Alerts**:
   ```python
   {
       "overdue": 3,           # Past deadline_date, status=pending
       "urgent": 7,            # Next 3 days
       "upcoming_week": 15,    # Next 7 days
       "upcoming_month": 42    # Next 30 days
   }
   ```

3. **Critical Cases** (Malpractice Risk):
   ```python
   # Cases with FATAL or CRITICAL deadlines in next 7 days
   [
       {
           "case_id": "...",
           "case_number": "2025-CA-001234",
           "case_name": "Doe v. Acme",
           "urgent_deadlines": [
               {
                   "title": "Answer Due",
                   "deadline_date": "2026-01-25",
                   "priority": "CRITICAL",
                   "days_until": 2
               }
           ]
       }
   ]
   ```

4. **Zombie Cases**:
   ```python
   # Active cases with NO pending deadlines in next 30 days
   # Risk: Forgotten case with missed deadline
   [
       {
           "case_id": "...",
           "case_number": "2024-CA-005678",
           "case_name": "Smith v. Corp",
           "last_activity": "2025-12-01",
           "days_inactive": 53
       }
   ]
   ```

5. **Calendar Hotspots** (Workload Saturation):
   ```python
   # Days with 5+ deadlines = high risk of burnout/mistakes
   [
       {
           "date": "2026-02-15",
           "deadline_count": 8,
           "fatal_count": 2,
           "critical_count": 3
       }
   ]
   ```

6. **Velocity Metrics**:
   ```python
   {
       "last_7_days": {
           "deadlines_completed": 15,
           "deadlines_added": 22,
           "documents_uploaded": 8,
           "cases_created": 2
       },
       "trend": "increasing_workload"  # added > completed
   }
   ```

#### Morning Report

**File**: `backend/app/services/morning_report_service.py`

**Purpose**: AI-generated daily briefing (sent via email or viewed in dashboard)

**Example**:
```
Good morning! Here's your briefing for Thursday, January 23, 2026:

🔴 URGENT - Action Required Today:
  - Doe v. Acme (2025-CA-001234): Answer due by 5:00 PM
  - Smith v. Corp (2024-CA-005678): Summary judgment response due

⚠️  High-Risk Cases:
  - Johnson v. LLC: Trial in 14 days, witness list not yet filed
  - Davis v. Inc: Discovery deadline in 3 days, 5 outstanding requests

📊 Workload Outlook:
  - 8 deadlines this week (2 FATAL, 3 CRITICAL)
  - Calendar hotspot: February 15 (8 deadlines)

🧟 Zombie Cases Detected:
  - Miller v. Partners: No activity in 60 days

💡 Suggested Actions:
  1. File answer in Doe v. Acme before 5 PM deadline
  2. Schedule witness prep for Johnson trial
  3. Review Miller case status and update deadline tracking
```

### 5. Deadline Priority System

**5 Levels with Legal Context**:

| Priority | Symbol | Color | Definition | Example |
|----------|--------|-------|------------|---------|
| **FATAL** | !! | Red | Jurisdictional deadline - missing = case dismissal or malpractice | Answer to complaint, statute of limitations |
| **CRITICAL** | !! | Orange | Court-ordered deadline with severe consequences | Compliance with court order, pretrial motions |
| **IMPORTANT** | ! | Amber | Procedural deadline with consequences | Discovery responses, expert disclosures |
| **STANDARD** | · | Slate | Regular practice deadlines | Internal review, client update |
| **INFORMATIONAL** | · | Gray | Internal reminders, no legal consequence | Calendar hold, follow-up reminder |

**Visual Indicators** (Sovereign Design):
- **Health Bar**: Left border color
- **Status Flags**: "!!" for fatal/critical, "!" for important
- **Overdue**: Red strikethrough + "OVERDUE" badge
- **Completed**: Green "DONE" stamp effect

---

## Integration Points

### Frontend ↔ Backend Communication

#### API Client Setup

**File**: `frontend/lib/api-client.ts`

```typescript
import axios from 'axios';

const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor: Add JWT token
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('authToken');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor: Handle 401 (expired token)
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('authToken');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default apiClient;
```

**Usage**:
```typescript
// All API calls use this client
const response = await apiClient.get('/cases');
const cases = response.data.data;
```

### Authentication Flow (End-to-End)

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. User Login                                                    │
│    - Frontend: Firebase.signInWithEmailAndPassword()            │
│    - Returns: { user, idToken }                                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. Token Exchange                                               │
│    POST /api/v1/auth/login/firebase                             │
│    Body: { idToken: "..." }                                     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. Backend Verification                                         │
│    - Verify idToken with Firebase Admin SDK                     │
│    - firebase_auth.verify_id_token(token)                       │
│    - Get user data from Firebase                                │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 4. User Lookup/Creation                                         │
│    - Check if user exists in PostgreSQL (by firebase_uid)       │
│    - If not exists: Create new user record                      │
│    - If exists: Return existing user                            │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 5. JWT Token Generation                                         │
│    - Create JWT with payload:                                   │
│      { sub: user.id, email: user.email, exp: now + 7 days }    │
│    - Sign with JWT_SECRET_KEY                                   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 6. Frontend Receives Token                                      │
│    Response: { token: "jwt_token", user: {...} }                │
│    - Store token in localStorage                                │
│    - Store user in auth context                                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 7. Subsequent Requests                                          │
│    - Axios interceptor adds: Authorization: Bearer {jwt}        │
│    - Backend verifies JWT with get_current_user dependency      │
│    - All queries filtered by user_id                            │
└─────────────────────────────────────────────────────────────────┘
```

**Key Files**:
- **Frontend**: `lib/auth/auth-context.tsx`, `lib/api-client.ts`
- **Backend**: `api/v1/auth.py`, `auth/jwt_handler.py`, `auth/firebase_auth.py`

### Event Bus (Real-Time Updates)

**Purpose**: Decouple components and enable cross-component communication without prop drilling

**Implementation**: `frontend/lib/eventBus.ts`

```typescript
type EventCallback = (data?: any) => void;

class EventBus {
  private events: Map<string, EventCallback[]> = new Map();

  on(event: string, callback: EventCallback) {
    if (!this.events.has(event)) {
      this.events.set(event, []);
    }
    this.events.get(event)!.push(callback);
  }

  emit(event: string, data?: any) {
    const callbacks = this.events.get(event) || [];
    callbacks.forEach(callback => callback(data));
  }

  off(event: string, callback: EventCallback) {
    const callbacks = this.events.get(event) || [];
    const index = callbacks.indexOf(callback);
    if (index > -1) {
      callbacks.splice(index, 1);
    }
  }
}

export const eventBus = new EventBus();
```

**Usage Pattern**:
```typescript
// Component A: DeadlineTable
const handleCreateDeadline = async (data) => {
  await apiClient.post('/deadlines', data);
  eventBus.emit('deadline:created', { deadlineId: response.data.id });
};

// Component B: CaseInsights (in different part of UI)
useEventBus('deadline:created', () => {
  // Refresh AI insights when new deadline added
  fetchInsights();
});

// Component C: CalendarView
useEventBus('deadline:created', () => {
  // Refresh calendar events
  fetchCalendarEvents();
});
```

**Standard Events**:
- `deadline:created`, `deadline:updated`, `deadline:deleted`, `deadline:completed`
- `deadlines:bulk-updated`
- `trigger:created`, `trigger:deleted`
- `document:uploaded`, `document:analyzed`
- `case:updated`
- `chat:action-taken`
- `calendar:refresh`, `insights:refresh`

### External Service Integration

#### 1. Firebase Authentication

**Purpose**: User authentication (email/password, Google OAuth)

**Flow**:
```
Frontend → Firebase Auth SDK → Firebase Auth Server
                                        ↓
                                   Returns idToken
                                        ↓
Frontend → Backend /auth/login/firebase with idToken
                                        ↓
Backend → Firebase Admin SDK verifies token
                                        ↓
Backend creates/updates user → Returns JWT
```

**Configuration**:
- **Frontend**: `lib/auth/firebase-config.ts`
- **Backend**: `services/firebase_service.py`
- **Environment**: `NEXT_PUBLIC_FIREBASE_*` (frontend), `FIREBASE_SERVICE_ACCOUNT` (backend)

#### 2. Anthropic Claude API

**Purpose**: Document analysis, chat, case insights, morning reports

**Models Used**:
- **Primary**: `claude-sonnet-4-20250514` (fast, accurate)
- **Optional**: `claude-opus-4` (complex reasoning, higher cost)

**Usage Patterns**:
1. **Document Analysis** (`ai_service.py`):
   ```python
   response = anthropic.messages.create(
       model="claude-sonnet-4-20250514",
       max_tokens=4000,
       system="You are a legal document analysis specialist...",
       messages=[{
           "role": "user",
           "content": f"Analyze this court document:\n\n{document_text}"
       }]
   )
   ```

2. **Streaming Chat** (`streaming_chat_service.py`):
   ```python
   with anthropic.messages.stream(
       model="claude-sonnet-4-20250514",
       max_tokens=4000,
       messages=messages,
       tools=tools,
       stream=True
   ) as stream:
       for event in stream:
           if event.type == "content_block_delta":
               yield f"data: {json.dumps({'token': event.delta.text})}\n\n"
           elif event.type == "message_stop":
               yield "event: done\ndata: {}\n\n"
   ```

3. **Tool Calling**:
   ```python
   tools = [
       {
           "name": "create_deadline",
           "description": "Create a new deadline for this case",
           "input_schema": {
               "type": "object",
               "properties": {
                   "title": {"type": "string"},
                   "deadline_date": {"type": "string", "format": "date"},
                   "priority": {"type": "string", "enum": ["FATAL", "CRITICAL", ...]}
               },
               "required": ["title", "deadline_date"]
           }
       }
   ]
   ```

**Rate Limiting**: 20 requests/minute per user

#### 3. Supabase (PostgreSQL)

**Purpose**: Primary data store

**Connection**:
```python
# backend/app/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = settings.SUPABASE_DB_URL

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
```

**Features Used**:
- PostgreSQL 15+
- pgvector extension (for RAG embeddings)
- Row-level security (optional, currently using app-level security)
- Automatic backups

#### 4. AWS S3 (Optional)

**Purpose**: Document storage

**Flow**:
```
User uploads PDF
      ↓
Backend receives base64-encoded file
      ↓
Upload to S3: s3_client.put_object(Bucket=bucket, Key=key, Body=file)
      ↓
Generate presigned URL (24h expiration):
  s3_client.generate_presigned_url('get_object', Params={...}, ExpiresIn=86400)
      ↓
Store presigned URL in database
      ↓
Frontend uses presigned URL for PDF viewing
```

**Alternative**: Store documents as base64 in PostgreSQL (current implementation for smaller deployments)

---

## Security & Compliance

### Legal Defensibility Features

LitDocket is designed for legal professionals where errors can result in malpractice. Every feature includes audit trails and transparency.

#### 1. Calculation Transparency

**Every deadline includes**:
- `calculation_basis`: Step-by-step explanation
- `rule_citation`: Legal authority (e.g., "FRCP 12(a)(1)(A)(i)")
- `trigger_date`: Original trigger event
- `service_method`: How document was served (affects deadline)

**Example**:
```
Deadline: Answer Due - January 27, 2026

Calculation Basis:
1. Trigger: Complaint served on January 1, 2026
2. Base deadline: 20 calendar days (FRCP 12(a))
3. Service method: Mail (+3 days per FRCP 6(d))
4. Raw calculation: January 24, 2026 (Saturday)
5. Roll to next business day: January 27, 2026 (Monday)

Rule Citation: FRCP 12(a)(1)(A)(i); FRCP 6(d)
```

#### 2. Complete Audit Trail

**DeadlineHistory Model** tracks:
- What changed (`field_changed`)
- Old value → New value
- Who made the change (`changed_by`)
- When (`timestamp`)
- Why (`reason`)

**Example History**:
```sql
SELECT * FROM deadline_history WHERE deadline_id = '...';

| change_type      | field_changed   | old_value   | new_value   | changed_by | reason               |
|------------------|-----------------|-------------|-------------|------------|----------------------|
| created          | -               | -           | -           | user_123   | Created from trigger |
| auto_recalculated| deadline_date   | 2026-03-01  | 2026-03-15  | system     | Trigger date changed |
| overridden       | deadline_date   | 2026-03-15  | 2026-03-10  | user_123   | Court rescheduled    |
| completed        | status          | pending     | completed   | user_123   | Answer filed         |
```

#### 3. Manual Override Protection

**Fields**:
- `is_manually_overridden`: Flag to prevent auto-recalculation
- `override_user_id`: Who overrode the calculated deadline
- `override_timestamp`: When override occurred
- `override_reason`: Why override was necessary
- `original_deadline_date`: Preserve original calculated date

**Logic**:
```python
# When trigger date changes, only update deadlines that weren't manually overridden
dependent_deadlines = db.query(Deadline).filter(
    Deadline.parent_deadline_id == trigger_id,
    Deadline.auto_recalculate == True,
    Deadline.is_manually_overridden == False  # Protect manual overrides
).all()
```

#### 4. Source Attribution

**Document-linked deadlines track**:
- `source_page`: Page number in PDF where deadline found
- `source_text`: Exact text snippet that triggered deadline
- `source_coordinates`: Optional coordinates for PDF highlighting
- `confidence_score`: AI confidence (0-100)

**Example**:
```json
{
  "title": "Summary Judgment Hearing",
  "deadline_date": "2026-02-15",
  "source_page": 3,
  "source_text": "The Court hereby sets Summary Judgment hearing for February 15, 2026 at 9:00 AM",
  "confidence_score": 95,
  "extraction_quality_score": 9
}
```

#### 5. Verification Gate (Case OS)

**Workflow**:
```
AI extracts deadline from document
         ↓
verification_status = "pending"
         ↓
Attorney reviews in Case Room
         ↓
Attorney clicks "Approve" or "Modify"
         ↓
If "Approve":
  - verification_status = "approved"
  - verified_by = current_user.id
  - verified_at = now()
         ↓
If "Modify":
  - verification_status = "modified"
  - verified_by = current_user.id
  - verification_notes = "Changed date from X to Y because..."
  - Update deadline_date
         ↓
Verified deadline appears in normal workflow
```

### Security Measures

#### 1. Authentication & Authorization

**Multi-Layer Auth**:
```
Request → Rate Limiter → CORS Check → JWT Verification → Ownership Verification → Database
```

**JWT Structure**:
```json
{
  "sub": "user_uuid",
  "email": "attorney@lawfirm.com",
  "exp": 1738281600,  // 7 days from issuance
  "iat": 1737676800
}
```

**Ownership Verification** (CRITICAL):
```python
# EVERY user-owned resource query MUST include user_id filter
deadline = db.query(Deadline).filter(
    Deadline.id == deadline_id,
    Deadline.user_id == str(current_user.id)  # IDOR prevention
).first()
```

#### 2. Rate Limiting

**Per-Endpoint Limits** (`middleware/security.py`):
```python
# Default: 100/minute
@limiter.limit("100/minute")

# Auth endpoints: 5/minute (brute force protection)
@limiter.limit("5/minute")
async def login(): ...

# File uploads: 10/minute
@limiter.limit("10/minute")
async def upload_document(): ...

# AI endpoints: 20/minute (cost control)
@limiter.limit("20/minute")
async def chat(): ...
```

#### 3. Input Validation

**Layers**:
1. **Pydantic Schemas**: All request bodies validated
2. **File Type Validation**: PDF magic number check (`%PDF-`)
3. **SQL Injection**: Prevented by SQLAlchemy ORM
4. **XSS**: React escapes by default, backend returns JSON only

**Example Pydantic Schema**:
```python
class DeadlineCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    deadline_date: date
    priority: DeadlinePriority  # Enum
    description: Optional[str] = Field(None, max_length=2000)

    @validator('deadline_date')
    def deadline_must_be_future(cls, v):
        if v < date.today():
            raise ValueError('Deadline must be in the future')
        return v
```

#### 4. Security Headers

```python
headers = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'"
}
```

#### 5. CORS Configuration

**Production**:
```python
allowed_origins = [
    "https://www.litdocket.com",
    "https://litdocket.com"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"]
)
```

**Development**:
```python
allowed_origins = ["http://localhost:3000"]
```

#### 6. Secrets Management

**Environment Variables Only** (NEVER in code):
```bash
# Backend
SECRET_KEY=<64+ character random string>
JWT_SECRET_KEY=<64+ character random string>
ANTHROPIC_API_KEY=sk-ant-...
SUPABASE_DB_URL=postgresql://...

# Frontend
NEXT_PUBLIC_API_URL=https://api.litdocket.com
NEXT_PUBLIC_FIREBASE_API_KEY=...
```

**API Key Sanitization**:
```python
# Never log full API keys
logger.info(f"Using API key: {api_key[:8]}...")
```

---

## Data Flow Examples

### Example 1: Create Trigger and Generate Deadline Chain

```
┌─────────────────────────────────────────────────────────────────┐
│ User Action: Clicks "Add Trigger" in Case Room                  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Frontend: SmartEventEntry component opens                       │
│ - Shows trigger type selector (TRIAL_DATE, COMPLAINT_SERVED)    │
│ - User selects "TRIAL_DATE"                                     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Frontend: Fetch required fields                                 │
│ GET /api/v1/triggers/template?type=TRIAL_DATE&jurisdiction=...  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Backend: RulesEngine.get_template()                             │
│ Returns: {                                                      │
│   required_fields: [                                            │
│     { name: "trial_date", type: "date", label: "Trial Date" }   │
│     { name: "trial_type", type: "select", options: [...] }      │
│   ],                                                            │
│   clarification_questions: [...]                                │
│ }                                                               │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Frontend: Show dialog with required fields                      │
│ User enters:                                                    │
│   - Trial Date: March 1, 2026                                   │
│   - Trial Type: Bench Trial                                     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Frontend: Submit trigger                                        │
│ POST /api/v1/triggers                                           │
│ Body: {                                                         │
│   case_id: "...",                                               │
│   trigger_type: "TRIAL_DATE",                                   │
│   trigger_date: "2026-03-01",                                   │
│   metadata: { trial_type: "bench" }                             │
│ }                                                               │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Backend: TriggerService.create_trigger()                        │
│                                                                 │
│ 1. Verify case ownership                                        │
│ 2. Load rule template for jurisdiction + trigger type           │
│ 3. Create parent deadline (the trigger itself)                  │
│ 4. Loop through dependent_deadlines in template:                │
│                                                                 │
│    For each dependent deadline:                                 │
│      a. Calculate deadline using AuthoritativeDeadlineCalculator│
│      b. Create Deadline record with:                            │
│         - is_dependent = True                                   │
│         - parent_deadline_id = trigger.id                       │
│         - auto_recalculate = True                               │
│         - calculation_basis = "..."                             │
│         - rule_citation = "..."                                 │
│      c. Create DeadlineChain record linking parent → dependent  │
│      d. Save to database                                        │
│                                                                 │
│ 5. Emit event: trigger:created                                  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Backend Response:                                               │
│ {                                                               │
│   "success": true,                                              │
│   "data": {                                                     │
│     "trigger_id": "...",                                        │
│     "deadlines_created": 47,                                    │
│     "deadline_ids": [...]                                       │
│   }                                                             │
│ }                                                               │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Frontend: Receives response                                     │
│ 1. eventBus.emit('trigger:created', { triggerId })              │
│ 2. eventBus.emit('deadlines:bulk-updated')                      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Frontend: Multiple components react to events                   │
│                                                                 │
│ - useCaseSync hook → Refreshes case data                        │
│ - DeadlineTable → Refreshes deadline list                       │
│ - TriggerCard → Shows new trigger card                          │
│ - CaseInsights → Refreshes AI insights                          │
│ - CalendarView → Refreshes calendar events                      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ UI Updates: User sees                                           │
│ - New trigger card: "Trial Date: March 1, 2026"                 │
│ - 47 new deadlines in table                                     │
│ - Dependency chain visualization                                │
│ - Toast: "✓ 47 deadlines created from Trial Date trigger"       │
└─────────────────────────────────────────────────────────────────┘
```

### Example 2: Upload Document and Auto-Create Case

```
┌─────────────────────────────────────────────────────────────────┐
│ User Action: Drags PDF into Document Analyzer tool              │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Frontend: Validate file                                         │
│ - Check file type (must be PDF)                                 │
│ - Check file size (max 10MB)                                    │
│ - Read file as base64                                           │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Frontend: Upload document                                       │
│ POST /api/v1/documents/upload                                   │
│ Body: {                                                         │
│   file: "base64_encoded_pdf",                                   │
│   filename: "complaint.pdf",                                    │
│   case_id: null  // Let backend auto-detect/create case         │
│ }                                                               │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Backend: DocumentService.upload_document()                      │
│                                                                 │
│ 1. Validate PDF magic number (%PDF-)                            │
│ 2. Extract text with PyPDF2                                     │
│ 3. Create Document record (status=processing)                   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Backend: AIService.analyze_document(text)                       │
│                                                                 │
│ Sends to Claude:                                                │
│ System: "You are a legal document analyst..."                   │
│ User: "Analyze this document and extract case metadata..."      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Claude API Response:                                            │
│ {                                                               │
│   "case_number": "2025-CA-001234",                              │
│   "court": "11th Judicial Circuit",                             │
│   "judge": "Hon. Jane Smith",                                   │
│   "document_type": "complaint",                                 │
│   "parties_plaintiff": "John Doe",                              │
│   "parties_defendant": "Acme Corporation",                      │
│   "filing_date": "2025-01-15",                                  │
│   "service_date": "2025-01-16",                                 │
│   "extracted_dates": [                                          │
│     {                                                           │
│       "date": "2025-02-15",                                     │
│       "type": "answer_deadline",                                │
│       "confidence": "high",                                     │
│       "source_page": 1,                                         │
│       "source_text": "Defendant shall answer within 20 days..." │
│     }                                                           │
│   ],                                                            │
│   "jurisdiction": "florida_civil",                              │
│   "confidence_score": 92                                        │
│ }                                                               │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Backend: Smart Case Routing                                     │
│                                                                 │
│ 1. Normalize case number: "2025-CA-001234" → "2025CA001234"    │
│ 2. Check if case exists:                                        │
│    db.query(Case).filter(                                       │
│      Case.user_id == current_user.id,                           │
│      Case.case_number_normalized == "2025CA001234"              │
│    ).first()                                                    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                    ┌─────────┴─────────┐
                    │                   │
              Case Exists         Case Doesn't Exist
                    │                   │
                    ▼                   ▼
    ┌───────────────────────┐   ┌──────────────────────┐
    │ Attach to Existing    │   │ Create New Case      │
    │                       │   │                      │
    │ - Update case metadata│   │ - case_number        │
    │   if more complete    │   │ - court, judge       │
    │ - Link document       │   │ - parties            │
    │ - Regenerate deadlines│   │ - jurisdiction       │
    │   from new dates      │   │ - Link document      │
    └───────────────────────┘   │ - Create deadlines   │
                                │   from extracted dates│
                                └──────────────────────┘
                    │                   │
                    └─────────┬─────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Backend: Create Deadlines from Extracted Dates                  │
│                                                                 │
│ For each extracted_date:                                        │
│   deadline = Deadline(                                          │
│     title = date.type,                                          │
│     deadline_date = date.date,                                  │
│     source_page = date.source_page,                             │
│     source_text = date.source_text,                             │
│     confidence_score = date.confidence,                         │
│     verification_status = "pending",  // Requires review        │
│     document_id = document.id                                   │
│   )                                                             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Backend: Store PDF and Generate Presigned URL                   │
│                                                                 │
│ 1. Upload to S3: s3.put_object(...)                             │
│ 2. Generate presigned URL (24h expiration)                      │
│ 3. Update Document record:                                      │
│    - analysis_status = "completed"                              │
│    - presigned_url = "..."                                      │
│    - presigned_url_expires_at = now() + 24h                     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Backend Response:                                               │
│ {                                                               │
│   "success": true,                                              │
│   "data": {                                                     │
│     "document_id": "...",                                       │
│     "case_id": "...",                                           │
│     "case_created": true,  // or false if attached to existing  │
│     "analysis": { ... },                                        │
│     "deadlines_created": 3,                                     │
│     "redirect_url": "/cases/{case_id}"                          │
│   }                                                             │
│ }                                                               │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Frontend: Handle response                                       │
│                                                                 │
│ 1. eventBus.emit('document:uploaded', { documentId, caseId })   │
│ 2. If case_created: eventBus.emit('case:updated')               │
│ 3. Navigate to /cases/{case_id}                                 │
│ 4. Toast: "✓ Document analyzed. Case created with 3 deadlines"  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Case Room Loads:                                                │
│ - Case metadata from AI analysis                                │
│ - Uploaded document with PDF viewer                             │
│ - 3 extracted deadlines (verification_status = "pending")       │
│ - Verification UI: "Review AI-extracted deadlines"              │
└─────────────────────────────────────────────────────────────────┘
```

---

## Development Workflows

### Adding a New API Endpoint

**Example**: Add endpoint to bulk-complete deadlines

1. **Create Pydantic Schema** (`backend/app/schemas/deadline.py`):
   ```python
   class BulkCompleteRequest(BaseModel):
       deadline_ids: List[str] = Field(..., min_items=1)
       completion_notes: Optional[str] = None
   ```

2. **Add Route Handler** (`backend/app/api/v1/deadlines.py`):
   ```python
   @router.post("/deadlines/bulk-complete")
   @limiter.limit("50/minute")
   async def bulk_complete_deadlines(
       request: BulkCompleteRequest,
       current_user: User = Depends(get_current_user),
       db: Session = Depends(get_db)
   ):
       # Verify ownership of ALL deadlines
       deadlines = db.query(Deadline).filter(
           Deadline.id.in_(request.deadline_ids),
           Deadline.user_id == str(current_user.id)  # CRITICAL
       ).all()

       if len(deadlines) != len(request.deadline_ids):
           raise HTTPException(status_code=404, detail="Some deadlines not found")

       # Update all deadlines
       for deadline in deadlines:
           deadline.status = "completed"
           deadline.completed_at = datetime.utcnow()

           # Log in history
           history = DeadlineHistory(
               deadline_id=deadline.id,
               changed_by=str(current_user.id),
               change_type="completed",
               field_changed="status",
               old_value="pending",
               new_value="completed"
           )
           db.add(history)

       db.commit()

       return {
           "success": True,
           "data": {"completed_count": len(deadlines)},
           "message": f"Completed {len(deadlines)} deadlines"
       }
   ```

3. **Register Route** (already registered via `router.py` include)

4. **Add Frontend API Call** (`frontend/lib/api-client.ts` or component):
   ```typescript
   export const bulkCompleteDeadlines = async (deadlineIds: string[]) => {
     const response = await apiClient.post('/deadlines/bulk-complete', {
       deadline_ids: deadlineIds
     });
     return response.data;
   };
   ```

5. **Update UI** (e.g., `DeadlineTable.tsx`):
   ```typescript
   const handleBulkComplete = async () => {
     await bulkCompleteDeadlines(selectedIds);
     eventBus.emit('deadlines:bulk-updated');
     toast.success(`Completed ${selectedIds.length} deadlines`);
   };
   ```

### Adding a New Frontend Page

**Example**: Add "Rules Library" page

1. **Create Page** (`frontend/app/(protected)/rules-library/page.tsx`):
   ```typescript
   export default async function RulesLibraryPage() {
     // Server Component - can fetch data directly
     return (
       <div>
         <h1>Rules Library</h1>
         <RulesLibraryClient />
       </div>
     );
   }
   ```

2. **Create Client Component** (`frontend/components/RulesLibraryClient.tsx`):
   ```typescript
   'use client';

   export default function RulesLibraryClient() {
     const [rules, setRules] = useState([]);

     useEffect(() => {
       fetchRules();
     }, []);

     const fetchRules = async () => {
       const response = await apiClient.get('/rules');
       setRules(response.data.data);
     };

     return (
       <div>
         {rules.map(rule => (
           <RuleCard key={rule.id} rule={rule} />
         ))}
       </div>
     );
   }
   ```

3. **Add to Navigation** (`frontend/components/layout/Sidebar.tsx`):
   ```typescript
   const navItems = [
     // ...
     { href: '/rules-library', label: 'Rules Library', icon: BookOpen }
   ];
   ```

4. **Add TypeScript Types** (`frontend/types/index.ts`):
   ```typescript
   export interface Rule {
     id: string;
     rule_id: string;
     trigger_type: string;
     jurisdiction: string;
     dependent_deadlines: DependentDeadline[];
   }
   ```

---

## Deployment Architecture

### Infrastructure Overview

```
┌────────────────────────────────────────────────────────────────┐
│                         PRODUCTION                              │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  Frontend (Vercel)                                             │
│  - Next.js 14 application                                      │
│  - Automatic deployments from main branch                      │
│  - CDN distribution (global)                                   │
│  - SSL/TLS automatic                                           │
│  - Environment: NEXT_PUBLIC_*                                  │
│                                                                │
│  Backend (Railway)                                             │
│  - FastAPI application                                         │
│  - Docker container                                            │
│  - Auto-deploy from main branch                                │
│  - Health check: /health                                       │
│  - Environment: SECRET_KEY, JWT_SECRET_KEY, ANTHROPIC_API_KEY  │
│                                                                │
│  Database (Supabase)                                           │
│  - PostgreSQL 15                                               │
│  - Automatic backups (daily)                                   │
│  - pgvector extension                                          │
│  - Connection pooling                                          │
│                                                                │
│  Storage (AWS S3 - Optional)                                   │
│  - Document storage                                            │
│  - Presigned URLs                                              │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

### Environment Configuration

#### Frontend (.env.local)
```bash
NEXT_PUBLIC_API_URL=https://api.litdocket.com
NEXT_PUBLIC_FIREBASE_API_KEY=...
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=...
NEXT_PUBLIC_FIREBASE_PROJECT_ID=...
```

#### Backend (.env)
```bash
# Core
SECRET_KEY=<64+ character random string>
JWT_SECRET_KEY=<64+ character random string>
DEBUG=false

# Database
SUPABASE_DB_URL=postgresql://user:pass@host:5432/db

# AI
ANTHROPIC_API_KEY=sk-ant-...

# Firebase
FIREBASE_SERVICE_ACCOUNT={"type":"service_account",...}

# Optional
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
SENDGRID_API_KEY=...

# Security
ALLOWED_ORIGINS=https://www.litdocket.com,https://litdocket.com
```

### Deployment Process

#### Frontend (Vercel)
```bash
# Automatic deployment
git push origin main
  ↓
Vercel detects push
  ↓
Build Next.js app
  ↓
Deploy to CDN
  ↓
Update DNS
  ↓
Live at litdocket.com
```

#### Backend (Railway)
```bash
# Automatic deployment
git push origin main
  ↓
Railway detects push
  ↓
Build Docker image
  ↓
Run migrations (alembic upgrade head)
  ↓
Health check (/health endpoint)
  ↓
Zero-downtime swap
  ↓
Live at api.litdocket.com
```

### Database Migrations

**Tool**: Alembic

**Create Migration**:
```bash
cd backend
alembic revision --autogenerate -m "Add verification_status to deadlines"
```

**Apply Migration**:
```bash
alembic upgrade head
```

**Rollback**:
```bash
alembic downgrade -1
```

### Monitoring & Health Checks

**Health Endpoint** (`backend/app/main.py`):
```python
@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    # Check database connection
    try:
        db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }
```

---

## Known Issues & Tech Debt

### Current Issues

1. **TypeScript `any` Types**:
   - Some event handlers still use `any`
   - **Fix**: Migrate to proper event types in `types/index.ts`

2. **Calendar DnD Library Typing**:
   - `react-big-calendar` has incomplete TypeScript definitions
   - **Workaround**: Using type assertions where needed

3. **Firebase Auth Bypass**:
   - `DEV_AUTH_BYPASS` flag exists for local development
   - **CRITICAL**: Ensure this is NEVER true in production

4. **Presigned URL Expiration**:
   - Currently 24 hours, no auto-refresh
   - **TODO**: Implement auto-refresh mechanism or increase expiration

5. **No WebSocket Support**:
   - Currently using event bus for real-time updates
   - **Future**: Add WebSocket for true real-time multi-user collaboration

### Tech Debt

1. **Document Storage**:
   - Currently storing base64 in PostgreSQL for small deployments
   - Should migrate to S3 for production scale

2. **RAG Implementation Incomplete**:
   - `rag_service.py` exists but not fully integrated
   - Document embeddings not being generated

3. **No End-to-End Tests**:
   - Only unit tests exist
   - **TODO**: Add Playwright E2E tests for critical flows

4. **Rate Limiting Per-User**:
   - Currently per-IP
   - Should be per-user for better fairness

5. **No Soft Delete for Cases**:
   - Hard delete exists
   - Should implement `status='archived'` pattern for legal audit trail

### Future Enhancements

1. **Multi-User Collaboration**:
   - Share cases with other users
   - Real-time updates via WebSockets
   - Commenting system

2. **Mobile App**:
   - React Native app for on-the-go deadline checking

3. **Email Integration**:
   - Receive court emails, auto-extract deadlines

4. **Custom Rule Templates**:
   - Allow users to create their own jurisdiction rules

5. **Calendar Sync**:
   - Two-way sync with Google Calendar, Outlook

---

## Appendix: Quick Reference

### Common Commands

```bash
# Frontend
cd frontend
npm run dev          # Start dev server
npm run build        # Production build
npm run lint         # ESLint

# Backend
cd backend
uvicorn app.main:app --reload  # Start dev server
pytest                         # Run tests
alembic upgrade head           # Apply migrations
alembic revision --autogenerate -m "message"  # Create migration

# Database
psql $SUPABASE_DB_URL  # Connect to database
```

### Key Files

| File | Purpose |
|------|---------|
| `frontend/lib/api-client.ts` | Axios instance with auth |
| `frontend/lib/eventBus.ts` | Event system |
| `frontend/hooks/useCaseData.ts` | Main data fetching |
| `backend/app/services/rules_engine.py` | Deadline calculation |
| `backend/app/utils/deadline_calculator.py` | Authoritative math |
| `backend/app/models/deadline.py` | Deadline ORM model |
| `backend/app/api/v1/deadlines.py` | Deadline routes |

### API Endpoints Reference

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/auth/login/firebase` | POST | Exchange Firebase token for JWT |
| `/api/v1/cases` | GET | List all cases |
| `/api/v1/cases/{id}` | GET | Get case details |
| `/api/v1/cases` | POST | Create case |
| `/api/v1/deadlines` | GET | List deadlines |
| `/api/v1/deadlines/{id}` | PUT | Update deadline |
| `/api/v1/triggers` | POST | Create trigger and generate deadlines |
| `/api/v1/documents/upload` | POST | Upload and analyze document |
| `/api/v1/chat/stream` | GET | Streaming chat (SSE) |
| `/api/v1/dashboard/stats` | GET | Dashboard metrics |

---

**End of Application Review**

*This document is a living reference. Update as features are added or architecture changes.*
