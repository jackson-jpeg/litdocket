# Frontend Inbox Workflow - Implementation Guide

## Overview
Phase 3 Task 8 requires building the inbox approval workflow UX. The backend API is complete; frontend implementation remains.

## Backend API Status: ✅ COMPLETE

All endpoints are functional:

```typescript
// List inbox items
GET /api/v1/inbox?type=RULE_VERIFICATION&status=PENDING

// Get single item
GET /api/v1/inbox/{item_id}

// Review item (approve/reject)
POST /api/v1/inbox/{item_id}/review
{
  resolution: "approved" | "rejected" | "deferred",
  notes?: string
}

// Bulk review
POST /api/v1/inbox/bulk-review
{
  item_ids: string[],
  resolution: string,
  notes?: string
}

// Pending summary
GET /api/v1/inbox/pending/summary
```

## Required Frontend Components

### 1. Page: `/frontend/app/(protected)/inbox/page.tsx`

**Purpose:** Unified inbox view with tabs for different item types

**Features:**
- Tab navigation: All | Jurisdictions | Rules | Changes | Failures
- Filter by status: Pending | Reviewed | Deferred
- Pagination (50 items per page)
- Bulk selection with checkbox
- Quick actions: Approve All, Reject All
- Search/filter by jurisdiction

**Layout:**
```tsx
<InboxPage>
  <InboxHeader>
    <Title>Inbox ({pendingCount})</Title>
    <BulkActions />
  </InboxHeader>

  <Tabs>
    <Tab value="all">All ({totalCount})</Tab>
    <Tab value="rules">Rule Verifications ({ruleCount})</Tab>
    <Tab value="changes">Watchtower Changes ({changeCount})</Tab>
    <Tab value="failures">Scraper Failures ({failureCount})</Tab>
  </Tabs>

  <InboxList>
    {items.map(item => (
      <InboxItemCard key={item.id} item={item} />
    ))}
  </InboxList>

  <Pagination />
</InboxPage>
```

**State Management:**
```typescript
const [items, setItems] = useState<InboxItem[]>([]);
const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
const [filter, setFilter] = useState({ type: null, status: 'PENDING' });
const [page, setPage] = useState({ limit: 50, offset: 0 });
```

### 2. Component: `/frontend/components/inbox/InboxItemCard.tsx`

**Purpose:** Display individual inbox item with metadata

**Props:**
```typescript
interface InboxItemCardProps {
  item: InboxItem;
  selected?: boolean;
  onSelect?: (id: string) => void;
  onReview?: (id: string, resolution: string) => void;
}
```

**Features:**
- Type badge (RULE_VERIFICATION, WATCHTOWER_CHANGE, etc.)
- Confidence badge (for rules)
- Priority indicator (high/medium/low)
- Timestamp
- Expandable details section
- Quick approve/reject buttons

**Layout:**
```tsx
<Card className="border-ink">
  <CardHeader>
    <Checkbox checked={selected} onChange={onSelect} />
    <TypeBadge type={item.type} />
    <PriorityIndicator priority={item.metadata.priority} />
    <h3>{item.title}</h3>
    <ConfidenceBadge score={item.metadata.confidence} />
  </CardHeader>

  <CardBody>
    <p>{item.description}</p>

    {expanded && (
      <InboxItemDetails item={item} />
    )}
  </CardBody>

  <CardFooter>
    <Button onClick={() => onReview('approved')}>Approve</Button>
    <Button onClick={() => onReview('rejected')}>Reject</Button>
    <Button variant="ghost" onClick={() => onReview('deferred')}>Defer</Button>
  </CardFooter>
</Card>
```

### 3. Component: `/frontend/components/inbox/RuleVerificationCard.tsx`

**Purpose:** Specialized card for RULE_VERIFICATION items showing rule details

**Features:**
- Rule code and name
- Citation
- Trigger type badge
- Deadlines count
- Confidence score with explanation
- Link to full rule proposal
- Inline rule preview

