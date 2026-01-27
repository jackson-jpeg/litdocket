# Rules Engine Redesign: Database-Driven Jurisdiction System

**Status**: Design Document
**Last Updated**: 2026-01-24
**Priority**: CRITICAL - Core Business Logic
**Complexity**: HIGH

---

## Executive Summary

The current rules engine is **hardcoded in Python**, limiting LitDocket to ~5 jurisdictions and requiring developer involvement for every new jurisdiction. This redesign transforms it into a **database-driven, visual, no-code system** that enables:

- ✅ **Unlimited Jurisdictions** - Users create custom rules via visual builder
- ✅ **Zero Code Deploys** - Rules stored as JSON in database
- ✅ **Rule Marketplace** - Share jurisdictions with other firms
- ✅ **Version Control** - Rollback to previous rule versions
- ✅ **Legal Defensibility** - Complete audit trail of rule changes
- ✅ **Testing Framework** - Validate rules before activation

---

## Current Architecture Problems

### 1. **Hardcoded Rules** (`rules_engine.py`)
```python
# Current approach - NOT SCALABLE
def get_florida_civil_trial_date_rules():
    return [
        {"name": "Expert Witness List", "days": -90, "priority": "CRITICAL"},
        {"name": "Pretrial Motions", "days": -30, "priority": "CRITICAL"},
        # ... 45+ more hardcoded rules
    ]
```

**Problems:**
- ❌ Adding a jurisdiction requires code changes
- ❌ No version control for rule changes
- ❌ Can't test rule variations
- ❌ No user-facing rule editor
- ❌ Difficult to maintain consistency
- ❌ No audit trail

### 2. **Limited Trigger Support**
Current triggers:
- `TRIAL_DATE`
- `COMPLAINT_SERVED`
- `DISCOVERY_COMMENCED`
- A few others

**Missing:**
- Event-based triggers (document filed, motion granted)
- Compound triggers (multiple conditions)
- Recurring triggers (every 30 days)
- Alert triggers (deadline approaching)

### 3. **No Visual Interface**
Users cannot:
- See rule structure visually
- Edit rules without developer
- Test rules with sample data
- Share rules with colleagues

---

## New Architecture: Database-Driven Rules System

### Core Principles

1. **Rules as Data, Not Code** - JSON schemas in database
2. **Deterministic Execution** - Same input always produces same output
3. **Immutable History** - Never delete, only version
4. **User-Friendly** - Visual builder for non-technical users
5. **Enterprise-Grade** - Audit trails, testing, validation

---

## Database Schema

### 1. **rule_templates** - Master Rule Definitions

```sql
CREATE TABLE rule_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Metadata
    rule_name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL,  -- "florida-civil-trial-date"
    jurisdiction VARCHAR(100) NOT NULL,  -- "florida_civil"
    trigger_type VARCHAR(100) NOT NULL,  -- "TRIAL_DATE"

    -- Ownership
    created_by UUID REFERENCES users(id),
    is_public BOOLEAN DEFAULT false,  -- Shareable in marketplace
    is_official BOOLEAN DEFAULT false,  -- Verified by LitDocket

    -- Versioning
    current_version_id UUID REFERENCES rule_versions(id),
    version_count INTEGER DEFAULT 1,

    -- Status
    status VARCHAR(50) DEFAULT 'draft',  -- draft, active, deprecated, archived

    -- Usage tracking
    usage_count INTEGER DEFAULT 0,  -- How many times this rule has been executed
    user_count INTEGER DEFAULT 0,   -- How many users have used this rule

    -- Metadata
    description TEXT,
    tags TEXT[],  -- ["florida", "civil", "trial"]

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    published_at TIMESTAMP,
    deprecated_at TIMESTAMP,

    -- Indexes
    INDEX idx_jurisdiction (jurisdiction),
    INDEX idx_trigger_type (trigger_type),
    INDEX idx_status (status),
    INDEX idx_public (is_public),
    UNIQUE INDEX idx_slug (slug)
);
```

### 2. **rule_versions** - Version History

