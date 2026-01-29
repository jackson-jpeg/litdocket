"""
Rules Scraper API - Endpoints for managing the automated rules gathering pipeline

This API provides:
1. Scraping job management (start, monitor, cancel)
2. Rules queue management (view, validate, approve, reject)
3. Coverage statistics and tracking
4. Admin approval workflow

Security: Admin-only endpoints for production use
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime, timezone
import logging

from app.database import get_db
from app.auth.middleware import get_current_user, get_current_admin
from app.models import User, ScrapedRule, JurisdictionCoverage, ScrapingJob
from app.models.enums import ScrapedRuleStatus, ScraperCourtType
from app.services.rules_scraper import rules_scraper, US_JURISDICTIONS, FEDERAL_JURISDICTIONS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rules-scraper", tags=["Rules Scraper"])


# ============================================================================
# Coverage & Statistics
# ============================================================================

@router.get("/coverage")
async def get_coverage_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get overall coverage statistics for all jurisdictions.

    Returns summary of scraping progress toward "all courts captured" goal.
    """
    # Get database stats
    coverage_records = db.query(JurisdictionCoverage).all()

    # Calculate totals
    total_scraped = sum(c.rules_scraped for c in coverage_records)
    total_validated = sum(c.rules_validated for c in coverage_records)
    total_deployed = sum(c.rules_deployed for c in coverage_records)
    total_expected = sum(c.total_rules_expected for c in coverage_records)

    # Count jurisdictions with any coverage
    jurisdictions_with_rules = len([c for c in coverage_records if c.rules_deployed > 0])

    # In-memory stats from scraper service
    service_stats = rules_scraper.get_coverage_stats()

    return {
        "success": True,
        "data": {
            "summary": {
                "total_jurisdictions": len(US_JURISDICTIONS) + len(FEDERAL_JURISDICTIONS),
                "jurisdictions_covered": jurisdictions_with_rules,
                "us_states": len(US_JURISDICTIONS),
                "federal_courts": len(FEDERAL_JURISDICTIONS),
            },
            "pipeline": {
                "total_scraped": total_scraped,
                "total_validated": total_validated,
                "total_deployed": total_deployed,
                "total_expected": total_expected,
                "coverage_percentage": (total_deployed / total_expected * 100) if total_expected > 0 else 0,
            },
            "queue": service_stats,
            "jurisdictions": [c.to_dict() for c in coverage_records],
        }
    }


