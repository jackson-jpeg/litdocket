"""
Comprehensive Court Rules Knowledge Base for Docket Overseer AI

This module contains the complete rules knowledge that powers the AI chatbot's
understanding of Florida state, Federal, and local court rules.

Sources:
- Florida Rules of Civil Procedure (Fla. R. Civ. P.)
- Florida Rules of Judicial Administration (Fla. R. Jud. Admin.)
- Florida Rules of Appellate Procedure (Fla. R. App. P.)
- Federal Rules of Civil Procedure (FRCP)
- Federal Rules of Appellate Procedure (FRAP)
- Local Rules for Florida Circuits (11th, 17th, 13th, 9th)
- Southern District of Florida Local Rules
- Middle District of Florida Local Rules
"""

from typing import Dict, List, Optional
from dataclasses import dataclass


# =============================================================================
# FLORIDA RULES OF CIVIL PROCEDURE - COMPREHENSIVE
# =============================================================================

FLORIDA_CIVIL_PROCEDURE_RULES = {
    # -------------------------------------------------------------------------
    # PLEADINGS AND MOTIONS
    # -------------------------------------------------------------------------
    "1.140": {
        "title": "Defenses",
        "subsections": {
            "(a)(1)": {
                "description": "Answer to Complaint",
                "deadline_days": 20,
                "calculation": "calendar_days",
                "trigger": "service of summons and complaint",
                "service_extension": True,  # +5 for mail
                "priority": "fatal",
                "notes": "Failure to answer may result in default"
            },
            "(a)(2)": {
                "description": "Answer to Amended Complaint",
                "deadline_days": 20,
                "calculation": "calendar_days",
                "trigger": "service of amended complaint",
                "service_extension": True,
                "priority": "fatal"
            },
            "(b)": {
                "description": "Motion to Dismiss",
                "deadline_days": 20,
                "calculation": "calendar_days",
                "trigger": "service of summons and complaint",
                "service_extension": True,
                "priority": "critical",
                "notes": "Must be filed before answer; tolls time to answer"
            }
        }
    },
    "1.100": {
        "title": "Pleadings and Motions",
        "subsections": {
            "(a)": {
                "description": "Pleadings allowed",
                "notes": "Complaint, answer, reply to counterclaim, answer to crossclaim, third-party complaint, third-party answer"
            }
        }
    },
    "1.110": {
        "title": "General Rules of Pleading",
        "subsections": {
            "(b)": {
                "description": "Claims for Relief",
                "notes": "Short and plain statement of ultimate facts"
            },
            "(e)": {
                "description": "Adoption by Reference",
                "notes": "Statements in a pleading may be adopted by reference in a different part"
            }
        }
    },

    # -------------------------------------------------------------------------
    # DISCOVERY RULES
    # -------------------------------------------------------------------------
    "1.280": {
        "title": "General Provisions Governing Discovery",
        "subsections": {
            "(a)": {
                "description": "Discovery Methods",
                "notes": "Depositions, interrogatories, production, physical/mental examination, requests for admission"
            },
            "(b)": {
                "description": "Scope of Discovery",
                "notes": "Any matter not privileged relevant to subject matter"
            },
            "(d)": {
                "description": "Protective Orders",
                "notes": "Court may limit discovery to protect parties"
            }
        }
    },
    "1.340": {
        "title": "Interrogatories to Parties",
        "subsections": {
            "(a)": {
                "description": "Response to Interrogatories",
                "deadline_days": 30,
                "calculation": "calendar_days",
                "trigger": "service of interrogatories",
                "service_extension": True,
                "priority": "important",
                "notes": "Answers must be verified under oath"
            },
            "(b)": {
                "description": "Scope",
                "notes": "May relate to any matter within scope of Rule 1.280(b)"
            },
            "(c)": {
                "description": "Option to Produce Records",
                "notes": "May specify records where answer may be found"
            }
        }
    },
    "1.350": {
        "title": "Production of Documents and Things",
        "subsections": {
            "(a)": {
                "description": "Response to Request for Production",
                "deadline_days": 30,
                "calculation": "calendar_days",
                "trigger": "service of request for production",
                "service_extension": True,
                "priority": "important",
                "notes": "Must state if documents withheld and basis"
            },
            "(b)": {
                "description": "Procedure for Non-Parties",
                "notes": "Must use subpoena under Rule 1.351"
            }
        }
    },
    "1.370": {
        "title": "Requests for Admission",
        "subsections": {
            "(a)": {
                "description": "Response to Requests for Admission",
                "deadline_days": 30,
                "calculation": "calendar_days",
                "trigger": "service of requests for admission",
                "service_extension": True,
                "priority": "fatal",
                "notes": "CRITICAL: Failure to respond = matters DEEMED ADMITTED"
            }
        }
    },
    "1.310": {
        "title": "Depositions Upon Oral Examination",
        "subsections": {
            "(a)": {
                "description": "When Depositions May Be Taken",
                "notes": "After commencement of action, any time"
            },
            "(b)(1)": {
                "description": "Notice of Deposition",
                "deadline_days": 10,  # Reasonable notice
                "calculation": "calendar_days",
                "notes": "Reasonable notice required, typically 10+ days"
            }
        }
    },
    "1.380": {
        "title": "Failure to Make Discovery; Sanctions",
        "subsections": {
            "(a)": {
                "description": "Motion to Compel Discovery",
                "notes": "Court may order discovery and award expenses"
            },
            "(b)": {
                "description": "Sanctions for Failure to Comply",
                "notes": "May include striking pleadings, default judgment, contempt"
            }
        }
    },

    # -------------------------------------------------------------------------
    # SUMMARY JUDGMENT
    # -------------------------------------------------------------------------
    "1.510": {
        "title": "Summary Judgment",
        "subsections": {
            "(a)": {
                "description": "Motion for Summary Judgment",
                "deadline_days": 40,
                "calculation": "calendar_days",
                "trigger": "hearing date",
                "direction": "before",
                "notes": "Must be served at least 40 days before hearing"
            },
            "(c)": {
                "description": "Response to Motion for Summary Judgment",
                "deadline_days": 20,
                "calculation": "calendar_days",
                "trigger": "service of motion for summary judgment",
                "service_extension": True,
                "priority": "critical",
                "notes": "Must include affidavits/evidence opposing material facts"
            }
        }
    },

    # -------------------------------------------------------------------------
    # MOTIONS PRACTICE
    # -------------------------------------------------------------------------
    "1.090": {
        "title": "Time",
        "subsections": {
            "(a)": {
                "description": "Computation of Time",
                "notes": "Defers to Fla. R. Jud. Admin. 2.514"
            },
            "(b)": {
                "description": "Enlargement of Time",
                "notes": "Court may extend time with or without motion"
            },
            "(d)": {
                "description": "Service by Mail - Additional Time",
                "notes": "Add 5 days when served by mail (See Rule 2.514)"
            }
        }
    },
    "1.160": {
        "title": "Motions",
        "subsections": {
            "(a)": {
                "description": "Motion Requirements",
                "notes": "Must state grounds with particularity"
            },
            "(b)": {
                "description": "Time for Response to Motion",
                "deadline_days": 10,
                "calculation": "calendar_days",
                "trigger": "service of motion",
                "service_extension": True,
                "notes": "Unless court sets different time"
            }
        }
    },

    # -------------------------------------------------------------------------
    # TRIAL RULES
    # -------------------------------------------------------------------------
    "1.440": {
        "title": "Setting Action for Trial",
        "subsections": {
            "(a)": {
                "description": "Notice for Trial",
                "notes": "Either party may file notice that case is ready for trial"
            },
            "(c)": {
                "description": "Setting for Trial",
                "notes": "Court shall set trial within reasonable time"
            }
        }
    },
    "1.460": {
        "title": "Continuances",
        "subsections": {
            "(a)": {
                "description": "Motion for Continuance",
                "notes": "Must show good cause"
            }
        }
    },

    # -------------------------------------------------------------------------
    # DEFAULT AND DISMISSAL
    # -------------------------------------------------------------------------
    "1.500": {
        "title": "Defaults and Final Judgments Thereon",
        "subsections": {
            "(a)": {
                "description": "Entry of Default",
                "notes": "Clerk enters default when party fails to plead/defend"
            },
            "(b)": {
                "description": "Default Judgment by Court",
                "notes": "Judgment may be entered by court if damages not certain"
            },
            "(d)": {
                "description": "Setting Aside Default",
                "notes": "Court may set aside for good cause shown"
            }
        }
    },
    "1.420": {
        "title": "Dismissal of Actions",
        "subsections": {
            "(a)(1)": {
                "description": "Voluntary Dismissal by Plaintiff",
                "notes": "Before trial or hearing on merits, without prejudice"
            },
            "(e)": {
                "description": "Failure to Prosecute",
                "notes": "Court may dismiss for lack of record activity for 10 months"
            }
        }
    },

    # -------------------------------------------------------------------------
    # MEDIATION
    # -------------------------------------------------------------------------
    "1.700": {
        "title": "Rules Common to Mediation and Arbitration",
        "subsections": {
            "(a)": {
                "description": "Scope",
                "notes": "Court may refer matters to mediation"
            }
        }
    },
    "1.710": {
        "title": "Mediation Rules",
        "subsections": {
            "(a)": {
                "description": "Completion of Mediation",
                "deadline_days": 120,
                "calculation": "calendar_days",
                "trigger": "order referring to mediation",
                "notes": "Unless extended by court order"
            },
            "(b)": {
                "description": "Appearance at Mediation",
                "notes": "Party representatives with authority must attend"
            }
        }
    },
    "1.720": {
        "title": "Mediation Procedures",
        "subsections": {
            "(b)": {
                "description": "Objection to Referral",
                "deadline_days": 10,
                "calculation": "calendar_days",
                "trigger": "order of referral",
                "notes": "Good cause required for objection"
            },
            "(f)": {
                "description": "Scheduling Mediation",
                "notes": "Mediator sets time with 15 days notice"
            }
        }
    }
}


