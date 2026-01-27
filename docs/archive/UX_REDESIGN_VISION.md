# LitDocket UX/UI Redesign Vision

## Core Philosophy: From Rule-Centric to Case-Centric

**Problem**: Current legal tech is built around *rules*, not *cases*. Attorneys don't think "I need to apply Rule 12(a)" — they think "I just got served in the Smith case, what do I do?"

**Solution**: Redesign around the attorney's mental model: **Cases → Documents → Deadlines → Actions**

---

## 🎯 Three Core Experiences

### 1. **Morning Report Dashboard** (Default View)
**Goal**: Answer "What needs my attention?" in 5 seconds

```
┌─────────────────────────────────────────────────────────────┐
│  Good morning, Sarah 👋                    Friday, Jan 27   │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  🚨 URGENT (Due in 48 hours)                                │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ ⚠️  Answer Due - Smith v. Jones Corp                  │  │
│  │     Monday, Jan 29 by 5:00 PM (2 days)               │  │
│  │     📎 Draft ready for review                         │  │
│  │     [Review Draft]  [Mark Complete]                   │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                               │
│  📅 THIS WEEK (3 deadlines)                                  │
│  • Discovery responses due - Johnson matter (Thu)            │
│  • Motion to compel hearing - Davis case (Fri)               │
│  • Expert designation - Miller v. State (Fri)                │
│                                                               │
│  ✅ COMPLETED TODAY (2)                                      │
│  • Filed opposition brief - Anderson case                    │
│  • Served interrogatories - Wilson matter                    │
│                                                               │
│  ⚡ QUICK ACTIONS                                            │
│  [+ New Case]  [Upload Document]  [View Calendar]            │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

**Key Features**:
- Color-coded urgency (red = <48h, yellow = this week, green = completed)
- Action buttons right where you need them
- Collapsible sections (focus on urgent)
- Smart grouping by deadline proximity

---

### 2. **Case Timeline View** (Visual Deadline Map)
**Goal**: See the entire case lifecycle at a glance

```
┌─────────────────────────────────────────────────────────────┐
│  Smith v. Jones Corp                      [⚙️ Settings] [📤] │
│  Case No. 2026-CV-12345 | Filed: Dec 15, 2025               │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Timeline View  [Calendar View]  [List View]                 │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐│
│  │                                                          ││
│  │  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ││
│  │  │         │         │    YOU    │         │           ││
│  │  │         │         │   ARE     │         │           ││
│  │ SERVED  ANSWER   DISCOVERY  HERE   TRIAL   VERDICT    ││
│  │ Dec 20   Jan 29   Mar 15          Aug 20   Sep 5      ││
│  │  ✅       🚨        📋             📅       📅         ││
│  │         2 DAYS                                          ││
│  │                                                          ││
│  └──────────────────────────────────────────────────────────┘│
│                                                               │
│  Upcoming Milestones:                                         │
│  🚨 Answer Due - Jan 29 (2 days) - FATAL                    │
│     ├─ Draft answer (in progress)                            │
│     ├─ Client review needed                                  │
│     └─ E-file by 4:00 PM                                     │
│                                                               │
│  📋 Initial Disclosures - Mar 15 (47 days)                   │
│  📅 Trial Date - Aug 20 (205 days)                           │
│                                                               │
│  [+ Add Milestone]  [Bulk Upload Dates]  [Export Timeline]   │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

**Key Features**:
- Visual timeline with "You Are Here" indicator
- Expandable milestones showing sub-tasks
- Color coding by priority (red=FATAL, yellow=CRITICAL, blue=IMPORTANT)
- Smart dependency lines (answer → discovery → trial)
- Drag-to-reschedule with cascade updates

---

### 3. **Smart Document Upload** (AI-Powered Rule Application)
**Goal**: Go from "I got served" to "All deadlines calculated" in 30 seconds

