# Case OS Implementation Plan
## High-Fidelity Rules Engine + Proactive Chatbot + Verification Gates

**Goal:** Transform DocketAssist from a document analyzer into a proactive "Case OS" that manages the entire docketing lifecycle with legal-grade precision and human verification gates.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    CASE OS CHATBOT                          │
│  Proactive Lifecycle Manager + Context-Aware Assistant      │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│               VERIFICATION GATE SYSTEM                      │
│  AI Extraction → Confidence Scoring → Human Review → Commit │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│            HIGH-FIDELITY RULES ENGINE                       │
│  Court Days • Service Methods • Jurisdictional Math         │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                  DEADLINE DATABASE                          │
│  Verified, Accurate, Traceable, Audit-Ready                │
└─────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Harden Rules Engine (Week 1)

### 1.1 Enhanced Court Day Calculations

**Current State:**
- ✅ Basic court days (skip weekends/holidays)
- ✅ Service method +3 for mail
- ✅ Roll logic for weekends/holidays

**Enhancements Needed:**

#### A. Jurisdiction-Specific Holiday Calendars

```python
# /backend/app/utils/jurisdictional_calendars.py

FLORIDA_STATE_HOLIDAYS = {
    2025: [
        date(2025, 1, 1),   # New Year's Day
        date(2025, 1, 20),  # MLK Day
        date(2025, 2, 17),  # Presidents Day
        date(2025, 5, 26),  # Memorial Day
        date(2025, 7, 4),   # Independence Day
        date(2025, 9, 1),   # Labor Day
        date(2025, 11, 11), # Veterans Day
        date(2025, 11, 27), # Thanksgiving
        date(2025, 12, 25), # Christmas
    ]
}

FEDERAL_HOLIDAYS = {
    2025: [
        # Federal courts observe different holidays
        # Example: MLK Day observed, Columbus Day NOT observed in some districts
    ]
}

def get_jurisdiction_holidays(jurisdiction: str, year: int) -> List[date]:
    """Get holidays for specific jurisdiction"""
    if jurisdiction == "state":
        return FLORIDA_STATE_HOLIDAYS.get(year, [])
    elif jurisdiction == "federal":
        return FEDERAL_HOLIDAYS.get(year, [])
    else:
        return []
```

#### B. Local Rule Overrides

```python
# /backend/app/utils/local_rules.py

LOCAL_RULE_OVERRIDES = {
    "11th_circuit_state": {
        "summary_judgment_deadline": {
            "days_before_trial": 45,  # Override default 30
            "calculation_method": "court_days",
            "citation": "11th Cir. Local Rule 1.6"
        }
    },
    "southern_district_florida": {
        "discovery_cutoff": {
            "days_before_trial": 30,
            "calculation_method": "calendar_days",
            "citation": "S.D. Fla. Local Rule 16.1(b)"
        }
    }
}

def apply_local_rules(
    court: str,
    deadline_type: str,
    default_calculation: Dict
) -> Dict:
    """Apply local rule overrides if they exist"""
    court_key = normalize_court_name(court)

    if court_key in LOCAL_RULE_OVERRIDES:
        rules = LOCAL_RULE_OVERRIDES[court_key]
        if deadline_type in rules:
            return {**default_calculation, **rules[deadline_type]}

    return default_calculation
```

#### C. Enhanced Service Method Logic

**Current:** Only handles mail (+3 days)

**Enhanced:**
```python
# /backend/app/utils/service_methods.py

SERVICE_METHOD_EXTENSIONS = {
    "electronic": {
        "additional_days": 0,
        "citation": "Fla. R. Civ. P. 2.514(b)",
        "notes": "No extension for e-service"
    },
    "mail": {
        "additional_days": 3,
        "citation": "Fla. R. Civ. P. 2.514(b)",
        "notes": "Add 3 days for service by U.S. Mail"
    },
    "hand_delivery": {
        "additional_days": 0,
        "citation": "Fla. R. Civ. P. 2.514(b)",
        "notes": "No extension for hand delivery"
    },
    "certified_mail": {
        "additional_days": 3,
        "citation": "Fla. R. Civ. P. 2.514(b)",
        "notes": "Add 3 days (same as regular mail)"
    },
    "overnight": {
        "additional_days": 0,
        "citation": "Fla. R. Civ. P. 2.514(b)",
        "notes": "Commercial overnight = hand delivery"
    }
}

def calculate_response_deadline(
    service_date: date,
    base_response_days: int,
    service_method: str,
    jurisdiction: str
) -> Dict:
    """
    Calculate response deadline with service extensions

    Returns:
        {
            "deadline_date": date,
            "calculation_steps": [
                "Service date: 2025-06-01",
                "Base response period: 20 days",
                "Service method: mail (+3 days)",
                "Subtotal: 23 days",
                "Lands on: 2025-06-24 (Tuesday)",
                "Final deadline: 2025-06-24"
            ],
            "service_extension": 3,
            "rule_citations": ["Fla. R. Civ. P. 2.514(b)"]
        }
    """
```

