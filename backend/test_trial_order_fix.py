#!/usr/bin/env python3
"""
Test script to verify the docketing fix for Uniform Trial Orders.
Tests that the rules engine generates countdown deadlines from a trial date trigger.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from datetime import date
from app.services.rules_engine import rules_engine, TriggerType
from app.services.deadline_service import DeadlineService
import asyncio


def test_hardcoded_rules_loaded():
    """Verify hardcoded rules are loaded"""
    print(f"\n{'='*60}")
    print("TEST 1: Hardcoded Rules Loaded")
    print(f"{'='*60}")
    print(f"Rule templates loaded: {len(rules_engine.rule_templates)}")
    for rule_id, rule in rules_engine.rule_templates.items():
        print(f"  - {rule_id}: {rule.name} ({len(rule.dependent_deadlines)} deadlines)")
    assert len(rules_engine.rule_templates) > 0, "FAIL: No rule templates loaded!"
    print("✅ PASS: Hardcoded rules are loaded")


def test_trial_trigger_match():
    """Verify trial order matches trigger"""
    print(f"\n{'='*60}")
    print("TEST 2: Trial Order Trigger Match")
    print(f"{'='*60}")
    result = rules_engine.match_document_to_trigger(
        document_type="Uniform Trial Order",
        jurisdiction="florida_state",
        court_type="civil"
    )
    print(f"  matches_trigger: {result['matches_trigger']}")
    print(f"  trigger_type: {result.get('trigger_type_str')}")
    print(f"  expected_deadlines: {result.get('expected_deadlines')}")
    assert result['matches_trigger'], "FAIL: Uniform Trial Order should match trial trigger!"
    print("✅ PASS: Trial order matches trigger")


def test_trial_deadline_generation():
    """Verify deadline chains generate from trial date"""
    print(f"\n{'='*60}")
    print("TEST 3: Trial Date Deadline Chain Generation")
    print(f"{'='*60}")
    
    trial_date = date(2027, 1, 4)  # From the test PDF
    
    applicable_rules = rules_engine.get_applicable_rules(
        jurisdiction="florida_state",
        court_type="civil",
        trigger_type=TriggerType.TRIAL_DATE
    )
    
    print(f"  Applicable rules found: {len(applicable_rules)}")
    
    all_deadlines = []
    for rule in applicable_rules:
        deadlines = rules_engine.calculate_dependent_deadlines(
            trigger_date=trial_date,
            rule_template=rule,
            service_method="electronic"
        )
        all_deadlines.extend(deadlines)
    
    print(f"  Total deadlines generated: {len(all_deadlines)}")
    print(f"\n  Generated deadlines:")
    for d in sorted(all_deadlines, key=lambda x: x.get('deadline_date') or date.min):
        dd = d.get('deadline_date')
        title = d.get('title', 'Unknown')
        priority = d.get('priority', '?')
        print(f"    {dd}  [{priority:>10}]  {title}")
    
    assert len(all_deadlines) >= 10, f"FAIL: Expected >=10 deadlines, got {len(all_deadlines)}"
    print(f"\n✅ PASS: Generated {len(all_deadlines)} deadlines from trial date")


async def test_deadline_service_chains():
    """Test the full DeadlineService.generate_deadline_chains path"""
    print(f"\n{'='*60}")
    print("TEST 4: DeadlineService.generate_deadline_chains()")
    print(f"{'='*60}")
    
    service = DeadlineService()
    deadlines = await service.generate_deadline_chains(
        trigger_event="trial date set",
        trigger_date=date(2027, 1, 4),
        jurisdiction="florida_state",
        court_type="civil",
        case_id="test-case-123",
        user_id="test-user-456",
        service_method="electronic"
    )
    
    print(f"  DeadlineService generated: {len(deadlines)} deadlines")
    for d in sorted(deadlines, key=lambda x: x.get('deadline_date') or date.min):
        dd = d.get('deadline_date')
        title = d.get('title', 'Unknown')
        print(f"    {dd}  {title}")
    
    assert len(deadlines) >= 10, f"FAIL: Expected >=10, got {len(deadlines)}"
    print(f"\n✅ PASS: DeadlineService generated {len(deadlines)} deadlines")


def test_path_a_fallthrough():
    """Test that check_rules_for_trigger works for trial orders"""
    print(f"\n{'='*60}")
    print("TEST 5: PATH A Trigger Check for Trial Orders")
    print(f"{'='*60}")
    
    service = DeadlineService()
    result = service.check_rules_for_trigger(
        document_type="Uniform Trial Order",
        jurisdiction="florida_state",
        court_type="civil"
    )
    
    print(f"  matches_trigger: {result['matches_trigger']}")
    print(f"  trigger_type: {result.get('trigger_type')}")
    print(f"  expected_deadlines: {result.get('expected_deadlines')}")
    
    assert result['matches_trigger'], "FAIL: Should match trigger"
    assert result['expected_deadlines'] > 0, "FAIL: Should expect >0 deadlines"
    print("✅ PASS: PATH A correctly identifies trial order trigger")


if __name__ == "__main__":
    print("=" * 60)
    print("DOCKET4ME - Trial Order Fix Verification")
    print("=" * 60)
    
    test_hardcoded_rules_loaded()
    test_trial_trigger_match()
    test_trial_deadline_generation()
    asyncio.run(test_deadline_service_chains())
    test_path_a_fallthrough()
    
    print(f"\n{'='*60}")
    print("ALL TESTS PASSED ✅")
    print(f"{'='*60}")