# =============================================================================
# FLORIDA RULES OF JUDICIAL ADMINISTRATION
# =============================================================================

FLORIDA_JUDICIAL_ADMINISTRATION_RULES = {
    "2.514": {
        "title": "Computing and Extending Time",
        "subsections": {
            "(a)(1)": {
                "description": "Exclude trigger day",
                "notes": "Day of act/event that triggers period is NOT counted"
            },
            "(a)(2)": {
                "description": "Count every day",
                "notes": "Count every calendar day including weekends and holidays"
            },
            "(a)(3)": {
                "description": "Last day rule",
                "notes": "If last day is weekend/holiday, period extends to next business day"
            },
            "(b)": {
                "description": "Service Extension",
                "notes": "Add 5 days when service is by mail"
            },
            "(c)": {
                "description": "Electronic Service",
                "notes": "NO additional days for electronic service (effective Jan 1, 2019)"
            }
        },
        "key_principle": "EXCLUDE trigger day, COUNT all days, ROLL if last day is non-business"
    },
    "2.516": {
        "title": "Service of Pleadings and Documents",
        "subsections": {
            "(b)(1)": {
                "description": "E-Filing Portal Service",
                "notes": "Service through Florida Courts E-Filing Portal"
            },
            "(b)(2)": {
                "description": "Email Service",
                "notes": "Service by email to designated email address"
            }
        }
    },
    "2.250": {
        "title": "Time Standards for Trial and Appellate Courts",
        "subsections": {
            "(a)": {
                "description": "Civil Division Time Standards",
                "notes": "Circuit civil: 18 months, County civil: 12 months to disposition"
            }
        }
    }
}


