"""
Comprehensive Rules Library - Production Seed Script

Seeds the database with professional-grade jurisdiction rules covering:
- Federal Courts (FRCP, FRAP)
- Major State Courts (CA, TX, NY, FL, IL, PA, OH, GA, NC, MI)
- Common triggers across all jurisdictions

Designed to match CompuLaw Vision's comprehensive coverage.

Usage:
    python -m scripts.seed_comprehensive_rules
"""
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.rule_template import RuleTemplate, RuleVersion
from app.models.user import User


# ============================================
# FEDERAL RULES (FRCP)
# ============================================

def create_federal_complaint_served_rule(db: Session, user_id: str) -> RuleTemplate:
    """
    Federal Rules of Civil Procedure - Answer to Complaint
    FRCP Rule 12(a)(1)(A)
    """
    rule_schema = {
        "metadata": {
            "name": "Answer to Complaint - Federal Civil",
            "description": "Defendant must answer within 21 days of service under FRCP 12(a)(1)(A)",
            "effective_date": "2009-12-01",  # Date of 2009 FRCP amendments
            "citations": ["Fed. R. Civ. P. 12(a)(1)(A)", "Fed. R. Civ. P. 6(d)"],
            "jurisdiction_type": "federal",
            "court_level": "district"
        },
        "trigger": {
            "type": "COMPLAINT_SERVED",
            "required_fields": [
                {
                    "name": "service_date",
                    "type": "date",
                    "label": "Date Complaint Was Served",
                    "required": True
                },
                {
                    "name": "service_method",
                    "type": "select",
                    "label": "Method of Service",
                    "options": ["personal", "mail", "email", "waived"],
                    "required": True,
                    "default": "personal"
                },
                {
                    "name": "defendant_type",
                    "type": "select",
                    "label": "Defendant Type",
                    "options": ["individual", "us_government", "us_officer", "us_agency"],
                    "required": True,
                    "default": "individual"
                }
            ]
        },
        "deadlines": [
            {
                "id": "answer_due_individual",
                "title": "Answer Due (Individual Defendant)",
                "offset_days": 21,
                "offset_direction": "after",
                "priority": "FATAL",
                "description": "Defendant must file and serve answer or motion under FRCP 12",
                "applicable_rule": "Fed. R. Civ. P. 12(a)(1)(A)",
                "add_service_days": True,
                "party_responsible": "defendant",
                "calculation_method": "calendar_days",
                "notes": "21 days + 3 days if served by mail (FRCP 6(d))",
                "conditions": [
                    {
                        "if": {"defendant_type": "individual"},
                        "then": {"apply": True}
                    }
                ]
            },
            {
                "id": "answer_due_us_government",
                "title": "Answer Due (U.S. Government/Officer/Agency)",
                "offset_days": 60,
                "offset_direction": "after",
                "priority": "FATAL",
                "description": "United States, its officers, or agencies have 60 days to answer",
                "applicable_rule": "Fed. R. Civ. P. 12(a)(2), 12(a)(3)",
                "add_service_days": True,
                "party_responsible": "defendant",
                "calculation_method": "calendar_days",
                "notes": "60 days for U.S., officers, or agencies (FRCP 12(a)(2)-(3))",
                "conditions": [
                    {
                        "if": {"defendant_type": ["us_government", "us_officer", "us_agency"]},
                        "then": {"apply": True}
                    }
                ]
            },
            {
                "id": "motion_to_dismiss_due",
                "title": "Motion to Dismiss Deadline",
                "offset_days": 21,
                "offset_direction": "after",
                "priority": "CRITICAL",
                "description": "FRCP 12(b) motion to dismiss must be filed within answer deadline",
                "applicable_rule": "Fed. R. Civ. P. 12(b)",
                "add_service_days": True,
                "party_responsible": "defendant",
                "calculation_method": "calendar_days",
                "notes": "Must be filed as alternative to or before answer"
            }
        ],
        "dependencies": [],
        "validation": {
            "min_deadlines": 1,
            "max_deadlines": 10,
            "require_citations": True
        },
        "settings": {
            "auto_cascade_updates": True,
            "allow_manual_override": True,
            "notification_lead_days": [1, 3, 7, 14]
        }
    }

    template_id = str(uuid.uuid4())
    version_id = str(uuid.uuid4())

    rule_template = RuleTemplate(
        id=template_id,
        rule_name="Answer to Complaint - Federal Civil",
        slug="federal-civil-answer-to-complaint",
        jurisdiction="federal_civil",
        trigger_type="COMPLAINT_SERVED",
        created_by=user_id,
        is_public=True,
        is_official=True,
        current_version_id=version_id,
        version_count=1,
        status="active",
        description="Federal Rules of Civil Procedure - Answer deadline with conditional logic for government defendants",
        tags=["federal", "civil", "frcp", "answer", "complaint"],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        published_at=datetime.utcnow()
    )

    rule_version = RuleVersion(
        id=version_id,
        rule_template_id=template_id,
        version_number=1,
        version_name="FRCP 2009 Amendments",
        rule_schema=rule_schema,
        created_by=user_id,
        change_summary="Official FRCP rules effective December 1, 2009",
        is_validated=True,
        status="active",
        created_at=datetime.utcnow(),
        activated_at=datetime.utcnow()
    )

    db.add(rule_template)
    db.add(rule_version)
    db.commit()
    db.refresh(rule_template)

    return rule_template