### 1.2 Confidence Scoring System

**Add to AI extraction pipeline:**

```python
# /backend/app/services/deadline_extraction_service.py

class DeadlineConfidence:
    """Calculate confidence scores for extracted deadlines"""

    @staticmethod
    def calculate_confidence(
        extraction: Dict,
        source_text: str,
        rule_match: Optional[RuleTemplate]
    ) -> Dict:
        """
        Calculate confidence score (0-100) for deadline extraction

        Factors:
        1. Rule match confidence (40%)
        2. Date format clarity (20%)
        3. Context keywords (20%)
        4. Calculation consistency (20%)
        """
        score = 0
        factors = []

        # 1. Rule Match Confidence
        if rule_match:
            score += 40
            factors.append({
                "factor": "Rule Match",
                "score": 40,
                "evidence": f"Matched: {rule_match.citation}"
            })
        else:
            score += 10
            factors.append({
                "factor": "Rule Match",
                "score": 10,
                "evidence": "Generic deadline extraction (no specific rule)"
            })

        # 2. Date Format Clarity
        if extraction.get('deadline_date'):
            date_str = extraction.get('date_source_text', '')
            if re.match(r'\d{1,2}/\d{1,2}/\d{4}', date_str):
                score += 20
                factors.append({
                    "factor": "Date Clarity",
                    "score": 20,
                    "evidence": f"Clear date format: {date_str}"
                })
            elif 'within' in date_str.lower() or 'days' in date_str.lower():
                score += 15
                factors.append({
                    "factor": "Date Clarity",
                    "score": 15,
                    "evidence": f"Relative date: {date_str}"
                })
            else:
                score += 5
                factors.append({
                    "factor": "Date Clarity",
                    "score": 5,
                    "evidence": f"Ambiguous date: {date_str}"
                })

        # 3. Context Keywords
        keywords = ['shall', 'must', 'due', 'deadline', 'respond', 'file']
        found_keywords = [kw for kw in keywords if kw in source_text.lower()]
        keyword_score = min(20, len(found_keywords) * 5)
        score += keyword_score
        factors.append({
            "factor": "Context Keywords",
            "score": keyword_score,
            "evidence": f"Found: {', '.join(found_keywords)}"
        })

        # 4. Calculation Consistency
        if extraction.get('calculation_basis'):
            score += 20
            factors.append({
                "factor": "Calculation Consistency",
                "score": 20,
                "evidence": extraction['calculation_basis']
            })

        return {
            "confidence_score": min(100, score),
            "confidence_level": get_confidence_level(score),
            "factors": factors,
            "requires_review": score < 70
        }

def get_confidence_level(score: int) -> str:
    if score >= 90:
        return "high"
    elif score >= 70:
        return "medium"
    else:
        return "low"
```

### 1.3 Source Attribution

**Link deadlines back to PDF text:**

```python
# /backend/app/models/deadline.py

# Add new fields
source_page = Column(Integer)  # PDF page number
source_text = Column(Text)  # Exact text snippet
source_coordinates = Column(JSON)  # PDF coordinates for highlighting
confidence_score = Column(Integer)  # 0-100
confidence_level = Column(String(20))  # high, medium, low
confidence_factors = Column(JSON)  # Detailed confidence breakdown
verification_status = Column(String(20), default="pending")  # pending, approved, rejected
verified_by = Column(String)  # User ID who verified
verified_at = Column(DateTime)
```

---

## Phase 2: Verification Gate System (Week 2)

### 2.1 Backend API Endpoints

```python
# /backend/app/api/v1/verification.py

@router.get("/cases/{case_id}/pending-verifications")
async def get_pending_verifications(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all unverified deadlines for a case

    Returns deadlines grouped by confidence level:
    {
        "high_confidence": [...],  # Auto-approved candidates
        "medium_confidence": [...],  # Need review
        "low_confidence": [...]  # Definitely need review
    }
    """

@router.post("/deadlines/{deadline_id}/verify")
async def verify_deadline(
    deadline_id: str,
    verification: VerificationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    User verifies or rejects a deadline

    Body:
    {
        "action": "approve" | "reject" | "modify",
        "modifications": {
            "deadline_date": "2025-06-15",
            "title": "Updated Title",
            "priority": "critical"
        },
        "notes": "User notes explaining decision"
    }
    """

@router.post("/cases/{case_id}/batch-verify")
async def batch_verify_deadlines(
    case_id: str,
    batch: BatchVerificationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Approve/reject multiple deadlines at once

    Body:
    {
        "approve": ["deadline_id_1", "deadline_id_2"],
        "reject": ["deadline_id_3"],
        "modifications": {
            "deadline_id_4": {
                "deadline_date": "2025-06-20"
            }
        }
    }
    """
```