# =============================================================================
# FEDERAL RULES OF CIVIL PROCEDURE - COMPREHENSIVE
# =============================================================================

FEDERAL_CIVIL_PROCEDURE_RULES = {
    "Rule 4": {
        "title": "Summons",
        "subsections": {
            "(d)": {
                "description": "Waiving Service",
                "notes": "Defendant has 60 days to answer if waiver returned"
            },
            "(m)": {
                "description": "Time Limit for Service",
                "deadline_days": 90,
                "calculation": "calendar_days",
                "trigger": "filing of complaint",
                "notes": "Must serve within 90 days or face dismissal"
            }
        }
    },
    "Rule 6": {
        "title": "Computing and Extending Time",
        "subsections": {
            "(a)(1)": {
                "description": "Computing Time",
                "notes": "Exclude trigger day, count every day, roll if non-business"
            },
            "(d)": {
                "description": "Service Extension",
                "notes": "Add 3 days when served by mail, electronic means, or other means under 5(b)(2)(D)"
            }
        },
        "key_difference": "Federal adds 3 days (not 5) for mail/electronic service"
    },
    "Rule 12": {
        "title": "Defenses and Objections",
        "subsections": {
            "(a)(1)(A)(i)": {
                "description": "Answer to Complaint",
                "deadline_days": 21,
                "calculation": "calendar_days",
                "trigger": "service of summons and complaint",
                "service_extension": True,  # +3 for mail
                "priority": "fatal"
            },
            "(a)(1)(A)(ii)": {
                "description": "Answer if Waiver of Service",
                "deadline_days": 60,
                "calculation": "calendar_days",
                "trigger": "request for waiver sent",
                "notes": "60 days from when request for waiver was sent"
            },
            "(a)(4)(A)": {
                "description": "Answer After Motion to Dismiss Denied",
                "deadline_days": 14,
                "calculation": "calendar_days",
                "trigger": "order denying motion to dismiss",
                "priority": "critical"
            },
            "(b)": {
                "description": "Motion to Dismiss",
                "deadline_days": 21,
                "calculation": "calendar_days",
                "trigger": "service of summons and complaint",
                "notes": "Must be filed before answer"
            }
        }
    },
    "Rule 26": {
        "title": "Duty to Disclose; General Provisions",
        "subsections": {
            "(a)(1)": {
                "description": "Initial Disclosures",
                "deadline_days": 14,
                "calculation": "calendar_days",
                "trigger": "Rule 26(f) conference",
                "priority": "important"
            },
            "(a)(2)(D)": {
                "description": "Expert Witness Disclosure",
                "deadline_days": 90,
                "calculation": "calendar_days",
                "trigger": "trial date",
                "direction": "before",
                "notes": "At least 90 days before trial"
            },
            "(f)": {
                "description": "Discovery Conference",
                "deadline_days": 21,
                "calculation": "calendar_days",
                "trigger": "Rule 16(b) scheduling conference",
                "direction": "before"
            }
        }
    },
    "Rule 33": {
        "title": "Interrogatories to Parties",
        "subsections": {
            "(b)(2)": {
                "description": "Response to Interrogatories",
                "deadline_days": 30,
                "calculation": "calendar_days",
                "trigger": "service of interrogatories",
                "service_extension": True,
                "priority": "important"
            }
        }
    },
    "Rule 34": {
        "title": "Producing Documents",
        "subsections": {
            "(b)(2)(A)": {
                "description": "Response to Request for Production",
                "deadline_days": 30,
                "calculation": "calendar_days",
                "trigger": "service of request for production",
                "service_extension": True,
                "priority": "important"
            }
        }
    },
    "Rule 36": {
        "title": "Requests for Admission",
        "subsections": {
            "(a)(3)": {
                "description": "Response to Requests for Admission",
                "deadline_days": 30,
                "calculation": "calendar_days",
                "trigger": "service of requests for admission",
                "service_extension": True,
                "priority": "fatal",
                "notes": "CRITICAL: Failure to respond = matters ADMITTED"
            }
        }
    },
    "Rule 56": {
        "title": "Summary Judgment",
        "subsections": {
            "(c)(1)(A)": {
                "description": "Motion for Summary Judgment",
                "deadline_days": 30,
                "calculation": "calendar_days",
                "trigger": "close of discovery",
                "notes": "Must file within 30 days after close of discovery unless court sets otherwise"
            }
        }
    }
}