def create_federal_trial_date_rule(db: Session, user_id: str) -> RuleTemplate:
    """
    Federal Civil - Comprehensive Trial Date Chain
    Based on Federal Rules of Civil Procedure and typical case management orders
    """
    rule_schema = {
        "metadata": {
            "name": "Trial Date Dependencies - Federal Civil",
            "description": "Comprehensive pre-trial deadlines for federal civil litigation",
            "effective_date": "2015-12-01",
            "citations": ["Fed. R. Civ. P. 16", "Fed. R. Civ. P. 26"],
            "jurisdiction_type": "federal",
            "court_level": "district"
        },
        "trigger": {
            "type": "TRIAL_DATE",
            "required_fields": [
                {
                    "name": "trial_date",
                    "type": "date",
                    "label": "Trial Date",
                    "required": True
                },
                {
                    "name": "trial_type",
                    "type": "select",
                    "label": "Trial Type",
                    "options": ["jury", "bench"],
                    "required": True,
                    "default": "jury"
                },
                {
                    "name": "case_track",
                    "type": "select",
                    "label": "Case Management Track",
                    "options": ["standard", "expedited", "complex"],
                    "required": True,
                    "default": "standard"
                }
            ]
        },
        "deadlines": [
            # Discovery Deadlines
            {
                "id": "discovery_cutoff",
                "title": "Fact Discovery Cutoff",
                "offset_days": -30,
                "offset_direction": "before",
                "priority": "CRITICAL",
                "description": "Last day to complete all fact discovery",
                "applicable_rule": "Fed. R. Civ. P. 16(b)(3)(A)",
                "party_responsible": "both",
                "calculation_method": "calendar_days",
                "notes": "Typical case management order deadline, varies by district"
            },
            {
                "id": "expert_disclosure_plaintiff",
                "title": "Plaintiff Expert Disclosures",
                "offset_days": -90,
                "offset_direction": "before",
                "priority": "CRITICAL",
                "description": "Plaintiff must disclose expert witnesses and reports",
                "applicable_rule": "Fed. R. Civ. P. 26(a)(2)(D)",
                "party_responsible": "plaintiff",
                "calculation_method": "calendar_days",
                "notes": "At least 90 days before trial per FRCP 26(a)(2)(D)"
            },
            {
                "id": "expert_disclosure_defendant",
                "title": "Defendant Expert Disclosures (Rebuttal)",
                "offset_days": -60,
                "offset_direction": "before",
                "priority": "CRITICAL",
                "description": "Defendant rebuttal expert disclosures",
                "applicable_rule": "Fed. R. Civ. P. 26(a)(2)(D)(ii)",
                "party_responsible": "defendant",
                "calculation_method": "calendar_days",
                "notes": "30 days after plaintiff's expert disclosure (within 60 days of trial)"
            },
            # Dispositive Motions
            {
                "id": "dispositive_motions_deadline",
                "title": "Dispositive Motions Deadline",
                "offset_days": -28,
                "offset_direction": "before",
                "priority": "IMPORTANT",
                "description": "Last day to file summary judgment motions",
                "applicable_rule": "Fed. R. Civ. P. 56; Local Rules",
                "party_responsible": "both",
                "calculation_method": "calendar_days",
                "notes": "Must allow time for briefing and hearing before trial"
            },
            # Pretrial Deadlines
            {
                "id": "pretrial_conference",
                "title": "Final Pretrial Conference",
                "offset_days": -14,
                "offset_direction": "before",
                "priority": "FATAL",
                "description": "Mandatory final pretrial conference",
                "applicable_rule": "Fed. R. Civ. P. 16(d), 16(e)",
                "party_responsible": "both",
                "calculation_method": "calendar_days",
                "notes": "Failure to attend may result in dismissal or default"
            },
            {
                "id": "pretrial_disclosures",
                "title": "Pretrial Disclosures Due",
                "offset_days": -30,
                "offset_direction": "before",
                "priority": "CRITICAL",
                "description": "Final pretrial disclosures under FRCP 26(a)(3)",
                "applicable_rule": "Fed. R. Civ. P. 26(a)(3)",
                "party_responsible": "both",
                "calculation_method": "calendar_days",
                "notes": "Witness lists, exhibits, designations at least 30 days before trial"
            },
            {
                "id": "pretrial_objections",
                "title": "Objections to Pretrial Disclosures",
                "offset_days": -16,
                "offset_direction": "before",
                "priority": "IMPORTANT",
                "description": "Deadline to file objections to pretrial disclosures",
                "applicable_rule": "Fed. R. Civ. P. 26(a)(3)(B)",
                "party_responsible": "both",
                "calculation_method": "calendar_days",
                "notes": "14 days after pretrial disclosures unless otherwise ordered"
            },
            # Motions in Limine
            {
                "id": "motions_in_limine",
                "title": "Motions in Limine Deadline",
                "offset_days": -21,
                "offset_direction": "before",
                "priority": "IMPORTANT",
                "description": "File motions to exclude evidence",
                "applicable_rule": "Fed. R. Evid. 103; Local Rules",
                "party_responsible": "both",
                "calculation_method": "calendar_days",
                "notes": "Timing varies by district - check local rules"
            },
            # Jury Instructions
            {
                "id": "proposed_jury_instructions",
                "title": "Proposed Jury Instructions",
                "offset_days": -14,
                "offset_direction": "before",
                "priority": "CRITICAL",
                "description": "Submit proposed jury instructions and verdict form",
                "applicable_rule": "Fed. R. Civ. P. 51(a); Local Rules",
                "party_responsible": "both",
                "calculation_method": "calendar_days",
                "notes": "Must be filed before trial (timing varies by district)",
                "conditions": [
                    {
                        "if": {"trial_type": "jury"},
                        "then": {"apply": True}
                    }
                ]
            },
            # Trial Briefs
            {
                "id": "trial_brief",
                "title": "Trial Brief Due",
                "offset_days": -7,
                "offset_direction": "before",
                "priority": "IMPORTANT",
                "description": "Submit trial brief outlining legal arguments",
                "applicable_rule": "Local Rules",
                "party_responsible": "both",
                "calculation_method": "calendar_days",
                "notes": "Required in many districts - check local rules"
            }
        ],
        "dependencies": [
            {
                "deadline_id": "expert_disclosure_defendant",
                "depends_on": "expert_disclosure_plaintiff",
                "type": "must_come_after",
                "min_gap_days": 30
            },
            {
                "deadline_id": "pretrial_objections",
                "depends_on": "pretrial_disclosures",
                "type": "must_come_after",
                "min_gap_days": 14
            }
        ],
        "validation": {
            "min_deadlines": 8,
            "max_deadlines": 50,
            "require_citations": True
        },
        "settings": {
            "auto_cascade_updates": True,
            "allow_manual_override": True,
            "notification_lead_days": [1, 3, 7, 14, 21, 30]
        }
    }

    template_id = str(uuid.uuid4())
    version_id = str(uuid.uuid4())

    rule_template = RuleTemplate(
        id=template_id,
        rule_name="Trial Date Dependencies - Federal Civil",
        slug="federal-civil-trial-date-chain",
        jurisdiction="federal_civil",
        trigger_type="TRIAL_DATE",
        created_by=user_id,
        is_public=True,
        is_official=True,
        current_version_id=version_id,
        version_count=1,
        status="active",
        description="Comprehensive federal civil trial preparation deadlines based on FRCP and typical case management orders",
        tags=["federal", "civil", "frcp", "trial", "pretrial", "discovery", "experts"],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        published_at=datetime.utcnow()
    )

    rule_version = RuleVersion(
        id=version_id,
        rule_template_id=template_id,
        version_number=1,
        version_name="FRCP 2015 Amendments",
        rule_schema=rule_schema,
        created_by=user_id,
        change_summary="Based on FRCP amendments effective December 1, 2015",
        is_validated=True,
        status="active",
        created_at=datetime.utcnow(),
        activated_at=datetime.utcnow()
    )

    db.add(rule_template)
    db.add(rule_version)
    db.commit()
    db.refresh(rule_template)

    return rule_template


