"""
Seed Data: CompuLaw-style Rule Sets for Florida Courts

Based on CompuLaw's Florida court rule structure:
- Florida Circuit Court (general jurisdiction)
- Florida County Court (limited jurisdiction)
- Florida District Courts of Appeal
- Florida Supreme Court
- U.S. District Courts (S.D. Fla, M.D. Fla, N.D. Fla)
- U.S. Bankruptcy Courts
"""
import uuid
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from app.models.jurisdiction import (
    Jurisdiction, RuleSet, RuleSetDependency, CourtLocation,
    RuleTemplate, RuleTemplateDeadline,
    JurisdictionType, CourtType, DependencyType, TriggerType,
    DeadlinePriority, CalculationMethod
)


def seed_jurisdictions(db: Session) -> Dict[str, Jurisdiction]:
    """Create base jurisdictions"""

    jurisdictions = {}

    # Federal jurisdiction (parent)
    fed = Jurisdiction(
        id=str(uuid.uuid4()),
        code="FED",
        name="Federal Courts",
        description="United States Federal Court System",
        jurisdiction_type=JurisdictionType.FEDERAL,
        state=None,
        federal_circuit=None
    )
    db.add(fed)
    jurisdictions["FED"] = fed

    # 11th Circuit (Federal)
    fed_11 = Jurisdiction(
        id=str(uuid.uuid4()),
        code="FED-11CIR",
        name="Eleventh Circuit Court of Appeals",
        description="Federal appellate court covering Alabama, Florida, Georgia",
        jurisdiction_type=JurisdictionType.APPELLATE,
        parent_jurisdiction_id=fed.id,
        federal_circuit=11
    )
    db.add(fed_11)
    jurisdictions["FED-11CIR"] = fed_11

    # Florida State (parent)
    fl = Jurisdiction(
        id=str(uuid.uuid4()),
        code="FL",
        name="Florida State Courts",
        description="Florida State Court System",
        jurisdiction_type=JurisdictionType.STATE,
        state="FL"
    )
    db.add(fl)
    jurisdictions["FL"] = fl

    # Florida DCAs
    for dca_num in [1, 2, 3, 4, 5, 6]:
        dca = Jurisdiction(
            id=str(uuid.uuid4()),
            code=f"FL-DCA{dca_num}",
            name=f"Florida {dca_num}{'st' if dca_num == 1 else 'nd' if dca_num == 2 else 'rd' if dca_num == 3 else 'th'} District Court of Appeal",
            jurisdiction_type=JurisdictionType.APPELLATE,
            parent_jurisdiction_id=fl.id,
            state="FL"
        )
        db.add(dca)
        jurisdictions[f"FL-DCA{dca_num}"] = dca

    # Federal Districts in Florida
    for district, name in [("SOUT", "Southern"), ("MD", "Middle"), ("ND", "Northern")]:
        fd = Jurisdiction(
            id=str(uuid.uuid4()),
            code=f"FL-USDC-{district}",
            name=f"U.S. District Court - {name} District of Florida",
            jurisdiction_type=JurisdictionType.FEDERAL,
            parent_jurisdiction_id=fed.id,
            state="FL",
            federal_circuit=11
        )
        db.add(fd)
        jurisdictions[f"FL-USDC-{district}"] = fd

    # Bankruptcy Courts
    for district, name in [("MD", "Middle"), ("ND", "Northern"), ("SD", "Southern")]:
        bk = Jurisdiction(
            id=str(uuid.uuid4()),
            code=f"FL-BK-{district}",
            name=f"U.S. Bankruptcy Court - {name} District of Florida",
            jurisdiction_type=JurisdictionType.BANKRUPTCY,
            parent_jurisdiction_id=fed.id,
            state="FL",
            federal_circuit=11
        )
        db.add(bk)
        jurisdictions[f"FL-BK-{district}"] = bk

    db.commit()
    return jurisdictions


