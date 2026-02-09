# Phase 3: Pilot Jurisdiction Testing Guide

## Overview
This guide provides procedures for testing the end-to-end harvest pipeline with 3 pilot jurisdictions.

## Test Jurisdictions

### 1. Florida Middle District Federal Court ✅ (Already Seeded)
- **Jurisdiction ID:** Check database for FED jurisdiction
- **Court Website:** https://www.flmd.uscourts.gov/
- **Rules URL:** https://www.flmd.uscourts.gov/local-rules
- **Complexity:** Medium (standard federal structure)
- **Expected Rules:** 20-30 local rules + federal rules

### 2. California Superior Court (New)
- **Court Website:** https://www.courts.ca.gov/
- **Rules URL:** https://www.courts.ca.gov/rules.htm
- **Complexity:** High (complex state rules, multiple rule sets)
- **Expected Rules:** 50+ rules across multiple categories

### 3. New York State Supreme Court (New)
- **Court Website:** https://ww2.nycourts.gov/
- **Rules URL:** https://ww2.nycourts.gov/rules/index.shtml
- **Complexity:** High (different structure, appellate vs trial rules)
- **Expected Rules:** 40+ rules

## Testing Procedure

### Phase 3.1: Setup Jurisdiction

```bash
# 1. Add jurisdiction to database
curl -X POST http://localhost:8000/api/v1/jurisdictions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "name": "California Superior Court",
    "code": "CA_SUP",
    "court_type": "state",
    "court_website": "https://www.courts.ca.gov/",
    "auto_sync_enabled": false
  }'

# Save the jurisdiction_id from response
```

### Phase 3.2: Cartographer Discovery

```bash
# 2. Trigger Cartographer to discover scraper config
curl -X POST http://localhost:8000/api/v1/authority-core/cartographer/discover/{jurisdiction_id} \
  -H "Authorization: Bearer $TOKEN"

# Expected: Cartographer analyzes page structure and returns CSS selectors
# Time: 1-2 minutes
```

### Phase 3.3: Rule Extraction

```bash
# 3. Harvest rules from URL
curl -X POST http://localhost:8000/api/v1/authority-core/harvest \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "jurisdiction_id": "{jurisdiction_id}",
    "url": "https://www.courts.ca.gov/rules.htm",
    "use_extended_thinking": false,
    "auto_approve_high_confidence": false
  }'

# Expected Response:
# {
#   "job_id": "...",
#   "status": "completed",
#   "rules_found": 25,
#   "proposals_created": 25,
#   "rules": [...]
# }

# Time: 2-5 minutes depending on page size
```

### Phase 3.4: Verify Inbox Items Created

```bash
# 4. Check inbox for pending rule verifications
curl http://localhost:8000/api/v1/inbox?type=RULE_VERIFICATION&status=PENDING \
  -H "Authorization: Bearer $TOKEN"

# Expected: Array of inbox items matching proposals_created count

# Check pending summary
curl http://localhost:8000/api/v1/inbox/pending/summary \
  -H "Authorization: Bearer $TOKEN"

# Expected:
# {
#   "total": 25,
#   "by_type": {
#     "RULE_VERIFICATION": 25
#   }
# }
```

### Phase 3.5: Review and Approve Rules

```bash
# 5. Review a single rule
curl http://localhost:8000/api/v1/inbox/{item_id} \
  -H "Authorization: Bearer $TOKEN"

# Expected: Full inbox item with metadata including:
# - proposal_id
# - confidence score
# - rule details

# 6. Approve high-confidence rules
curl -X POST http://localhost:8000/api/v1/inbox/{item_id}/review \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "resolution": "approved",
    "notes": "Rule verified - citations match official court rules"
  }'

# Expected: AuthorityRule created with is_verified=True, is_active=True

# 7. Bulk approve multiple rules
curl -X POST http://localhost:8000/api/v1/inbox/bulk-review \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "item_ids": ["{item_id_1}", "{item_id_2}", "{item_id_3}"],
    "resolution": "approved",
    "notes": "Batch approval of high-confidence rules"
  }'
```

### Phase 3.6: Verify Rules Created