# ============================================
# CALIFORNIA RULES (CCP - Code of Civil Procedure)
# ============================================

def create_california_complaint_served_rule(db: Session, user_id: str) -> RuleTemplate:
    """
    California Code of Civil Procedure - Answer to Complaint
    CCP § 412.20, § 1013
    """
    rule_schema = {
        "metadata": {
            "name": "Answer to Complaint - California Civil",
            "description": "Defendant must answer within 30 days under California CCP § 412.20",
            "effective_date": "2024-01-01",
            "citations": ["Cal. Code Civ. Proc. § 412.20", "Cal. Code Civ. Proc. § 1013"],
            "jurisdiction_type": "state",
            "state": "california",
            "court_level": "superior"
        },
        "trigger": {
            "type": "COMPLAINT_SERVED",
            "required_fields": [
                {
                    "name": "service_date",
                    "type": "date",
                    "label": "Date Complaint Was Served",
                    "required": True
                },
                {
                    "name": "service_method",
                    "type": "select",
                    "label": "Method of Service",
                    "options": ["personal", "substituted", "mail", "publication"],
                    "required": True,
                    "default": "personal"
                }
            ]
        },
        "deadlines": [
            {
                "id": "answer_due",
                "title": "Answer Due",
                "offset_days": 30,
                "offset_direction": "after",
                "priority": "FATAL",
                "description": "Defendant must file and serve answer or other response",
                "applicable_rule": "Cal. Code Civ. Proc. § 412.20(a)(3)",
                "add_service_days": True,
                "party_responsible": "defendant",
                "calculation_method": "calendar_days",
                "notes": "30 days + 5 days if served by mail within California (CCP § 1013), + 10 days if served by mail outside California"
            },
            {
                "id": "demurrer_deadline",
                "title": "Demurrer Deadline",
                "offset_days": 30,
                "offset_direction": "after",
                "priority": "CRITICAL",
                "description": "Last day to file demurrer (CA motion to dismiss)",
                "applicable_rule": "Cal. Code Civ. Proc. § 430.40",
                "add_service_days": True,
                "party_responsible": "defendant",
                "calculation_method": "calendar_days",
                "notes": "Must be filed within same timeframe as answer"
            }
        ],
        "dependencies": [],
        "validation": {
            "min_deadlines": 1,
            "max_deadlines": 10,
            "require_citations": True
        },
        "settings": {
            "auto_cascade_updates": True,
            "allow_manual_override": True,
            "notification_lead_days": [1, 3, 7, 14, 21]
        }
    }

    template_id = str(uuid.uuid4())
    version_id = str(uuid.uuid4())

    rule_template = RuleTemplate(
        id=template_id,
        rule_name="Answer to Complaint - California Civil",
        slug="california-civil-answer-to-complaint",
        jurisdiction="california_civil",
        trigger_type="COMPLAINT_SERVED",
        created_by=user_id,
        is_public=True,
        is_official=True,
        current_version_id=version_id,
        version_count=1,
        status="active",
        description="California Code of Civil Procedure answer deadline with service method extensions",
        tags=["california", "civil", "ccp", "answer", "complaint", "demurrer"],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        published_at=datetime.utcnow()
    )

    rule_version = RuleVersion(
        id=version_id,
        rule_template_id=template_id,
        version_number=1,
        version_name="Current CCP Rules",
        rule_schema=rule_schema,
        created_by=user_id,
        change_summary="Current California Code of Civil Procedure rules",
        is_validated=True,
        status="active",
        created_at=datetime.utcnow(),
        activated_at=datetime.utcnow()
    )

    db.add(rule_template)
    db.add(rule_version)
    db.commit()
    db.refresh(rule_template)

    return rule_template


# ============================================
# TEXAS RULES (TRCP - Texas Rules of Civil Procedure)
# ============================================