def seed_rule_sets(db: Session, jurisdictions: Dict[str, Jurisdiction]) -> Dict[str, RuleSet]:
    """Create CompuLaw-style rule sets"""

    rule_sets = {}

    # ================================================================
    # FEDERAL RULES (Base)
    # ================================================================

    frcp = RuleSet(
        id=str(uuid.uuid4()),
        code="FRCP",
        name="Federal Rules of Civil Procedure",
        description="Rules governing civil procedure in federal courts",
        jurisdiction_id=jurisdictions["FED"].id,
        court_type=CourtType.DISTRICT,
        contains_deadlines_from=[
            "Federal Rules of Civil Procedure",
            "28 United States Code"
        ],
        is_local=False
    )
    db.add(frcp)
    rule_sets["FRCP"] = frcp

    frap = RuleSet(
        id=str(uuid.uuid4()),
        code="FRAP",
        name="Federal Rules of Appellate Procedure",
        description="Rules governing appeals in federal courts",
        jurisdiction_id=jurisdictions["FED"].id,
        court_type=CourtType.APPELLATE_FEDERAL,
        contains_deadlines_from=[
            "Federal Rules of Appellate Procedure",
            "11th Circuit Rules"
        ],
        is_local=False
    )
    db.add(frap)
    rule_sets["FRAP"] = frap

    frbp = RuleSet(
        id=str(uuid.uuid4()),
        code="FRBP",
        name="Federal Rules of Bankruptcy Procedure",
        description="Rules governing bankruptcy proceedings",
        jurisdiction_id=jurisdictions["FED"].id,
        court_type=CourtType.BANKRUPTCY,
        contains_deadlines_from=[
            "Federal Rules of Bankruptcy Procedure",
            "Bankruptcy Code (Title 11)"
        ],
        is_local=False
    )
    db.add(frbp)
    rule_sets["FRBP"] = frbp

    # ================================================================
    # FLORIDA STATE RULES
    # ================================================================

    # FL:RCP - Florida Rules of Civil Procedure (Circuit Court base)
    fl_rcp = RuleSet(
        id=str(uuid.uuid4()),
        code="FL:RCP",
        name="Florida Rules of Civil Procedure",
        description="Base rules for Florida civil litigation",
        jurisdiction_id=jurisdictions["FL"].id,
        court_type=CourtType.CIRCUIT,
        contains_deadlines_from=[
            "Florida Rules of Civil Procedure",
            "Florida Rules of Appellate Procedure",
            "Rules of General Practice and Judicial Administration",
            "28 United States Code §1446"
        ],
        is_local=False
    )
    db.add(fl_rcp)
    rule_sets["FL:RCP"] = fl_rcp

    # FL:CPP - Florida Civil Practice & Procedure
    fl_cpp = RuleSet(
        id=str(uuid.uuid4()),
        code="FL:CPP",
        name="Florida Civil Practice & Procedure",
        description="Title VI of Florida Statutes - Civil Practice",
        jurisdiction_id=jurisdictions["FL"].id,
        court_type=CourtType.CIRCUIT,
        contains_deadlines_from=[
            "Florida Civil Practice & Procedure, Title VI of Florida Statutes",
            "Rules of Judicial Administration"
        ],
        is_local=False
    )
    db.add(fl_cpp)
    rule_sets["FL:CPP"] = fl_cpp

    # FL:RAP - Florida Rules of Appellate Procedure
    fl_rap = RuleSet(
        id=str(uuid.uuid4()),
        code="FL:RAP",
        name="Florida Rules of Appellate Procedure",
        description="Rules for Florida appellate courts",
        jurisdiction_id=jurisdictions["FL"].id,
        court_type=CourtType.APPELLATE_STATE,
        contains_deadlines_from=[
            "Florida Rules of Appellate Procedure",
            "Florida Supreme Court Manual of Internal Operating Procedures",
            "Rules of General Practice and Judicial Administration"
        ],
        is_local=False
    )
    db.add(fl_rap)
    rule_sets["FL:RAP"] = fl_rap

    # FL:PB-FPR - Florida Probate Rules
    fl_pb_fpr = RuleSet(
        id=str(uuid.uuid4()),
        code="FL:PB-FPR",
        name="Florida Probate Rules",
        description="Rules for probate proceedings in Florida",
        jurisdiction_id=jurisdictions["FL"].id,
        court_type=CourtType.CIRCUIT,
        contains_deadlines_from=[
            "Florida Probate Rules",
            "Florida Probate Code - Title XLII - Chapter 733",
            "Rules of General Practice and Judicial Administration",
            "Florida Rules of Civil Procedure",
            "Florida Rules of Appellate Procedure"
        ],
        is_local=False
    )
    db.add(fl_pb_fpr)
    rule_sets["FL:PB-FPR"] = fl_pb_fpr

    # FL:PB-CODE - Florida Probate Code
    fl_pb_code = RuleSet(
        id=str(uuid.uuid4()),
        code="FL:PB-CODE",
        name="Florida Probate Code",
        description="Title XLII - Chapters 731-735",
        jurisdiction_id=jurisdictions["FL"].id,
        court_type=CourtType.CIRCUIT,
        contains_deadlines_from=[
            "Florida Probate Code - Title XLII - Chapters 731-735",
            "Rules of General Practice and Judicial Administration"
        ],
        is_local=False
    )
    db.add(fl_pb_code)
    rule_sets["FL:PB-CODE"] = fl_pb_code

    # FL:PB-TRST - Florida Trust Code
    fl_pb_trst = RuleSet(
        id=str(uuid.uuid4()),
        code="FL:PB-TRST",
        name="Florida Trust Code",
        description="Title XLII - Chapters 736-739",
        jurisdiction_id=jurisdictions["FL"].id,
        court_type=CourtType.CIRCUIT,
        contains_deadlines_from=[
            "Florida Trust Code - Title XLII - Chapters 736-739",
            "Rules of General Practice and Judicial Administration"
        ],
        is_local=False
    )
    db.add(fl_pb_trst)
    rule_sets["FL:PB-TRST"] = fl_pb_trst

    # FL:FLRP - Florida Family Rules
    fl_flrp = RuleSet(
        id=str(uuid.uuid4()),
        code="FL:FLRP",
        name="Florida Family Law Rules of Procedure",
        description="Rules for family law proceedings",
        jurisdiction_id=jurisdictions["FL"].id,
        court_type=CourtType.CIRCUIT,
        contains_deadlines_from=[
            "Florida Family Law Rules of Procedure",
            "Florida Rules of Appellate Procedure"
        ],
        is_local=False
    )
    db.add(fl_flrp)
    rule_sets["FL:FLRP"] = fl_flrp

    # FL:LIMIT - Limitations of Actions
    fl_limit = RuleSet(
        id=str(uuid.uuid4()),
        code="FL:LIMIT",
        name="Florida Statutes of Limitations",
        description="Title VIII - Chapter 95 - Limitations of Actions",
        jurisdiction_id=jurisdictions["FL"].id,
        court_type=CourtType.CIRCUIT,
        contains_deadlines_from=[
            "Florida Statutes - Title VIII - Chapter 95"
        ],
        is_local=False
    )
    db.add(fl_limit)
    rule_sets["FL:LIMIT"] = fl_limit

    # FL:STATUTE - Pre-Action Requirements
    fl_statute = RuleSet(
        id=str(uuid.uuid4()),
        code="FL:STATUTE",
        name="Florida Miscellaneous Pre-Action Requirements",
        description="Pre-suit notice and other statutory requirements",
        jurisdiction_id=jurisdictions["FL"].id,
        court_type=CourtType.CIRCUIT,
        contains_deadlines_from=[
            "Florida Statutes - Title XXXIII - Chapter 558",
            "Florida Statutes 627.4137"
        ],
        is_local=False
    )
    db.add(fl_statute)
    rule_sets["FL:STATUTE"] = fl_statute

    # FL:SCR - Small Claims Rules
    fl_scr = RuleSet(
        id=str(uuid.uuid4()),
        code="FL:SCR",
        name="Florida Small Claims Rules",
        description="Rules for small claims court",
        jurisdiction_id=jurisdictions["FL"].id,
        court_type=CourtType.COUNTY,
        contains_deadlines_from=[
            "Florida Small Claims Rules",
            "Florida Rules of Civil Procedure",
            "Rules of General Practice and Judicial Administration"
        ],
        is_local=False
    )
    db.add(fl_scr)
    rule_sets["FL:SCR"] = fl_scr

    # FL:LLT - Landlord Tenant
    fl_llt = RuleSet(
        id=str(uuid.uuid4()),
        code="FL:LLT",
        name="Florida Landlord and Tenant Rules",
        description="Title VI - Chapter 83",
        jurisdiction_id=jurisdictions["FL"].id,
        court_type=CourtType.COUNTY,
        contains_deadlines_from=[
            "Florida Landlord and Tenant Rules - Title VI - Chapter 83",
            "Florida Rules of Civil Procedure"
        ],
        is_local=False
    )
    db.add(fl_llt)
    rule_sets["FL:LLT"] = fl_llt

    # FL:SP - Summary Procedure
    fl_sp = RuleSet(
        id=str(uuid.uuid4()),
        code="FL:SP",
        name="Florida Summary Procedure",
        description="Title VI - Chapter 51",
        jurisdiction_id=jurisdictions["FL"].id,
        court_type=CourtType.COUNTY,
        contains_deadlines_from=[
            "Florida Summary Procedure - Title VI - Chapter 51",
            "Rules of General Practice and Judicial Administration"
        ],
        is_local=False
    )
    db.add(fl_sp)
    rule_sets["FL:SP"] = fl_sp

    # ================================================================
    # FEDERAL DISTRICT COURT LOCAL RULES (Florida)
    # ================================================================

    for district, name, jur_code in [
        ("SOUT", "Southern", "FL-USDC-SOUT"),
        ("MD", "Middle", "FL-USDC-MD"),
        ("ND", "Northern", "FL-USDC-ND")
    ]:
        local = RuleSet(
            id=str(uuid.uuid4()),
            code=f"FL:DC-{district}",
            name=f"U.S. District Court - {name} District of Florida Local Rules",
            description=f"Local rules for the {name} District of Florida",
            jurisdiction_id=jurisdictions[jur_code].id,
            court_type=CourtType.DISTRICT,
            contains_deadlines_from=[
                f"Local Rules of the USDC, {name} District of Florida",
                f"Select Orders of the USDC, {name} District of Florida",
                "Federal Rules of Civil Procedure"
            ],
            is_local=True
        )
        db.add(local)
        rule_sets[f"FL:DC-{district}"] = local

    # ================================================================
    # BANKRUPTCY COURT LOCAL RULES
    # ================================================================

    # Middle District Bankruptcy (Chapters 7, 11, 12, 13)
    for chapter in [7, 11, 12, 13]:
        bk_md = RuleSet(
            id=str(uuid.uuid4()),
            code=f"FL:BRMD-{chapter}",
            name=f"Bankruptcy Court - Middle District - Chapter {chapter}",
            description=f"Local rules for Chapter {chapter} bankruptcy in Middle District",
            jurisdiction_id=jurisdictions["FL-BK-MD"].id,
            court_type=CourtType.BANKRUPTCY,
            contains_deadlines_from=[
                "Local Bankruptcy Rules of the USBC, Middle District of Florida",
                "Select Orders and Procedures of the USBC, Middle District",
                "Federal Rules of Civil Procedure",
                "Federal Rules of Bankruptcy Procedure"
            ],
            is_local=True
        )
        db.add(bk_md)
        rule_sets[f"FL:BRMD-{chapter}"] = bk_md

    # Northern District Bankruptcy
    for chapter in [7, 9, 11, 12, 13, 15]:
        bk_nd = RuleSet(
            id=str(uuid.uuid4()),
            code=f"FL:BRND-{chapter}",
            name=f"Bankruptcy Court - Northern District - Chapter {chapter}",
            description=f"Local rules for Chapter {chapter} bankruptcy in Northern District",
            jurisdiction_id=jurisdictions["FL-BK-ND"].id,
            court_type=CourtType.BANKRUPTCY,
            contains_deadlines_from=[
                "Local Bankruptcy Rules of the USBC, Northern District of Florida",
                "Select Orders of the USBC, Northern District",
                "Federal Rules of Civil Procedure",
                "Federal Rules of Bankruptcy Procedure"
            ],
            is_local=True
        )
        db.add(bk_nd)
        rule_sets[f"FL:BRND-{chapter}"] = bk_nd

    # Southern District Bankruptcy
    for chapter in [7, 11, 13, 15]:
        bk_sd = RuleSet(
            id=str(uuid.uuid4()),
            code=f"FL:BRSD-{chapter}",
            name=f"Bankruptcy Court - Southern District - Chapter {chapter}",
            description=f"Local rules for Chapter {chapter} bankruptcy in Southern District",
            jurisdiction_id=jurisdictions["FL-BK-SD"].id,
            court_type=CourtType.BANKRUPTCY,
            contains_deadlines_from=[
                "Local Bankruptcy Rules of the USBC, Southern District of Florida",
                "Select Orders of the USBC, Southern District",
                "Federal Rules of Civil Procedure",
                "Federal Rules of Bankruptcy Procedure"
            ],
            is_local=True
        )
        db.add(bk_sd)
        rule_sets[f"FL:BRSD-{chapter}"] = bk_sd

    db.commit()
    return rule_sets