```sql
CREATE TABLE rule_versions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rule_template_id UUID REFERENCES rule_templates(id) ON DELETE CASCADE,

    -- Version info
    version_number INTEGER NOT NULL,
    version_name VARCHAR(255),  -- "2025 Update", "Post-Reform Changes"

    -- The actual rule definition (JSON)
    rule_schema JSONB NOT NULL,

    -- Change tracking
    created_by UUID REFERENCES users(id),
    change_summary TEXT,  -- "Added service method extensions"

    -- Validation
    is_validated BOOLEAN DEFAULT false,
    validation_errors JSONB,  -- Array of validation issues

    -- Testing
    test_cases_passed INTEGER DEFAULT 0,
    test_cases_failed INTEGER DEFAULT 0,

    -- Status
    status VARCHAR(50) DEFAULT 'draft',  -- draft, active, deprecated

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    activated_at TIMESTAMP,
    deprecated_at TIMESTAMP,

    -- Ensure version uniqueness per template
    UNIQUE (rule_template_id, version_number)
);
```

### 3. **rule_conditions** - If-Then Logic

```sql
CREATE TABLE rule_conditions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rule_version_id UUID REFERENCES rule_versions(id) ON DELETE CASCADE,
    deadline_id VARCHAR(100) NOT NULL,  -- Which deadline this condition affects

    -- Condition definition (JSON)
    condition_schema JSONB NOT NULL,
    -- Example: {"if": {"case_type": "personal_injury"}, "then": {"offset_days": -120}}

    -- Priority (conditions evaluated in order)
    priority INTEGER DEFAULT 0,

    created_at TIMESTAMP DEFAULT NOW()
);
```

### 4. **rule_executions** - Audit Trail

```sql
CREATE TABLE rule_executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- What was executed
    rule_template_id UUID REFERENCES rule_templates(id),
    rule_version_id UUID REFERENCES rule_versions(id),

    -- Where it was executed
    case_id UUID REFERENCES cases(id),
    trigger_deadline_id UUID REFERENCES deadlines(id),

    -- Who executed it
    user_id UUID REFERENCES users(id),

    -- Input data
    trigger_data JSONB,  -- {"trial_date": "2026-03-01", "trial_type": "jury"}

    -- Output results
    deadlines_created INTEGER,
    deadline_ids UUID[],

    -- Performance
    execution_time_ms INTEGER,

    -- Status
    status VARCHAR(50),  -- success, failed, partial
    error_message TEXT,

    -- Timestamps
    executed_at TIMESTAMP DEFAULT NOW(),

    -- Indexes
    INDEX idx_case (case_id),
    INDEX idx_user (user_id),
    INDEX idx_executed_at (executed_at)
);
```

### 5. **rule_test_cases** - Validation Framework

```sql
CREATE TABLE rule_test_cases (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rule_template_id UUID REFERENCES rule_templates(id) ON DELETE CASCADE,

    -- Test case definition
    test_name VARCHAR(255) NOT NULL,
    test_description TEXT,

    -- Input data
    input_data JSONB NOT NULL,
    -- Example: {"trial_date": "2026-06-01", "case_type": "civil"}

    -- Expected output
    expected_deadlines JSONB NOT NULL,
    -- Array of expected deadline objects with dates, priorities, etc.

    -- Validation rules
    validation_rules JSONB,
    -- {"min_deadlines": 10, "max_deadlines": 60, "require_citations": true}

    -- Test results
    last_run_at TIMESTAMP,
    last_run_status VARCHAR(50),  -- passed, failed
    last_run_errors JSONB,

    created_at TIMESTAMP DEFAULT NOW()
);
```

### 6. **rule_dependencies** - Deadline Relationships

```sql
CREATE TABLE rule_dependencies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rule_version_id UUID REFERENCES rule_versions(id) ON DELETE CASCADE,

    -- Dependency relationship
    deadline_id VARCHAR(100) NOT NULL,
    depends_on_deadline_id VARCHAR(100) NOT NULL,

    -- Dependency type
    dependency_type VARCHAR(50),  -- must_come_after, must_come_before, same_day

    -- Offset if sequential
    offset_days INTEGER,

    created_at TIMESTAMP DEFAULT NOW(),

    -- Prevent circular dependencies
    CHECK (deadline_id != depends_on_deadline_id)
);
```