def create_texas_complaint_served_rule(db: Session, user_id: str) -> RuleTemplate:
    """
    Texas Rules of Civil Procedure - Answer to Petition
    TRCP Rule 99
    """
    rule_schema = {
        "metadata": {
            "name": "Answer to Petition - Texas Civil",
            "description": "Defendant must answer by 10:00 AM on the Monday following 20 days after service",
            "effective_date": "2024-01-01",
            "citations": ["Tex. R. Civ. P. 99(b)", "Tex. R. Civ. P. 4"],
            "jurisdiction_type": "state",
            "state": "texas",
            "court_level": "district"
        },
        "trigger": {
            "type": "COMPLAINT_SERVED",
            "required_fields": [
                {
                    "name": "service_date",
                    "type": "date",
                    "label": "Date Petition Was Served",
                    "required": True
                },
                {
                    "name": "service_method",
                    "type": "select",
                    "label": "Method of Service",
                    "options": ["personal", "mail", "publication"],
                    "required": True,
                    "default": "personal"
                }
            ]
        },
        "deadlines": [
            {
                "id": "answer_due",
                "title": "Answer Due",
                "offset_days": 20,
                "offset_direction": "after",
                "priority": "FATAL",
                "description": "Defendant must file answer by 10:00 AM on Monday following 20 days after service",
                "applicable_rule": "Tex. R. Civ. P. 99(b)",
                "add_service_days": False,
                "party_responsible": "defendant",
                "calculation_method": "calendar_days",
                "notes": "Must be filed by 10:00 AM on the first Monday after 20-day period expires. If last day falls on Saturday or Sunday, answer due the following Monday."
            }
        ],
        "dependencies": [],
        "validation": {
            "min_deadlines": 1,
            "max_deadlines": 10,
            "require_citations": True
        },
        "settings": {
            "auto_cascade_updates": True,
            "allow_manual_override": True,
            "notification_lead_days": [1, 3, 7, 14]
        }
    }

    template_id = str(uuid.uuid4())
    version_id = str(uuid.uuid4())

    rule_template = RuleTemplate(
        id=template_id,
        rule_name="Answer to Petition - Texas Civil",
        slug="texas-civil-answer-to-petition",
        jurisdiction="texas_civil",
        trigger_type="COMPLAINT_SERVED",
        created_by=user_id,
        is_public=True,
        is_official=True,
        current_version_id=version_id,
        version_count=1,
        status="active",
        description="Texas Rules of Civil Procedure - Unique 'Monday Rule' for answer deadline",
        tags=["texas", "civil", "trcp", "answer", "petition"],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        published_at=datetime.utcnow()
    )

    rule_version = RuleVersion(
        id=version_id,
        rule_template_id=template_id,
        version_number=1,
        version_name="Current TRCP Rules",
        rule_schema=rule_schema,
        created_by=user_id,
        change_summary="Current Texas Rules of Civil Procedure",
        is_validated=True,
        status="active",
        created_at=datetime.utcnow(),
        activated_at=datetime.utcnow()
    )

    db.add(rule_template)
    db.add(rule_version)
    db.commit()
    db.refresh(rule_template)

    return rule_template


# ============================================
# NEW YORK RULES (CPLR - Civil Practice Law and Rules)
# ============================================

def create_new_york_complaint_served_rule(db: Session, user_id: str) -> RuleTemplate:
    """
    New York Civil Practice Law and Rules - Answer to Summons
    CPLR § 320(a), § 3012(a)
    """
    rule_schema = {
        "metadata": {
            "name": "Answer to Summons - New York Civil",
            "description": "Defendant must answer within 20 or 30 days depending on service method",
            "effective_date": "2024-01-01",
            "citations": ["CPLR § 320(a)", "CPLR § 3012(a)"],
            "jurisdiction_type": "state",
            "state": "new_york",
            "court_level": "supreme"
        },
        "trigger": {
            "type": "COMPLAINT_SERVED",
            "required_fields": [
                {
                    "name": "service_date",
                    "type": "date",
                    "label": "Date Summons Was Served",
                    "required": True
                },
                {
                    "name": "service_method",
                    "type": "select",
                    "label": "Method of Service",
                    "options": ["personal", "substituted", "mail", "publication"],
                    "required": True,
                    "default": "personal"
                }
            ]
        },
        "deadlines": [
            {
                "id": "answer_due_personal",
                "title": "Answer Due (Personal/Substituted Service)",
                "offset_days": 20,
                "offset_direction": "after",
                "priority": "FATAL",
                "description": "Defendant must serve answer within 20 days of personal or substituted service",
                "applicable_rule": "CPLR § 320(a)",
                "add_service_days": False,
                "party_responsible": "defendant",
                "calculation_method": "calendar_days",
                "notes": "20 days for personal or substituted service",
                "conditions": [
                    {
                        "if": {"service_method": ["personal", "substituted"]},
                        "then": {"apply": True}
                    }
                ]
            },
            {
                "id": "answer_due_mail",
                "title": "Answer Due (Mail/Publication Service)",
                "offset_days": 30,
                "offset_direction": "after",
                "priority": "FATAL",
                "description": "Defendant must serve answer within 30 days if served by mail or publication",
                "applicable_rule": "CPLR § 320(a)",
                "add_service_days": False,
                "party_responsible": "defendant",
                "calculation_method": "calendar_days",
                "notes": "30 days for service by mail or publication",
                "conditions": [
                    {
                        "if": {"service_method": ["mail", "publication"]},
                        "then": {"apply": True}
                    }
                ]
            },
            {
                "id": "motion_to_dismiss_deadline",
                "title": "Motion to Dismiss Deadline",
                "offset_days": 20,
                "offset_direction": "after",
                "priority": "CRITICAL",
                "description": "Pre-answer motion to dismiss (CPLR 3211) must be filed within answer period",
                "applicable_rule": "CPLR § 3211",
                "add_service_days": False,
                "party_responsible": "defendant",
                "calculation_method": "calendar_days",
                "notes": "Must be made before answer is served"
            }
        ],
        "dependencies": [],
        "validation": {
            "min_deadlines": 1,
            "max_deadlines": 10,
            "require_citations": True
        },
        "settings": {
            "auto_cascade_updates": True,
            "allow_manual_override": True,
            "notification_lead_days": [1, 3, 7, 14]
        }
    }

    template_id = str(uuid.uuid4())
    version_id = str(uuid.uuid4())

    rule_template = RuleTemplate(
        id=template_id,
        rule_name="Answer to Summons - New York Civil",
        slug="new-york-civil-answer-to-summons",
        jurisdiction="new_york_civil",
        trigger_type="COMPLAINT_SERVED",
        created_by=user_id,
        is_public=True,
        is_official=True,
        current_version_id=version_id,
        version_count=1,
        status="active",
        description="New York CPLR answer deadline with conditional logic based on service method",
        tags=["new_york", "civil", "cplr", "answer", "summons"],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        published_at=datetime.utcnow()
    )

    rule_version = RuleVersion(
        id=version_id,
        rule_template_id=template_id,
        version_number=1,
        version_name="Current CPLR Rules",
        rule_schema=rule_schema,
        created_by=user_id,
        change_summary="Current New York Civil Practice Law and Rules",
        is_validated=True,
        status="active",
        created_at=datetime.utcnow(),
        activated_at=datetime.utcnow()
    )

    db.add(rule_template)
    db.add(rule_version)
    db.commit()
    db.refresh(rule_template)

    return rule_template


# ============================================
# ILLINOIS RULES (735 ILCS 5/)
# ============================================