@router.get("/coverage/{jurisdiction_code}")
async def get_jurisdiction_coverage(
    jurisdiction_code: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get coverage details for a specific jurisdiction."""
    coverage = db.query(JurisdictionCoverage).filter(
        JurisdictionCoverage.jurisdiction_code == jurisdiction_code
    ).first()

    if not coverage:
        # Check if it's a valid jurisdiction
        if jurisdiction_code not in US_JURISDICTIONS and jurisdiction_code not in FEDERAL_JURISDICTIONS:
            raise HTTPException(status_code=404, detail="Invalid jurisdiction code")

        # Create new coverage record
        name = US_JURISDICTIONS.get(jurisdiction_code) or FEDERAL_JURISDICTIONS.get(jurisdiction_code)
        coverage = JurisdictionCoverage(
            jurisdiction_code=jurisdiction_code,
            jurisdiction_name=name,
            jurisdiction_type="state" if jurisdiction_code in US_JURISDICTIONS else "federal",
        )
        db.add(coverage)
        db.commit()
        db.refresh(coverage)

    # Get rules for this jurisdiction
    rules = db.query(ScrapedRule).filter(
        ScrapedRule.jurisdiction_code == jurisdiction_code
    ).all()

    return {
        "success": True,
        "data": {
            "coverage": coverage.to_dict(),
            "rules_by_status": {
                status.value: len([r for r in rules if r.status == status])
                for status in ScrapedRuleStatus
            },
            "recent_rules": [r.to_dict() for r in rules[:20]],
        }
    }


# ============================================================================
# Rules Queue Management
# ============================================================================

@router.get("/queue")
async def get_rules_queue(
    status: Optional[str] = Query(None, description="Filter by status"),
    jurisdiction: Optional[str] = Query(None, description="Filter by jurisdiction"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get scraped rules from the queue with optional filters.
    """
    query = db.query(ScrapedRule)

    if status:
        try:
            status_enum = ScrapedRuleStatus(status)
            query = query.filter(ScrapedRule.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    if jurisdiction:
        query = query.filter(ScrapedRule.jurisdiction_code == jurisdiction)

    total = query.count()
    rules = query.order_by(ScrapedRule.created_at.desc()).offset(skip).limit(limit).all()

    return {
        "success": True,
        "data": {
            "rules": [r.to_dict() for r in rules],
            "total": total,
            "skip": skip,
            "limit": limit,
        }
    }


@router.get("/queue/{rule_id}")
async def get_rule_details(
    rule_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed information about a specific scraped rule."""
    rule = db.query(ScrapedRule).filter(ScrapedRule.id == rule_id).first()

    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    return {
        "success": True,
        "data": {
            "id": rule.id,
            "jurisdiction_code": rule.jurisdiction_code,
            "jurisdiction_name": rule.jurisdiction_name,
            "court_type": rule.court_type.value if rule.court_type else None,
            "rule_number": rule.rule_number,
            "rule_title": rule.rule_title,
            "rule_text": rule.rule_text,  # Full text
            "rule_citation": rule.rule_citation,
            "source_url": rule.source_url,
            "source_document": rule.source_document,
            "effective_date": rule.effective_date.isoformat() if rule.effective_date else None,
            "triggers": rule.triggers or [],
            "deadlines": rule.deadlines or [],
            "status": rule.status.value if rule.status else None,
            "confidence_score": rule.confidence_score,
            "validation_notes": rule.validation_notes,
            "validation_issues": rule.validation_issues or [],
            "validated_at": rule.validated_at.isoformat() if rule.validated_at else None,
            "approved_by": rule.approved_by,
            "approved_at": rule.approved_at.isoformat() if rule.approved_at else None,
            "created_at": rule.created_at.isoformat() if rule.created_at else None,
        }
    }


# ============================================================================
# Approval Workflow
# ============================================================================

@router.post("/queue/{rule_id}/approve")
async def approve_rule(
    rule_id: str,
    notes: Optional[str] = None,
    current_user: User = Depends(get_current_admin),  # Admin only
    db: Session = Depends(get_db)
):
    """
    Approve a validated rule for deployment.

    This moves the rule to APPROVED status, ready to be deployed as a RuleTemplate.
    """
    rule = db.query(ScrapedRule).filter(ScrapedRule.id == rule_id).first()

    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    if rule.status not in [ScrapedRuleStatus.VALIDATED, ScrapedRuleStatus.PENDING_APPROVAL]:
        raise HTTPException(
            status_code=400,
            detail=f"Rule must be validated or pending approval. Current status: {rule.status.value}"
        )

    rule.status = ScrapedRuleStatus.APPROVED
    rule.approved_by = str(current_user.id)
    rule.approved_at = datetime.now(timezone.utc)
    rule.approval_notes = notes

    # Update coverage stats
    coverage = db.query(JurisdictionCoverage).filter(
        JurisdictionCoverage.jurisdiction_code == rule.jurisdiction_code
    ).first()
    if coverage:
        coverage.rules_approved += 1
        coverage.needs_review = db.query(ScrapedRule).filter(
            ScrapedRule.jurisdiction_code == rule.jurisdiction_code,
            ScrapedRule.status == ScrapedRuleStatus.PENDING_APPROVAL
        ).count() > 0

    db.commit()
    db.refresh(rule)

    logger.info(f"Rule {rule_id} approved by user {current_user.id}")

    return {
        "success": True,
        "message": "Rule approved successfully",
        "data": rule.to_dict()
    }


@router.post("/queue/{rule_id}/reject")
async def reject_rule(
    rule_id: str,
    reason: str,
    current_user: User = Depends(get_current_admin),  # Admin only
    db: Session = Depends(get_db)
):
    """
    Reject a scraped rule.

    Rejected rules are kept for reference but will not be deployed.
    """
    rule = db.query(ScrapedRule).filter(ScrapedRule.id == rule_id).first()

    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    rule.status = ScrapedRuleStatus.REJECTED
    rule.approved_by = str(current_user.id)
    rule.approved_at = datetime.now(timezone.utc)
    rule.approval_notes = f"REJECTED: {reason}"

    # Update coverage stats
    coverage = db.query(JurisdictionCoverage).filter(
        JurisdictionCoverage.jurisdiction_code == rule.jurisdiction_code
    ).first()
    if coverage:
        coverage.rules_rejected += 1

    db.commit()

    logger.info(f"Rule {rule_id} rejected by user {current_user.id}: {reason}")

    return {
        "success": True,
        "message": "Rule rejected",
        "data": rule.to_dict()
    }


# ============================================================================
# Scraping Jobs
# ============================================================================

@router.get("/jobs")
async def get_scraping_jobs(
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get list of scraping jobs."""
    query = db.query(ScrapingJob)

    if status:
        query = query.filter(ScrapingJob.status == status)

    total = query.count()
    jobs = query.order_by(ScrapingJob.created_at.desc()).offset(skip).limit(limit).all()

    return {
        "success": True,
        "data": {
            "jobs": [j.to_dict() for j in jobs],
            "total": total,
        }
    }


@router.post("/jobs/scrape")
async def start_scraping_job(
    jurisdiction_code: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_admin),  # Admin only
    db: Session = Depends(get_db)
):
    """
    Start a scraping job for a jurisdiction.

    This creates a background job that will scrape rules from court sources.
    """
    # Validate jurisdiction
    if jurisdiction_code not in US_JURISDICTIONS and jurisdiction_code not in FEDERAL_JURISDICTIONS:
        raise HTTPException(status_code=400, detail="Invalid jurisdiction code")

    # Create job record
    job = ScrapingJob(
        job_type="jurisdiction_scrape",
        jurisdiction_code=jurisdiction_code,
        status="pending",
        initiated_by=str(current_user.id),
        config={"jurisdiction": jurisdiction_code}
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    logger.info(f"Scraping job {job.id} created for {jurisdiction_code}")

    # Note: In production, this would trigger a background worker
    # For now, we just create the job record
    # background_tasks.add_task(run_scraping_job, job.id)

    return {
        "success": True,
        "message": f"Scraping job started for {jurisdiction_code}",
        "data": job.to_dict()
    }


@router.post("/jobs/validate")
async def start_validation_job(
    batch_size: int = Query(10, ge=1, le=100),
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(get_current_admin),  # Admin only
    db: Session = Depends(get_db)
):
    """
    Start a validation job to process scraped rules with Opus 4.5.
    """
    # Create job record
    job = ScrapingJob(
        job_type="batch_validate",
        status="pending",
        initiated_by=str(current_user.id),
        config={"batch_size": batch_size}
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    logger.info(f"Validation job {job.id} created for batch of {batch_size}")

    return {
        "success": True,
        "message": f"Validation job started for {batch_size} rules",
        "data": job.to_dict()
    }


# ============================================================================
# Utility Endpoints
# ============================================================================

@router.get("/jurisdictions")
async def list_jurisdictions(
    current_user: User = Depends(get_current_user)
):
    """List all available jurisdictions for scraping."""
    return {
        "success": True,
        "data": {
            "us_states": [
                {"code": code, "name": name}
                for code, name in sorted(US_JURISDICTIONS.items(), key=lambda x: x[1])
            ],
            "federal_courts": [
                {"code": code, "name": name}
                for code, name in sorted(FEDERAL_JURISDICTIONS.items(), key=lambda x: x[1])
            ],
            "total": len(US_JURISDICTIONS) + len(FEDERAL_JURISDICTIONS)
        }
    }


@router.get("/models")
async def get_ai_models(
    current_user: User = Depends(get_current_user)
):
    """Get information about AI models used in the scraping pipeline."""
    from app.config import settings

    return {
        "success": True,
        "data": {
            "scraping_model": {
                "name": "Claude Haiku",
                "model_id": settings.AI_MODEL_HAIKU,
                "use_case": "High-volume rule extraction",
                "cost_tier": "low"
            },
            "validation_model": {
                "name": "Claude Opus 4.5",
                "model_id": settings.AI_MODEL_OPUS,
                "use_case": "Quality validation and enrichment",
                "cost_tier": "high"
            },
            "default_model": {
                "name": "Claude Opus 4.5",
                "model_id": settings.DEFAULT_AI_MODEL,
                "use_case": "Document analysis, chat, legal research",
                "cost_tier": "high"
            }
        }
    }