# =============================================================================
# FLORIDA LOCAL RULES BY CIRCUIT
# =============================================================================

FLORIDA_LOCAL_RULES = {
    # 11th Circuit - Miami-Dade County
    "11th_circuit": {
        "name": "Eleventh Judicial Circuit (Miami-Dade County)",
        "website": "https://www.jud11.flcourts.org",
        "rules": {
            "case_management": {
                "description": "Case Management Conference",
                "deadline_days": 60,
                "trigger": "filing of answer or responsive pleading",
                "notes": "Uniform Motion Calendar for civil cases"
            },
            "motion_calendar": {
                "description": "Motion Calendar Notice",
                "deadline_days": 5,
                "trigger": "motion hearing",
                "direction": "before",
                "notes": "Notice required 5 days before UMC hearing"
            },
            "pretrial_stipulation": {
                "description": "Pretrial Stipulation",
                "deadline_days": 10,
                "trigger": "trial date",
                "direction": "before",
                "notes": "Joint pretrial stipulation due 10 days before trial"
            },
            "witness_list": {
                "description": "Witness and Exhibit Lists",
                "deadline_days": 10,
                "trigger": "trial date",
                "direction": "before"
            },
            "motions_in_limine": {
                "description": "Motions in Limine",
                "deadline_days": 10,
                "trigger": "trial date",
                "direction": "before"
            },
            "discovery_cutoff": {
                "description": "Discovery Cutoff",
                "deadline_days": 30,
                "trigger": "trial date",
                "direction": "before",
                "notes": "All discovery must be completed 30 days before trial"
            }
        },
        "uniform_motion_calendar": {
            "days": ["Monday", "Wednesday", "Friday"],
            "time": "8:30 AM",
            "notes": "Check division calendar for specific judge"
        }
    },

    # 17th Circuit - Broward County
    "17th_circuit": {
        "name": "Seventeenth Judicial Circuit (Broward County)",
        "website": "https://www.17th.flcourts.org",
        "rules": {
            "case_management": {
                "description": "Case Management Conference",
                "deadline_days": 180,
                "trigger": "case filing",
                "notes": "CMC required within 180 days of filing"
            },
            "pretrial_conference": {
                "description": "Pretrial Conference",
                "deadline_days": 30,
                "trigger": "trial date",
                "direction": "before"
            },
            "pretrial_stipulation": {
                "description": "Pretrial Stipulation",
                "deadline_days": 10,
                "trigger": "pretrial conference",
                "direction": "before"
            },
            "discovery_deadline": {
                "description": "Discovery Deadline",
                "notes": "Per case management order"
            },
            "expert_disclosure": {
                "description": "Expert Witness Disclosure",
                "deadline_days": 90,
                "trigger": "trial date",
                "direction": "before"
            }
        }
    },

    # 13th Circuit - Hillsborough County (Tampa)
    "13th_circuit": {
        "name": "Thirteenth Judicial Circuit (Hillsborough County - Tampa)",
        "website": "https://www.fljud13.org",
        "rules": {
            "case_management": {
                "description": "Case Management Conference",
                "deadline_days": 90,
                "trigger": "at-issue date",
                "notes": "90 days after case is at issue"
            },
            "motion_calendar": {
                "description": "Motion Calendar",
                "notes": "Uniform Motion Calendar on Fridays"
            },
            "pretrial_conference": {
                "description": "Pretrial Conference",
                "deadline_days": 30,
                "trigger": "trial date",
                "direction": "before"
            },
            "pretrial_stipulation": {
                "description": "Pretrial Stipulation",
                "deadline_days": 7,
                "trigger": "pretrial conference",
                "direction": "before"
            },
            "motions_in_limine": {
                "description": "Motions in Limine",
                "deadline_days": 15,
                "trigger": "trial date",
                "direction": "before"
            }
        }
    },

    # 9th Circuit - Orange and Osceola Counties (Orlando)
    "9th_circuit": {
        "name": "Ninth Judicial Circuit (Orange & Osceola Counties - Orlando)",
        "website": "https://www.ninthcircuit.org",
        "rules": {
            "case_management": {
                "description": "Case Management Conference",
                "deadline_days": 120,
                "trigger": "case filing",
                "notes": "Per Administrative Order"
            },
            "motion_hearing": {
                "description": "Motion Hearing Notice",
                "deadline_days": 5,
                "trigger": "hearing date",
                "direction": "before",
                "notes": "5 business days notice required"
            },
            "pretrial_conference": {
                "description": "Pretrial Conference",
                "deadline_days": 14,
                "trigger": "trial date",
                "direction": "before"
            },
            "pretrial_checklist": {
                "description": "Pretrial Checklist",
                "deadline_days": 5,
                "trigger": "pretrial conference",
                "direction": "before"
            },
            "jury_instructions": {
                "description": "Proposed Jury Instructions",
                "deadline_days": 10,
                "trigger": "trial date",
                "direction": "before"
            }
        }
    }
}