def seed_rule_dependencies(db: Session, rule_sets: Dict[str, RuleSet]):
    """Create dependencies between rule sets (concurrent loading)"""

    dependencies = []

    # Federal District Courts require FRCP
    for district in ["SOUT", "MD", "ND"]:
        dep = RuleSetDependency(
            id=str(uuid.uuid4()),
            rule_set_id=rule_sets[f"FL:DC-{district}"].id,
            required_rule_set_id=rule_sets["FRCP"].id,
            dependency_type=DependencyType.CONCURRENT,
            priority=10,
            notes="Local rules must be used concurrently with FRCP"
        )
        db.add(dep)
        dependencies.append(dep)

    # Bankruptcy Courts require FRCP and FRBP
    for code in rule_sets:
        if code.startswith("FL:BR"):
            # Requires FRBP
            dep1 = RuleSetDependency(
                id=str(uuid.uuid4()),
                rule_set_id=rule_sets[code].id,
                required_rule_set_id=rule_sets["FRBP"].id,
                dependency_type=DependencyType.CONCURRENT,
                priority=10,
                notes="Bankruptcy local rules require FRBP"
            )
            db.add(dep1)

            # Requires FRCP (for certain procedures)
            dep2 = RuleSetDependency(
                id=str(uuid.uuid4()),
                rule_set_id=rule_sets[code].id,
                required_rule_set_id=rule_sets["FRCP"].id,
                dependency_type=DependencyType.CONCURRENT,
                priority=5,
                notes="Bankruptcy incorporates certain FRCP provisions"
            )
            db.add(dep2)

    # Florida appellate rules apply to circuit court appeals
    dep = RuleSetDependency(
        id=str(uuid.uuid4()),
        rule_set_id=rule_sets["FL:RCP"].id,
        required_rule_set_id=rule_sets["FL:RAP"].id,
        dependency_type=DependencyType.SUPPLEMENTS,
        priority=5,
        notes="FL:RAP applies for appeals from circuit court"
    )
    db.add(dep)

    # Probate rules supplement RCP
    dep = RuleSetDependency(
        id=str(uuid.uuid4()),
        rule_set_id=rule_sets["FL:PB-FPR"].id,
        required_rule_set_id=rule_sets["FL:RCP"].id,
        dependency_type=DependencyType.SUPPLEMENTS,
        priority=5,
        notes="Probate Rules supplement Rules of Civil Procedure"
    )
    db.add(dep)

    # Family rules supplement RCP
    dep = RuleSetDependency(
        id=str(uuid.uuid4()),
        rule_set_id=rule_sets["FL:FLRP"].id,
        required_rule_set_id=rule_sets["FL:RCP"].id,
        dependency_type=DependencyType.SUPPLEMENTS,
        priority=5,
        notes="Family Law Rules supplement Rules of Civil Procedure"
    )
    db.add(dep)

    db.commit()


