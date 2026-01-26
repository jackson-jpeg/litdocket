# Deadline Calculations Quick Reference

**Purpose**: Fast lookup for common deadline calculations across jurisdictions
**Audience**: Developers adding new rules, attorneys verifying calculations, QA testing

---

## Answer to Complaint Deadlines by Jurisdiction

| Jurisdiction | Days | Service Extension | Calculation Type | Special Rules |
|--------------|------|-------------------|------------------|---------------|
| **Federal (FRCP)** | 21 | +3 mail | Calendar | 60 days if U.S./officer/agency |
| **Alabama** | 30 | +3 mail | Calendar | - |
| **Alaska** | 20 | +3 mail | Calendar | - |
| **Arizona** | 20 | +3 mail | Calendar | - |
| **Arkansas** | 30 | +3 mail | Calendar | - |
| **California** | 30 | +5 mail (in-state), +10 out-of-state | Calendar | - |
| **Colorado** | 21 | +3 mail | Calendar | Follows FRCP |
| **Connecticut** | 30 | +3 mail | Calendar | - |
| **Delaware** | 20 | +3 mail | Calendar | - |
| **Florida** | 20 | +5 mail/email | Calendar | - |
| **Georgia** | 30 | None | Calendar | No extension for mail |
| **Hawaii** | 20 | +3 mail | Calendar | - |
| **Idaho** | 21 | +3 mail | Calendar | Follows FRCP |
| **Illinois** | 30 | +3 mail | Calendar | - |
| **Indiana** | 20 | +3 mail | Calendar | - |
| **Iowa** | 20 | +3 mail | Calendar | - |
| **Kansas** | 21 | +3 mail | Calendar | Follows FRCP |
| **Kentucky** | 20 | +3 mail | Calendar | - |
| **Louisiana** | 15 | None | Calendar | **Shortest in nation!** |
| **Maine** | 21 | +3 mail | Calendar | Follows FRCP |
| **Maryland** | 30 | +3 mail | Calendar | - |
| **Massachusetts** | 20 | +3 mail | Calendar | - |
| **Michigan** | 21 | +3 mail | Calendar | - |
| **Minnesota** | 21 | +3 mail | Calendar | Follows FRCP |
| **Mississippi** | 30 | +3 mail | Calendar | - |
| **Missouri** | 30 | +3 mail | Calendar | - |
| **Montana** | 21 | +3 mail | Calendar | Follows FRCP |
| **Nebraska** | 30 | +3 mail | Calendar | - |
| **Nevada** | 21 | +2 mail (in-state), +5 out-of-state | Calendar | Unique extension |
| **New Hampshire** | 30 | +3 mail | Calendar | - |
| **New Jersey** | 35 | None | Calendar | **Second longest!** |
| **New Mexico** | 30 | +3 mail | Calendar | - |
| **New York** | 20 personal, 30 mail | Built-in | Calendar | **Conditional deadline** |
| **North Carolina** | 30 | +3 mail | Calendar | - |
| **North Dakota** | 21 | +3 mail | Calendar | Follows FRCP |
| **Ohio** | 28 | +3 mail | Calendar | - |
| **Oklahoma** | 20 | +3 mail | Calendar | - |
| **Oregon** | 30 | +3 mail | Calendar | - |
| **Pennsylvania** | 20 | +3 mail | Calendar | 30 days if not personally served |
| **Rhode Island** | 20 | +3 mail | Calendar | - |
| **South Carolina** | 30 | +3 mail | Calendar | - |
| **South Dakota** | 21 | +3 mail | Calendar | - |
| **Tennessee** | 30 | +3 mail | Calendar | - |
| **Texas** | **20 + Monday** | None | Calendar | **Due 10 AM on Monday after 20 days** |
| **Utah** | 21 | +3 mail | Calendar | Follows FRCP |
| **Vermont** | 21 | +3 mail | Calendar | Follows FRCP |
| **Virginia** | 21 | +3 mail | Calendar | - |
| **Washington** | 20 | +3 mail | Calendar | - |
| **West Virginia** | 20 | +3 mail | Calendar | - |
| **Wisconsin** | 45 | +3 mail | Calendar | **LONGEST in nation!** |
| **Wyoming** | 21 | +3 mail | Calendar | Follows FRCP |

### Key Outliers
- **Shortest**: Louisiana (15 days)
- **Longest**: Wisconsin (45 days), New Jersey (35 days - second longest)
- **Unique Rules**: Texas (Monday Rule), New York (conditional), Nevada (different extensions), Florida (+5 mail/email)

---

## Federal Discovery Deadlines (FRCP)