# =============================================================================
# FEDERAL DISTRICT LOCAL RULES (FLORIDA)
# =============================================================================

FEDERAL_LOCAL_RULES = {
    "southern_district": {
        "name": "Southern District of Florida",
        "website": "https://www.flsd.uscourts.gov",
        "rules": {
            "scheduling_order": {
                "description": "Scheduling Order",
                "notes": "Per Local Rule 16.1 - Court issues scheduling order after Rule 26(f) conference"
            },
            "discovery_dispute": {
                "description": "Discovery Dispute Resolution",
                "notes": "Local Rule 26.1 - Must confer in good faith before filing motion to compel"
            },
            "motion_response": {
                "description": "Response to Motion",
                "deadline_days": 14,
                "trigger": "service of motion",
                "service_extension": True,
                "notes": "Local Rule 7.1(c)"
            },
            "motion_reply": {
                "description": "Reply to Response",
                "deadline_days": 7,
                "trigger": "service of response",
                "service_extension": True,
                "notes": "Local Rule 7.1(c)"
            },
            "trial_preparation": {
                "description": "Trial Preparation",
                "notes": "Per Scheduling Order and Local Rule 16.1"
            },
            "pretrial_stipulation": {
                "description": "Pretrial Stipulation",
                "deadline_days": 14,
                "trigger": "calendar call or pretrial conference",
                "direction": "before",
                "notes": "Local Rule 16.1(g)"
            },
            "proposed_jury_instructions": {
                "description": "Proposed Jury Instructions",
                "deadline_days": 14,
                "trigger": "trial date",
                "direction": "before",
                "notes": "Local Rule 51.1"
            },
            "deposition_notice": {
                "description": "Deposition Notice",
                "deadline_days": 14,
                "trigger": "deposition date",
                "direction": "before",
                "notes": "Local Rule 30.1 - 14 days reasonable notice"
            }
        }
    },
    "middle_district": {
        "name": "Middle District of Florida",
        "website": "https://www.flmd.uscourts.gov",
        "rules": {
            "case_management": {
                "description": "Case Management Report",
                "deadline_days": 14,
                "trigger": "Rule 26(f) conference",
                "notes": "Local Rule 3.05(c)"
            },
            "motion_response": {
                "description": "Response to Motion",
                "deadline_days": 14,
                "trigger": "service of motion",
                "service_extension": True,
                "notes": "Local Rule 3.01(b)"
            },
            "motion_reply": {
                "description": "Reply to Response",
                "deadline_days": 7,
                "trigger": "service of response",
                "service_extension": True,
                "notes": "Local Rule 3.01(c)"
            },
            "pretrial_statement": {
                "description": "Pretrial Statement",
                "deadline_days": 7,
                "trigger": "final pretrial conference",
                "direction": "before",
                "notes": "Local Rule 3.06"
            },
            "exhibit_list": {
                "description": "Exhibit List",
                "deadline_days": 7,
                "trigger": "final pretrial conference",
                "direction": "before"
            }
        }
    }
}