### 2.2 Frontend Verification UI

**Component: `/frontend/components/VerificationGate.tsx`**

```typescript
interface VerificationGateProps {
  caseId: string;
  onComplete: () => void;
}

export default function VerificationGate({ caseId, onComplete }: VerificationGateProps) {
  // Show pending deadlines in review interface
  // For each deadline:
  //   - Show confidence score (visual indicator)
  //   - Show source text (from PDF)
  //   - Show calculation basis
  //   - Show related rule citation
  //   - Allow approve/reject/modify
  //   - PDF viewer with highlighted text

  return (
    <div className="verification-gate">
      {/* High Confidence - Quick Approve Section */}
      <VerificationSection
        title="High Confidence (Auto-Approve Recommended)"
        deadlines={highConfidenceDeadlines}
        defaultExpanded={false}
      />

      {/* Medium Confidence - Review Needed */}
      <VerificationSection
        title="Medium Confidence (Review Recommended)"
        deadlines={mediumConfidenceDeadlines}
        defaultExpanded={true}
      />

      {/* Low Confidence - Definitely Review */}
      <VerificationSection
        title="Low Confidence (Manual Review Required)"
        deadlines={lowConfidenceDeadlines}
        defaultExpanded={true}
      />
    </div>
  );
}
```

**Component: `/frontend/components/DeadlineVerificationCard.tsx`**

```typescript
interface DeadlineVerificationCardProps {
  deadline: PendingDeadline;
  onVerify: (action: 'approve' | 'reject' | 'modify', data?: any) => void;
}

export default function DeadlineVerificationCard({ deadline, onVerify }: Props) {
  return (
    <div className="deadline-verification-card">
      {/* Header with confidence score */}
      <div className="confidence-indicator">
        <ConfidenceScore score={deadline.confidence_score} />
      </div>

      {/* Deadline Info */}
      <div className="deadline-info">
        <h4>{deadline.title}</h4>
        <p>Date: {deadline.deadline_date}</p>
        <p>Priority: {deadline.priority}</p>
      </div>

      {/* Source Attribution */}
      <div className="source-attribution">
        <p className="label">Extracted from PDF (Page {deadline.source_page}):</p>
        <blockquote className="source-text">
          {deadline.source_text}
        </blockquote>
        <button onClick={() => openPDFViewer(deadline)}>
          View in PDF
        </button>
      </div>

      {/* Calculation Basis */}
      <div className="calculation-basis">
        <p className="label">Calculation:</p>
        <p>{deadline.calculation_basis}</p>
        {deadline.rule_citation && (
          <p className="citation">{deadline.rule_citation}</p>
        )}
      </div>

      {/* Confidence Factors */}
      <ConfidenceFactors factors={deadline.confidence_factors} />

      {/* Actions */}
      <div className="actions">
        <button onClick={() => onVerify('approve')}>
          ✓ Approve
        </button>
        <button onClick={() => setShowModify(true)}>
          ✎ Modify
        </button>
        <button onClick={() => onVerify('reject')}>
          ✗ Reject
        </button>
      </div>
    </div>
  );
}
```

---

## Phase 3: Proactive Case OS Chatbot (Week 3)

### 3.1 Lifecycle Management

**Transform chatbot from reactive to proactive:**