### 7. **rule_marketplace_shares** - Rule Sharing

```sql
CREATE TABLE rule_marketplace_shares (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rule_template_id UUID REFERENCES rule_templates(id) ON DELETE CASCADE,

    -- Who shared it
    shared_by UUID REFERENCES users(id),

    -- Access control
    is_public BOOLEAN DEFAULT false,
    allowed_users UUID[],  -- Specific users who can access
    allowed_firms VARCHAR[],  -- Firms that can access

    -- Stats
    view_count INTEGER DEFAULT 0,
    install_count INTEGER DEFAULT 0,
    rating_avg DECIMAL(3,2),
    rating_count INTEGER DEFAULT 0,

    -- Timestamps
    shared_at TIMESTAMP DEFAULT NOW()
);
```

---

## JSON Rule Schema

### Complete Rule Definition Example

```json
{
  "metadata": {
    "name": "Florida Civil - Trial Date Chain",
    "description": "Generates all pre-trial deadlines for Florida civil cases",
    "jurisdiction": "florida_civil",
    "effective_date": "2025-01-01",
    "sunset_date": null,
    "citations": [
      "Florida Rules of Civil Procedure",
      "FRCP 16(b)",
      "FL R. Civ. P. 1.440"
    ],
    "author": "LitDocket Official",
    "tags": ["florida", "civil", "trial", "pre-trial"],
    "complexity": "advanced"
  },

  "trigger": {
    "type": "TRIAL_DATE",
    "label": "Trial Date Set",
    "description": "When a trial date is scheduled by the court",

    "required_fields": [
      {
        "field": "trial_date",
        "type": "date",
        "label": "Trial Date",
        "validation": {
          "required": true,
          "must_be_future": true,
          "min_days_ahead": 30
        },
        "help_text": "The date the trial is scheduled to begin"
      },
      {
        "field": "trial_type",
        "type": "select",
        "label": "Trial Type",
        "options": [
          {"value": "jury", "label": "Jury Trial"},
          {"value": "bench", "label": "Bench Trial"},
          {"value": "arbitration", "label": "Arbitration"}
        ],
        "default": "jury",
        "help_text": "Type of trial or hearing"
      },
      {
        "field": "case_type",
        "type": "select",
        "label": "Case Type",
        "options": [
          {"value": "personal_injury", "label": "Personal Injury"},
          {"value": "contract", "label": "Contract Dispute"},
          {"value": "property", "label": "Property Dispute"},
          {"value": "other", "label": "Other Civil"}
        ],
        "required": false
      },
      {
        "field": "service_method",
        "type": "select",
        "label": "Service Method",
        "options": [
          {"value": "personal", "label": "Personal Service"},
          {"value": "mail", "label": "Mail"},
          {"value": "email", "label": "Email"}
        ],
        "default": "personal"
      }
    ],

    "clarification_questions": [
      {
        "question": "Is this a complex case requiring expert testimony?",
        "field": "requires_experts",
        "type": "yes_no",
        "affects_deadlines": ["expert_witness_list", "expert_disclosures"]
      },
      {
        "question": "Will you be filing any pretrial motions?",
        "field": "pretrial_motions_planned",
        "type": "yes_no",
        "affects_deadlines": ["pretrial_motions_deadline"]
      }
    ]
  },

  "deadlines": [
    {
      "id": "expert_witness_list",
      "name": "Expert Witness List",
      "description": "Deadline to disclose expert witnesses",

      "offset_days": -90,
      "offset_type": "calendar_days",
      "offset_from": "trigger",  // or another deadline_id

      "priority": "CRITICAL",
      "category": "discovery",

      "rule_citation": "FL R. Civ. P. 1.280(b)(5)(A)",
      "calculation_basis": "90 days before trial per FL R. Civ. P. 1.280(b)(5)(A)",

      "service_method_extension": false,

      "conditions": [
        {
          "if": {"case_type": "personal_injury"},
          "then": {"offset_days": -120},
          "reason": "Personal injury cases require earlier expert disclosure"
        },
        {
          "if": {"requires_experts": false},
          "then": {"skip": true},
          "reason": "No expert testimony planned"
        }
      ],

      "dependencies": [],  // No dependencies

      "attributes": {
        "is_court_ordered": false,
        "is_moveable": true,
        "requires_court_approval": false,
        "allows_extensions": true
      },

      "action_required": "File and serve expert witness list",
      "party_responsible": "plaintiff",

      "resources": [
        {
          "type": "template",
          "name": "Expert Witness List Template",
          "url": "/templates/expert-witness-list.docx"
        },
        {
          "type": "guide",
          "name": "Expert Disclosure Guide",
          "url": "/guides/expert-disclosure"
        }
      ]
    },

    {
      "id": "pretrial_motions",
      "name": "Pretrial Motions Deadline",
      "description": "Last day to file pretrial motions",

      "offset_days": -30,
      "offset_type": "court_days",
      "offset_from": "trigger",

      "priority": "CRITICAL",
      "category": "motions",

      "rule_citation": "FL R. Civ. P. 1.440(a)",
      "calculation_basis": "30 court days before trial per FL R. Civ. P. 1.440(a)",

      "service_method_extension": true,

      "conditions": [],

      "dependencies": ["expert_witness_list"],  // Must come after expert list

      "attributes": {
        "is_court_ordered": true,
        "is_moveable": false,
        "requires_court_approval": true
      },

      "action_required": "File any pretrial motions (motions in limine, etc.)",
      "party_responsible": "both"
    },

    {
      "id": "witness_list",
      "name": "Witness List Due",
      "description": "Deadline to file witness list",

      "offset_days": -21,
      "offset_type": "calendar_days",
      "offset_from": "trigger",

      "priority": "CRITICAL",
      "category": "pre-trial",

      "rule_citation": "FL R. Civ. P. 1.200",
      "service_method_extension": false,

      "dependencies": ["expert_witness_list"]
    },

    {
      "id": "motions_in_limine",
      "name": "Motions in Limine Deadline",
      "description": "Deadline to file motions in limine",

      "offset_days": -14,
      "offset_type": "calendar_days",
      "offset_from": "trigger",

      "priority": "IMPORTANT",
      "category": "motions",

      "rule_citation": "Local Rules",
      "dependencies": ["pretrial_motions"]
    },

    {
      "id": "pretrial_statement",
      "name": "Final Pretrial Statement",
      "description": "Joint pretrial statement due",

      "offset_days": -7,
      "offset_type": "court_days",
      "offset_from": "trigger",

      "priority": "CRITICAL",
      "category": "pre-trial",

      "rule_citation": "FL R. Civ. P. 1.200(d)",
      "dependencies": ["witness_list", "motions_in_limine"]
    }

    // ... 40+ more deadlines
  ],

  "validation": {
    "min_deadlines_generated": 10,
    "max_deadlines_generated": 60,
    "require_citations": true,
    "require_unique_names": true,
    "check_circular_dependencies": true
  },

  "settings": {
    "auto_recalculate_dependents": true,
    "warn_before_cascade_update": true,
    "allow_manual_overrides": true,
    "generate_checklist": true
  }
}
```

