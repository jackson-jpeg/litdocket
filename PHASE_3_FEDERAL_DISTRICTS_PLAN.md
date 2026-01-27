# Phase 3: Federal District Courts - Implementation Plan

## 🎯 Goal
Add local rules for all 94 U.S. Federal District Courts, focusing on high-volume litigation districts first.

**Target**: 94 districts × ~4 rules each = ~376 new rules

---

## 📊 Priority Matrix

### Tier 1: Top 10 High-Volume Districts (Implement First)

| District | Abbrev. | Why Priority | Est. Rules |
|----------|---------|--------------|------------|
| **S.D. New York** | SDNY | Wall Street litigation, securities, IP | 5 |
| **C.D. California** | CDCA | Entertainment, tech, employment | 5 |
| **N.D. Illinois** | NDIL | Chicago commercial hub, class actions | 4 |
| **D. Delaware** | D.Del. | Corporate law capital, patent litigation | 5 |
| **N.D. California** | NDCA | Silicon Valley, tech/IP disputes | 5 |
| **E.D. Texas** | EDTX | Patent litigation capital | 4 |
| **D. New Jersey** | D.N.J. | Pharmaceutical, corporate | 4 |
| **D. Massachusetts** | D.Mass. | Biotech, IP, academic disputes | 4 |
| **S.D. Florida** | SDFL | Securities, international, maritime | 4 |
| **N.D. Texas** | NDTX | Dallas/Fort Worth commercial | 4 |

**Total Tier 1**: 44 rules

### Tier 2: High-Volume Districts (11-30)

| District | Key Practice Areas | Est. Rules |
|----------|-------------------|------------|
| **E.D. Virginia** | Rocket docket, national security | 4 |
| **S.D. Texas** | Energy, immigration, border | 4 |
| **E.D. Pennsylvania** | Philadelphia commercial, pharma | 4 |
| **C.D. Illinois** | Downstate commercial | 3 |
| **W.D. Texas** | Austin tech, San Antonio | 4 |
| **M.D. Florida** | Orlando/Tampa litigation | 3 |
| **N.D. Georgia** | Atlanta commercial, civil rights | 4 |
| **W.D. Washington** | Seattle tech, aerospace | 4 |
| **D. Colorado** | Denver commercial, natural resources | 4 |
| **D. Arizona** | Immigration, tribal law | 3 |
| **E.D. Michigan** | Detroit auto, employment | 3 |
| **S.D. Ohio** | Cincinnati/Columbus commercial | 3 |
| **W.D. Missouri** | Kansas City litigation | 3 |
| **D. Maryland** | Baltimore federal practice | 3 |
| **D. Connecticut** | Hartford insurance, corporate | 3 |
| **E.D. New York** | Brooklyn federal, Long Island | 4 |
| **W.D. Pennsylvania** | Pittsburgh commercial | 3 |
| **D. Nevada** | Las Vegas gaming, bankruptcy | 3 |
| **D. Minnesota** | Minneapolis corporate | 3 |
| **E.D. Louisiana** | New Orleans maritime, energy | 4 |

**Total Tier 2**: 69 rules

### Tier 3: Remaining Districts (31-94)
Lower volume but still important for complete coverage.

**Total Tier 3**: ~263 rules

---

## 🔍 Federal District Court Rule Types

### Common Local Rules Across Districts

1. **Answer/Motion Deadline Variations**
   - Some districts: 21 days (standard FRCP)
   - Some districts: 14 days (expedited)
   - Some districts: Special rules for prisoner cases

2. **Initial Scheduling Conference**
   - Timing: 90-120 days after filing
   - Pre-conference requirements vary by district

3. **Discovery Deadlines**
   - Initial disclosures: 14-30 days after conference
   - Discovery cutoff: Often 30 days before trial
   - Expert reports: 90 days before trial (opening), 60 days (rebuttal)

4. **Motion Practice**
   - Motion to dismiss: With answer or within 21 days
   - Summary judgment: 30-60 days before trial (varies)
   - Pre-motion conferences: Required in many districts

5. **Pretrial Deadlines**
   - Pretrial order: 14-30 days before trial
   - Motions in limine: 7-14 days before trial
   - Jury instructions: 7-14 days before trial
   - Witness/exhibit lists: 7-14 days before trial

### District-Specific Unique Rules

**SDNY**:
- Mandatory pre-motion conferences for all motions
- Strict page limits (25 pages for summary judgment)
- ECF filing deadlines (midnight ET, not 11:59 PM local)