```bash
# 8. Query created AuthorityRules
curl "http://localhost:8000/api/v1/authority-core/rules?jurisdiction_id={jurisdiction_id}&is_active=true" \
  -H "Authorization: Bearer $TOKEN"

# Expected: Array of AuthorityRule objects with:
# - is_verified: true
# - is_active: true
# - confidence_score: 0.0-1.0
```

### Phase 3.7: Test Deadline Calculation

```bash
# 9. Calculate deadlines using newly harvested rules
curl -X POST http://localhost:8000/api/v1/triggers/preview-deadlines \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "trigger_type": "trial_date",
    "trigger_date": "2026-12-15",
    "jurisdiction": "california_state",
    "court_type": "civil"
  }'

# Expected: Deadlines calculated using Authority Core rules
# Verify: source_rule_id populated with harvested rule IDs
```

### Phase 3.8: Enable Watchtower Monitoring

```bash
# 10. Enable auto-sync for jurisdiction
curl -X PATCH http://localhost:8000/api/v1/jurisdictions/{jurisdiction_id} \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "auto_sync_enabled": true,
    "sync_frequency": "WEEKLY"
  }'

# 11. Test Watchtower manually
curl -X POST http://localhost:8000/api/v1/authority-core/watchtower/check/{jurisdiction_id} \
  -H "Authorization: Bearer $TOKEN"

# Expected: Watchtower checks URLs and reports no changes (first run)
```

## Success Criteria

### Per Jurisdiction:

- [ ] Jurisdiction added to database
- [ ] Cartographer discovered valid scraper_config
- [ ] Rules extracted with >75% avg confidence
- [ ] Inbox items created for all proposals
- [ ] At least 10 rules approved and active
- [ ] Deadlines calculate correctly using new rules
- [ ] Watchtower baseline established
- [ ] Auto-sync enabled

### Overall Phase 3:

- [ ] 3 jurisdictions fully onboarded
- [ ] 50+ total rules harvested and approved
- [ ] 100% of new deadlines use Authority Core
- [ ] Inbox workflow functional
- [ ] Watchtower monitoring active

## Confidence Score Analysis

After harvesting, analyze confidence distribution:

```sql
-- Check confidence distribution
SELECT
  CASE
    WHEN confidence_score >= 0.95 THEN '95%+ (Auto-approve)'
    WHEN confidence_score >= 0.80 THEN '80-95% (Recommend)'
    WHEN confidence_score >= 0.60 THEN '60-80% (Review)'
    ELSE '<60% (Careful review)'
  END as confidence_bracket,
  COUNT(*) as rule_count
FROM authority_rules
WHERE jurisdiction_id = '{jurisdiction_id}'
  AND is_active = true
GROUP BY confidence_bracket
ORDER BY MIN(confidence_score) DESC;
```

**Expected Distribution:**
- 30-40%: High confidence (≥95%)
- 40-50%: Medium-high (80-95%)
- 10-20%: Medium (60-80%)
- 0-10%: Low (<60%)

## Troubleshooting

### Issue: Cartographer fails to discover selectors
**Solution:** Check if website uses JavaScript rendering. Add `requires_js: true` flag and integrate Playwright (Phase 5).

### Issue: Low confidence scores across all rules
**Solution:** Review extraction prompts in `rule_extraction_service.py`. May need jurisdiction-specific tuning.

### Issue: Inbox items not created
**Solution:** Check logs for errors in `authority_core_service.create_proposal()`. Verify InboxService integration.

### Issue: Watchtower not detecting changes
**Solution:** Verify URL is accessible and content hasn't been restructured. Check `watchtower_service.py` hash comparison logic.

## Performance Benchmarks

**Target Performance:**
- Cartographer discovery: <2 minutes
- Rule extraction (25 rules): <5 minutes
- Inbox item creation: <1 second
- Bulk approval (10 rules): <5 seconds
- Deadline calculation: <1 second

## Next Steps After Phase 3

Once 3 pilot jurisdictions are successfully tested:

1. **Phase 4:** Integrate harvested rules into chat (AI-powered docketing)
2. **Phase 5:** Scale to 50+ jurisdictions with batch operations
3. **Phase 6:** Add self-healing and advanced intelligence

## Notes

- Always test in staging before production
- Keep detailed logs of extraction quality
- Monitor Anthropic API usage (costs scale with jurisdiction count)
- Backup database before bulk operations