```python
# /backend/app/services/case_os_agent.py

class CaseOSAgent:
    """
    Proactive Case Operating System

    Manages entire docketing lifecycle:
    1. Document Upload → Analysis
    2. Deadline Extraction → Verification
    3. Trigger Events → Cascade Updates
    4. Deadline Monitoring → Proactive Alerts
    5. Workflow Suggestions → User Approval
    """

    async def analyze_new_document(
        self,
        document_id: str,
        db: Session
    ) -> Dict:
        """
        Proactive analysis workflow:
        1. Extract deadlines
        2. Calculate confidence scores
        3. Generate verification gates
        4. Suggest related triggers
        5. Identify dependent deadlines
        """

        # Extract deadlines
        extractions = await self.extract_deadlines(document_id)

        # Score confidence
        scored_extractions = [
            {
                **ext,
                **self.calculate_confidence(ext)
            }
            for ext in extractions
        ]

        # Generate proactive suggestions
        suggestions = await self.generate_suggestions(scored_extractions, db)

        return {
            "extractions": scored_extractions,
            "suggestions": suggestions,
            "verification_required": any(
                ext['confidence_score'] < 90
                for ext in scored_extractions
            )
        }

    async def generate_suggestions(
        self,
        extractions: List[Dict],
        db: Session
    ) -> List[Dict]:
        """
        Proactive suggestions based on extracted deadlines

        Examples:
        - "I found a trial date. Should I create the pretrial deadline cascade?"
        - "This is a motion. Should I calculate the response deadline?"
        - "I see a hearing date. Want me to set reminders?"
        """
        suggestions = []

        for ext in extractions:
            # Check if this is a trigger event
            if self.is_trigger_event(ext):
                suggestions.append({
                    "type": "create_cascade",
                    "message": f"I found a {ext['title']}. Should I create the deadline cascade?",
                    "action": "create_dependent_deadlines",
                    "data": ext
                })

            # Check if related deadlines exist
            related = await self.find_related_deadlines(ext, db)
            if related:
                suggestions.append({
                    "type": "link_deadlines",
                    "message": f"This deadline might be related to {related[0]['title']}. Link them?",
                    "action": "link_deadlines",
                    "data": {"source": ext, "targets": related}
                })

        return suggestions
```

### 3.2 Enhanced Chat Interface

**Component: `/frontend/components/ProactiveChatbot.tsx`**

```typescript
interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
  suggestions?: Suggestion[];
  verifications?: PendingVerification[];
}

interface Suggestion {
  id: string;
  type: 'create_cascade' | 'link_deadlines' | 'set_reminder';
  message: string;
  action: string;
  data: any;
}

export default function ProactiveChatbot({ caseId }: { caseId: string }) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);

  // Proactive message on document upload
  useEffect(() => {
    // When document analysis completes
    socket.on('analysis_complete', (data) => {
      if (data.suggestions.length > 0) {
        addMessage({
          role: 'assistant',
          content: "I've analyzed the document. Here's what I found:",
          suggestions: data.suggestions
        });
      }

      if (data.verification_required) {
        addMessage({
          role: 'assistant',
          content: "Some deadlines need your review:",
          verifications: data.pending_verifications
        });
      }
    });
  }, []);

  return (
    <div className="proactive-chatbot">
      {/* Message List */}
      {messages.map((msg, idx) => (
        <ChatMessage key={idx} message={msg}>
          {/* Render suggestions as action buttons */}
          {msg.suggestions?.map(suggestion => (
            <SuggestionCard
              key={suggestion.id}
              suggestion={suggestion}
              onAccept={() => handleAcceptSuggestion(suggestion)}
              onReject={() => handleRejectSuggestion(suggestion)}
            />
          ))}

          {/* Render verification gates inline */}
          {msg.verifications?.map(verification => (
            <InlineVerificationCard
              key={verification.id}
              verification={verification}
              onVerify={(action) => handleVerify(verification.id, action)}
            />
          ))}
        </ChatMessage>
      ))}

      {/* Input */}
      <ChatInput onSend={handleSendMessage} />
    </div>
  );
}
```

### 3.3 Proactive Monitoring

```python
# /backend/app/services/proactive_monitor.py

class ProactiveMonitor:
    """
    Background service that proactively monitors cases
    """

    async def check_for_proactive_actions(self, db: Session):
        """
        Run periodically (e.g., daily) to check:
        1. Upcoming deadlines → Send reminders
        2. Completed tasks → Suggest next steps
        3. Missing information → Request clarification
        4. Rule changes → Alert affected deadlines
        """

        # Check upcoming deadlines (7 days, 3 days, 1 day)
        upcoming = await self.get_upcoming_deadlines(db, days=7)
        for deadline in upcoming:
            await self.send_proactive_reminder(deadline)

        # Check for completed milestones
        completed = await self.get_recently_completed_deadlines(db)
        for deadline in completed:
            next_steps = await self.suggest_next_steps(deadline, db)
            await self.send_next_step_suggestions(deadline, next_steps)
```

---

## Implementation Roadmap

### Week 1: Harden Rules Engine
- [ ] Day 1-2: Enhance court day calculations with jurisdiction-specific holidays
- [ ] Day 3: Implement local rule overrides
- [ ] Day 4: Add comprehensive service method logic
- [ ] Day 5: Implement confidence scoring system
- [ ] Day 6: Add source attribution to database
- [ ] Day 7: Test all enhanced calculations