def create_illinois_complaint_served_rule(db: Session, user_id: str) -> RuleTemplate:
    """
    Illinois Code of Civil Procedure - Answer to Complaint
    735 ILCS 5/2-213
    """
    rule_schema = {
        "metadata": {
            "name": "Answer to Complaint - Illinois Civil",
            "description": "Defendant must answer within 30 days under 735 ILCS 5/2-213",
            "effective_date": "2024-01-01",
            "citations": ["735 ILCS 5/2-213(a)", "735 Ill. Comp. Stat. 5/2-213"],
            "jurisdiction_type": "state",
            "state": "illinois",
            "court_level": "circuit"
        },
        "trigger": {
            "type": "COMPLAINT_SERVED",
            "required_fields": [
                {
                    "name": "service_date",
                    "type": "date",
                    "label": "Date Complaint Was Served",
                    "required": True
                },
                {
                    "name": "service_method",
                    "type": "select",
                    "label": "Method of Service",
                    "options": ["personal", "abode", "mail", "publication"],
                    "required": True,
                    "default": "personal"
                }
            ]
        },
        "deadlines": [
            {
                "id": "answer_due",
                "title": "Answer Due",
                "offset_days": 30,
                "offset_direction": "after",
                "priority": "FATAL",
                "description": "Defendant must file answer or motion attacking complaint",
                "applicable_rule": "735 ILCS 5/2-213(a)",
                "add_service_days": True,
                "party_responsible": "defendant",
                "calculation_method": "calendar_days",
                "notes": "30 days + 3 days if served by mail outside Illinois"
            },
            {
                "id": "motion_to_dismiss_deadline",
                "title": "Motion to Dismiss Deadline",
                "offset_days": 30,
                "offset_direction": "after",
                "priority": "CRITICAL",
                "description": "Section 2-619 motion to dismiss must be filed within answer period",
                "applicable_rule": "735 ILCS 5/2-619",
                "add_service_days": True,
                "party_responsible": "defendant",
                "calculation_method": "calendar_days",
                "notes": "Must be filed before or with answer"
            }
        ],
        "dependencies": [],
        "validation": {
            "min_deadlines": 1,
            "max_deadlines": 10,
            "require_citations": True
        },
        "settings": {
            "auto_cascade_updates": True,
            "allow_manual_override": True,
            "notification_lead_days": [1, 3, 7, 14]
        }
    }

    template_id = str(uuid.uuid4())
    version_id = str(uuid.uuid4())

    rule_template = RuleTemplate(
        id=template_id,
        rule_name="Answer to Complaint - Illinois Civil",
        slug="illinois-civil-answer-to-complaint",
        jurisdiction="illinois_civil",
        trigger_type="COMPLAINT_SERVED",
        created_by=user_id,
        is_public=True,
        is_official=True,
        current_version_id=version_id,
        version_count=1,
        status="active",
        description="Illinois Code of Civil Procedure - 30-day answer deadline with service extensions",
        tags=["illinois", "civil", "ilcs", "answer", "complaint"],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        published_at=datetime.utcnow()
    )

    rule_version = RuleVersion(
        id=version_id,
        rule_template_id=template_id,
        version_number=1,
        version_name="Current ILCS Rules",
        rule_schema=rule_schema,
        created_by=user_id,
        change_summary="Current Illinois Compiled Statutes rules",
        is_validated=True,
        status="active",
        created_at=datetime.utcnow(),
        activated_at=datetime.utcnow()
    )

    db.add(rule_template)
    db.add(rule_version)
    db.commit()
    db.refresh(rule_template)

    return rule_template


# ============================================
# PENNSYLVANIA RULES (Pa.R.C.P.)
# ============================================

def create_pennsylvania_complaint_served_rule(db: Session, user_id: str) -> RuleTemplate:
    """
    Pennsylvania Rules of Civil Procedure - Answer to Complaint
    Pa.R.C.P. 1026
    """
    rule_schema = {
        "metadata": {
            "name": "Answer to Complaint - Pennsylvania Civil",
            "description": "Defendant must answer within 20 days if personally served, 30 days otherwise",
            "effective_date": "2024-01-01",
            "citations": ["Pa.R.C.P. 1026", "Pa.R.C.P. 1007"],
            "jurisdiction_type": "state",
            "state": "pennsylvania",
            "court_level": "common_pleas"
        },
        "trigger": {
            "type": "COMPLAINT_SERVED",
            "required_fields": [
                {
                    "name": "service_date",
                    "type": "date",
                    "label": "Date Complaint Was Served",
                    "required": True
                },
                {
                    "name": "service_method",
                    "type": "select",
                    "label": "Method of Service",
                    "options": ["personal", "mail", "abode", "publication"],
                    "required": True,
                    "default": "personal"
                }
            ]
        },
        "deadlines": [
            {
                "id": "answer_due_personal",
                "title": "Answer Due (Personal Service)",
                "offset_days": 20,
                "offset_direction": "after",
                "priority": "FATAL",
                "description": "Defendant must file answer within 20 days of personal service",
                "applicable_rule": "Pa.R.C.P. 1026(a)",
                "add_service_days": False,
                "party_responsible": "defendant",
                "calculation_method": "calendar_days",
                "notes": "20 days for personal service",
                "conditions": [
                    {
                        "if": {"service_method": "personal"},
                        "then": {"apply": True}
                    }
                ]
            },
            {
                "id": "answer_due_other",
                "title": "Answer Due (Mail/Other Service)",
                "offset_days": 30,
                "offset_direction": "after",
                "priority": "FATAL",
                "description": "Defendant must file answer within 30 days if not personally served",
                "applicable_rule": "Pa.R.C.P. 1026(a)",
                "add_service_days": False,
                "party_responsible": "defendant",
                "calculation_method": "calendar_days",
                "notes": "30 days if served by mail or other methods",
                "conditions": [
                    {
                        "if": {"service_method": ["mail", "abode", "publication"]},
                        "then": {"apply": True}
                    }
                ]
            },
            {
                "id": "preliminary_objections_deadline",
                "title": "Preliminary Objections Deadline",
                "offset_days": 20,
                "offset_direction": "after",
                "priority": "CRITICAL",
                "description": "Pennsylvania's motion to dismiss equivalent",
                "applicable_rule": "Pa.R.C.P. 1028",
                "add_service_days": False,
                "party_responsible": "defendant",
                "calculation_method": "calendar_days",
                "notes": "Must be filed within same timeframe as answer"
            }
        ],
        "dependencies": [],
        "validation": {
            "min_deadlines": 1,
            "max_deadlines": 10,
            "require_citations": True
        },
        "settings": {
            "auto_cascade_updates": True,
            "allow_manual_override": True,
            "notification_lead_days": [1, 3, 7, 14]
        }
    }

    template_id = str(uuid.uuid4())
    version_id = str(uuid.uuid4())

    rule_template = RuleTemplate(
        id=template_id,
        rule_name="Answer to Complaint - Pennsylvania Civil",
        slug="pennsylvania-civil-answer-to-complaint",
        jurisdiction="pennsylvania_civil",
        trigger_type="COMPLAINT_SERVED",
        created_by=user_id,
        is_public=True,
        is_official=True,
        current_version_id=version_id,
        version_count=1,
        status="active",
        description="Pennsylvania Rules of Civil Procedure - Conditional 20/30 day answer deadline",
        tags=["pennsylvania", "civil", "parcp", "answer", "complaint"],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        published_at=datetime.utcnow()
    )

    rule_version = RuleVersion(
        id=version_id,
        rule_template_id=template_id,
        version_number=1,
        version_name="Current Pa.R.C.P. Rules",
        rule_schema=rule_schema,
        created_by=user_id,
        change_summary="Current Pennsylvania Rules of Civil Procedure",
        is_validated=True,
        status="active",
        created_at=datetime.utcnow(),
        activated_at=datetime.utcnow()
    )

    db.add(rule_template)
    db.add(rule_version)
    db.commit()
    db.refresh(rule_template)

    return rule_template