```
┌─────────────────────────────────────────────────────────────┐
│  Upload Document                                       [✕]   │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐│
│  │                                                          ││
│  │         📄 Drag & drop or click to upload               ││
│  │                                                          ││
│  │         Supported: PDF, DOCX, images                    ││
│  │                                                          ││
│  └──────────────────────────────────────────────────────────┘│
│                                                               │
│  OR paste text:                                               │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ "Summons and Complaint served via certified mail on    ││
│  │  January 15, 2026 in California state court..."        ││
│  └──────────────────────────────────────────────────────────┘│
│                                                               │
│  [Analyze Document]                                           │
│                                                               │
└─────────────────────────────────────────────────────────────┘

      ↓ ↓ ↓ (After upload) ↓ ↓ ↓

┌─────────────────────────────────────────────────────────────┐
│  ✨ Document Analysis Complete                               │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  I found these key dates:                                     │
│  • Service Date: January 15, 2026                            │
│  • Service Method: Certified mail                            │
│  • Jurisdiction: California Superior Court                   │
│  • Document Type: Summons and Complaint                      │
│                                                               │
│  📅 Calculated Deadlines:                                    │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ 🚨 Answer Due: February 19, 2026 (35 days)            │  │
│  │    California: 30 days + 5 days for mail service      │  │
│  │    Rule: CCP § 412.20(a)(3)                           │  │
│  │    Priority: FATAL                                     │  │
│  │                                                        │  │
│  │    [✓] Add to calendar                                │  │
│  │    [✓] Create reminder (7 days before)                │  │
│  │    [✓] Notify co-counsel                              │  │
│  │                                                        │  │
│  │    Confidence: 99% ✓ Verified                         │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                               │
│  📋 Related Deadlines (auto-calculated):                     │
│  • Motion to dismiss deadline: Feb 19, 2026                  │
│  • General appearance alternative: Feb 19, 2026              │
│                                                               │
│  [Create Case & Add Deadlines]  [Adjust Dates]               │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

**Key Features**:
- Claude AI extracts dates, jurisdiction, document type
- Auto-applies correct rule based on context
- Shows calculation with legal citations
- Confidence score (AI transparency)
- One-click accept or manual adjustment
- Batch imports (e.g., mass tort cases)

---

## 🎨 Design System

### Color Palette (Legal + Modern)
```
Primary (IBM Blue):     #0F62FE (trust, authority)
Fatal Red:              #DA1E28 (urgent, cannot miss)
Critical Orange:        #FF832B (important, attention needed)
Important Yellow:       #F1C21B (monitor closely)
Success Green:          #24A148 (completed, good status)
Neutral Gray:           #525252 (supporting text)
Background:             #F4F4F4 (light) / #161616 (dark mode)
```

### Typography
```
Headings:    IBM Plex Serif (legal gravitas)
Body:        IBM Plex Sans (clarity, readability)
Code/Rules:  IBM Plex Mono (citations, statutes)
```

### Priority Visual Language
```
🚨 FATAL:     Red badge, pulsing dot, bold
⚠️  CRITICAL:  Orange badge, bold
📋 IMPORTANT:  Yellow badge, normal weight
📅 STANDARD:   Blue badge, normal weight
ℹ️  INFO:      Gray badge, lighter weight
```

---

## 📱 Mobile-First Critical Features

### Push Notifications (Smart Timing)
```
Morning (8 AM):  "2 deadlines due this week"
Before EOD:      "Answer due tomorrow - draft ready?"
Weekend:         "Monday deadline approaching - Smith case"
```

### Mobile Quick Actions
- Swipe right: Mark complete
- Swipe left: Snooze/reschedule
- Long press: View details
- Pull to refresh: Check for updates

### Offline Mode
- View all deadlines (cached)
- Mark items complete (sync when online)
- Critical info always available

---

## ⌨️ Power User Features

### Command Palette (⌘K or Ctrl+K)
```
┌─────────────────────────────────────────────────────────────┐
│  Type a command...                                      ⌘K   │
├─────────────────────────────────────────────────────────────┤
│  > add deadline                                               │
│                                                               │
│  Suggestions:                                                 │
│  📅 Add deadline to Smith case                               │
│  📅 Add new case with deadline                               │
│  📄 Upload document and calculate deadlines                  │
│  ⚙️  Manage deadline rules                                   │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### Keyboard Shortcuts
```
n          New case
d          New deadline
u          Upload document
/          Search
⌘/Ctrl+K   Command palette
c          Toggle calendar view
m          Morning report
?          Show all shortcuts
```

### Bulk Operations
- Select multiple deadlines → Reschedule all
- Import CSV of trial dates → Auto-calculate all pre-trial deadlines
- Clone case → Duplicate timeline structure

---

## 🔔 Smart Alerts & Reminders

### Intelligent Notification Schedule
```
FATAL deadlines:
  - 14 days before (first warning)
  - 7 days before (second warning)
  - 3 days before (urgent)
  - 1 day before (final warning)
  - Morning of (day of)
  - 2 hours before COB (last chance)

CRITICAL deadlines:
  - 7 days before
  - 1 day before
  - Morning of

IMPORTANT deadlines:
  - 3 days before
  - Morning of
```