---

## Dynamic Rules Execution Engine

### Architecture

```python
# backend/app/services/dynamic_rules_engine.py

class DynamicRulesEngine:
    """
    Executes database-stored rules dynamically

    Features:
    - Loads rules from database (not hardcoded)
    - Evaluates conditions dynamically
    - Handles dependencies and ordering
    - Validates against test cases
    - Provides dry-run mode
    - Complete audit trail
    """

    def __init__(self, db: Session):
        self.db = db
        self.calculator = AuthoritativeDeadlineCalculator()

    async def execute_rule(
        self,
        rule_template_id: str,
        trigger_data: dict,
        case_id: str,
        user_id: str,
        dry_run: bool = False
    ) -> RuleExecutionResult:
        """
        Execute a rule and generate deadlines

        Args:
            rule_template_id: UUID of rule template
            trigger_data: Input data (trial_date, case_type, etc.)
            case_id: Case to attach deadlines to
            user_id: User executing the rule
            dry_run: If True, don't save to database (preview mode)

        Returns:
            RuleExecutionResult with generated deadlines and stats
        """

        start_time = time.time()

        # 1. Load rule from database
        rule_template = self.db.query(RuleTemplate).filter(
            RuleTemplate.id == rule_template_id,
            RuleTemplate.status == 'active'
        ).first()

        if not rule_template:
            raise RuleNotFoundException()

        # 2. Get current version
        rule_version = self.db.query(RuleVersion).filter(
            RuleVersion.id == rule_template.current_version_id
        ).first()

        rule_schema = rule_version.rule_schema

        # 3. Validate input data
        validation_result = self._validate_trigger_data(
            rule_schema['trigger']['required_fields'],
            trigger_data
        )

        if not validation_result.is_valid:
            raise InvalidTriggerDataException(validation_result.errors)

        # 4. Generate deadlines
        deadlines = []

        for deadline_template in rule_schema['deadlines']:
            # Evaluate conditions
            should_create = self._evaluate_conditions(
                deadline_template.get('conditions', []),
                trigger_data
            )

            if not should_create:
                continue

            # Calculate deadline date
            deadline_date = self._calculate_deadline_date(
                deadline_template,
                trigger_data,
                deadlines  # For dependency resolution
            )

            # Create deadline object
            deadline = Deadline(
                case_id=case_id,
                user_id=user_id,
                title=deadline_template['name'],
                description=deadline_template.get('description'),
                deadline_date=deadline_date,
                priority=deadline_template['priority'],
                category=deadline_template.get('category'),
                rule_citation=deadline_template.get('rule_citation'),
                calculation_basis=deadline_template.get('calculation_basis'),
                action_required=deadline_template.get('action_required'),
                is_calculated=True,
                is_dependent=True,
                trigger_event=rule_schema['trigger']['type']
            )

            deadlines.append(deadline)

        # 5. Validate dependency order
        self._validate_dependencies(deadlines, rule_schema)

        # 6. Save to database (unless dry-run)
        if not dry_run:
            for deadline in deadlines:
                self.db.add(deadline)

            # Create execution audit record
            execution = RuleExecution(
                rule_template_id=rule_template_id,
                rule_version_id=rule_version.id,
                case_id=case_id,
                user_id=user_id,
                trigger_data=trigger_data,
                deadlines_created=len(deadlines),
                deadline_ids=[str(d.id) for d in deadlines],
                execution_time_ms=int((time.time() - start_time) * 1000),
                status='success'
            )
            self.db.add(execution)

            self.db.commit()

        # 7. Return result
        return RuleExecutionResult(
            success=True,
            deadlines_created=len(deadlines),
            deadlines=deadlines,
            execution_time_ms=int((time.time() - start_time) * 1000),
            rule_name=rule_schema['metadata']['name'],
            rule_version=rule_version.version_number
        )

    def _evaluate_conditions(
        self,
        conditions: list,
        trigger_data: dict
    ) -> bool:
        """
        Evaluate if-then conditions

        Returns True if deadline should be created
        """

        for condition in conditions:
            if_clause = condition.get('if', {})
            then_clause = condition.get('then', {})

            # Check if condition matches
            condition_met = all(
                trigger_data.get(key) == value
                for key, value in if_clause.items()
            )

            if condition_met:
                # Apply the "then" clause
                if then_clause.get('skip'):
                    return False  # Don't create this deadline

                # Could modify offset_days, priority, etc.
                # (handled in calculation step)

        return True  # Create deadline by default

    def _calculate_deadline_date(
        self,
        deadline_template: dict,
        trigger_data: dict,
        existing_deadlines: list
    ) -> date:
        """
        Calculate the deadline date with all business logic

        Handles:
        - Offset calculations
        - Service method extensions
        - Condition-based adjustments
        - Dependency-based offsets
        """

        # Get base offset
        offset_days = deadline_template['offset_days']
        offset_type = deadline_template.get('offset_type', 'calendar_days')

        # Apply condition-based adjustments
        for condition in deadline_template.get('conditions', []):
            if self._condition_matches(condition['if'], trigger_data):
                if 'offset_days' in condition['then']:
                    offset_days = condition['then']['offset_days']

        # Determine offset_from
        offset_from = deadline_template.get('offset_from', 'trigger')

        if offset_from == 'trigger':
            base_date = trigger_data.get('trial_date')  # Or other trigger field
        else:
            # Offset from another deadline (dependency)
            base_deadline = next(
                (d for d in existing_deadlines if d.id == offset_from),
                None
            )
            base_date = base_deadline.deadline_date if base_deadline else None

        if not base_date:
            raise ValueError(f"Cannot determine base date for deadline")

        # Calculate with service method extensions
        service_method = trigger_data.get('service_method', 'personal')
        add_service_extension = deadline_template.get('service_method_extension', False)

        result = self.calculator.calculate_deadline(
            trigger_date=base_date,
            days_to_add=offset_days,
            calculation_type=offset_type,
            service_method=service_method if add_service_extension else None
        )

        return result.deadline_date
```