**Layout:**
```tsx
<RuleVerificationCard>
  <RuleHeader>
    <RuleCode>{metadata.rule_code}</RuleCode>
    <RuleName>{metadata.rule_name}</RuleName>
    <ConfidenceBadge score={metadata.confidence}>
      {confidenceLevel} ({metadata.confidence * 100}%)
    </ConfidenceBadge>
  </RuleHeader>

  <RuleMetadata>
    <MetadataItem>
      <Label>Citation</Label>
      <Value>{metadata.citation}</Value>
    </MetadataItem>
    <MetadataItem>
      <Label>Trigger</Label>
      <TriggerBadge>{metadata.trigger_type}</TriggerBadge>
    </MetadataItem>
    <MetadataItem>
      <Label>Deadlines</Label>
      <Value>{metadata.deadlines_count} deadline(s)</Value>
    </MetadataItem>
  </RuleMetadata>

  <RulePreview>
    <h4>Extracted Deadlines:</h4>
    <DeadlinesList deadlines={proposalData.deadlines} />
  </RulePreview>

  <ReviewActions>
    <ApproveButton />
    <RejectButton />
    <EditButton />  {/* Opens rule editor modal */}
  </ReviewActions>
</RuleVerificationCard>
```

### 4. Component: `/frontend/components/inbox/WatchtowerChangeCard.tsx`

**Purpose:** Show detected rule changes with diff viewer

**Features:**
- Changed URL
- Detect timestamp
- Diff viewer (old vs new content)
- Link to rule that needs updating
- Accept/Ignore actions

**Layout:**
```tsx
<WatchtowerChangeCard>
  <ChangeHeader>
    <h3>Rule Change Detected</h3>
    <Badge>Watchtower</Badge>
  </ChangeHeader>

  <ChangeDetails>
    <p>URL: {metadata.url}</p>
    <p>Detected: {formatDate(item.created_at)}</p>
  </ChangeDetails>

  <DiffViewer>
    <DiffPanel side="before">
      <h4>Previous Version</h4>
      <pre>{metadata.previous_content}</pre>
    </DiffPanel>
    <DiffPanel side="after">
      <h4>Current Version</h4>
      <pre>{metadata.current_content}</pre>
    </DiffPanel>
  </DiffViewer>

  <ChangeActions>
    <Button onClick={handleAccept}>Accept Change</Button>
    <Button onClick={handleIgnore}>Ignore</Button>
    <Button variant="link" onClick={viewRule}>View Rule</Button>
  </ChangeActions>
</WatchtowerChangeCard>
```

### 5. Component: `/frontend/components/inbox/ConfidenceBadge.tsx`

**Purpose:** Visual confidence score with color coding

**Color Scheme (Paper & Steel):**
- **≥95% (High):** Green background, dark text
- **80-95% (Medium-High):** Yellow background, dark text
- **60-80% (Medium):** Orange background, dark text
- **<60% (Low):** Red background, white text

**Implementation:**
```tsx
export function ConfidenceBadge({ score }: { score: number }) {
  const getStyle = (score: number) => {
    if (score >= 0.95) return {
      bg: '#22C55E',  // Green
      text: '#000',
      label: 'High Confidence'
    };
    if (score >= 0.80) return {
      bg: '#EAB308',  // Yellow
      text: '#000',
      label: 'Recommend Approval'
    };
    if (score >= 0.60) return {
      bg: '#F97316',  // Orange
      text: '#000',
      label: 'Review Required'
    };
    return {
      bg: '#DC2626',  // Red
      text: '#FFF',
      label: 'Careful Review'
    };
  };

  const style = getStyle(score);

  return (
    <Badge
      style={{
        backgroundColor: style.bg,
        color: style.text,
        borderRadius: 0,  // Paper & Steel: no rounded corners
        padding: '4px 8px'
      }}
    >
      {style.label} ({Math.round(score * 100)}%)
    </Badge>
  );
}
```

### 6. Component: `/frontend/components/rules/RuleEditor.tsx`

**Purpose:** Inline rule editing for modifications before approval

**Features:**
- Edit rule code, name, citation
- Add/remove/edit deadlines
- Adjust trigger type
- Modify conditions
- Preview changes
- Save as modified proposal

**Not Required for MVP** - Can approve/reject first, edit later

## API Integration

### Hooks to Create:

```typescript
// /frontend/hooks/useInbox.ts
export function useInbox() {
  const [items, setItems] = useState<InboxItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [pendingCount, setPendingCount] = useState(0);

  const fetchItems = async (filters?: InboxFilters) => { /* ... */ };
  const reviewItem = async (id: string, resolution: string, notes?: string) => { /* ... */ };
  const bulkReview = async (ids: string[], resolution: string) => { /* ... */ };

  return { items, loading, pendingCount, fetchItems, reviewItem, bulkReview };
}

// /frontend/hooks/useInboxPendingCount.ts
export function useInboxPendingCount() {
  // Real-time pending count for navbar badge
  const { data } = useSWR('/api/v1/inbox/pending/summary', fetcher, {
    refreshInterval: 30000  // Refresh every 30 seconds
  });

  return data?.total || 0;
}
```

### Type Definitions:

```typescript
// /frontend/types/inbox.ts
export interface InboxItem {
  id: string;
  type: InboxItemType;
  status: InboxStatus;
  title: string;
  description?: string;
  jurisdiction_id?: string;
  rule_id?: string;
  confidence?: number;
  metadata: Record<string, any>;
  created_at: string;
  reviewed_at?: string;
  reviewed_by?: string;
  resolution?: string;
  resolution_notes?: string;
}

export enum InboxItemType {
  RULE_VERIFICATION = 'RULE_VERIFICATION',
  WATCHTOWER_CHANGE = 'WATCHTOWER_CHANGE',
  SCRAPER_ERROR = 'SCRAPER_ERROR',
  CONFIG_WARNING = 'CONFIG_WARNING',
  JURISDICTION_DISABLED = 'JURISDICTION_DISABLED'
}

export enum InboxStatus {
  PENDING = 'PENDING',
  REVIEWED = 'REVIEWED',
  DEFERRED = 'DEFERRED',
  ARCHIVED = 'ARCHIVED'
}
```

## UI/UX Considerations

### Paper & Steel Design System Compliance:
- ✅ Zero border-radius (no rounded corners)
- ✅ `gap-px` grid technique for layouts
- ✅ `border-ink` for borders
- ✅ Serif fonts for legal content (IBM Plex Serif)
- ✅ Sans-serif for UI (IBM Plex Sans)
- ✅ No shadows (use borders instead)

### Performance:
- Pagination: 50 items per page (configurable)
- Virtual scrolling for large lists
- Optimistic updates for instant feedback
- SWR for caching and revalidation

### Accessibility:
- Keyboard navigation (Tab, Enter, Escape)
- Screen reader support
- Focus indicators
- Color contrast (WCAG AA)

## Implementation Priority

### Phase 1 (MVP):
- [x] Backend API (complete)
- [ ] Basic inbox page with list
- [ ] InboxItemCard component
- [ ] RuleVerificationCard component
- [ ] ConfidenceBadge component
- [ ] Review actions (approve/reject/defer)

### Phase 2 (Enhanced):
- [ ] Bulk operations
- [ ] Advanced filtering
- [ ] WatchtowerChangeCard with diff
- [ ] Real-time updates (WebSocket or polling)
- [ ] Keyboard shortcuts

### Phase 3 (Future):
- [ ] RuleEditor component
- [ ] Inline rule modification
- [ ] Audit trail viewer
- [ ] Export/import rules

## Estimated Development Time

- Basic inbox page: 2 hours
- InboxItemCard: 1 hour
- RuleVerificationCard: 1.5 hours
- ConfidenceBadge: 30 minutes
- WatchtowerChangeCard: 1 hour
- API integration hooks: 1 hour
- Testing and polish: 1 hour

**Total: ~8 hours** for complete inbox workflow

## Testing Checklist

- [ ] Load inbox with 50+ items
- [ ] Filter by type and status
- [ ] Approve single rule
- [ ] Reject single rule
- [ ] Defer single rule
- [ ] Bulk approve 10 rules
- [ ] Bulk reject 5 rules
- [ ] Verify AuthorityRule created after approval
- [ ] Verify inbox item status updates
- [ ] Test pagination
- [ ] Test search/filter
- [ ] Test error handling (network failures)
- [ ] Test optimistic updates

## Notes

- Frontend implementation deferred to allow focus on backend pipeline completion
- All API endpoints are tested and working
- Component structure follows Next.js 14 App Router conventions
- State management via React hooks + SWR
- No state management library (Redux/Zustand) needed at this scale