### Smart Snoozing
```
"Remind me about this when..."
  • Draft is ready for review
  • Client responds to email
  • Co-counsel files their motion
  • 3 days before deadline
  • Custom date/time
```

---

## 🔗 Integration Points

### Calendar Sync (Two-Way)
- Export deadlines to Outlook/Google Calendar
- Show court dates from calendar in LitDocket
- Auto-update both when changed

### Email Integration
- Forward service emails → Auto-detect dates
- Send deadline reminders via email
- Export deadline report to client

### Court E-Filing Systems
- Check filing confirmation → Auto-mark complete
- Pull trial dates from court dockets
- Verify service dates from e-filing receipts

### Document Management
- Link to NetDocuments, iManage, SharePoint
- Attach drafts to deadlines
- Version control for filings

---

## 🎯 Implementation Priority

### Phase 1 (MVP - 2 weeks)
1. ✅ Morning Report Dashboard
2. ✅ Case Timeline View (basic)
3. ✅ Manual deadline creation (improved UX)
4. ✅ Priority color coding
5. ✅ Mobile responsive design

### Phase 2 (Enhanced - 4 weeks)
1. ✅ Smart Document Upload (AI extraction)
2. ✅ Command palette (⌘K)
3. ✅ Calendar sync (export)
4. ✅ Bulk operations
5. ✅ Dark mode

### Phase 3 (Power Features - 6 weeks)
1. ✅ Visual timeline with drag-to-reschedule
2. ✅ Smart notifications (push)
3. ✅ Offline mode (mobile)
4. ✅ Advanced search & filters
5. ✅ Client-facing reports

### Phase 4 (Integrations - 8 weeks)
1. ✅ Two-way calendar sync
2. ✅ Email forwarding integration
3. ✅ Document management links
4. ✅ Court e-filing integration
5. ✅ Team collaboration features

---

## 🧪 Testing with Real Attorneys

### Usability Testing Script
1. **Task 1**: "You just got served in a California case. Show me how you'd use LitDocket."
   - Expected: Upload doc → AI extracts → Accept deadline → Done (<60 sec)

2. **Task 2**: "Show me what deadlines you have this week."
   - Expected: Lands on Morning Report → Sees urgent items immediately

3. **Task 3**: "The trial date just changed. Update it."
   - Expected: Find case → Change trial date → See cascade update → Confirm

4. **Task 4**: "You're in court and need to check a deadline on your phone."
   - Expected: Opens mobile → Sees critical info → No scrolling needed

### Success Metrics
- Time to value: <30 seconds (from login to seeing urgent deadlines)
- Deadline accuracy: 100% (verified against court rules)
- User satisfaction: >4.5/5 (post-pilot survey)
- Mobile usage: >40% (attorneys check between hearings)
- Feature adoption: >80% use AI upload within first month

---

## 💡 Unique Differentiators

**vs CompuLaw**:
- Modern UI (not Windows 95)
- AI-powered document analysis
- Mobile-first design
- Real-time collaboration

**vs LawToolBox**:
- Visual timeline (not just list)
- Smart rule suggestions
- Built-in document upload
- Cheaper pricing ($50/user vs $95/user)

**vs Manual Calendaring**:
- Automatic cascade updates
- No human error in calculation
- Audit trail for malpractice protection
- Team visibility

---

## 🎨 Example Wireframe: Morning Report (Detailed)