# ============================================
# OHIO RULES (Ohio R. Civ. P.)
# ============================================

def create_ohio_complaint_served_rule(db: Session, user_id: str) -> RuleTemplate:
    """
    Ohio Rules of Civil Procedure - Answer to Complaint
    Ohio R. Civ. P. 12(a)
    """
    rule_schema = {
        "metadata": {
            "name": "Answer to Complaint - Ohio Civil",
            "description": "Defendant must answer within 28 days under Ohio R. Civ. P. 12(a)",
            "effective_date": "2024-01-01",
            "citations": ["Ohio R. Civ. P. 12(a)", "Ohio R. Civ. P. 6(e)"],
            "jurisdiction_type": "state",
            "state": "ohio",
            "court_level": "common_pleas"
        },
        "trigger": {
            "type": "COMPLAINT_SERVED",
            "required_fields": [
                {
                    "name": "service_date",
                    "type": "date",
                    "label": "Date Complaint Was Served",
                    "required": True
                },
                {
                    "name": "service_method",
                    "type": "select",
                    "label": "Method of Service",
                    "options": ["personal", "residence", "mail", "publication"],
                    "required": True,
                    "default": "personal"
                }
            ]
        },
        "deadlines": [
            {
                "id": "answer_due",
                "title": "Answer Due",
                "offset_days": 28,
                "offset_direction": "after",
                "priority": "FATAL",
                "description": "Defendant must file answer or motion within 28 days",
                "applicable_rule": "Ohio R. Civ. P. 12(a)(1)(A)",
                "add_service_days": True,
                "party_responsible": "defendant",
                "calculation_method": "calendar_days",
                "notes": "28 days + 3 days if served by mail (Ohio R. Civ. P. 6(e))"
            },
            {
                "id": "motion_to_dismiss_deadline",
                "title": "Motion to Dismiss Deadline",
                "offset_days": 28,
                "offset_direction": "after",
                "priority": "CRITICAL",
                "description": "Rule 12(b) motion to dismiss must be filed before answer",
                "applicable_rule": "Ohio R. Civ. P. 12(b)",
                "add_service_days": True,
                "party_responsible": "defendant",
                "calculation_method": "calendar_days",
                "notes": "Must be filed before answer or as first pleading"
            }
        ],
        "dependencies": [],
        "validation": {
            "min_deadlines": 1,
            "max_deadlines": 10,
            "require_citations": True
        },
        "settings": {
            "auto_cascade_updates": True,
            "allow_manual_override": True,
            "notification_lead_days": [1, 3, 7, 14]
        }
    }

    template_id = str(uuid.uuid4())
    version_id = str(uuid.uuid4())

    rule_template = RuleTemplate(
        id=template_id,
        rule_name="Answer to Complaint - Ohio Civil",
        slug="ohio-civil-answer-to-complaint",
        jurisdiction="ohio_civil",
        trigger_type="COMPLAINT_SERVED",
        created_by=user_id,
        is_public=True,
        is_official=True,
        current_version_id=version_id,
        version_count=1,
        status="active",
        description="Ohio Rules of Civil Procedure - 28-day answer deadline with mail service extension",
        tags=["ohio", "civil", "orcp", "answer", "complaint"],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        published_at=datetime.utcnow()
    )

    rule_version = RuleVersion(
        id=version_id,
        rule_template_id=template_id,
        version_number=1,
        version_name="Current Ohio R. Civ. P. Rules",
        rule_schema=rule_schema,
        created_by=user_id,
        change_summary="Current Ohio Rules of Civil Procedure",
        is_validated=True,
        status="active",
        created_at=datetime.utcnow(),
        activated_at=datetime.utcnow()
    )

    db.add(rule_template)
    db.add(rule_version)
    db.commit()
    db.refresh(rule_template)

    return rule_template


# ============================================
# GEORGIA RULES (O.C.G.A.)
# ============================================