---

## Visual Rule Builder UI

### Component Architecture

```typescript
// frontend/components/rules/RuleBuilder.tsx

interface RuleBuilderProps {
  ruleTemplateId?: string;  // For editing existing rule
  onSave: (rule: RuleTemplate) => void;
}

export function RuleBuilder({ ruleTemplateId, onSave }: RuleBuilderProps) {
  const [rule, setRule] = useState<RuleSchema>(DEFAULT_RULE);
  const [activeTab, setActiveTab] = useState<'metadata' | 'trigger' | 'deadlines' | 'conditions' | 'test'>('metadata');

  return (
    <div className="rule-builder">
      {/* Tab Navigation */}
      <TabNav activeTab={activeTab} onChange={setActiveTab} />

      {/* Metadata Tab */}
      {activeTab === 'metadata' && (
        <MetadataEditor
          metadata={rule.metadata}
          onChange={(metadata) => setRule({...rule, metadata})}
        />
      )}

      {/* Trigger Tab */}
      {activeTab === 'trigger' && (
        <TriggerEditor
          trigger={rule.trigger}
          onChange={(trigger) => setRule({...rule, trigger})}
        />
      )}

      {/* Deadlines Tab - Main Timeline Builder */}
      {activeTab === 'deadlines' && (
        <DeadlineTimelineBuilder
          deadlines={rule.deadlines}
          trigger={rule.trigger}
          onChange={(deadlines) => setRule({...rule, deadlines})}
        />
      )}

      {/* Conditions Tab */}
      {activeTab === 'conditions' && (
        <ConditionBuilder
          deadlines={rule.deadlines}
          onChange={(deadlines) => setRule({...rule, deadlines})}
        />
      )}

      {/* Test Tab */}
      {activeTab === 'test' && (
        <RuleTester
          rule={rule}
          onTest={(testCase) => runTest(rule, testCase)}
        />
      )}

      {/* Actions */}
      <RuleBuilderActions
        rule={rule}
        onSave={onSave}
        onTest={() => setActiveTab('test')}
        onPreview={() => showPreview(rule)}
      />
    </div>
  );
}
```