```
┌───────────────────────────────────────────────────────────────────┐
│ [☰]  LitDocket                    [🔍 Search]  [⌘K]  [👤 Profile] │
├───────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Good morning, Sarah 👋            🌤️  Fri, January 27, 2026      │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │ 🚨 URGENT: 2 deadlines due in next 48 hours                 │  │
│  │                                                              │  │
│  │ ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓  │  │
│  │ ┃ ⚠️  Answer Due - Smith v. Jones Corp                   ┃  │  │
│  │ ┃     Monday, Jan 29, 2026 @ 5:00 PM PT                  ┃  │  │
│  │ ┃     ⏰ 2 days, 6 hours remaining                        ┃  │  │
│  │ ┃                                                         ┃  │  │
│  │ ┃     California Superior Court | Case No. 2026-CV-12345 ┃  │  │
│  │ ┃     CCP § 412.20(a) - 30 days + 5 mail service        ┃  │  │
│  │ ┃                                                         ┃  │  │
│  │ ┃     Status: 📝 Draft in progress (75% complete)        ┃  │  │
│  │ ┃     Assigned: John Doe (co-counsel)                    ┃  │  │
│  │ ┃                                                         ┃  │  │
│  │ ┃     [📄 View Draft]  [✓ Mark Complete]  [⏰ Snooze]    ┃  │  │
│  │ ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛  │  │
│  │                                                              │  │
│  │ ┌─────────────────────────────────────────────────────────┐│  │
│  │ │ ⚠️  Discovery Responses - Johnson v. XYZ Inc           ││  │
│  │ │     Monday, Jan 29, 2026 @ 5:00 PM EST                 ││  │
│  │ │     ⏰ 2 days, 9 hours remaining                        ││  │
│  │ │                                                         ││  │
│  │ │     [📂 View Responses]  [✓ Complete]  [Extend]       ││  │
│  │ └─────────────────────────────────────────────────────────┘│  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  📅 THIS WEEK (5 deadlines) ────────────────────────── [View All]  │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │ Wed 1/31  • Motion to Compel Hearing - Davis case (10 AM)  │  │
│  │ Thu 2/1   • Expert Designation - Miller v. State           │  │
│  │ Fri 2/2   • Deposition: Jane Smith - Anderson matter       │  │
│  │ Fri 2/2   • Opposition brief due - Wilson case              │  │
│  │ Fri 2/2   • Status conference - Thompson v. ABC Corp       │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ✅ COMPLETED TODAY (3) ──────────────────────────── [View All]   │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │ ✓ Filed opposition brief - Anderson case (9:45 AM)          │  │
│  │ ✓ Served interrogatories - Wilson matter (11:30 AM)         │  │
│  │ ✓ Client meeting - Smith case recap (2:00 PM)               │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ⚡ QUICK ACTIONS ───────────────────────────────────────────────  │
│  [+ New Case]  [📄 Upload Doc]  [📅 Calendar]  [⚙️ Settings]      │
│                                                                     │
│  ───────────────────────────────────────────────────────────────  │
│  Recent Activity                                                    │
│  • 15 min ago: John added note to Smith case                       │
│  • 1 hour ago: Trial date updated in Davis case                    │
│  • 2 hours ago: New document uploaded - Johnson matter             │
│                                                                     │
└───────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Technical Implementation Notes

### Frontend Stack
- **Next.js 14** (App Router) - Already using
- **Tailwind CSS** - Already using, extend with custom design system
- **Framer Motion** - For smooth animations (timeline, drag-drop)
- **React DnD** - Drag-to-reschedule deadlines
- **date-fns** - Date manipulation (replace moment.js)
- **Recharts** - Timeline visualizations
- **Radix UI** - Accessible components (command palette, modals)

### New Components Needed
```
/components
  /dashboard
    MorningReport.tsx
    UrgentDeadlineCard.tsx
    WeeklyPreview.tsx
    QuickActions.tsx
  /timeline
    CaseTimeline.tsx
    TimelineEvent.tsx
    DraggableDeadline.tsx
  /upload
    SmartUpload.tsx
    AIAnalysisResult.tsx
    DeadlineConfirmation.tsx
  /shared
    CommandPalette.tsx (⌘K)
    PriorityBadge.tsx
    DeadlineCountdown.tsx
```

### Backend Enhancements Needed
```python
# New endpoints
POST /api/v1/ai/analyze-document
  - Accept: PDF, DOCX, image
  - Claude API to extract dates/jurisdiction
  - Return: structured deadline data

GET /api/v1/dashboard/morning-report
  - Urgent deadlines (<48h)
  - This week's deadlines
  - Today's completed items

POST /api/v1/deadlines/bulk-update
  - Update multiple deadlines
  - Cascade changes to dependencies

GET /api/v1/cases/{id}/timeline
  - All milestones for a case
  - With dependencies mapped
```

---

## 📊 Analytics to Track

### User Engagement
- Daily active users
- Feature adoption rates
- Time spent per session
- Most-used features

### Deadline Management
- Deadlines missed (goal: 0%)
- Average time to create deadline
- AI extraction accuracy
- Manual overrides (% of auto-calculations changed)

### Business Impact
- Cases managed per user
- Deadlines tracked per case
- User retention (monthly)
- NPS score

---

This redesign transforms LitDocket from a "rules database" into an **intelligent deadline assistant** that works the way attorneys think.

**Next Steps**:
1. Get feedback on this vision
2. Prioritize features for MVP
3. Start with Morning Report Dashboard
4. Build out AI document upload
5. Iterate based on beta user feedback