| Trigger | Deadline | Rule | Priority |
|---------|----------|------|----------|
| **Initial Disclosures** | Within 14 days of Rule 26(f) conference | FRCP 26(a)(1) | CRITICAL |
| **Expert Disclosures (Plaintiff)** | At least 90 days before trial | FRCP 26(a)(2)(D)(i) | CRITICAL |
| **Expert Disclosures (Defendant)** | Within 30 days after plaintiff | FRCP 26(a)(2)(D)(ii) | CRITICAL |
| **Pretrial Disclosures** | At least 30 days before trial | FRCP 26(a)(3) | CRITICAL |
| **Objections to Pretrial Disclosures** | Within 14 days after disclosure | FRCP 26(a)(3)(B) | IMPORTANT |
| **Interrogatory Responses** | 30 days after service | FRCP 33(b)(2) | CRITICAL |
| **Document Production** | 30 days after service | FRCP 34(b)(2)(A) | CRITICAL |
| **Admission Responses** | 30 days after service | FRCP 36(a)(3) | CRITICAL |

---

## Appellate Deadlines (Federal)

| Trigger | Deadline | Rule | Priority |
|---------|----------|------|----------|
| **Notice of Appeal (Civil)** | 30 days after judgment | FRAP 4(a)(1)(A) | FATAL |
| **Notice of Appeal (U.S. as party)** | 60 days after judgment | FRAP 4(a)(1)(B) | FATAL |
| **Notice of Appeal (Criminal)** | 14 days after judgment | FRAP 4(b)(1)(A) | FATAL |
| **Appellant Brief** | 40 days after record filed | FRAP 31(a)(1) | FATAL |
| **Appellee Brief** | 30 days after appellant brief | FRAP 31(a)(1) | FATAL |
| **Reply Brief** | 21 days after appellee brief | FRAP 31(a)(1) | CRITICAL |
| **Petition for Rehearing** | 14 days after judgment | FRAP 40(a)(1) | IMPORTANT |
| **Petition for Certiorari (SCOTUS)** | 90 days after judgment | Supreme Court Rule 13 | IMPORTANT |

---

## Service Method Extensions

### Federal (FRCP 6(d))
- **Mail/Email/Electronic**: +3 days
- **Personal**: No extension

### State Variations
| State | Mail | Email | Publication |
|-------|------|-------|-------------|
| **California** | +5 (in-state), +10 (out-of-state) | +2 | +4 |
| **Florida** | +5 | +5 | +7 |
| **Texas** | None (built into Monday Rule) | None | None |
| **New York** | Built into 30-day rule | +1 | +4 |
| **Federal** | +3 | +3 | +3 |
| **Nevada** | +2 (in-state), +5 (out-of-state) | +1 | +3 |

---

## Calculation Methods

### Calendar Days
- **Definition**: All days including weekends and holidays
- **Used By**: Most jurisdictions (default)
- **Example**: 20 calendar days from Jan 1 = Jan 21

### Business Days
- **Definition**: Monday-Friday only (excluding holidays)
- **Used By**: Some local rules, specific motions
- **Example**: 20 business days from Jan 1 (Fri) = Jan 29 (Mon)

### Court Days
- **Definition**: Days court is actually open
- **Used By**: Some specialized rules
- **Example**: Excludes weekends, holidays, AND court closures

---

## Weekend/Holiday Rules

### Federal Rule (FRCP 6(a))
If last day falls on:
- **Saturday, Sunday, or legal holiday** → Next business day
- Applies to all FRCP deadlines

### State Variations
Most states follow similar rule, but check:
- **Louisiana**: Different holiday calendar
- **Texas**: Monday Rule (special case)
- **New York**: Specific statute (Gen. Constr. Law § 25-a)

### Federal Legal Holidays
- New Year's Day
- Martin Luther King Jr. Day
- Presidents' Day
- Memorial Day
- Juneteenth (added 2021)
- Independence Day
- Labor Day
- Columbus Day
- Veterans Day
- Thanksgiving
- Christmas

---

## Time Computation Formulas

### FRCP 6(a) - Computation Method

#### For periods less than 11 days:
1. **Exclude** the event day
2. **Count** every day (including weekends/holidays)
3. **Include** the last day
4. If last day is weekend/holiday → **roll to next business day**

#### For periods 11 days or more:
1. **Exclude** the event day
2. **Count** every day (including weekends/holidays)
3. **Include** the last day
4. If last day is weekend/holiday → **roll to next business day**

#### For "backward counting" (before trial):
1. **Exclude** trial date
2. **Count backward** including all days
3. If deadline falls on weekend/holiday → **roll to previous business day**

### Example Calculations

**Example 1: 21-day answer period (served Monday, Jan 1)**
1. Exclude Jan 1 (service day)
2. Count 21 days → Jan 22 (Monday)
3. Jan 22 is business day → **Answer due Jan 22**