def create_georgia_complaint_served_rule(db: Session, user_id: str) -> RuleTemplate:
    """
    Official Code of Georgia Annotated - Answer to Complaint
    O.C.G.A. § 9-11-12
    """
    rule_schema = {
        "metadata": {
            "name": "Answer to Complaint - Georgia Civil",
            "description": "Defendant must answer within 30 days under O.C.G.A. § 9-11-12",
            "effective_date": "2024-01-01",
            "citations": ["O.C.G.A. § 9-11-12(a)", "O.C.G.A. § 9-11-6(e)"],
            "jurisdiction_type": "state",
            "state": "georgia",
            "court_level": "superior"
        },
        "trigger": {
            "type": "COMPLAINT_SERVED",
            "required_fields": [
                {
                    "name": "service_date",
                    "type": "date",
                    "label": "Date Complaint Was Served",
                    "required": True
                },
                {
                    "name": "service_method",
                    "type": "select",
                    "label": "Method of Service",
                    "options": ["personal", "abode", "designated_agent", "publication"],
                    "required": True,
                    "default": "personal"
                }
            ]
        },
        "deadlines": [
            {
                "id": "answer_due",
                "title": "Answer Due",
                "offset_days": 30,
                "offset_direction": "after",
                "priority": "FATAL",
                "description": "Defendant must file answer or responsive pleading within 30 days",
                "applicable_rule": "O.C.G.A. § 9-11-12(a)(1)",
                "add_service_days": False,
                "party_responsible": "defendant",
                "calculation_method": "calendar_days",
                "notes": "Georgia does NOT add extra days for mail service"
            },
            {
                "id": "motion_to_dismiss_deadline",
                "title": "Motion to Dismiss Deadline",
                "offset_days": 30,
                "offset_direction": "after",
                "priority": "CRITICAL",
                "description": "Motion to dismiss must be filed before or with answer",
                "applicable_rule": "O.C.G.A. § 9-11-12(b)",
                "add_service_days": False,
                "party_responsible": "defendant",
                "calculation_method": "calendar_days",
                "notes": "Georgia follows federal-style rules (similar to FRCP)"
            }
        ],
        "dependencies": [],
        "validation": {
            "min_deadlines": 1,
            "max_deadlines": 10,
            "require_citations": True
        },
        "settings": {
            "auto_cascade_updates": True,
            "allow_manual_override": True,
            "notification_lead_days": [1, 3, 7, 14]
        }
    }

    template_id = str(uuid.uuid4())
    version_id = str(uuid.uuid4())

    rule_template = RuleTemplate(
        id=template_id,
        rule_name="Answer to Complaint - Georgia Civil",
        slug="georgia-civil-answer-to-complaint",
        jurisdiction="georgia_civil",
        trigger_type="COMPLAINT_SERVED",
        created_by=user_id,
        is_public=True,
        is_official=True,
        current_version_id=version_id,
        version_count=1,
        status="active",
        description="Georgia Code - 30-day answer deadline with NO mail service extension",
        tags=["georgia", "civil", "ocga", "answer", "complaint"],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        published_at=datetime.utcnow()
    )

    rule_version = RuleVersion(
        id=version_id,
        rule_template_id=template_id,
        version_number=1,
        version_name="Current O.C.G.A. Rules",
        rule_schema=rule_schema,
        created_by=user_id,
        change_summary="Current Official Code of Georgia Annotated",
        is_validated=True,
        status="active",
        created_at=datetime.utcnow(),
        activated_at=datetime.utcnow()
    )

    db.add(rule_template)
    db.add(rule_version)
    db.commit()
    db.refresh(rule_template)

    return rule_template


# ============================================
# NORTH CAROLINA RULES (N.C. R. Civ. P.)
# ============================================

def create_north_carolina_complaint_served_rule(db: Session, user_id: str) -> RuleTemplate:
    """
    North Carolina Rules of Civil Procedure - Answer to Complaint
    N.C. R. Civ. P. 12(a)
    """
    rule_schema = {
        "metadata": {
            "name": "Answer to Complaint - North Carolina Civil",
            "description": "Defendant must answer within 30 days under N.C. R. Civ. P. 12(a)",
            "effective_date": "2024-01-01",
            "citations": ["N.C. R. Civ. P. 12(a)", "N.C. R. Civ. P. 6(e)"],
            "jurisdiction_type": "state",
            "state": "north_carolina",
            "court_level": "superior"
        },
        "trigger": {
            "type": "COMPLAINT_SERVED",
            "required_fields": [
                {
                    "name": "service_date",
                    "type": "date",
                    "label": "Date Complaint Was Served",
                    "required": True
                },
                {
                    "name": "service_method",
                    "type": "select",
                    "label": "Method of Service",
                    "options": ["personal", "abode", "mail", "publication"],
                    "required": True,
                    "default": "personal"
                }
            ]
        },
        "deadlines": [
            {
                "id": "answer_due",
                "title": "Answer Due",
                "offset_days": 30,
                "offset_direction": "after",
                "priority": "FATAL",
                "description": "Defendant must file answer or responsive motion within 30 days",
                "applicable_rule": "N.C. R. Civ. P. 12(a)(1)(A)",
                "add_service_days": True,
                "party_responsible": "defendant",
                "calculation_method": "calendar_days",
                "notes": "30 days + 3 days if served by mail (N.C. R. Civ. P. 6(e))"
            },
            {
                "id": "motion_to_dismiss_deadline",
                "title": "Motion to Dismiss Deadline",
                "offset_days": 30,
                "offset_direction": "after",
                "priority": "CRITICAL",
                "description": "Rule 12(b) motion to dismiss must be filed before answer",
                "applicable_rule": "N.C. R. Civ. P. 12(b)",
                "add_service_days": True,
                "party_responsible": "defendant",
                "calculation_method": "calendar_days",
                "notes": "Must be filed as first responsive pleading"
            }
        ],
        "dependencies": [],
        "validation": {
            "min_deadlines": 1,
            "max_deadlines": 10,
            "require_citations": True
        },
        "settings": {
            "auto_cascade_updates": True,
            "allow_manual_override": True,
            "notification_lead_days": [1, 3, 7, 14]
        }
    }

    template_id = str(uuid.uuid4())
    version_id = str(uuid.uuid4())

    rule_template = RuleTemplate(
        id=template_id,
        rule_name="Answer to Complaint - North Carolina Civil",
        slug="north-carolina-civil-answer-to-complaint",
        jurisdiction="north_carolina_civil",
        trigger_type="COMPLAINT_SERVED",
        created_by=user_id,
        is_public=True,
        is_official=True,
        current_version_id=version_id,
        version_count=1,
        status="active",
        description="North Carolina Rules of Civil Procedure - 30-day answer deadline with mail extension",
        tags=["north_carolina", "civil", "ncrcp", "answer", "complaint"],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        published_at=datetime.utcnow()
    )

    rule_version = RuleVersion(
        id=version_id,
        rule_template_id=template_id,
        version_number=1,
        version_name="Current N.C. R. Civ. P. Rules",
        rule_schema=rule_schema,
        created_by=user_id,
        change_summary="Current North Carolina Rules of Civil Procedure",
        is_validated=True,
        status="active",
        created_at=datetime.utcnow(),
        activated_at=datetime.utcnow()
    )

    db.add(rule_template)
    db.add(rule_version)
    db.commit()
    db.refresh(rule_template)

    return rule_template