**EDTX (Patent Cases)**:
- Expedited schedule (trial in 12-18 months)
- Patent local rules (P.R. 3-1 through 3-8)
- Infringement contentions: 10 days after scheduling conference

**D.Del. (Corporate)**:
- Default schedule order on filing
- Fact discovery: 8 months
- Expert discovery: 4 months
- Close of discovery to trial: 3-4 months

**NDCA (Tech)**:
- Patent local rules
- ADR program (mandatory for some cases)
- Standing orders vary by judge

---

## 📋 Implementation Strategy

### Phase 3A: Tier 1 Districts (Week 1-3)
**Goal**: Implement top 10 high-volume districts

**Approach**:
1. Research each district's local rules (LR)
2. Identify common patterns
3. Build reusable templates
4. Implement district-by-district
5. Test with real case scenarios

**Deliverable**: 44 new rules across 10 districts

### Phase 3B: Tier 2 Districts (Week 4-8)
**Goal**: Implement next 20 high-volume districts

**Approach**:
1. Use templates from Tier 1
2. Identify district-specific variations
3. Batch similar districts (e.g., all California districts)
4. Focus on discovery and pretrial rules

**Deliverable**: 69 new rules across 20 districts

### Phase 3C: Tier 3 Districts (Week 9-16)
**Goal**: Complete remaining 64 districts

**Approach**:
1. Group by circuit (similar practices)
2. Use standardized templates
3. Note only significant deviations
4. Batch implementation

**Deliverable**: ~263 new rules across 64 districts

---

## 🏗️ Technical Architecture Changes

### New Rule Schema Fields

```python
# Add to rule_schema metadata
"district_court": {
    "circuit": "2nd",  # 1st-11th, DC, Federal
    "district": "SDNY",
    "judges": ["optional", "list", "of", "judges"],
    "case_types": ["civil", "patent", "mdl"],  # Multidistrict Litigation
    "standing_orders": ["link", "to", "orders"]
}
```

### New Trigger Types

```python
TRIGGER_TYPES = {
    # Existing
    "COMPLAINT_SERVED": "Answer deadline",
    "TRIAL_DATE": "Pretrial deadlines",

    # New for Federal Districts
    "SCHEDULING_CONFERENCE": "Discovery deadlines",
    "SCHEDULING_ORDER_ENTERED": "Discovery cutoff",
    "MOTION_FILED": "Opposition/reply deadlines",
    "EXPERT_DESIGNATION": "Expert report deadlines",
    "PRETRIAL_CONFERENCE": "Final pretrial order",
}
```

### Database Schema Updates

```sql
-- Add district court fields to rule_template
ALTER TABLE rule_templates ADD COLUMN circuit VARCHAR(20);
ALTER TABLE rule_templates ADD COLUMN district_code VARCHAR(10);
ALTER TABLE rule_templates ADD COLUMN case_type VARCHAR(50);

-- Create index for fast district lookups
CREATE INDEX idx_rule_templates_district ON rule_templates(district_code);
CREATE INDEX idx_rule_templates_circuit ON rule_templates(circuit);
```

---

## 📚 Data Sources

### Official Sources (Free)
1. **U.S. Courts Website**: https://www.uscourts.gov/
   - Links to all district court websites
   - Local rules PDFs

2. **Individual District Court Sites**
   - Example SDNY: https://www.nysd.uscourts.gov/
   - Local Rules → Download PDF
   - Standing Orders → Check judge-specific rules

3. **Free Law Project**: https://www.courtlistener.com/
   - Aggregated court rules
   - Search by district

### Reference Materials
1. **Federal Civil Judicial Procedure and Rules** (West Publishing)
2. **Moore's Federal Practice** (LexisNexis)
3. **Wright & Miller Federal Practice and Procedure**

---

## 🧪 Testing Strategy

### Rule Accuracy Testing
For each district:
1. ✅ Verify against official local rules PDF
2. ✅ Check for recent amendments (2024-2026)
3. ✅ Cross-reference with clerk's office guides
4. ✅ Test calculation with real case dates

### Sample Test Cases

**SDNY Test Case**:
```
Scenario: New civil case filed in SDNY
Filing Date: January 15, 2026
Case Type: Commercial dispute

Expected Deadlines:
- Initial Conference: Rule 26(f) conference within 21 days = Feb 5, 2026
- Scheduling Conference: Within 90 days = April 15, 2026
- Initial Disclosures: 14 days after conference = April 29, 2026
- Discovery Cutoff: [Set in scheduling order]
```