# =============================================================================
# APPELLATE RULES
# =============================================================================

FLORIDA_APPELLATE_RULES = {
    "9.110": {
        "title": "Appeal Proceedings to Review Final Orders",
        "subsections": {
            "(b)": {
                "description": "Notice of Appeal",
                "deadline_days": 30,
                "calculation": "calendar_days",
                "trigger": "rendition of order",
                "service_extension": True,
                "priority": "fatal",
                "notes": "JURISDICTIONAL - Cannot be extended"
            }
        }
    },
    "9.130": {
        "title": "Proceedings to Review Non-Final Orders",
        "subsections": {
            "(b)": {
                "description": "Notice of Appeal (Non-Final)",
                "deadline_days": 30,
                "calculation": "calendar_days",
                "trigger": "rendition of non-final order",
                "priority": "fatal"
            }
        }
    },
    "9.140": {
        "title": "Appeal Proceedings in Criminal Cases",
        "subsections": {
            "(b)(3)": {
                "description": "Notice of Appeal (Criminal)",
                "deadline_days": 30,
                "calculation": "calendar_days",
                "trigger": "rendition of sentence",
                "priority": "fatal"
            }
        }
    },
    "9.200": {
        "title": "The Record",
        "subsections": {
            "(a)(1)": {
                "description": "Designation to Reporter",
                "deadline_days": 10,
                "calculation": "calendar_days",
                "trigger": "filing notice of appeal"
            }
        }
    },
    "9.210": {
        "title": "Briefs",
        "subsections": {
            "(b)(1)": {
                "description": "Initial Brief",
                "deadline_days": 70,
                "calculation": "calendar_days",
                "trigger": "filing notice of appeal",
                "priority": "critical"
            },
            "(b)(2)": {
                "description": "Answer Brief",
                "deadline_days": 20,
                "calculation": "calendar_days",
                "trigger": "service of initial brief"
            },
            "(b)(3)": {
                "description": "Reply Brief",
                "deadline_days": 20,
                "calculation": "calendar_days",
                "trigger": "service of answer brief",
                "notes": "Optional"
            }
        }
    }
}