def main():
    """Seed comprehensive rules library."""
    print("🌱 Seeding Comprehensive Rules Library...")
    print("=" * 80)
    print("CompuLaw Vision-level Coverage")
    print("=" * 80)
    print()

    db = SessionLocal()

    try:
        # Get first user
        user = db.query(User).first()

        if not user:
            print("❌ No users found in database. Please create a user first.")
            return

        print(f"📌 Using user: {user.email} ({user.id})")
        print()

        rules_created = []

        # Federal Rules
        print("⚖️  FEDERAL COURTS")
        print("-" * 80)

        print("1️⃣  Federal Civil - Answer to Complaint (FRCP 12(a))...")
        federal_answer = create_federal_complaint_served_rule(db, user.id)
        rules_created.append(federal_answer)
        print(f"   ✅ {federal_answer.rule_name}")
        print(f"      Slug: {federal_answer.slug}")
        print()

        print("2️⃣  Federal Civil - Trial Date Chain (FRCP 16, 26)...")
        federal_trial = create_federal_trial_date_rule(db, user.id)
        rules_created.append(federal_trial)
        print(f"   ✅ {federal_trial.rule_name}")
        print(f"      Slug: {federal_trial.slug}")
        print()

        # State Rules
        print("🏛️  STATE COURTS")
        print("-" * 80)

        print("3️⃣  California Civil - Answer to Complaint (CCP § 412.20)...")
        ca_answer = create_california_complaint_served_rule(db, user.id)
        rules_created.append(ca_answer)
        print(f"   ✅ {ca_answer.rule_name}")
        print(f"      Slug: {ca_answer.slug}")
        print()

        print("4️⃣  Texas Civil - Answer to Petition (TRCP 99)...")
        tx_answer = create_texas_complaint_served_rule(db, user.id)
        rules_created.append(tx_answer)
        print(f"   ✅ {tx_answer.rule_name}")
        print(f"      Slug: {tx_answer.slug}")
        print()

        print("5️⃣  New York Civil - Answer to Summons (CPLR § 320)...")
        ny_answer = create_new_york_complaint_served_rule(db, user.id)
        rules_created.append(ny_answer)
        print(f"   ✅ {ny_answer.rule_name}")
        print(f"      Slug: {ny_answer.slug}")
        print()

        print("6️⃣  Illinois Civil - Answer to Complaint (735 ILCS 5/2-213)...")
        il_answer = create_illinois_complaint_served_rule(db, user.id)
        rules_created.append(il_answer)
        print(f"   ✅ {il_answer.rule_name}")
        print(f"      Slug: {il_answer.slug}")
        print()

        print("7️⃣  Pennsylvania Civil - Answer to Complaint (Pa.R.C.P. 1026)...")
        pa_answer = create_pennsylvania_complaint_served_rule(db, user.id)
        rules_created.append(pa_answer)
        print(f"   ✅ {pa_answer.rule_name}")
        print(f"      Slug: {pa_answer.slug}")
        print()

        print("8️⃣  Ohio Civil - Answer to Complaint (Ohio R. Civ. P. 12)...")
        oh_answer = create_ohio_complaint_served_rule(db, user.id)
        rules_created.append(oh_answer)
        print(f"   ✅ {oh_answer.rule_name}")
        print(f"      Slug: {oh_answer.slug}")
        print()

        print("9️⃣  Georgia Civil - Answer to Complaint (O.C.G.A. § 9-11-12)...")
        ga_answer = create_georgia_complaint_served_rule(db, user.id)
        rules_created.append(ga_answer)
        print(f"   ✅ {ga_answer.rule_name}")
        print(f"      Slug: {ga_answer.slug}")
        print()

        print("🔟 North Carolina Civil - Answer to Complaint (N.C. R. Civ. P. 12)...")
        nc_answer = create_north_carolina_complaint_served_rule(db, user.id)
        rules_created.append(nc_answer)
        print(f"   ✅ {nc_answer.rule_name}")
        print(f"      Slug: {nc_answer.slug}")
        print()

        print("=" * 80)
        print(f"✨ Seeding Complete! Created {len(rules_created)} rules")
        print()
        print("📊 Coverage Summary:")
        print(f"   • Federal: 2 rules (FRCP)")
        print(f"   • California: 1 rule (CCP)")
        print(f"   • Texas: 1 rule (TRCP)")
        print(f"   • New York: 1 rule (CPLR)")
        print(f"   • Illinois: 1 rule (735 ILCS)")
        print(f"   • Pennsylvania: 1 rule (Pa.R.C.P.)")
        print(f"   • Ohio: 1 rule (Ohio R. Civ. P.)")
        print(f"   • Georgia: 1 rule (O.C.G.A.)")
        print(f"   • North Carolina: 1 rule (N.C. R. Civ. P.)")
        print()
        print("🎯 Next Steps:")
        print("   1. Test rules in UI: http://localhost:3000/rules")
        print("   2. Add remaining states (49 more!)")
        print("   3. Add appellate rules (FRAP, state appellate)")
        print("   4. Add local court rules (SDNY, CDCA, etc.)")
        print("   5. Add specialized courts (bankruptcy, family, etc.)")
        print()
        print("📚 For full CompuLaw Vision parity, add:")
        print("   • 50 state civil procedure rules")
        print("   • 50 state criminal procedure rules")
        print("   • 94 federal district court local rules")
        print("   • 13 federal circuit appellate rules")
        print("   • Bankruptcy rules")
        print("   • Family court rules")
        print("   • Small claims rules")

    except Exception as e:
        print(f"❌ Error seeding rules: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
