# LitDocket Comprehensive Revamp Plan
## From 5% Shell → Professional Docketing System

**Goal**: Transform this from a demo into a production-ready, competitive alternative to Compulaw Vision.

---

## Current State Analysis

### What Works (The 5%)
✅ PDF upload and AI deadline extraction
✅ Basic chat interface
✅ Case insights
✅ Deadline list view
✅ Firebase storage integration

### Critical Missing Pieces (The 95%)
❌ **No real authentication** (demo user only)
❌ **No proper dashboard** (just a case list)
❌ **No calendar views** (fundamental for docketing)
❌ **No document organization** (just a flat list)
❌ **No notifications/alerts** (core feature for deadlines)
❌ **No user settings** (preferences, jurisdictions)
❌ **No search functionality** (can't find cases/deadlines)
❌ **No conflict checking** (double-booked dates)
❌ **Poor navigation** (no clear information architecture)
❌ **Feels unfinished** (inconsistent UI, no polish)

---

## Implementation Plan: 4 Phases

### **PHASE 1: Core Infrastructure (2-3 weeks)**
*Make it feel real - authentication, database, users*

#### 1.1 Authentication System
**Priority: CRITICAL**

**Backend:**
- Replace demo user with Firebase Auth
- Support Google OAuth + email/password
- JWT token management
- User registration flow
- Password reset functionality

**Frontend:**
- Professional login/signup pages
- Google "Sign in with Google" button
- Session management
- Protected routes
- "Remember me" functionality

**Database:**
```sql
-- Enhanced users table
CREATE TABLE users (
  id UUID PRIMARY KEY,
  email VARCHAR(255) UNIQUE NOT NULL,
  firebase_uid VARCHAR(255) UNIQUE,
  full_name VARCHAR(255),
  firm_name VARCHAR(255),
  role VARCHAR(50), -- 'litdocket_admin', 'attorney', 'paralegal', 'assistant'
  jurisdictions JSONB, -- ['FL', 'GA', 'Federal']
  created_at TIMESTAMP,
  last_login TIMESTAMP,
  settings JSONB -- User preferences
);

-- User preferences structure
{
  "notifications": {
    "email_enabled": true,
    "in_app_enabled": true,
    "deadline_alerts": [7, 3, 1], // days before
    "alert_methods": ["email", "in_app"]
  },
  "calendar": {
    "default_view": "month",
    "week_start": "sunday",
    "business_hours": {"start": "9:00", "end": "17:00"}
  },
  "ui": {
    "cases_per_page": 25,
    "default_case_view": "list",
    "timezone": "America/New_York"
  }
}
```

**Files to Create:**
```
/backend/app/auth/
  ├── firebase_auth.py       # Firebase Auth integration
  ├── jwt_handler.py         # JWT generation/validation
  ├── middleware.py          # Auth middleware
  └── models.py              # Auth-related Pydantic models

/frontend/app/(auth)/
  ├── login/page.tsx         # Login page
  ├── signup/page.tsx        # Signup page
  ├── forgot-password/page.tsx
  └── verify-email/page.tsx

/frontend/lib/auth/
  ├── firebase-config.ts     # Firebase client config
  ├── auth-context.tsx       # Auth context provider
  └── protected-route.tsx    # Route protection HOC
```

#### 1.2 User Settings & Profile
**Priority: HIGH**

**Features:**
- Settings page with tabs: Profile, Preferences, Notifications, Jurisdictions
- Editable user profile (name, firm, jurisdictions)
- Notification preferences (email, in-app, timing)
- Calendar preferences (default view, working hours)
- UI preferences (cases per page, default views)

**UI Design:**
```
Settings Page
├── Profile Tab
│   ├── Full Name
│   ├── Firm Name
│   ├── Email (read-only)
│   └── Role (read-only for customers)
├── Jurisdictions Tab
│   ├── Multi-select: FL, GA, AL, Federal, etc.
│   └── Default jurisdiction for new cases
├── Notifications Tab
│   ├── Email notifications (toggle)
│   ├── In-app notifications (toggle)
│   ├── Deadline alert timing (7 days, 3 days, 1 day checkboxes)
│   └── Alert methods (email, in-app)
└── Preferences Tab
    ├── Default calendar view (month/week/list)
    ├── Cases per page
    └── Timezone
```

**Files to Create:**
```
/frontend/app/settings/
  ├── page.tsx               # Settings main page
  ├── profile/page.tsx
  ├── jurisdictions/page.tsx
  ├── notifications/page.tsx
  └── preferences/page.tsx

/backend/app/api/v1/users.py  # User settings endpoints
```

#### 1.3 Enhanced Database Schema
**Priority: CRITICAL**

**New/Updated Tables:**

```sql
-- Cases: Add jurisdiction, status tracking
ALTER TABLE cases ADD COLUMN jurisdiction VARCHAR(50); -- 'FL', 'Federal-MD-FL', etc.
ALTER TABLE cases ADD COLUMN case_stage VARCHAR(50); -- 'discovery', 'trial', 'appeal'
ALTER TABLE cases ADD COLUMN assigned_to UUID REFERENCES users(id); -- Owner
ALTER TABLE cases ADD COLUMN last_activity TIMESTAMP;
ALTER TABLE cases ADD COLUMN is_archived BOOLEAN DEFAULT FALSE;

-- Deadlines: Add conflict detection, reminders
ALTER TABLE deadlines ADD COLUMN calendar_id VARCHAR(255); -- Google Calendar event ID
ALTER TABLE deadlines ADD COLUMN reminder_sent BOOLEAN DEFAULT FALSE;
ALTER TABLE deadlines ADD COLUMN conflict_detected BOOLEAN DEFAULT FALSE;
ALTER TABLE deadlines ADD COLUMN conflicting_deadline_id UUID REFERENCES deadlines(id);
ALTER TABLE deadlines ADD COLUMN assigned_to UUID REFERENCES users(id); -- Task assignment

-- Documents: Add categorization, OCR status
ALTER TABLE documents ADD COLUMN category VARCHAR(50); -- 'motion', 'order', 'discovery', etc.
ALTER TABLE documents ADD COLUMN tags JSONB; -- ['summary-judgment', 'important']
ALTER TABLE documents ADD COLUMN ocr_status VARCHAR(20); -- 'not_needed', 'processing', 'completed'
ALTER TABLE documents ADD COLUMN ocr_confidence FLOAT;
ALTER TABLE documents ADD COLUMN is_readable BOOLEAN DEFAULT TRUE;

-- Notifications table (NEW)
CREATE TABLE notifications (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  type VARCHAR(50), -- 'deadline_reminder', 'document_uploaded', 'conflict_detected'
  title VARCHAR(255),
  message TEXT,
  related_case_id UUID REFERENCES cases(id),
  related_deadline_id UUID REFERENCES deadlines(id),
  related_document_id UUID REFERENCES documents(id),
  is_read BOOLEAN DEFAULT FALSE,
  sent_via JSONB, -- ['email', 'in_app']
  created_at TIMESTAMP DEFAULT NOW()
);

-- Comments table (NEW)
CREATE TABLE comments (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  case_id UUID REFERENCES cases(id),
  deadline_id UUID REFERENCES deadlines(id),
  document_id UUID REFERENCES documents(id),
  parent_comment_id UUID REFERENCES comments(id), -- For replies
  content TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP
);

-- Activity log (NEW)
CREATE TABLE activity_log (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  case_id UUID REFERENCES cases(id),
  action VARCHAR(50), -- 'created_deadline', 'uploaded_document', 'completed_deadline'
  description TEXT,
  metadata JSONB,
  created_at TIMESTAMP DEFAULT NOW()
);
```

---

### **PHASE 2: Professional Dashboard & Navigation (1-2 weeks)**
*Make it look and feel professional*

#### 2.1 Main Dashboard
**Priority: CRITICAL**

**Layout:**
```
┌─────────────────────────────────────────────────────┐
│  LitDocket  [Search]         [Notifications] [User] │
├─────────────────────────────────────────────────────┤
│                                                      │
│  📊 Dashboard          🗂️ Cases          ⚙️ Settings │
│                                                      │
│  ┌──────────────────┐  ┌──────────────────┐        │
│  │ Upcoming         │  │ Cases Requiring  │        │
│  │ Deadlines        │  │ Attention        │        │
│  │                  │  │                  │        │
│  │ • Motion due     │  │ • Case ABC       │        │
│  │   Jan 15 (3d)    │  │   5 overdue      │        │
│  │ • Answer due     │  │ • Case XYZ       │        │
│  │   Jan 18 (6d)    │  │   Missing docs   │        │
│  └──────────────────┘  └──────────────────┘        │
│                                                      │
│  ┌──────────────────┐  ┌──────────────────┐        │
│  │ This Week        │  │ AI Assistant     │        │
│  │ Calendar         │  │                  │        │
│  │                  │  │ "How can I help" │        │
│  │ [Mini Calendar]  │  │ [Chat input]     │        │
│  └──────────────────┘  └──────────────────┘        │
│                                                      │
│  Recent Activity                                    │
│  • John uploaded motion.pdf to Case ABC             │
│  • AI extracted 3 deadlines from order.pdf          │
│                                                      │
└─────────────────────────────────────────────────────┘
```

**Components:**
1. **Upcoming Deadlines Widget**
   - Next 10 deadlines across all cases
   - Color-coded by urgency (red <3 days, yellow <7 days, blue >7 days)
   - Click to navigate to case
   - "View all" link to full deadline calendar

2. **Cases Requiring Attention**
   - Cases with overdue deadlines
   - Cases with no recent activity (>30 days)
   - Cases missing critical information

3. **Mini Calendar**
   - Current week view
   - Dots indicating deadlines on dates
   - Click date to see deadlines

4. **Quick AI Assistant**
   - Global chat that can access any case
   - "Create deadline for Case ABC"
   - "What's due this week?"

5. **Recent Activity Feed**
   - Last 20 actions across all cases
   - User avatars, timestamps
   - Filterable by case/user

**Files to Create:**
```
/frontend/app/dashboard/
  ├── page.tsx                    # Main dashboard
  ├── components/
  │   ├── UpcomingDeadlines.tsx
  │   ├── CasesRequiringAttention.tsx
  │   ├── MiniCalendar.tsx
  │   ├── QuickAI.tsx
  │   └── ActivityFeed.tsx

/backend/app/api/v1/dashboard.py  # Dashboard data endpoint
```

#### 2.2 Navigation & Layout
**Priority: HIGH**

**New Navigation Structure:**
```
Top Nav:
- LitDocket Logo (home)
- Global Search (⌘K to open)
- Notifications Bell (with count badge)
- User Menu (Settings, Logout)

Side Nav (collapsible):
- 📊 Dashboard
- 📅 Calendar
- 🗂️ Cases
  - All Cases
  - Active
  - Archived
- ⚡ Quick Actions
  - New Case
  - Upload Document
  - Create Deadline
- ⚙️ Settings

Breadcrumbs:
Dashboard > Cases > Case ABC > Deadlines
```

**Files to Update:**
```
/frontend/components/
  ├── Navigation.tsx          # Top nav
  ├── Sidebar.tsx             # Side nav
  ├── Breadcrumbs.tsx         # Breadcrumb trail
  └── GlobalSearch.tsx        # ⌘K search

/frontend/app/layout.tsx      # Update with new navigation
```

#### 2.3 Global Search
**Priority: HIGH**

**Features:**
- ⌘K (Mac) / Ctrl+K (Windows) to open
- Search across cases, deadlines, documents
- Fuzzy matching
- Recent searches
- Keyboard navigation

**Search Results:**
```
┌─────────────────────────────────────┐
│ Search                          ⌘K  │
│ ┌─────────────────────────────────┐ │
│ │ motion to dismiss              │ │
│ └─────────────────────────────────┘ │
│                                     │
│ Cases (2)                           │
│ ○ Smith v. Jones - #2024-CV-123    │
│ ○ Doe v. Roe - #2024-CV-456        │
│                                     │
│ Documents (5)                       │
│ ○ Motion to Dismiss.pdf             │
│ ○ Order on MTD.pdf                  │
│                                     │
│ Deadlines (1)                       │
│ ○ Response to MTD - Jan 15, 2024    │
└─────────────────────────────────────┘
```

**Backend:**
```python
# /backend/app/api/v1/search.py
@router.get("/search")
def global_search(
    query: str,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Search cases (case number, title, parties)
    # Search deadlines (title, description)
    # Search documents (filename, content via embeddings)
    # Return ranked results
```

---

### **PHASE 3: Calendar & Deadline Management (2 weeks)**
*The core of any docketing system*

#### 3.1 Full Calendar View
**Priority: CRITICAL**

**Features:**
- Month view (default)
- Week view
- Day view
- List view (existing deadline list enhanced)
- Filter by case, jurisdiction, status
- Color-coded by case or priority
- Drag & drop to reschedule (with confirmation)
- Click deadline to see details
- Create deadline by clicking date

**Calendar UI:**
```
┌─────────────────────────────────────────────────────┐
│ Calendar                     Jan 2024      [Month▼] │
├─────────────────────────────────────────────────────┤
│ Filters: [All Cases ▼] [All Jurisdictions ▼]       │
├─────────────────────────────────────────────────────┤
│  Sun   Mon   Tue   Wed   Thu   Fri   Sat           │
│        1     2     3     4     5     6              │
│              ●     ●                                 │
│  7     8     9     10    11    12    13             │
│                          ●●                          │
│  14    15    16    17    18    19    20             │
│        ●●●                                           │
│  21    22    23    24    25    26    27             │
│                                                      │
│  28    29    30    31                                │
│                                                      │
├─────────────────────────────────────────────────────┤
│ Legend: ● = 1 deadline  ●● = 2+  Red = Urgent      │
└─────────────────────────────────────────────────────┘
```

**Day View (when clicking a date):**
```
┌─────────────────────────────────────────┐
│ Monday, January 15, 2024                │
├─────────────────────────────────────────┤
│ 9:00 AM  Court Hearing - Smith v Jones  │
│          Courtroom 3B, Judge Anderson   │
│          [View Case] [Add to Calendar]  │
│                                          │
│ 5:00 PM  Response to MTD Due            │
│          Case: Doe v. Roe               │
│          [Mark Complete] [View]         │
│                                          │
│ [+ Add Deadline]                         │
└─────────────────────────────────────────┘
```

**Files to Create:**
```
/frontend/app/calendar/
  ├── page.tsx                  # Calendar main page
  ├── components/
  │   ├── MonthView.tsx
  │   ├── WeekView.tsx
  │   ├── DayView.tsx
  │   ├── ListView.tsx
  │   ├── CalendarFilters.tsx
  │   ├── DeadlineModal.tsx     # Click deadline to open
  │   └── CreateDeadlineModal.tsx

/backend/app/api/v1/calendar.py
  ├── GET /calendar/events?start=2024-01-01&end=2024-01-31
  ├── GET /calendar/day/2024-01-15
  └── POST /calendar/sync  # One-way sync to Google Calendar
```

**Libraries:**
- `react-big-calendar` or `@fullcalendar/react` for calendar UI
- `date-fns` for date manipulation

#### 3.2 Case-Specific Calendar
**Priority: HIGH**

**Add to each case page:**
```
┌─────────────────────────────────────────┐
│ Case: Smith v. Jones                    │
├─────────────────────────────────────────┤
│ [Overview] [Documents] [Deadlines]      │
│ [Calendar] [Chat] [Activity]            │ ← NEW TAB
├─────────────────────────────────────────┤
│                                          │
│      Case Calendar - Jan 2024           │
│  Sun   Mon   Tue   Wed   Thu   Fri      │
│        1     2     3     4     5         │
│              ●                            │
│  ...                                     │
│                                          │
│  Upcoming for this case:                 │
│  • Motion to Dismiss - Jan 15            │
│  • Discovery Deadline - Feb 1            │
│                                          │
└─────────────────────────────────────────┘
```

#### 3.3 Conflict Detection
**Priority: HIGH**

**Backend Logic:**
```python
# /backend/app/services/conflict_detector.py
def check_conflicts(deadline_date: date, user_id: str, db: Session):
    """
    Check if user has conflicting deadlines on same date/time

    Conflicts:
    - Multiple court hearings on same day
    - Overlapping hearing times
    - Multiple "hard" deadlines on same day (warn only)
    """
    conflicts = []

    # Check same date
    same_day_deadlines = db.query(Deadline).filter(
        Deadline.deadline_date == deadline_date,
        Deadline.user_id == user_id,
        Deadline.status == 'pending'
    ).all()

    # Check if any are hearings
    hearings = [d for d in same_day_deadlines if d.deadline_type == 'hearing']
    if len(hearings) > 1:
        conflicts.append({
            'type': 'multiple_hearings',
            'severity': 'critical',
            'message': f'Multiple hearings scheduled on {deadline_date}'
        })

    return conflicts
```

**UI:**
```
┌─────────────────────────────────────────┐
│ ⚠️ Conflict Detected                    │
├─────────────────────────────────────────┤
│ You have multiple deadlines on Jan 15:  │
│                                          │
│ • Court Hearing - Smith v. Jones         │
│   9:00 AM, Courtroom 3B                  │
│                                          │
│ • Response to MTD - Doe v. Roe           │
│   Due by 5:00 PM                         │
│                                          │
│ [Create Anyway] [Reschedule]             │
└─────────────────────────────────────────┘
```

#### 3.4 Google Calendar Sync (One-Way)
**Priority: MEDIUM**

**Features:**
- Connect Google Calendar in settings
- Push deadlines to Google Calendar (one-way only)
- Updates in LitDocket sync to Google
- Changes in Google Calendar are IGNORED
- Sync button to manually trigger sync

**Implementation:**
```typescript
// /frontend/lib/google-calendar.ts
export async function syncToGoogleCalendar(deadline: Deadline) {
  // Only if user has connected Google Calendar
  // Create/update event in Google Calendar
  // Store google_event_id on deadline
}
```

---

### **PHASE 4: Document Management & Polish (1-2 weeks)**
*Make documents organized and professional*

#### 4.1 Enhanced Document Management
**Priority: HIGH**

**Features:**
- Sort by: Date (default), Name, Type, Size
- Filter by: Type (motion, order, discovery, correspondence)
- Color-coded by type
- Tags (user-defined + AI-suggested)
- Bulk actions (download multiple, tag multiple)
- Document preview (PDF viewer)
- Quick actions (download, delete, view in case)

**Document List UI:**
```
┌─────────────────────────────────────────────────────┐
│ Documents                    [Sort: Date ▼] [Filter]│
├─────────────────────────────────────────────────────┤
│ Jan 15, 2024                                         │
│ 📄 Motion to Dismiss.pdf           [Motion] [★]     │
│    Smith v. Jones • 1.2 MB                          │
│    Tags: summary-judgment, important                │
│    [View] [Download] [Add Tag]                      │
│                                                      │
│ Jan 14, 2024                                         │
│ 📄 Discovery Request.pdf           [Discovery]      │
│    Doe v. Roe • 450 KB                              │
│    [View] [Download] [Add Tag]                      │
│                                                      │
│ Jan 10, 2024                                         │
│ 📄 Order on MTD.pdf               [Order] [★]       │
│    Smith v. Jones • 89 KB                           │
│    [View] [Download] [Add Tag]                      │
└─────────────────────────────────────────────────────┘
```

**Color Coding:**
- 🔵 Motion (blue)
- 🟢 Order (green)
- 🟡 Discovery (yellow)
- 🟣 Correspondence (purple)
- ⚪ Other (gray)

#### 4.2 AI Document Categorization
**Priority: HIGH**

**Auto-categorize on upload:**
```python
# /backend/app/services/document_categorizer.py
async def categorize_document(text: str) -> dict:
    """
    Use Claude to categorize document

    Returns:
    {
        'category': 'motion',  # motion, order, discovery, correspondence, pleading
        'subcategory': 'motion_to_dismiss',
        'confidence': 0.95,
        'suggested_tags': ['summary-judgment', 'dispositive']
    }
    """

    prompt = f"""Analyze this legal document and categorize it.

    Categories: motion, order, discovery, correspondence, pleading, notice, brief, other

    Document text:
    {text[:5000]}  # First 5000 chars

    Return JSON:
    {{
        "category": "...",
        "subcategory": "...",
        "confidence": 0.0-1.0,
        "suggested_tags": []
    }}
    """
```

**UI Feedback:**
```
┌─────────────────────────────────────────┐
│ ✓ Document Uploaded                     │
├─────────────────────────────────────────┤
│ Motion to Dismiss.pdf                    │
│                                          │
│ AI Analysis:                             │
│ Category: Motion                         │
│ Subcategory: Motion to Dismiss           │
│ Suggested tags: summary-judgment         │
│                                          │
│ [Accept] [Edit]                          │
└─────────────────────────────────────────┘
```

#### 4.3 OCR Integration
**Priority: MEDIUM**

**Workflow:**
1. Upload PDF
2. Check if text is extractable
3. If text extraction fails or confidence low → OCR
4. Show OCR status to user
5. Allow user to manually trigger OCR

**Backend:**
```python
# /backend/app/services/ocr_service.py
from google.cloud import vision

async def check_if_readable(pdf_bytes: bytes) -> bool:
    """Check if PDF has extractable text"""
    try:
        text = extract_text_from_pdf(pdf_bytes)
        return len(text.strip()) > 100  # Arbitrary threshold
    except:
        return False

async def perform_ocr(pdf_bytes: bytes) -> dict:
    """
    Perform OCR using Google Cloud Vision API

    Returns:
    {
        'text': '...',
        'confidence': 0.95,
        'status': 'completed'
    }
    """
    # Convert PDF to images
    # Send to Google Vision API
    # Combine results
    # Return text + confidence
```

**UI:**
```
┌─────────────────────────────────────────┐
│ 📄 Scanned Document.pdf                 │
├─────────────────────────────────────────┤
│ ⚠️ This appears to be a scanned image   │
│                                          │
│ OCR Status: Processing...                │
│ ████████░░░░ 80%                         │
│                                          │
│ Estimated completion: 30 seconds         │
└─────────────────────────────────────────┘
```

#### 4.4 Comments & Notes
**Priority: MEDIUM**

**Add comments to:**
- Cases
- Deadlines
- Documents

**UI:**
```
┌─────────────────────────────────────────┐
│ Motion to Dismiss.pdf                    │
├─────────────────────────────────────────┤
│ 💬 Comments (2)                          │
│                                          │
│ John Doe • 2 hours ago                   │
│ "This is a strong motion, we should     │
│  focus on the jurisdictional issue."     │
│                                          │
│ Jane Smith • 1 hour ago                  │
│ "Agreed. I'll draft the response."       │
│                                          │
│ [Add Comment]                            │
└─────────────────────────────────────────┘
```

---

### **PHASE 5: Notifications & Alerts (1 week)**
*Critical for deadline management*

#### 5.1 Notification System
**Priority: CRITICAL**

**Backend:**
```python
# /backend/app/services/notification_service.py
class NotificationService:
    def create_notification(
        self,
        user_id: str,
        type: str,
        title: str,
        message: str,
        related_case_id: str = None,
        related_deadline_id: str = None,
        db: Session = None
    ):
        # Create notification in database
        # Send via configured methods (email, in-app)

    def send_deadline_reminder(self, deadline: Deadline, db: Session):
        # Check user preferences
        # Calculate days until deadline
        # If matches alert preference (7d, 3d, 1d)
        # Send notification

# Scheduled job (Celery or Cloud Scheduler)
@scheduler.scheduled_job('cron', hour=8)  # Run daily at 8 AM
def send_daily_deadline_reminders():
    # Find all deadlines due in 1, 3, 7 days
    # Check if reminder already sent
    # Send reminders based on user preferences
```

**Email Template:**
```html
Subject: Deadline Reminder: Motion to Dismiss due in 3 days

Hi [User Name],

You have an upcoming deadline:

Case: Smith v. Jones (#2024-CV-123)
Deadline: Motion to Dismiss Response
Due: January 15, 2024 (3 days from now)

[View in LitDocket]

---
LitDocket - Professional Legal Docketing
Manage notification preferences: [Settings]
```

#### 5.2 In-App Notifications
**Priority: HIGH**

**Notification Bell:**
```
┌─────────────────────────────────────────┐
│ 🔔 (3)                                   │
└─────────────────────────────────────────┘
     ↓ (click)
┌─────────────────────────────────────────┐
│ Notifications                  [Mark All]│
├─────────────────────────────────────────┤
│ ● Motion to Dismiss due in 3 days        │
│   Smith v. Jones                         │
│   2 hours ago                            │
│                                          │
│ ● New document uploaded                  │
│   Doe v. Roe: Order.pdf                  │
│   5 hours ago                            │
│                                          │
│ ● Conflict detected                      │
│   Two hearings on Jan 15                 │
│   1 day ago                              │
│                                          │
│ [View All Notifications]                 │
└─────────────────────────────────────────┘
```

**Real-time Updates:**
- Use Server-Sent Events (SSE) for real-time in-app notifications
- Simpler than WebSocket, one-way communication

```typescript
// /frontend/lib/notifications.ts
export function useNotifications() {
  useEffect(() => {
    const eventSource = new EventSource('/api/v1/notifications/stream');

    eventSource.onmessage = (event) => {
      const notification = JSON.parse(event.data);
      // Show toast
      // Update notification bell count
      // Play sound (optional)
    };

    return () => eventSource.close();
  }, []);
}
```

---

### **PHASE 6: UX Polish & Professional Feel (1 week)**
*Make it feel like a $10,000 product*

#### 6.1 Visual Design System
**Priority: HIGH**

**Create consistent design language:**
```
Colors:
- Primary: #2563eb (blue-600)
- Success: #10b981 (green-500)
- Warning: #f59e0b (amber-500)
- Danger: #ef4444 (red-500)
- Gray scale: slate-50 to slate-900

Typography:
- Headings: Inter font, bold
- Body: Inter font, regular
- Mono: JetBrains Mono (for case numbers, dates)

Shadows:
- sm: subtle elevation
- md: cards, modals
- lg: popovers, dropdowns
- xl: overlays

Spacing:
- 4px base unit
- Consistent padding/margins
```

**Component Library:**
```
/frontend/components/ui/
  ├── Button.tsx         # Primary, Secondary, Danger variants
  ├── Card.tsx          # Consistent card styling
  ├── Badge.tsx         # Status badges
  ├── Modal.tsx         # Consistent modal
  ├── Dropdown.tsx      # Menus
  ├── Tabs.tsx          # Tab navigation
  ├── Toast.tsx         # Already exists, enhance
  └── EmptyState.tsx    # "No cases yet" states
```

#### 6.2 Loading & Empty States
**Priority: MEDIUM**

**Loading States:**
- Skeleton screens (not spinners)
- Smooth transitions
- Progress indicators for uploads

**Empty States:**
```
┌─────────────────────────────────────────┐
│                                          │
│         📁                               │
│                                          │
│    No cases yet                          │
│                                          │
│    Get started by creating your first   │
│    case or uploading a document          │
│                                          │
│    [Create Case] [Upload Document]       │
│                                          │
└─────────────────────────────────────────┘
```

#### 6.3 Responsive Design
**Priority: MEDIUM**

- Desktop-first (lawyers use computers)
- Tablet: Sidebar collapses to hamburger
- Mobile: Stack vertically, touch-friendly buttons

#### 6.4 Keyboard Shortcuts
**Priority: LOW**

```
Global:
⌘K / Ctrl+K - Search
⌘N / Ctrl+N - New case
⌘U / Ctrl+U - Upload document
⌘/ / Ctrl+/ - Show shortcuts

Navigation:
⌘1 / Ctrl+1 - Dashboard
⌘2 / Ctrl+2 - Calendar
⌘3 / Ctrl+3 - Cases
```

#### 6.5 Animations & Transitions
**Priority: LOW**

- Smooth page transitions (Framer Motion)
- Hover states on all interactive elements
- Micro-interactions (checkmark animation on complete)
- Loading state animations

---

## Summary: Feature Comparison

### Before (Current 5%)
- ❌ Demo user only
- ❌ Basic case list
- ❌ Flat deadline list
- ❌ No calendar
- ❌ No notifications
- ❌ No search
- ❌ Basic document list
- ✅ PDF upload
- ✅ AI deadline extraction
- ✅ Chat interface

### After (Target 90%)
- ✅ **Google OAuth + email/password auth**
- ✅ **User profiles & settings**
- ✅ **Professional dashboard**
- ✅ **Full calendar views** (month, week, day, list)
- ✅ **Case-specific calendars**
- ✅ **Conflict detection**
- ✅ **Notification system** (email + in-app)
- ✅ **Global search** (⌘K)
- ✅ **Enhanced document management** (categorization, tags, colors)
- ✅ **AI auto-categorization**
- ✅ **OCR for scanned documents**
- ✅ **Comments on cases/deadlines/documents**
- ✅ **Task assignment**
- ✅ **Activity feed**
- ✅ **One-way Google Calendar sync**
- ✅ **Professional UI/UX**
- ✅ **Responsive design**
- ✅ **Consistent design system**
- ✅ All existing features (PDF upload, AI extraction, chat)

---

## Implementation Timeline

| Phase | Duration | Focus |
|-------|----------|-------|
| Phase 1 | 2-3 weeks | Auth, Users, Database |
| Phase 2 | 1-2 weeks | Dashboard, Navigation |
| Phase 3 | 2 weeks | Calendar, Conflicts |
| Phase 4 | 1-2 weeks | Documents, OCR |
| Phase 5 | 1 week | Notifications |
| Phase 6 | 1 week | Polish, UX |
| **Total** | **8-11 weeks** | **Full System** |

---

## Technology Stack Updates

### Backend
- ✅ FastAPI (keep)
- ✅ PostgreSQL (keep)
- ✅ Firebase Storage (keep)
- ➕ **Firebase Auth** (add for authentication)
- ➕ **Google Cloud Vision** (add for OCR)
- ➕ **SendGrid** (add for email notifications)
- ➕ **Celery + Redis** (add for scheduled jobs - deadline reminders)

### Frontend
- ✅ Next.js (keep)
- ✅ Tailwind CSS (keep)
- ➕ **react-big-calendar** or **@fullcalendar/react** (calendar views)
- ➕ **cmdk** (⌘K search interface)
- ➕ **Framer Motion** (animations)
- ➕ **date-fns** (date manipulation)
- ➕ **react-pdf** or **pdf.js** (PDF preview)

---

## Deployment Strategy

**Recommended: Vercel + Neon + Firebase**

| Service | Purpose | Cost |
|---------|---------|------|
| Vercel | Frontend + Backend (serverless) | Free → $20/mo |
| Neon | PostgreSQL database | Free → $19/mo |
| Firebase | Auth + Storage | Free → $5/mo |
| SendGrid | Email notifications | Free (100/day) |
| Google Cloud Vision | OCR | $1.50/1000 pages |

**Total: $0-50/month** depending on usage

---

## Next Steps

### Immediate (This Week):
1. ✅ Fix chat error (DONE)
2. Implement Firebase Auth (Phase 1.1)
3. Create login/signup pages
4. Update database with user enhancements

### Week 2:
1. User settings page
2. Start dashboard layout
3. Global search

### Week 3-4:
1. Calendar views
2. Conflict detection
3. Google Calendar sync

**Let me know if you want me to:**
1. Start with Phase 1 (Authentication) right now?
2. Create detailed UI mockups for specific pages?
3. Adjust priorities based on your feedback?

This plan will transform LitDocket from a 5% shell into a professional, competitive docketing system that attorneys will actually want to use.