FEDERAL_APPELLATE_RULES = {
    "Rule 4": {
        "title": "Appeal as of Right - When Taken",
        "subsections": {
            "(a)(1)(A)": {
                "description": "Notice of Appeal (Civil)",
                "deadline_days": 30,
                "calculation": "calendar_days",
                "trigger": "entry of judgment",
                "priority": "fatal",
                "notes": "JURISDICTIONAL"
            },
            "(a)(1)(B)": {
                "description": "Notice of Appeal (USA Party)",
                "deadline_days": 60,
                "calculation": "calendar_days",
                "trigger": "entry of judgment",
                "priority": "fatal",
                "notes": "60 days when United States is a party"
            }
        }
    },
    "Rule 31": {
        "title": "Serving and Filing Briefs",
        "subsections": {
            "(a)(1)": {
                "description": "Appellant's Brief",
                "deadline_days": 40,
                "calculation": "calendar_days",
                "trigger": "record filed or docketing statement",
                "priority": "critical"
            },
            "(a)(1)_appellee": {
                "description": "Appellee's Brief",
                "deadline_days": 30,
                "calculation": "calendar_days",
                "trigger": "service of appellant's brief"
            },
            "(a)(1)_reply": {
                "description": "Reply Brief",
                "deadline_days": 21,
                "calculation": "calendar_days",
                "trigger": "service of appellee's brief",
                "notes": "Optional, but due within 21 days if filed"
            }
        }
    }
}


# =============================================================================
# DOCKET OVERSEER KNOWLEDGE - COMPREHENSIVE DEADLINES
# =============================================================================

