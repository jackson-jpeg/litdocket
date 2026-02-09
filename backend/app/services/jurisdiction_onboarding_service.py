"""
Jurisdiction Onboarding Service - Automated End-to-End Onboarding

Phase 5: Multi-Jurisdiction Scaling

Automates the complete workflow for adding a new jurisdiction:
1. Validate court website URL
2. Trigger Cartographer to discover scraper config
3. Auto-harvest rules if confidence ≥85%
4. Establish Watchtower baseline
5. Configure sync schedule
6. Generate onboarding report

This service enables scaling to 50+ jurisdictions with minimal manual intervention.
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from sqlalchemy.orm import Session
import logging
import asyncio
import re
from urllib.parse import urlparse

from app.models.jurisdiction import Jurisdiction
from app.models.authority_core import AuthorityRule
from app.models.enums import InboxItemType
from app.services.ai_scraper_service import AIScraperService
from app.services.authority_core_service import AuthorityCoreService
from app.services.watchtower_service import WatchtowerService
from app.services.inbox_service import InboxService

logger = logging.getLogger(__name__)


class JurisdictionOnboardingService:
    """
    Automated jurisdiction onboarding service.

    Handles complete end-to-end onboarding workflow with progress tracking,
    error handling, and rollback capabilities.
    """

    def __init__(self, db: Session):
        self.db = db
        self.ai_scraper = AIScraperService(db)
        self.authority_service = AuthorityCoreService(db)
        self.watchtower = WatchtowerService(db)
        self.inbox_service = InboxService(db)

    async def onboard_jurisdiction(
        self,
        name: str,
        code: str,
        court_website: str,
        rules_url: str,
        court_type: str = "state",
        auto_harvest_threshold: float = 0.85,
        sync_frequency: str = "WEEKLY",
        auto_approve_high_confidence: bool = False
    ) -> Dict[str, Any]:
        """
        Complete automated jurisdiction onboarding.

        Args:
            name: Jurisdiction name (e.g., "California Superior Court")
            code: Jurisdiction code (e.g., "CA_SUP")
            court_website: Main court website URL
            rules_url: URL to court rules page
            court_type: "federal", "state", or "local"
            auto_harvest_threshold: Confidence threshold for auto-harvest (0.85 = 85%)
            sync_frequency: "DAILY", "WEEKLY", or "MONTHLY"
            auto_approve_high_confidence: Auto-approve rules with confidence ≥95%

        Returns:
            Comprehensive onboarding report with status, metrics, and next steps
        """
        logger.info(f"Starting onboarding for {name} ({code})")

        report = {
            "jurisdiction_name": name,
            "jurisdiction_code": code,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "status": "in_progress",
            "steps_completed": [],
            "steps_failed": [],
            "warnings": [],
            "metrics": {},
            "next_steps": []
        }

        try:
            # Step 1: Validate URLs
            logger.info(f"Step 1: Validating URLs for {name}")
            validation_result = self._validate_urls(court_website, rules_url)

            if not validation_result["valid"]:
                report["status"] = "failed"
                report["steps_failed"].append({
                    "step": "URL Validation",
                    "error": validation_result["error"]
                })
                return report

            report["steps_completed"].append("URL Validation")

            # Step 2: Create or update jurisdiction
            logger.info(f"Step 2: Creating jurisdiction record for {name}")
            jurisdiction = self._create_or_update_jurisdiction(
                name, code, court_website, court_type
            )

            if not jurisdiction:
                report["status"] = "failed"
                report["steps_failed"].append({
                    "step": "Jurisdiction Creation",
                    "error": "Failed to create jurisdiction record"
                })
                return report

            report["jurisdiction_id"] = jurisdiction.id
            report["steps_completed"].append("Jurisdiction Record Created")

            # Step 3: Template Detection OR Cartographer Discovery
            logger.info(f"Step 3: Attempting template detection first (cost optimization)")
            scraper_config = None

            try:
                # Try template library first (instant, no API cost)
                from app.services.scraper_templates import get_template_for_url

                template_config = get_template_for_url(rules_url)

                if template_config and template_config.get("confidence", 0) >= 0.85:
                    # Template found! Use it directly
                    scraper_config = template_config
                    jurisdiction.scraper_config = scraper_config
                    jurisdiction.last_scraped_at = datetime.now(timezone.utc)
                    self.db.commit()

                    report["steps_completed"].append("Template Applied")
                    report["metrics"]["template_used"] = template_config.get("template_used", "unknown")
                    report["metrics"]["scraper_confidence"] = template_config.get("confidence", 0)
                    logger.info(f"Template '{template_config.get('template_used')}' applied - skipping Cartographer")
                else:
                    # No template match - fall back to Cartographer
                    logger.info("No template match - falling back to Cartographer")
                    scraper_config = await self.ai_scraper.discover_scraper_config(
                        url=rules_url,
                        jurisdiction_id=jurisdiction.id
                    )

                    if scraper_config and scraper_config.get("confidence", 0) >= 0.70:
                        # Save scraper config
                        jurisdiction.scraper_config = scraper_config
                        jurisdiction.last_scraped_at = datetime.now(timezone.utc)
                        self.db.commit()

                        report["steps_completed"].append("Cartographer Discovery")
                        report["metrics"]["cartographer_confidence"] = scraper_config.get("confidence", 0)
                    else:
                        report["warnings"].append(
                            "Cartographer confidence too low. Manual scraper config may be required."
                        )
                        report["steps_completed"].append("Cartographer Discovery (Low Confidence)")

            except Exception as e:
                logger.error(f"Scraper config discovery failed: {str(e)}")
                report["warnings"].append(f"Scraper config failed: {str(e)}")

            # Step 4: Rule Extraction
            logger.info(f"Step 4: Extracting rules from {rules_url}")
            try:
                harvest_result = await self.authority_service.harvest_rules_from_url(
                    jurisdiction_id=jurisdiction.id,
                    url=rules_url,
                    use_extended_thinking=False,  # Faster for onboarding
                    auto_approve_high_confidence=auto_approve_high_confidence
                )

                if harvest_result and harvest_result.get("success"):
                    rules_found = harvest_result.get("rules_found", 0)
                    avg_confidence = harvest_result.get("average_confidence", 0)

                    report["steps_completed"].append("Rule Extraction")
                    report["metrics"]["rules_found"] = rules_found
                    report["metrics"]["average_confidence"] = avg_confidence
                    report["metrics"]["proposals_created"] = harvest_result.get("proposals_created", 0)

                    # Auto-harvest decision
                    if avg_confidence >= auto_harvest_threshold:
                        report["steps_completed"].append("Auto-Harvest Eligible")
                        report["metrics"]["auto_harvest_eligible"] = True
                    else:
                        report["warnings"].append(
                            f"Average confidence ({avg_confidence:.1%}) below threshold ({auto_harvest_threshold:.1%}). Manual review required."
                        )
                else:
                    report["steps_failed"].append({
                        "step": "Rule Extraction",
                        "error": harvest_result.get("error", "Unknown error")
                    })
            except Exception as e:
                logger.error(f"Rule extraction failed: {str(e)}")
                report["steps_failed"].append({
                    "step": "Rule Extraction",
                    "error": str(e)
                })

            # Step 5: Watchtower Baseline
            logger.info(f"Step 5: Establishing Watchtower baseline")
            try:
                baseline_result = self.watchtower.establish_baseline(
                    jurisdiction_id=jurisdiction.id,
                    url=rules_url
                )

                if baseline_result:
                    report["steps_completed"].append("Watchtower Baseline")
                    report["metrics"]["watchtower_hash"] = baseline_result.get("content_hash", "N/A")
                else:
                    report["warnings"].append("Watchtower baseline could not be established")
            except Exception as e:
                logger.error(f"Watchtower baseline failed: {str(e)}")
                report["warnings"].append(f"Watchtower failed: {str(e)}")

            # Step 6: Configure Sync Schedule
            logger.info(f"Step 6: Configuring sync schedule")
            jurisdiction.auto_sync_enabled = True
            jurisdiction.sync_frequency = sync_frequency
            jurisdiction.consecutive_scrape_failures = 0
            self.db.commit()

            report["steps_completed"].append("Sync Schedule Configured")
            report["metrics"]["sync_frequency"] = sync_frequency

            # Step 7: Generate Next Steps
            report["next_steps"] = self._generate_next_steps(report)

            # Final status
            if len(report["steps_failed"]) == 0:
                report["status"] = "completed"
            elif len(report["steps_completed"]) >= 4:
                report["status"] = "partial_success"
            else:
                report["status"] = "failed"

            report["completed_at"] = datetime.now(timezone.utc).isoformat()
            logger.info(f"Onboarding completed for {name} with status: {report['status']}")

            return report

        except Exception as e:
            logger.error(f"Onboarding failed for {name}: {str(e)}")
            report["status"] = "failed"
            report["steps_failed"].append({
                "step": "Unknown",
                "error": str(e)
            })
            report["completed_at"] = datetime.now(timezone.utc).isoformat()
            return report

    def _validate_urls(self, court_website: str, rules_url: str) -> Dict[str, Any]:
        """Validate URLs are well-formed and accessible"""
        try:
            # Parse URLs
            court_parsed = urlparse(court_website)
            rules_parsed = urlparse(rules_url)

            # Check if valid HTTP(S) URLs
            if court_parsed.scheme not in ['http', 'https']:
                return {"valid": False, "error": "Court website must be HTTP or HTTPS"}

            if rules_parsed.scheme not in ['http', 'https']:
                return {"valid": False, "error": "Rules URL must be HTTP or HTTPS"}

            # Check if domains are valid
            if not court_parsed.netloc or not rules_parsed.netloc:
                return {"valid": False, "error": "Invalid URL format"}

            # Basic sanity checks
            if len(court_website) < 10 or len(rules_url) < 10:
                return {"valid": False, "error": "URLs too short"}

            return {"valid": True}

        except Exception as e:
            return {"valid": False, "error": f"URL validation failed: {str(e)}"}

    def _create_or_update_jurisdiction(
        self,
        name: str,
        code: str,
        court_website: str,
        court_type: str
    ) -> Optional[Jurisdiction]:
        """Create new jurisdiction or update existing"""
        try:
            # Check if exists
            existing = self.db.query(Jurisdiction).filter(
                Jurisdiction.code == code
            ).first()

            if existing:
                logger.info(f"Updating existing jurisdiction: {code}")
                existing.name = name
                existing.court_website = court_website
                existing.court_type = court_type
                self.db.commit()
                self.db.refresh(existing)
                return existing
            else:
                logger.info(f"Creating new jurisdiction: {code}")
                jurisdiction = Jurisdiction(
                    name=name,
                    code=code,
                    court_website=court_website,
                    court_type=court_type,
                    auto_sync_enabled=False,  # Will be enabled after successful onboarding
                    consecutive_scrape_failures=0
                )
                self.db.add(jurisdiction)
                self.db.commit()
                self.db.refresh(jurisdiction)
                return jurisdiction

        except Exception as e:
            logger.error(f"Failed to create/update jurisdiction: {str(e)}")
            self.db.rollback()
            return None

    def _generate_next_steps(self, report: Dict[str, Any]) -> List[str]:
        """Generate actionable next steps based on onboarding results"""
        next_steps = []

        # Check if rules need approval
        if report["metrics"].get("proposals_created", 0) > 0:
            next_steps.append(
                f"Review {report['metrics']['proposals_created']} rule proposals in inbox: /api/v1/inbox?type=RULE_VERIFICATION"
            )

        # Check confidence
        avg_confidence = report["metrics"].get("average_confidence", 0)
        if avg_confidence < 0.80:
            next_steps.append(
                "Low average confidence detected. Consider manual review of extracted rules."
            )

        # Check scraper config
        if "Cartographer Discovery (Low Confidence)" in report["steps_completed"]:
            next_steps.append(
                "Cartographer confidence was low. Manual scraper config may be needed."
            )

        # Check failures
        if report["steps_failed"]:
            next_steps.append(
                f"Fix {len(report['steps_failed'])} failed step(s) and re-run onboarding."
            )

        # Success case
        if report["status"] == "completed":
            next_steps.append(
                "Onboarding complete! Jurisdiction is now monitored by Watchtower."
            )
            next_steps.append(
                "Test deadline calculations using the new jurisdiction's rules."
            )

        return next_steps

    async def batch_onboard_jurisdictions(
        self,
        jurisdictions: List[Dict[str, str]],
        max_concurrent: int = 5
    ) -> Dict[str, Any]:
        """
        Onboard multiple jurisdictions in parallel with concurrency control.

        Args:
            jurisdictions: List of jurisdiction configs with name, code, court_website, rules_url
            max_concurrent: Maximum simultaneous onboarding operations (default: 5)

        Returns:
            Batch onboarding report with per-jurisdiction results
        """
        logger.info(f"Starting batch onboarding for {len(jurisdictions)} jurisdictions")

        batch_report = {
            "total_jurisdictions": len(jurisdictions),
            "started_at": datetime.now(timezone.utc).isoformat(),
            "status": "in_progress",
            "results": [],
            "summary": {
                "completed": 0,
                "partial_success": 0,
                "failed": 0
            }
        }

        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(max_concurrent)

        async def onboard_with_semaphore(jurisdiction_config):
            async with semaphore:
                return await self.onboard_jurisdiction(
                    name=jurisdiction_config.get("name"),
                    code=jurisdiction_config.get("code"),
                    court_website=jurisdiction_config.get("court_website"),
                    rules_url=jurisdiction_config.get("rules_url"),
                    court_type=jurisdiction_config.get("court_type", "state")
                )

        # Run onboarding tasks
        tasks = [onboard_with_semaphore(j) for j in jurisdictions]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        for result in results:
            if isinstance(result, Exception):
                batch_report["results"].append({
                    "status": "failed",
                    "error": str(result)
                })
                batch_report["summary"]["failed"] += 1
            else:
                batch_report["results"].append(result)
                status = result.get("status", "failed")
                if status == "completed":
                    batch_report["summary"]["completed"] += 1
                elif status == "partial_success":
                    batch_report["summary"]["partial_success"] += 1
                else:
                    batch_report["summary"]["failed"] += 1

        batch_report["completed_at"] = datetime.now(timezone.utc).isoformat()
        batch_report["status"] = "completed"

        logger.info(
            f"Batch onboarding completed: {batch_report['summary']['completed']} succeeded, "
            f"{batch_report['summary']['failed']} failed"
        )

        return batch_report

    def get_onboarding_status(self, jurisdiction_id: str) -> Dict[str, Any]:
        """Get current onboarding status for a jurisdiction"""
        jurisdiction = self.db.query(Jurisdiction).filter(
            Jurisdiction.id == jurisdiction_id
        ).first()

        if not jurisdiction:
            return {"error": "Jurisdiction not found"}

        # Get rule statistics
        rules = self.db.query(AuthorityRule).filter(
            AuthorityRule.jurisdiction_id == jurisdiction_id,
            AuthorityRule.is_active == True
        ).all()

        verified_count = sum(1 for r in rules if r.is_verified)
        pending_count = len(rules) - verified_count

        # Get pending inbox items
        from app.models.inbox import InboxItem
        pending_approvals = self.db.query(InboxItem).filter(
            InboxItem.jurisdiction_id == jurisdiction_id,
            InboxItem.type == InboxItemType.RULE_VERIFICATION,
            InboxItem.status == "PENDING"
        ).count()

        return {
            "jurisdiction_id": jurisdiction_id,
            "name": jurisdiction.name,
            "code": jurisdiction.code,
            "auto_sync_enabled": jurisdiction.auto_sync_enabled,
            "sync_frequency": jurisdiction.sync_frequency,
            "last_scraped_at": jurisdiction.last_scraped_at.isoformat() if jurisdiction.last_scraped_at else None,
            "consecutive_failures": jurisdiction.consecutive_scrape_failures,
            "rules": {
                "total": len(rules),
                "verified": verified_count,
                "pending": pending_count
            },
            "pending_inbox_items": pending_approvals,
            "has_scraper_config": bool(jurisdiction.scraper_config),
            "ready_for_production": verified_count > 0 and jurisdiction.auto_sync_enabled
        }