### Timeline Builder Component

```typescript
// frontend/components/rules/DeadlineTimelineBuilder.tsx

export function DeadlineTimelineBuilder({ deadlines, trigger, onChange }: Props) {
  const [selectedDeadline, setSelectedDeadline] = useState<string | null>(null);

  // Visual timeline from -180 days to trial date
  const timelineRange = [-180, 0];  // 6 months before trial

  return (
    <div className="timeline-builder">
      {/* Timeline Visualization */}
      <div className="timeline-container">
        <svg className="timeline-svg" width="100%" height="600">
          {/* Trigger Date (vertical line at 0) */}
          <line
            x1="50%"
            y1="0"
            x2="50%"
            y2="600"
            stroke="#3b82f6"
            strokeWidth="3"
          />
          <text x="50%" y="20" textAnchor="middle" className="font-bold">
            {trigger.label} (Day 0)
          </text>

          {/* Deadline Markers */}
          {deadlines.map((deadline, i) => {
            const xPos = calculateXPosition(deadline.offset_days, timelineRange);
            const yPos = 100 + (i * 40);

            return (
              <g key={deadline.id}>
                {/* Deadline Dot */}
                <circle
                  cx={xPos}
                  cy={yPos}
                  r="8"
                  fill={getPriorityColor(deadline.priority)}
                  className="cursor-pointer hover:scale-110"
                  onClick={() => setSelectedDeadline(deadline.id)}
                />

                {/* Deadline Label */}
                <text
                  x={xPos + 15}
                  y={yPos + 5}
                  className="text-sm"
                >
                  {deadline.name} ({deadline.offset_days} days)
                </text>

                {/* Dependency Lines */}
                {deadline.dependencies?.map(depId => {
                  const depDeadline = deadlines.find(d => d.id === depId);
                  if (!depDeadline) return null;

                  const depX = calculateXPosition(depDeadline.offset_days, timelineRange);
                  const depY = 100 + (deadlines.indexOf(depDeadline) * 40);

                  return (
                    <line
                      key={`${deadline.id}-${depId}`}
                      x1={depX}
                      y1={depY}
                      x2={xPos}
                      y2={yPos}
                      stroke="#94a3b8"
                      strokeWidth="2"
                      strokeDasharray="5,5"
                    />
                  );
                })}
              </g>
            );
          })}
        </svg>
      </div>

      {/* Deadline Editor Panel */}
      {selectedDeadline && (
        <DeadlineEditorPanel
          deadline={deadlines.find(d => d.id === selectedDeadline)!}
          allDeadlines={deadlines}
          onChange={(updated) => {
            const newDeadlines = deadlines.map(d =>
              d.id === selectedDeadline ? updated : d
            );
            onChange(newDeadlines);
          }}
          onClose={() => setSelectedDeadline(null)}
        />
      )}

      {/* Add Deadline Button */}
      <button
        onClick={() => {
          const newDeadline = createDefaultDeadline();
          onChange([...deadlines, newDeadline]);
          setSelectedDeadline(newDeadline.id);
        }}
        className="btn-primary"
      >
        + Add Deadline
      </button>
    </div>
  );
}
```