COMMON_DEADLINE_TEMPLATES = {
    # Pleadings
    "answer_to_complaint_fl": {
        "name": "Answer to Complaint (Florida)",
        "days": 20,
        "trigger": "service of complaint",
        "rule": "Fla. R. Civ. P. 1.140(a)(1)",
        "service_extension": True,
        "jurisdiction": "florida_state",
        "priority": "fatal"
    },
    "answer_to_complaint_fed": {
        "name": "Answer to Complaint (Federal)",
        "days": 21,
        "trigger": "service of complaint",
        "rule": "FRCP 12(a)(1)(A)(i)",
        "service_extension": True,
        "jurisdiction": "federal",
        "priority": "fatal"
    },

    # Discovery
    "interrogatories_response": {
        "name": "Response to Interrogatories",
        "days": 30,
        "trigger": "service of interrogatories",
        "rule": "Fla. R. Civ. P. 1.340(a) / FRCP 33(b)(2)",
        "service_extension": True,
        "priority": "important"
    },
    "rfp_response": {
        "name": "Response to Request for Production",
        "days": 30,
        "trigger": "service of RFP",
        "rule": "Fla. R. Civ. P. 1.350(a) / FRCP 34(b)(2)(A)",
        "service_extension": True,
        "priority": "important"
    },
    "rfa_response": {
        "name": "Response to Requests for Admission",
        "days": 30,
        "trigger": "service of RFA",
        "rule": "Fla. R. Civ. P. 1.370(a) / FRCP 36(a)(3)",
        "service_extension": True,
        "priority": "fatal",
        "warning": "CRITICAL: Failure to respond = DEEMED ADMITTED"
    },

    # Motions
    "motion_response_fl": {
        "name": "Response to Motion (Florida)",
        "days": 10,
        "trigger": "service of motion",
        "rule": "Fla. R. Civ. P. 1.160(b)",
        "service_extension": True,
        "priority": "important"
    },
    "msj_response_fl": {
        "name": "Response to Motion for Summary Judgment (Florida)",
        "days": 20,
        "trigger": "service of MSJ",
        "rule": "Fla. R. Civ. P. 1.510(c)",
        "service_extension": True,
        "priority": "critical"
    },

    # Appeals
    "notice_of_appeal_fl": {
        "name": "Notice of Appeal (Florida)",
        "days": 30,
        "trigger": "rendition of order",
        "rule": "Fla. R. App. P. 9.110(b)",
        "service_extension": True,
        "priority": "fatal",
        "warning": "JURISDICTIONAL - Cannot be extended"
    },
    "notice_of_appeal_fed": {
        "name": "Notice of Appeal (Federal)",
        "days": 30,
        "trigger": "entry of judgment",
        "rule": "FRAP 4(a)(1)(A)",
        "priority": "fatal",
        "warning": "JURISDICTIONAL - Cannot be extended"
    }
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_rule_details(rule_number: str, jurisdiction: str = "florida_state") -> Optional[Dict]:
    """Get detailed information about a specific rule."""
    if jurisdiction == "florida_state" or jurisdiction == "state":
        if rule_number in FLORIDA_CIVIL_PROCEDURE_RULES:
            return FLORIDA_CIVIL_PROCEDURE_RULES[rule_number]
        elif rule_number in FLORIDA_JUDICIAL_ADMINISTRATION_RULES:
            return FLORIDA_JUDICIAL_ADMINISTRATION_RULES[rule_number]
        elif rule_number in FLORIDA_APPELLATE_RULES:
            return FLORIDA_APPELLATE_RULES[rule_number]
    elif jurisdiction == "federal":
        # Remove "Rule " prefix if present
        rule_key = rule_number.replace("Rule ", "")
        if f"Rule {rule_key}" in FEDERAL_CIVIL_PROCEDURE_RULES:
            return FEDERAL_CIVIL_PROCEDURE_RULES[f"Rule {rule_key}"]
        elif f"Rule {rule_key}" in FEDERAL_APPELLATE_RULES:
            return FEDERAL_APPELLATE_RULES[f"Rule {rule_key}"]
    return None


def get_local_rules(circuit: str) -> Optional[Dict]:
    """Get local rules for a specific Florida circuit."""
    circuit_key = circuit.lower().replace(" ", "_")
    if not circuit_key.endswith("_circuit"):
        circuit_key = f"{circuit_key}_circuit"
    return FLORIDA_LOCAL_RULES.get(circuit_key)


def get_federal_local_rules(district: str) -> Optional[Dict]:
    """Get local rules for a federal district."""
    district_key = district.lower().replace(" ", "_")
    if "southern" in district_key:
        return FEDERAL_LOCAL_RULES.get("southern_district")
    elif "middle" in district_key:
        return FEDERAL_LOCAL_RULES.get("middle_district")
    return None


def get_deadline_template(template_key: str) -> Optional[Dict]:
    """Get a common deadline template."""
    return COMMON_DEADLINE_TEMPLATES.get(template_key)


def format_rules_for_ai_context() -> str:
    """Format all rules knowledge into a string for AI context."""
    sections = []

    # Florida Civil Procedure highlights
    sections.append("## FLORIDA RULES OF CIVIL PROCEDURE - KEY DEADLINES")
    sections.append("- Answer to Complaint: 20 days (Fla. R. Civ. P. 1.140(a)(1))")
    sections.append("- Response to Discovery: 30 days (Rules 1.340, 1.350, 1.370)")
    sections.append("- Response to Motion: 10 days (Rule 1.160(b))")
    sections.append("- Response to MSJ: 20 days (Rule 1.510(c))")
    sections.append("- Service by mail adds 5 days (Rule 2.514(b))")
    sections.append("- Electronic service: NO additional days (since Jan 2019)")
    sections.append("")

    # Federal Civil Procedure highlights
    sections.append("## FEDERAL RULES OF CIVIL PROCEDURE - KEY DEADLINES")
    sections.append("- Answer to Complaint: 21 days (FRCP 12(a)(1)(A)(i))")
    sections.append("- Response to Discovery: 30 days (Rules 33, 34, 36)")
    sections.append("- Initial Disclosures: 14 days after Rule 26(f) conference")
    sections.append("- Service by mail adds 3 days (FRCP 6(d))")
    sections.append("")

    # Appellate highlights
    sections.append("## APPELLATE DEADLINES (JURISDICTIONAL)")
    sections.append("- Florida Notice of Appeal: 30 days from rendition (Fla. R. App. P. 9.110(b))")
    sections.append("- Federal Notice of Appeal: 30 days from entry (FRAP 4(a)(1)(A))")
    sections.append("- Federal with USA party: 60 days (FRAP 4(a)(1)(B))")
    sections.append("")

    # Local Rules
    sections.append("## FLORIDA LOCAL RULES")
    sections.append("- 11th Circuit (Miami-Dade): Pretrial stip 10 days before trial")
    sections.append("- 17th Circuit (Broward): CMC within 180 days of filing")
    sections.append("- 13th Circuit (Tampa): UMC on Fridays, pretrial stip 7 days before CMC")
    sections.append("- 9th Circuit (Orlando): Jury instructions 10 days before trial")

    return "\n".join(sections)