**EDTX Patent Case**:
```
Scenario: Patent infringement case filed in EDTX
Filing Date: January 15, 2026
Case Type: Patent

Expected Deadlines:
- Scheduling Conference: Within 30 days = Feb 14, 2026
- Infringement Contentions: 10 days after conference = Feb 24, 2026
- Invalidity Contentions: 45 days after infringement = April 10, 2026
- Fact Discovery Close: ~8 months from filing = Sept 15, 2026
```

---

## 🎯 Success Metrics

### Coverage Metrics
- [x] All 50 states covered (Phase 2 ✅)
- [ ] Top 10 federal districts (Phase 3A)
- [ ] Top 30 federal districts (Phase 3B)
- [ ] All 94 federal districts (Phase 3C)

### Quality Metrics
- [ ] 100% accuracy vs. official local rules
- [ ] Quarterly review process established
- [ ] User feedback: >4.5/5 on federal rules
- [ ] Zero missed deadlines due to rule errors

### Usage Metrics
- [ ] >60% of federal cases use LitDocket
- [ ] AI extraction accuracy >95% for federal cases
- [ ] Average time to docket federal case: <2 minutes

---

## 🚀 Implementation Plan: First 5 Districts

### Week 1: SDNY (Southern District of New York)

**Rules to Implement**:
1. Answer deadline (21 days per FRCP, no local variation)
2. Initial conference & disclosures (Local Civil Rule 26.3)
3. Motion practice (Local Civil Rule 6.1 - pre-motion conferences)
4. Summary judgment deadlines (must be filed 60 days before trial)
5. Pretrial order (Local Civil Rule 16.1)

**Local Rule Quirks**:
- Pre-motion conference REQUIRED for all non-discovery motions
- Individual judge rules vary significantly
- Electronic filing rules (Local Civil Rule 5.2)

### Week 1: CDCA (Central District of California)

**Rules to Implement**:
1. Answer deadline (21 days per FRCP)
2. Initial case management conference (Local Rule 16-3)
3. Discovery plan (Local Rule 26-1)
4. Motion practice (Local Rule 7)
5. Pretrial procedures (Local Rule 16-4)

**Local Rule Quirks**:
- Early neutral evaluation program (optional)
- Different rules for different divisions (LA vs. Santa Ana vs. Riverside)
- Strict meet-and-confer requirements

### Week 1-2: D.Del. (District of Delaware)

**Rules to Implement**:
1. Answer deadline (21 days per FRCP)
2. Default scheduling order (automatically issued)
3. Fact discovery close (8 months from scheduling order)
4. Expert discovery close (4 months after fact discovery)
5. Dispositive motions (filed before discovery closes)

**Local Rule Quirks**:
- Default schedule is aggressive (12 months to trial)
- Limited discovery in patent cases
- Mandatory mediation program

### Week 2: EDTX (Eastern District of Texas - Patent Hub)

**Rules to Implement**:
1. Answer deadline (21 days per FRCP)
2. Patent Local Rules (P.R. 3-1 through 3-8)
3. Infringement contentions (10 days after scheduling conference)
4. Invalidity contentions (45 days after infringement)
5. Discovery deadlines (expedited - 8 months total)

**Local Rule Quirks**:
- Patent cases have unique expedited schedule
- Claim construction (Markman) hearing within 4-5 months
- Trial typically 12-18 months from filing
- Strict compliance with P.R. 3 rules required

### Week 2-3: NDCA (Northern District of California - Silicon Valley)

**Rules to Implement**:
1. Answer deadline (21 days per FRCP)
2. Patent Local Rules (for San Jose Division)
3. Initial case management conference (ADR Rule 3-5)
4. Discovery deadlines (Civil L.R. 16)
5. Summary judgment timing (28 days before hearing)

**Local Rule Quirks**:
- Different rules by division (San Francisco vs. San Jose vs. Oakland)
- Mandatory settlement conference in some case types
- Judge-specific standing orders common
- Patent cases: Special rules in San Jose

---

## 💾 Code Structure

### New Files to Create

```
backend/scripts/
  seed_federal_districts_tier1.py    # Top 10 districts
  seed_federal_districts_tier2.py    # Next 20 districts
  seed_federal_districts_tier3.py    # Remaining 64 districts

backend/app/services/
  federal_district_service.py        # Helper for district-specific logic

backend/app/models/
  federal_district.py                # Model for district metadata
```

