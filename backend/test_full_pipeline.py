#!/usr/bin/env python3
"""
Full pipeline test: PDF → AI Analysis → Trigger Detection → Deadline Generation
Tests with the actual Uniform Trial Order PDF.
"""
import sys, os, asyncio
sys.path.insert(0, os.path.dirname(__file__))

from datetime import date
from app.services.rules_engine import rules_engine, TriggerType
from app.services.deadline_service import DeadlineService
from app.services.ai_service import AIService
from app.utils.pdf_parser import extract_text_from_pdf


async def test_full_pipeline():
    pdf_path = "/Users/jackson/Downloads/[Local] 2026-01-13 Uniform Trial Order_Setting Case For Trial - General.pdf"
    
    print("=" * 70)
    print("FULL PIPELINE TEST: Uniform Trial Order PDF")
    print("=" * 70)
    
    # Step 1: Extract text
    print("\n📄 Step 1: PDF Text Extraction")
    with open(pdf_path, 'rb') as f:
        text = extract_text_from_pdf(f.read())
    print(f"  Extracted {len(text)} chars")
    
    # Step 2: AI Analysis
    print("\n🤖 Step 2: AI Document Analysis")
    ai = AIService()
    analysis = await ai.analyze_legal_document(text)
    print(f"  document_type: {analysis.get('document_type')}")
    print(f"  case_number: {analysis.get('case_number')}")
    print(f"  court: {analysis.get('court')}")
    print(f"  filing_date: {analysis.get('filing_date')}")
    print(f"  service_date: {analysis.get('service_date')}")
    print(f"  key_dates: {analysis.get('key_dates')}")
    print(f"  deadlines_mentioned: {analysis.get('deadlines_mentioned')}")
    
    # Step 3: Trigger matching
    print("\n🎯 Step 3: Trigger Detection")
    doc_type = analysis.get('document_type', '')
    result = rules_engine.match_document_to_trigger(
        document_type=doc_type,
        jurisdiction="florida_state",
        court_type="civil"
    )
    print(f"  matches_trigger: {result['matches_trigger']}")
    print(f"  trigger_type: {result.get('trigger_type_str')}")
    print(f"  expected_deadlines: {result.get('expected_deadlines')}")
    print(f"  matched_pattern: {result.get('matched_pattern')}")
    
    # Step 4: Trigger date extraction (simulating document_service logic)
    print("\n📅 Step 4: Trigger Date Extraction")
    trigger_type_str = result.get('trigger_type_str', '')
    trigger_date_str = None
    
    if 'trial' in trigger_type_str.lower():
        key_dates = analysis.get('key_dates', [])
        for kd in key_dates:
            desc = (kd.get('description') or '').lower()
            if any(w in desc for w in ['trial', 'trial period', 'trial date', 'trial commenc']):
                trigger_date_str = kd.get('date')
                print(f"  Found trial date in key_dates: {trigger_date_str} ('{kd.get('description')}')")
                break
        
        if not trigger_date_str:
            for dm in analysis.get('deadlines_mentioned', []):
                desc = (dm.get('description') or dm.get('deadline_type') or '').lower()
                if 'trial' in desc:
                    trigger_date_str = dm.get('date')
                    print(f"  Found trial date in deadlines_mentioned: {trigger_date_str}")
                    break
    
    if not trigger_date_str:
        trigger_date_str = analysis.get('service_date') or analysis.get('filing_date')
        print(f"  Fallback to service/filing date: {trigger_date_str}")
    
    print(f"  Final trigger_date: {trigger_date_str}")
    
    expected_trial_date = "2027-01-04"
    if trigger_date_str == expected_trial_date:
        print(f"  ✅ Correct! Trial date is {expected_trial_date}")
    else:
        print(f"  ⚠️  Expected {expected_trial_date}, got {trigger_date_str}")
    
    # Step 5: Generate deadlines
    print("\n⚡ Step 5: Deadline Chain Generation")
    if trigger_date_str and result['matches_trigger']:
        from datetime import datetime
        trigger_date = datetime.strptime(trigger_date_str, '%Y-%m-%d').date()
        
        service = DeadlineService()
        deadlines = await service.generate_deadline_chains(
            trigger_event=trigger_type_str,
            trigger_date=trigger_date,
            jurisdiction="florida_state",
            court_type="civil",
            case_id="test-case",
            user_id="test-user",
            service_method="electronic"
        )
        
        print(f"  Generated {len(deadlines)} deadlines:\n")
        for d in sorted(deadlines, key=lambda x: x.get('deadline_date') or date.min):
            dd = d.get('deadline_date')
            title = d.get('title', '?')
            priority = d.get('priority', '?')
            rule = d.get('rule_citation', '')
            print(f"    {dd}  [{priority:>10}]  {title}")
            if rule:
                print(f"              └─ {rule}")
        
        if len(deadlines) >= 20:
            print(f"\n  ✅ PASS: {len(deadlines)} deadlines generated (expected ≥20)")
        else:
            print(f"\n  ⚠️  Only {len(deadlines)} deadlines (expected ≥20)")
    else:
        print("  ❌ Cannot generate — no trigger match or no date")
    
    print("\n" + "=" * 70)
    print("PIPELINE TEST COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_full_pipeline())