**Example 2: 21-day period (served Friday, Dec 29)**
1. Exclude Dec 29 (service day)
2. Count 21 days → Jan 19 (Friday)
3. Jan 19 is business day → **Answer due Jan 19**

**Example 3: 21-day period + mail service (served Monday, Jan 1)**
1. Exclude Jan 1 (service day)
2. Count 21 days → Jan 22
3. Add 3 days mail extension → Jan 25 (Thursday)
4. Jan 25 is business day → **Answer due Jan 25**

**Example 4: 90 days before trial (trial Monday, April 1)**
1. Exclude April 1 (trial date)
2. Count backward 90 days → Jan 1 (Monday, New Year's Day)
3. Jan 1 is holiday → **Roll to previous business day: Dec 31**

---

## Common Pitfalls & Traps

### ❌ Mistake: Counting the trigger day
**Wrong**: Complaint served Jan 1, 20 days = Jan 20
**Right**: Complaint served Jan 1, **exclude Jan 1**, 20 days = Jan 21

### ❌ Mistake: Forgetting service extensions
**Wrong**: Served by mail Jan 1, 21 days = Jan 22
**Right**: Served by mail Jan 1, 21 days + 3 = Jan 25

### ❌ Mistake: Not checking for holidays
**Wrong**: 20 days from Dec 15 = Jan 4 (but New Year's Day!)
**Right**: Jan 4 is Saturday, Jan 1 is holiday → Jan 6 (Monday)

### ❌ Mistake: Using wrong calculation for backwards counting
**Wrong**: 30 days before trial (April 1) = March 2
**Right**: **Exclude trial date**, count backward = March 3

### ❌ Mistake: Not accounting for Texas Monday Rule
**Wrong**: Served Jan 1 (Monday), 20 days = Jan 21
**Right**: 20 days after Jan 1 = Jan 21, **next Monday** = Jan 21 (same day) by 10 AM

### ❌ Mistake: Assuming all states have mail extensions
**Wrong**: Georgia complaint + mail service = 30 days + 3
**Right**: Georgia has **no mail service extension** = 30 days only

---

## Testing Checklist

When implementing new jurisdiction rules, test:

- [ ] Standard calculation (no holidays, weekends)
- [ ] Deadline falls on Saturday
- [ ] Deadline falls on Sunday
- [ ] Deadline falls on federal holiday
- [ ] Service by mail (with extension)
- [ ] Service by email (if different)
- [ ] Service by personal delivery
- [ ] Government defendant (if applicable)
- [ ] Backward counting (before trial)
- [ ] Leap year (Feb 29)
- [ ] Year boundary (Dec → Jan)
- [ ] State-specific holidays

---

## Resources for Verification

### Primary Sources
1. **Cornell Legal Information Institute**
   - https://www.law.cornell.edu/rules/frcp
   - https://www.law.cornell.edu/rules/frap

2. **State Court Websites**
   - Search "[State] Supreme Court Rules"
   - Usually under "Courts" or "Rules" section

3. **Practice Guides**
   - State bar associations
   - Legal treatises (Moore's Federal Practice, etc.)

### Calculation Tools (for verification)
- **CourtDays.com** - Free online calculator
- **CompuLaw Vision** - Commercial (competitor)
- **Legal Calendar** - Various state bar apps

---

## Quick Reference: Most Common Deadlines

### Top 10 Most Common (Any Jurisdiction)
1. **Answer to Complaint**: 15-45 days (varies)
2. **Discovery Responses**: 30 days
3. **Summary Judgment Opposition**: 14-30 days (varies)
4. **Notice of Appeal**: 30-60 days
5. **Expert Disclosures**: 90 days before trial
6. **Pretrial Conference**: 14-30 days before trial
7. **Trial Brief**: 7-14 days before trial
8. **Jury Instructions**: 7-14 days before trial
9. **Motion Opposition**: 14-21 days
10. **Reply Brief (Motion)**: 7-14 days

---

## Updates & Maintenance

**Last Updated**: January 2026
**Next Review**: Quarterly (April, July, October, January)

### Change Log
- 2026-01-01: Initial creation with 50 states + federal
- 2025-12-01: Added FRCP 2015 amendments
- 2025-06-19: Added Juneteenth as federal holiday

### How to Report Errors
If you find an incorrect deadline calculation:
1. Open GitHub issue: `litdocket/issues`
2. Tag: `deadline-calculation-error`
3. Include: Jurisdiction, rule citation, expected vs actual
4. Provide source (statute, rule, court order)

---

**⚖️ Legal Disclaimer**: This is a reference guide only. Always verify deadlines against primary sources (statutes, court rules, case law) and consult local counsel. Deadline calculations can vary based on specific circumstances, local rules, and recent rule amendments.
