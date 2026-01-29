"""
Rule Proposal Model

Phase 2 of intelligent document recognition. This model stores AI-proposed
deadline rules that require attorney review before being applied.

Proposals are created when:
1. A document is uploaded that doesn't match known triggers
2. The user clicks "Research Deadlines" to find applicable rules
3. The RuleDiscoveryService finds potential rules

Workflow:
- status='pending': Awaiting attorney review
- status='approved': Converted to active rule in rule_templates
- status='rejected': Dismissed by attorney
- status='modified': Approved with changes
"""

from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, Numeric, JSON, func
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class RuleProposal(Base):
    __tablename__ = "rule_proposals"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Link to source document that triggered the research
    case_id = Column(String(36), ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    user_id = Column(String(36), nullable=False, index=True)

    # What trigger event was detected/proposed
    # e.g., "Receipt of Motion for Sanctions", "Service of Subpoena"
    proposed_trigger = Column(String(255), nullable=False)
    proposed_trigger_type = Column(String(100))

    # Proposed deadline rule
    proposed_days = Column(Integer, nullable=False)
    proposed_priority = Column(String(20), default="standard")
    proposed_calculation_method = Column(String(50), default="calendar_days")

    # Rule citation if found
    # e.g., "Fla. R. Civ. P. 1.140(b)", "FRCP 12(a)(1)"
    citation = Column(String(255))
    citation_url = Column(String(500))

    # Source text that supports this proposal
    # The exact quote from the rule or source that justifies this deadline
    source_text = Column(Text)
    source_snippet = Column(Text)

    # AI reasoning for this proposal
    reasoning = Column(Text)

    # AI confidence in this proposal (0.0 - 1.0)
    confidence_score = Column(Numeric(3, 2))

    # Detected conflicts with existing rules
    # JSON array: [{"type": "STANDARD_DEVIATION", "message": "...", "severity": "warning"}]
    conflicts = Column(JSON, default=list)

    # Research sources used to generate this proposal
    # JSON array: [{"source_type": "local_rule", "citation": "...", "text": "..."}]
    research_sources = Column(JSON, default=list)

    # Warnings or caveats about this proposal
    # JSON array of strings
    warnings = Column(JSON, default=list)

    # Review workflow
    status = Column(String(20), default="pending", index=True)
    reviewed_by = Column(String(36))
    reviewed_at = Column(DateTime(timezone=True))
    user_notes = Column(Text)  # Attorney's notes on decision

    # If approved, link to the created rule template
    created_rule_template_id = Column(String(36))

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    case = relationship("Case", backref="rule_proposals")
    document = relationship("Document", backref="rule_proposals")

    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "case_id": self.case_id,
            "document_id": self.document_id,
            "user_id": self.user_id,
            "proposed_trigger": self.proposed_trigger,
            "proposed_trigger_type": self.proposed_trigger_type,
            "proposed_days": self.proposed_days,
            "proposed_priority": self.proposed_priority,
            "proposed_calculation_method": self.proposed_calculation_method,
            "citation": self.citation,
            "citation_url": self.citation_url,
            "source_text": self.source_text,
            "reasoning": self.reasoning,
            "confidence_score": float(self.confidence_score) if self.confidence_score else None,
            "conflicts": self.conflicts or [],
            "warnings": self.warnings or [],
            "status": self.status,
            "reviewed_by": self.reviewed_by,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "user_notes": self.user_notes,
            "created_rule_template_id": self.created_rule_template_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<RuleProposal {self.id}: {self.proposed_trigger} ({self.proposed_days} days) - {self.status}>"