def seed_court_locations(db: Session, jurisdictions: Dict[str, Jurisdiction], rule_sets: Dict[str, RuleSet]):
    """Create court locations for auto-detection"""

    # U.S. District Court - Southern District of Florida
    sdfl = CourtLocation(
        id=str(uuid.uuid4()),
        jurisdiction_id=jurisdictions["FL-USDC-SOUT"].id,
        name="U.S. District Court - Southern District of Florida",
        short_name="S.D. Fla.",
        court_type=CourtType.DISTRICT,
        district="Southern",
        circuit=11,
        detection_patterns=[
            "SOUTHERN DISTRICT OF FLORIDA",
            "S.D. FLA",
            "S.D.FLA.",
            "SDFL",
            "SD FLA"
        ],
        case_number_pattern=r"^\d{1,2}:\d{2}-cv-\d+",
        default_rule_set_id=rule_sets["FRCP"].id,
        local_rule_set_id=rule_sets["FL:DC-SOUT"].id
    )
    db.add(sdfl)

    # U.S. District Court - Middle District of Florida
    mdfl = CourtLocation(
        id=str(uuid.uuid4()),
        jurisdiction_id=jurisdictions["FL-USDC-MD"].id,
        name="U.S. District Court - Middle District of Florida",
        short_name="M.D. Fla.",
        court_type=CourtType.DISTRICT,
        district="Middle",
        circuit=11,
        detection_patterns=[
            "MIDDLE DISTRICT OF FLORIDA",
            "M.D. FLA",
            "M.D.FLA.",
            "MDFL"
        ],
        case_number_pattern=r"^\d{1,2}:\d{2}-cv-\d+",
        default_rule_set_id=rule_sets["FRCP"].id,
        local_rule_set_id=rule_sets["FL:DC-MD"].id
    )
    db.add(mdfl)

    # U.S. District Court - Northern District of Florida
    ndfl = CourtLocation(
        id=str(uuid.uuid4()),
        jurisdiction_id=jurisdictions["FL-USDC-ND"].id,
        name="U.S. District Court - Northern District of Florida",
        short_name="N.D. Fla.",
        court_type=CourtType.DISTRICT,
        district="Northern",
        circuit=11,
        detection_patterns=[
            "NORTHERN DISTRICT OF FLORIDA",
            "N.D. FLA",
            "N.D.FLA.",
            "NDFL"
        ],
        case_number_pattern=r"^\d{1,2}:\d{2}-cv-\d+",
        default_rule_set_id=rule_sets["FRCP"].id,
        local_rule_set_id=rule_sets["FL:DC-ND"].id
    )
    db.add(ndfl)

    # Florida Circuit Courts (example: 11th Judicial Circuit - Miami-Dade)
    fl_11cir = CourtLocation(
        id=str(uuid.uuid4()),
        jurisdiction_id=jurisdictions["FL"].id,
        name="Circuit Court of the 11th Judicial Circuit",
        short_name="11th Cir. Ct.",
        court_type=CourtType.CIRCUIT,
        district=None,
        circuit=11,
        division="Miami-Dade",
        detection_patterns=[
            "11TH JUDICIAL CIRCUIT",
            "ELEVENTH JUDICIAL CIRCUIT",
            "CIRCUIT COURT OF THE ELEVENTH",
            "MIAMI-DADE COUNTY"
        ],
        case_number_pattern=r"^\d{4}-\d+-CA-\d+",
        default_rule_set_id=rule_sets["FL:RCP"].id,
        local_rule_set_id=None  # Would add local circuit rules here
    )
    db.add(fl_11cir)

    # Bankruptcy Court - Southern District
    bk_sd = CourtLocation(
        id=str(uuid.uuid4()),
        jurisdiction_id=jurisdictions["FL-BK-SD"].id,
        name="U.S. Bankruptcy Court - Southern District of Florida",
        short_name="Bankr. S.D. Fla.",
        court_type=CourtType.BANKRUPTCY,
        district="Southern",
        circuit=11,
        detection_patterns=[
            "BANKRUPTCY COURT",
            "SOUTHERN DISTRICT OF FLORIDA",
            "BANKR. S.D. FLA",
            "IN RE:"
        ],
        case_number_pattern=r"^\d{2}-\d+-[A-Z]{3}",
        default_rule_set_id=rule_sets["FRBP"].id,
        local_rule_set_id=rule_sets["FL:BRSD-7"].id  # Default to Chapter 7
    )
    db.add(bk_sd)

    db.commit()