---

## Implementation Roadmap

### Phase 1: Database Schema (Week 1-2)
- ✅ Create migration files
- ✅ Implement models
- ✅ Add indexes and constraints
- ✅ Seed with existing hardcoded rules

### Phase 2: Dynamic Execution Engine (Week 3-4)
- ✅ Build DynamicRulesEngine
- ✅ Implement condition evaluation
- ✅ Add dependency resolution
- ✅ Create dry-run mode
- ✅ Add audit logging

### Phase 3: API Endpoints (Week 5)
- ✅ CRUD operations for rule templates
- ✅ Version management endpoints
- ✅ Test case execution
- ✅ Rule marketplace API

### Phase 4: Visual Builder (Week 6-8)
- ✅ Timeline visualization
- ✅ Drag-and-drop deadline placement
- ✅ Condition builder UI
- ✅ Test runner interface

### Phase 5: Testing & Migration (Week 9-10)
- ✅ Convert existing hardcoded rules to JSON
- ✅ Validate against test cases
- ✅ Performance testing
- ✅ User acceptance testing

### Phase 6: Marketplace (Week 11-12)
- ✅ Rule sharing system
- ✅ Search and discovery
- ✅ Rating and reviews
- ✅ Import/export functionality

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| **Jurisdictions Supported** | 5 (hardcoded) | Unlimited (user-created) |
| **Time to Add Jurisdiction** | 2-3 days (developer) | 30 minutes (user) |
| **Rule Changes Audit Trail** | None | 100% tracked |
| **User-Created Rules** | 0 | 100+ in first quarter |
| **Rule Marketplace Listings** | 0 | 50+ in first year |

---

## Next Steps

1. **Review this design** with legal team for accuracy
2. **Get user feedback** on visual builder mockups
3. **Start implementation** with database schema
4. **Migrate existing rules** to new system
5. **Beta test** with power users

---

**This architecture transforms LitDocket from a hardcoded tool into a platform that scales infinitely with user-generated content.**