### Rule Template Pattern

```python
def create_sdny_scheduling_conference_rule(db: Session, user_id: str) -> RuleTemplate:
    """
    S.D.N.Y. - Initial Scheduling Conference
    Local Civil Rule 26.3 - Conference within 90 days
    """
    rule_schema = {
        "metadata": {
            "name": "Initial Scheduling Conference - S.D.N.Y.",
            "description": "Federal Rule 26(f) conference and scheduling order",
            "effective_date": "2024-01-01",
            "citations": [
                "Local Civil Rule 26.3",
                "FRCP 26(f)",
                "FRCP 16(b)"
            ],
            "jurisdiction_type": "federal_district",
            "circuit": "2nd",
            "district": "SDNY",
            "court_level": "district"
        },
        "trigger": {
            "type": "COMPLAINT_FILED",
            "required_fields": [
                {
                    "name": "filing_date",
                    "type": "date",
                    "label": "Date Complaint Was Filed",
                    "required": True
                },
                {
                    "name": "case_type",
                    "type": "select",
                    "label": "Case Type",
                    "options": ["civil", "patent", "securities", "employment"],
                    "required": False,
                    "default": "civil"
                }
            ]
        },
        "deadlines": [
            {
                "id": "rule_26f_conference",
                "title": "Rule 26(f) Conference",
                "offset_days": 21,
                "offset_direction": "after",
                "priority": "CRITICAL",
                "description": "Parties must confer about case management",
                "applicable_rule": "FRCP 26(f)",
                "add_service_days": False,
                "party_responsible": "all_parties",
                "calculation_method": "calendar_days",
                "notes": "Meet and confer before scheduling conference"
            },
            {
                "id": "scheduling_conference",
                "title": "Scheduling Conference",
                "offset_days": 90,
                "offset_direction": "after",
                "priority": "CRITICAL",
                "description": "Court holds scheduling conference",
                "applicable_rule": "Local Civil Rule 26.3",
                "add_service_days": False,
                "party_responsible": "all_parties",
                "calculation_method": "calendar_days",
                "notes": "Court will set discovery and trial deadlines"
            },
            {
                "id": "initial_disclosures",
                "title": "Initial Disclosures Due",
                "offset_days": 14,
                "offset_direction": "after",
                "offset_from": "rule_26f_conference",  # Relative to other deadline
                "priority": "CRITICAL",
                "description": "FRCP 26(a)(1) initial disclosures",
                "applicable_rule": "FRCP 26(a)(1)",
                "add_service_days": False,
                "party_responsible": "all_parties",
                "calculation_method": "calendar_days",
                "notes": "Within 14 days after Rule 26(f) conference"
            }
        ],
        "dependencies": [
            {
                "parent_id": "rule_26f_conference",
                "child_id": "initial_disclosures",
                "relationship": "triggers",
                "auto_calculate": True
            }
        ],
        "validation": {
            "min_deadlines": 1,
            "max_deadlines": 20,
            "require_citations": True
        },
        "settings": {
            "auto_cascade_updates": True,
            "allow_manual_override": True,
            "notification_lead_days": [1, 3, 7, 14, 30]
        }
    }

    # ... rest of template creation (same pattern as states)
```

---

## 📝 Next Steps

1. ✅ Complete Phase 2 (All 50 states) - DONE!
2. ✅ Create Phase 3 implementation plan - DONE!
3. [ ] Implement SDNY rules (first district)
4. [ ] Implement CDCA rules
5. [ ] Implement D.Del. rules
6. [ ] Implement EDTX rules
7. [ ] Implement NDCA rules
8. [ ] Complete Tier 1 (10 districts, 44 rules)
9. [ ] Begin Tier 2 (20 districts, 69 rules)
10. [ ] Complete all 94 districts (376+ rules)

---

## 🎉 Vision: Complete Federal Coverage

Once Phase 3 is complete, LitDocket will have:
- ✅ All 50 U.S. states (54 rules)
- ✅ All 94 federal district courts (~376 rules)
- **Total: ~430 rules covering 146 jurisdictions**

This represents **complete trial court coverage** for the United States, making LitDocket the most comprehensive deadline calculation system available.

**Market Position**:
- CompuLaw Vision: ~250 jurisdictions
- LawToolBox: ~150 jurisdictions
- **LitDocket**: 146+ jurisdictions (comparable coverage, better UX, AI-powered)

---

Ready to begin implementation! 🚀