def seed_rule_templates(db: Session, rule_sets: Dict[str, RuleSet]):
    """Create rule templates with deadline definitions"""

    # ================================================================
    # FL:RCP - COMPLAINT SERVED TRIGGER
    # ================================================================

    fl_complaint_served = RuleTemplate(
        id=str(uuid.uuid4()),
        rule_set_id=rule_sets["FL:RCP"].id,
        rule_code="FL_CIV_COMPLAINT_SERVED",
        name="Complaint Served - Full Response Chain",
        description="All defendant response deadlines from service of complaint",
        trigger_type=TriggerType.COMPLAINT_SERVED,
        citation="Fla. R. Civ. P. 1.140",
        court_type=CourtType.CIRCUIT
    )
    db.add(fl_complaint_served)
    db.flush()

    # Deadlines for this template
    deadlines = [
        RuleTemplateDeadline(
            id=str(uuid.uuid4()),
            rule_template_id=fl_complaint_served.id,
            name="Answer Due",
            description="Defendant must file and serve Answer",
            days_from_trigger=20,
            priority=DeadlinePriority.FATAL,
            party_responsible="defendant",
            action_required="File and serve Answer to Complaint",
            calculation_method=CalculationMethod.CALENDAR_DAYS,
            add_service_days=True,
            rule_citation="Fla. R. Civ. P. 1.140(a)(1)",
            notes="20 days after service (+ 5 if by mail)",
            display_order=1
        ),
        RuleTemplateDeadline(
            id=str(uuid.uuid4()),
            rule_template_id=fl_complaint_served.id,
            name="Motion to Dismiss Deadline",
            description="Last day to file motion to dismiss (instead of answer)",
            days_from_trigger=20,
            priority=DeadlinePriority.CRITICAL,
            party_responsible="defendant",
            action_required="File motion to dismiss under Rule 1.140(b)",
            calculation_method=CalculationMethod.CALENDAR_DAYS,
            add_service_days=True,
            rule_citation="Fla. R. Civ. P. 1.140(b)",
            notes="Must be filed BEFORE answer; same deadline",
            display_order=2
        ),
        RuleTemplateDeadline(
            id=str(uuid.uuid4()),
            rule_template_id=fl_complaint_served.id,
            name="Affirmative Defenses Due",
            description="Affirmative defenses must be raised in Answer",
            days_from_trigger=20,
            priority=DeadlinePriority.FATAL,
            party_responsible="defendant",
            action_required="Include all affirmative defenses in Answer or they may be waived",
            calculation_method=CalculationMethod.CALENDAR_DAYS,
            add_service_days=True,
            rule_citation="Fla. R. Civ. P. 1.110(d)",
            display_order=3
        ),
    ]
    for d in deadlines:
        db.add(d)

    # ================================================================
    # FL:RCP - TRIAL DATE TRIGGER (Comprehensive 30+ deadlines)
    # ================================================================

    fl_trial = RuleTemplate(
        id=str(uuid.uuid4()),
        rule_set_id=rule_sets["FL:RCP"].id,
        rule_code="FL_CIV_TRIAL",
        name="Trial Date Dependencies",
        description="Comprehensive deadlines calculated from trial date - Florida Civil",
        trigger_type=TriggerType.TRIAL_DATE,
        citation="Fla. R. Civ. P. 1.200",
        court_type=CourtType.CIRCUIT
    )
    db.add(fl_trial)
    db.flush()

    trial_deadlines = [
        # Discovery
        ("Discovery Cutoff", -45, DeadlinePriority.CRITICAL, "both", "Complete all discovery", "Fla. R. Civ. P. 1.280", 1),
        ("Discovery Responses Due", -30, DeadlinePriority.CRITICAL, "both", "Serve all outstanding discovery responses", "Fla. R. Civ. P. 1.340", 2),
        # Experts
        ("Plaintiff Expert Disclosure", -90, DeadlinePriority.CRITICAL, "plaintiff", "Serve expert witness list with opinions", "Fla. R. Civ. P. 1.280(b)(5)", 3),
        ("Defendant Expert Disclosure", -60, DeadlinePriority.CRITICAL, "defendant", "Serve expert witness list with opinions", "Fla. R. Civ. P. 1.280(b)(5)", 4),
        ("Rebuttal Expert Disclosure", -45, DeadlinePriority.IMPORTANT, "plaintiff", "Serve rebuttal expert witness disclosure", "Fla. R. Civ. P. 1.280(b)(5)", 5),
        ("Expert Deposition Cutoff", -30, DeadlinePriority.IMPORTANT, "both", "Complete all expert depositions", "Fla. R. Civ. P. 1.280", 6),
        # Dispositive Motions
        ("Motion for Summary Judgment", -60, DeadlinePriority.IMPORTANT, "both", "File motion for summary judgment", "Fla. R. Civ. P. 1.510(c)", 7),
        ("MSJ Response", -40, DeadlinePriority.CRITICAL, "both", "File response to MSJ", "Fla. R. Civ. P. 1.510(c)", 8),
        # Pretrial
        ("Pretrial Stipulation Due", -15, DeadlinePriority.CRITICAL, "both", "File joint pretrial stipulation", "Local Rules", 9),
        ("Final Witness List", -30, DeadlinePriority.CRITICAL, "both", "Exchange final witness lists", "Local Rules", 10),
        ("Final Exhibit List", -30, DeadlinePriority.CRITICAL, "both", "Exchange exhibit lists", "Local Rules", 11),
        ("Exchange Trial Exhibits", -21, DeadlinePriority.CRITICAL, "both", "Exchange copies of all exhibits", "Local Rules", 12),
        ("Exhibit Objections", -14, DeadlinePriority.IMPORTANT, "both", "File objections to exhibits", "Local Rules", 13),
        # Motions in Limine
        ("Motions in Limine", -21, DeadlinePriority.IMPORTANT, "both", "File motions to exclude evidence", "Local Rules", 14),
        ("MIL Responses", -14, DeadlinePriority.IMPORTANT, "both", "Respond to motions in limine", "Local Rules", 15),
        # Jury
        ("Proposed Jury Instructions", -14, DeadlinePriority.IMPORTANT, "both", "File proposed jury instructions", "Fla. R. Civ. P. 1.470(b)", 16),
        ("Proposed Verdict Form", -14, DeadlinePriority.IMPORTANT, "both", "File proposed verdict form", "Fla. R. Civ. P. 1.480", 17),
        ("Proposed Voir Dire", -10, DeadlinePriority.STANDARD, "both", "File proposed voir dire questions", "Local Rules", 18),
        # Depositions
        ("Deposition Designations", -21, DeadlinePriority.IMPORTANT, "both", "Designate deposition testimony", "Fla. R. Civ. P. 1.330", 19),
        ("Counter-Designations", -14, DeadlinePriority.IMPORTANT, "both", "Counter-designate testimony", "Fla. R. Civ. P. 1.330", 20),
        # Final
        ("Trial Subpoenas", -10, DeadlinePriority.IMPORTANT, "both", "Serve trial subpoenas on witnesses", "Fla. R. Civ. P. 1.410(d)", 21),
        ("Trial Brief", -7, DeadlinePriority.STANDARD, "both", "File trial brief", "Local Rules", 22),
        ("Pretrial Conference", -7, DeadlinePriority.CRITICAL, "both", "Attend pretrial conference", "Fla. R. Civ. P. 1.200", 23),
    ]

    for name, days, priority, party, action, citation, order in trial_deadlines:
        d = RuleTemplateDeadline(
            id=str(uuid.uuid4()),
            rule_template_id=fl_trial.id,
            name=name,
            description=name,
            days_from_trigger=days,
            priority=priority,
            party_responsible=party,
            action_required=action,
            calculation_method=CalculationMethod.CALENDAR_DAYS,
            add_service_days=False,
            rule_citation=citation,
            display_order=order
        )
        db.add(d)

    # ================================================================
    # FRCP - COMPLAINT SERVED (Federal)
    # ================================================================

    fed_complaint = RuleTemplate(
        id=str(uuid.uuid4()),
        rule_set_id=rule_sets["FRCP"].id,
        rule_code="FED_CIV_COMPLAINT_SERVED",
        name="Federal Complaint Served - Response Chain",
        description="Defendant response deadlines from service (Federal)",
        trigger_type=TriggerType.COMPLAINT_SERVED,
        citation="FRCP 12",
        court_type=CourtType.DISTRICT
    )
    db.add(fed_complaint)
    db.flush()

    fed_deadlines = [
        RuleTemplateDeadline(
            id=str(uuid.uuid4()),
            rule_template_id=fed_complaint.id,
            name="Answer Due (Federal)",
            description="Defendant must file Answer",
            days_from_trigger=21,
            priority=DeadlinePriority.FATAL,
            party_responsible="defendant",
            action_required="File Answer to Complaint",
            calculation_method=CalculationMethod.CALENDAR_DAYS,
            add_service_days=True,
            rule_citation="FRCP 12(a)(1)(A)(i)",
            notes="21 days (+ 3 if by mail under FRCP 6(d))",
            display_order=1
        ),
        RuleTemplateDeadline(
            id=str(uuid.uuid4()),
            rule_template_id=fed_complaint.id,
            name="Rule 12 Motion Deadline",
            description="File pre-answer Rule 12 motion",
            days_from_trigger=21,
            priority=DeadlinePriority.CRITICAL,
            party_responsible="defendant",
            action_required="File Rule 12(b) motion to dismiss",
            calculation_method=CalculationMethod.CALENDAR_DAYS,
            add_service_days=True,
            rule_citation="FRCP 12(b)",
            display_order=2
        ),
        RuleTemplateDeadline(
            id=str(uuid.uuid4()),
            rule_template_id=fed_complaint.id,
            name="Waiver of Service Response",
            description="Extended deadline if waiver executed",
            days_from_trigger=60,
            priority=DeadlinePriority.CRITICAL,
            party_responsible="defendant",
            action_required="Answer due if waiver of service was executed",
            calculation_method=CalculationMethod.CALENDAR_DAYS,
            add_service_days=False,
            rule_citation="FRCP 4(d)(3)",
            notes="60 days from when waiver request was sent",
            conditions={"if_waiver_of_service": True},
            display_order=3
        ),
    ]
    for d in fed_deadlines:
        db.add(d)

    db.commit()


def run_seed(db: Session):
    """Run all seed functions"""

    # Check if already seeded
    existing = db.query(Jurisdiction).filter(Jurisdiction.code == "FL").first()
    if existing:
        print("Database already seeded. Skipping...")
        return

    print("Seeding jurisdictions...")
    jurisdictions = seed_jurisdictions(db)

    print("Seeding rule sets...")
    rule_sets = seed_rule_sets(db, jurisdictions)

    print("Seeding rule dependencies...")
    seed_rule_dependencies(db, rule_sets)

    print("Seeding court locations...")
    seed_court_locations(db, jurisdictions, rule_sets)

    print("Seeding rule templates...")
    seed_rule_templates(db, rule_sets)

    print("Seed complete!")


if __name__ == "__main__":
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        run_seed(db)
    finally:
        db.close()