### Week 2: Verification Gates
- [ ] Day 8-9: Build backend verification APIs
- [ ] Day 10-11: Create frontend verification UI components
- [ ] Day 12: Integrate PDF viewer with text highlighting
- [ ] Day 13: Add batch verification
- [ ] Day 14: End-to-end verification testing

### Week 3: Proactive Case OS
- [ ] Day 15-16: Build Case OS Agent with lifecycle management
- [ ] Day 17: Implement proactive suggestions system
- [ ] Day 18-19: Enhance chatbot with proactive features
- [ ] Day 20: Add background monitoring service
- [ ] Day 21: Full integration testing

---

## Success Metrics

### Rules Engine Quality
- ✅ 100% accuracy on court day calculations
- ✅ All jurisdictional holidays accounted for
- ✅ Service method extensions applied correctly
- ✅ Local rules properly overridden

### Verification System
- ✅ Confidence scores correlate with actual accuracy (>90%)
- ✅ High-confidence extractions: <5% error rate
- ✅ Medium-confidence extractions: <15% error rate
- ✅ Low-confidence extractions: Human review required
- ✅ Source attribution: 100% of extractions linked to PDF text

### Proactive Case OS
- ✅ Proactive suggestions accepted >70% of time
- ✅ Verification gates reduce attorney review time by 50%
- ✅ Deadline cascades created automatically with user approval
- ✅ Zero missed deadlines due to calculation errors

---

## Technical Architecture

### Database Schema Updates

```sql
-- Confidence and Verification
ALTER TABLE deadlines ADD COLUMN source_page INTEGER;
ALTER TABLE deadlines ADD COLUMN source_text TEXT;
ALTER TABLE deadlines ADD COLUMN source_coordinates JSONB;
ALTER TABLE deadlines ADD COLUMN confidence_score INTEGER;
ALTER TABLE deadlines ADD COLUMN confidence_level VARCHAR(20);
ALTER TABLE deadlines ADD COLUMN confidence_factors JSONB;
ALTER TABLE deadlines ADD COLUMN verification_status VARCHAR(20) DEFAULT 'pending';
ALTER TABLE deadlines ADD COLUMN verified_by VARCHAR;
ALTER TABLE deadlines ADD COLUMN verified_at TIMESTAMP;
ALTER TABLE deadlines ADD COLUMN verification_notes TEXT;

-- Jurisdiction-specific fields
ALTER TABLE cases ADD COLUMN local_rules JSONB;
ALTER TABLE cases ADD COLUMN court_type VARCHAR(50); -- circuit, district, appellate
ALTER TABLE cases ADD COLUMN division VARCHAR(50); -- specific division/branch

-- Proactive suggestions tracking
CREATE TABLE proactive_suggestions (
    id UUID PRIMARY KEY,
    case_id UUID REFERENCES cases(id),
    suggestion_type VARCHAR(50),
    message TEXT,
    action VARCHAR(50),
    data JSONB,
    status VARCHAR(20), -- pending, accepted, rejected
    created_at TIMESTAMP DEFAULT NOW(),
    resolved_at TIMESTAMP,
    resolved_by VARCHAR
);
```

---

## User Experience Flow

### New Document Upload Workflow

```
1. User uploads PDF
   ↓
2. System analyzes document
   ↓
3. Chatbot: "I've analyzed the motion. I found 3 deadlines."
   ↓
4. Show verification gate:
   ┌─────────────────────────────────────────┐
   │ High Confidence (Auto-Approve?)         │
   │ ✓ Response Due: 2025-06-24 (20 days)   │
   │   Source: Page 3, "Defendant shall..."  │
   │   Confidence: 95% ✓                      │
   │   [Approve] [Review] [Reject]           │
   └─────────────────────────────────────────┘
   ↓
5. Chatbot: "This looks like a motion. Should I create the hearing deadline too?"
   [Yes] [No, just the response]
   ↓
6. User approves → Deadlines committed to database
   ↓
7. Chatbot: "All set! I'll remind you 7 days before the deadline."
```

---

## Next Steps

1. **Review existing Phase 3 code** - Ensure court days work correctly
2. **Implement confidence scoring** - Add to extraction pipeline
3. **Build verification API** - Backend endpoints for review workflow
4. **Create verification UI** - Frontend components
5. **Enhance chatbot** - Add proactive features
6. **Test end-to-end** - Document upload → Verification → Approval

This transforms DocketAssist from a passive analyzer into an active Case Operating System that partners with attorneys to manage their docket with legal precision and human oversight.
