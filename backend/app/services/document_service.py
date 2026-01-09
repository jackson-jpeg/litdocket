from typing import Dict, Optional, List, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
import uuid
import logging
from datetime import datetime

from app.services.ai_service import AIService

logger = logging.getLogger(__name__)
from app.services.firebase_service import firebase_service
from app.services.deadline_service import DeadlineService
from app.services.confidence_scoring import confidence_scorer
from app.services.jurisdiction_detector import JurisdictionDetector
from app.utils.pdf_parser import extract_text_from_pdf, get_pdf_metadata
from app.models.document import Document
from app.models.case import Case
from app.models.deadline import Deadline
from app.models.jurisdiction import CaseRuleSet


class DocumentService:
    """Service for document processing and analysis"""

    def __init__(self, db: Session):
        self.db = db
        self.ai_service = AIService()
        self.deadline_service = DeadlineService()
        self.jurisdiction_detector = JurisdictionDetector(db)

    def _safe_commit(self):
        """Safely commit transaction with rollback on failure"""
        try:
            self.db.commit()
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database commit failed: {e}")
            raise

    def _safe_rollback(self):
        """Safely rollback transaction"""
        try:
            self.db.rollback()
        except Exception as e:
            logger.error(f"Rollback failed: {e}")

    def ensure_case_exists(
        self,
        user_id: str,
        case_number: Optional[str],
        analysis: Dict,
        file_name: str
    ) -> Tuple[str, bool]:
        """
        IDEMPOTENT CASE CREATION: Check-then-act pattern with race condition handling.

        This ensures we never get duplicate key errors or zombie transactions.

        Args:
            user_id: The user ID
            case_number: Case number from analysis (may be None)
            analysis: Document analysis dict
            file_name: Original filename for placeholder cases

        Returns:
            Tuple of (case_id, was_created)

        Raises:
            SQLAlchemyError if case creation fails after all retries
        """
        # Step 1: If we have a case number, check if it exists
        if case_number:
            try:
                existing_case = self.db.query(Case).filter(
                    Case.user_id == user_id,
                    Case.case_number == case_number
                ).first()

                if existing_case:
                    logger.info(f"Found existing case {existing_case.id} for case_number {case_number}")
                    return str(existing_case.id), False
            except SQLAlchemyError as e:
                # Query failed - rollback and re-raise
                logger.error(f"Error querying for existing case: {e}")
                self._safe_rollback()
                raise

        # Step 2: Create new case
        try:
            if case_number:
                new_case = self.create_case_from_analysis(user_id, analysis)
            else:
                # No case number - create placeholder
                new_case = Case(
                    user_id=user_id,
                    case_number=f"NEW-{uuid.uuid4().hex[:8].upper()}",
                    title=f"New Case - {file_name}",
                    court=analysis.get('court'),
                    judge=analysis.get('judge'),
                    case_type=analysis.get('case_type', 'Unknown'),
                    jurisdiction=analysis.get('jurisdiction'),
                    district=analysis.get('district'),
                    parties=analysis.get('parties', []),
                    case_metadata=analysis
                )

            self.db.add(new_case)
            self._safe_commit()
            self.db.refresh(new_case)
            logger.info(f"Created new case {new_case.id}")
            return str(new_case.id), True

        except IntegrityError as e:
            # Race condition - another request created the case between our check and insert
            logger.warning(f"IntegrityError creating case (race condition): {e}")
            self._safe_rollback()

            # Re-query to get the case that was created by the other request
            if case_number:
                existing_case = self.db.query(Case).filter(
                    Case.user_id == user_id,
                    Case.case_number == case_number
                ).first()

                if existing_case:
                    logger.info(f"Found case {existing_case.id} after race condition")
                    return str(existing_case.id), False

            # If we still can't find it, something is wrong
            raise SQLAlchemyError(f"Failed to find or create case after IntegrityError: {e}")

        except SQLAlchemyError as e:
            # Any other SQL error - rollback and re-raise
            logger.error(f"SQLAlchemyError creating case: {e}")
            self._safe_rollback()
            raise

    async def analyze_document(
        self,
        pdf_bytes: bytes,
        file_name: str,
        user_id: str,
        case_id: Optional[str] = None
    ) -> Dict:
        """
        Analyze uploaded PDF and extract case information.

        Args:
            pdf_bytes: PDF file content
            file_name: Original filename
            user_id: User ID who uploaded the document
            case_id: Optional existing case ID

        Returns:
            Dictionary with analysis results and routing information
        """

        # Extract text from PDF
        try:
            extracted_text = extract_text_from_pdf(pdf_bytes)
            pdf_metadata = get_pdf_metadata(pdf_bytes)
        except Exception as e:
            return {
                'error': f'PDF extraction failed: {str(e)}',
                'success': False
            }

        # Analyze with Claude AI
        try:
            analysis = await self.ai_service.analyze_legal_document(extracted_text)
        except Exception as e:
            return {
                'error': f'AI analysis failed: {str(e)}',
                'success': False
            }

        # Detect jurisdiction from document text
        jurisdiction_result = None
        try:
            jurisdiction_result = self.jurisdiction_detector.detect_from_text(
                text=extracted_text,
                case_number=analysis.get('case_number'),
                court_name=analysis.get('court')
            )

            if jurisdiction_result.detected:
                logger.info(
                    f"Detected jurisdiction: {jurisdiction_result.jurisdiction.name if jurisdiction_result.jurisdiction else 'Unknown'} "
                    f"(confidence: {jurisdiction_result.confidence:.2f})"
                )

                # Enhance analysis with detected jurisdiction info
                analysis['detected_jurisdiction'] = {
                    'jurisdiction_id': jurisdiction_result.jurisdiction.id if jurisdiction_result.jurisdiction else None,
                    'jurisdiction_name': jurisdiction_result.jurisdiction.name if jurisdiction_result.jurisdiction else None,
                    'jurisdiction_code': jurisdiction_result.jurisdiction.code if jurisdiction_result.jurisdiction else None,
                    'court_location_id': jurisdiction_result.court_location.id if jurisdiction_result.court_location else None,
                    'court_location_name': jurisdiction_result.court_location.name if jurisdiction_result.court_location else None,
                    'applicable_rule_sets': [rs.code for rs in jurisdiction_result.applicable_rule_sets],
                    'confidence': jurisdiction_result.confidence,
                    'matched_patterns': jurisdiction_result.matched_patterns,
                    'detected_court_name': jurisdiction_result.detected_court_name,
                    'detected_district': jurisdiction_result.detected_district
                }
        except Exception as e:
            logger.warning(f"Jurisdiction detection failed (non-critical): {e}")

        # Storage handled by API endpoint (local /tmp or S3)
        # Firebase Storage not used in MVP - files stored locally
        storage_path = f"pending/{user_id}/{file_name}"  # Placeholder, overwritten by endpoint
        storage_url = None  # Not used in MVP

        # Determine case routing using IDEMPOTENT ensure_case_exists
        target_case_id = case_id
        case_created = False
        case_number = analysis.get('case_number')

        if not case_id:
            # No case_id provided - use ensure_case_exists for idempotent creation
            try:
                target_case_id, case_created = self.ensure_case_exists(
                    user_id=user_id,
                    case_number=case_number,
                    analysis=analysis,
                    file_name=file_name
                )
            except SQLAlchemyError as e:
                return {
                    'error': f'Failed to find or create case: {str(e)}',
                    'success': False
                }

        # Auto-assign detected rule sets to case if jurisdiction was detected
        assigned_rule_sets = []
        if target_case_id and jurisdiction_result and jurisdiction_result.detected:
            try:
                assigned_rule_sets = self.assign_rule_sets_to_case(
                    case_id=target_case_id,
                    jurisdiction_result=jurisdiction_result
                )
                logger.info(f"Auto-assigned {len(assigned_rule_sets)} rule sets to case {target_case_id}")
            except Exception as e:
                logger.warning(f"Failed to auto-assign rule sets: {e}")
                self._safe_rollback()

        return {
            'success': True,
            'extracted_text': extracted_text,
            'pdf_metadata': pdf_metadata,
            'analysis': analysis,
            'case_id': target_case_id,
            'case_created': case_created,
            'file_size_bytes': len(pdf_bytes),
            'storage_path': storage_path,
            'storage_url': storage_url,
            'jurisdiction_detected': jurisdiction_result.detected if jurisdiction_result else False,
            'assigned_rule_sets': assigned_rule_sets
        }

    def create_case_from_analysis(self, user_id: str, analysis: Dict) -> Case:
        """Create a new case from document analysis"""

        case = Case(
            user_id=user_id,
            case_number=analysis.get('case_number', 'UNKNOWN'),
            title=analysis.get('summary', f"Case {analysis.get('case_number', 'UNKNOWN')}"),
            court=analysis.get('court'),
            judge=analysis.get('judge'),
            case_type=analysis.get('case_type'),
            jurisdiction=analysis.get('jurisdiction'),
            district=analysis.get('district'),
            parties=analysis.get('parties', []),
            case_metadata=analysis
        )

        # Parse filing date if present
        if analysis.get('filing_date'):
            try:
                case.filing_date = datetime.strptime(analysis['filing_date'], '%Y-%m-%d').date()
            except (KeyError, ValueError, TypeError) as e:
                logger.warning(f"Could not parse filing date: {e}")
                pass

        return case

    def assign_rule_sets_to_case(
        self,
        case_id: str,
        jurisdiction_result
    ) -> List[str]:
        """
        Assign detected rule sets to a case.

        Creates CaseRuleSet records for each applicable rule set detected
        from document analysis.

        Args:
            case_id: The case to assign rule sets to
            jurisdiction_result: DetectionResult from JurisdictionDetector

        Returns:
            List of assigned rule set codes
        """
        assigned_codes = []

        if not jurisdiction_result.applicable_rule_sets:
            return assigned_codes

        try:
            for priority, rule_set in enumerate(jurisdiction_result.applicable_rule_sets):
                # Check if already assigned
                existing = self.db.query(CaseRuleSet).filter(
                    CaseRuleSet.case_id == case_id,
                    CaseRuleSet.rule_set_id == rule_set.id
                ).first()

                if existing:
                    # Reactivate if inactive
                    if not existing.is_active:
                        existing.is_active = True
                        existing.assignment_method = "auto_detected"
                else:
                    # Create new assignment
                    assignment = CaseRuleSet(
                        id=str(uuid.uuid4()),
                        case_id=case_id,
                        rule_set_id=rule_set.id,
                        assignment_method="auto_detected",
                        priority=priority
                    )
                    self.db.add(assignment)

                assigned_codes.append(rule_set.code)

            self._safe_commit()
        except SQLAlchemyError as e:
            self._safe_rollback()
            logger.error(f"Failed to assign rule sets: {e}")
            raise

        return assigned_codes

    def create_document_record(
        self,
        case_id: str,
        user_id: str,
        file_name: str,
        storage_path: str,
        extracted_text: str,
        analysis: Dict,
        file_size_bytes: int
    ) -> Document:
        """Create database record for uploaded document"""

        document = Document(
            case_id=case_id,
            user_id=user_id,
            file_name=file_name,
            file_type='pdf',
            file_size_bytes=file_size_bytes,
            storage_path=storage_path,
            document_type=analysis.get('document_type'),
            extracted_text=extracted_text,
            ai_summary=analysis.get('summary'),
            extracted_metadata=analysis,
            analysis_status='completed'
        )

        # Parse filing date
        if analysis.get('filing_date'):
            try:
                document.filing_date = datetime.strptime(analysis['filing_date'], '%Y-%m-%d').date()
            except (KeyError, ValueError, TypeError) as e:
                logger.warning(f"Could not parse document filing date: {e}")
                pass

        document.received_date = datetime.now().date()

        try:
            self.db.add(document)
            self._safe_commit()
            self.db.refresh(document)
        except SQLAlchemyError as e:
            self._safe_rollback()
            logger.error(f"Failed to create document record: {e}")
            raise

        return document

    async def extract_and_save_deadlines(
        self,
        document: Document,
        extracted_text: str,
        analysis: Dict
    ) -> Dict[str, Any]:
        """
        TRIGGER-FIRST ARCHITECTURE: Extract deadlines from document and save to database.

        Decision Tree:
        1. CHECK FIRST: Is this document type a known trigger?
        2. PATH A (Match Found): Use rules engine ONLY - skip AI extraction to prevent duplicates
        3. PATH B (No Match): Use AI extraction for manual deadlines

        Returns:
            Dict with:
                - deadlines: List[Deadline]
                - extraction_method: "trigger" or "manual"
                - trigger_info: Dict (if trigger was used)
                - message: str (explanation for chatbot)
        """

        # Build document metadata
        document_metadata = {
            'document_type': document.document_type,
            'jurisdiction': analysis.get('jurisdiction', 'florida_state'),
            'court': analysis.get('court', ''),
            'filing_date': analysis.get('filing_date') or (document.filing_date.isoformat() if document.filing_date else None),
            'service_method': analysis.get('service_method'),
            'service_date': analysis.get('service_date'),
            'parties': analysis.get('parties', [])
        }

        # Normalize jurisdiction
        jurisdiction = document_metadata.get('jurisdiction', 'florida_state')
        if jurisdiction in ['state', 'State', 'florida', 'Florida']:
            jurisdiction = 'florida_state'
        court_type = analysis.get('case_type', 'civil')

        all_deadlines = []
        extraction_method = "manual"
        trigger_info = None
        chatbot_message = ""

        # ═══════════════════════════════════════════════════════════════════════════
        # STEP 1: THE RULE LOOKUP (The "Check First" Step)
        # Before creating ANY deadlines, check if document type matches a known trigger
        # ═══════════════════════════════════════════════════════════════════════════

        rule_check = self.deadline_service.check_rules_for_trigger(
            document_type=document.document_type or "",
            jurisdiction=jurisdiction,
            court_type=court_type
        )

        logger.info(f"Trigger-First Check: document_type='{document.document_type}' → matches_trigger={rule_check['matches_trigger']}")

        if rule_check['matches_trigger']:
            # ═══════════════════════════════════════════════════════════════════════
            # PATH A: TRIGGER FOUND - Use Rules Engine ONLY
            # DO NOT run AI extraction to prevent double docketing
            # ═══════════════════════════════════════════════════════════════════════

            logger.info(f"PATH A: Using rules engine for trigger '{rule_check['trigger_type']}' ({rule_check['rule_set_code']})")
            extraction_method = "trigger"

            # Get trigger date (service date takes precedence over filing date)
            trigger_date_str = analysis.get('service_date') or analysis.get('filing_date')
            if trigger_date_str:
                try:
                    from datetime import datetime
                    trigger_date = datetime.strptime(trigger_date_str, '%Y-%m-%d').date()
                except (ValueError, TypeError):
                    trigger_date = datetime.now().date()
            else:
                trigger_date = datetime.now().date()

            # Get service method
            service_method = analysis.get('service_method', 'electronic')

            trigger_info = {
                'trigger_type': rule_check['trigger_type'],
                'trigger_date': trigger_date,
                'rule_set_code': rule_check['rule_set_code'],
                'expected_deadlines': rule_check['expected_deadlines'],
                'description': rule_check['trigger_description'],
            }

            # Generate deadline chains using rules engine
            try:
                chain_deadlines = await self.deadline_service.generate_deadline_chains(
                    trigger_event=rule_check['trigger_type'],
                    trigger_date=trigger_date,
                    jurisdiction=jurisdiction,
                    court_type=court_type,
                    case_id=document.case_id,
                    user_id=document.user_id,
                    service_method=service_method
                )

                logger.info(f"Rules engine generated {len(chain_deadlines)} deadline(s) from trigger")

                # Save rules-engine generated deadlines
                for chain_deadline in chain_deadlines:
                    try:
                        rule_match = {
                            'citation': chain_deadline.get('rule_citation', rule_check['rule_set_code']),
                            'confidence': 'high'
                        }

                        source_text = chain_deadline.get('calculation_basis', '') + ' ' + chain_deadline.get('description', '')
                        confidence_result = confidence_scorer.calculate_confidence(
                            extraction=chain_deadline,
                            source_text=source_text,
                            rule_match=rule_match,
                            document_type=document.document_type
                        )

                        deadline = Deadline(
                            case_id=chain_deadline['case_id'],
                            user_id=chain_deadline['user_id'],
                            document_id=str(document.id),
                            title=chain_deadline['title'],
                            description=chain_deadline['description'],
                            deadline_date=chain_deadline.get('deadline_date'),
                            deadline_type=chain_deadline.get('deadline_type', 'general'),
                            applicable_rule=chain_deadline.get('rule_citation'),
                            rule_citation=chain_deadline.get('rule_citation'),
                            calculation_basis=chain_deadline.get('calculation_basis'),
                            priority=chain_deadline.get('priority', 'medium'),
                            status='pending',
                            party_role=chain_deadline.get('party_role'),
                            action_required=chain_deadline.get('action_required'),
                            trigger_event=rule_check['trigger_type'],
                            trigger_date=trigger_date,
                            is_estimated=False,
                            is_calculated=True,  # Rules-engine calculated
                            is_dependent=chain_deadline.get('is_dependent', False),
                            source_document=f"{document.document_type} (trigger: {rule_check['trigger_type']})",
                            service_method=service_method,
                            confidence_score=confidence_result['confidence_score'],
                            confidence_level=confidence_result['confidence_level'],
                            confidence_factors=confidence_result['factors'],
                            verification_status='pending',
                            extraction_method='rule-based',
                            extraction_quality_score=min(10, confidence_result['confidence_score'] // 10),
                            source_text=source_text[:500]
                        )

                        self.db.add(deadline)
                        all_deadlines.append(deadline)
                    except Exception as e:
                        logger.error(f"Error creating chain deadline: {e}")
                        continue

                # Build chatbot message for PATH A
                chatbot_message = (
                    f"I identified this as a '{document.document_type}'. "
                    f"This triggers **{rule_check['rule_set_code']} {rule_check['trigger_type']}**. "
                    f"I have auto-calculated {len(all_deadlines)} deadline(s) using the rules engine. "
                    f"({rule_check['trigger_description']})"
                )

            except Exception as e:
                logger.error(f"Error generating deadline chains: {e}")
                chatbot_message = f"Error generating deadlines from trigger: {e}"

        else:
            # ═══════════════════════════════════════════════════════════════════════
            # PATH B: NO TRIGGER MATCH - Use AI Extraction
            # Extract deadlines manually from document text
            # ═══════════════════════════════════════════════════════════════════════

            logger.info(f"PATH B: No trigger match for '{document.document_type}' - using AI extraction")
            extraction_method = "manual"

            try:
                deadline_data_list = await self.deadline_service.extract_deadlines_from_document(
                    document_text=extracted_text,
                    document_metadata=document_metadata,
                    case_id=document.case_id,
                    user_id=document.user_id
                )
            except Exception as e:
                logger.error(f"Error extracting deadlines: {e}")
                deadline_data_list = []

            # Save AI-extracted deadlines
            for deadline_data in deadline_data_list:
                try:
                    rule_match = None
                    if deadline_data.get('applicable_rule'):
                        rule_match = {
                            'citation': deadline_data.get('applicable_rule'),
                            'confidence': 'high' if deadline_data.get('calculation_basis') else 'medium'
                        }

                    source_text = deadline_data.get('calculation_basis', '') + ' ' + deadline_data.get('description', '')
                    confidence_result = confidence_scorer.calculate_confidence(
                        extraction=deadline_data,
                        source_text=source_text,
                        rule_match=rule_match,
                        document_type=document.document_type
                    )

                    deadline = Deadline(
                        case_id=deadline_data['case_id'],
                        user_id=deadline_data['user_id'],
                        document_id=str(document.id),
                        title=deadline_data['title'],
                        description=deadline_data['description'],
                        deadline_date=deadline_data.get('deadline_date'),
                        deadline_type=deadline_data.get('deadline_type', 'general'),
                        applicable_rule=deadline_data.get('applicable_rule'),
                        rule_citation=deadline_data.get('rule_citation'),
                        calculation_basis=deadline_data.get('calculation_basis'),
                        priority=deadline_data.get('priority', 'medium'),
                        status='pending',
                        party_role=deadline_data.get('party_role'),
                        action_required=deadline_data.get('action_required'),
                        trigger_event=deadline_data.get('trigger_event'),
                        trigger_date=deadline_data.get('trigger_date'),
                        is_estimated=deadline_data.get('is_estimated', False),
                        is_calculated=False,  # AI-extracted, not rules-engine
                        source_document=deadline_data.get('source_document'),
                        service_method=deadline_data.get('service_method'),
                        confidence_score=confidence_result['confidence_score'],
                        confidence_level=confidence_result['confidence_level'],
                        confidence_factors=confidence_result['factors'],
                        verification_status='pending',
                        extraction_method='ai',
                        extraction_quality_score=min(10, confidence_result['confidence_score'] // 10),
                        source_text=source_text[:500]
                    )

                    self.db.add(deadline)
                    all_deadlines.append(deadline)
                except Exception as e:
                    logger.error(f"Error creating deadline: {e}")
                    continue

            # Build chatbot message for PATH B
            chatbot_message = (
                f"I did not find a standard rule template for '{document.document_type}'. "
                f"I have manually extracted {len(all_deadlines)} deadline(s) from the document text."
            )

            # PATH B also checks for additional trigger events (hearing dates, trial dates)
            # These are NON-DOCUMENT-TYPE triggers found in the document content
            trigger_events = self.deadline_service.extract_trigger_events_from_analysis(
                document_analysis=analysis,
                court_info=analysis.get('court', '')
            )

            if trigger_events:
                logger.info(f"Found {len(trigger_events)} additional trigger event(s) in document")
                service_method = analysis.get('service_method', 'electronic')

                for trig_info in trigger_events:
                    try:
                        chain_deadlines = await self.deadline_service.generate_deadline_chains(
                            trigger_event=trig_info['trigger_event'],
                            trigger_date=trig_info['trigger_date'],
                            jurisdiction=trig_info['jurisdiction'],
                            court_type=trig_info['court_type'],
                            case_id=document.case_id,
                            user_id=document.user_id,
                            service_method=service_method
                        )

                        for chain_deadline in chain_deadlines:
                            try:
                                rule_match = {
                                    'citation': chain_deadline.get('rule_citation', 'Rules Engine'),
                                    'confidence': 'high'
                                }

                                source_text = chain_deadline.get('calculation_basis', '') + ' ' + chain_deadline.get('description', '')
                                confidence_result = confidence_scorer.calculate_confidence(
                                    extraction=chain_deadline,
                                    source_text=source_text,
                                    rule_match=rule_match,
                                    document_type=document.document_type
                                )

                                deadline = Deadline(
                                    case_id=chain_deadline['case_id'],
                                    user_id=chain_deadline['user_id'],
                                    document_id=str(document.id),
                                    title=chain_deadline['title'],
                                    description=chain_deadline['description'],
                                    deadline_date=chain_deadline.get('deadline_date'),
                                    deadline_type=chain_deadline.get('deadline_type', 'general'),
                                    applicable_rule=chain_deadline.get('rule_citation'),
                                    rule_citation=chain_deadline.get('rule_citation'),
                                    calculation_basis=chain_deadline.get('calculation_basis'),
                                    priority=chain_deadline.get('priority', 'medium'),
                                    status='pending',
                                    party_role=chain_deadline.get('party_role'),
                                    action_required=chain_deadline.get('action_required'),
                                    trigger_event=trig_info['trigger_event'],
                                    trigger_date=trig_info['trigger_date'],
                                    is_estimated=False,
                                    is_calculated=True,
                                    is_dependent=chain_deadline.get('is_dependent', False),
                                    source_document=f"{document.document_type} (trigger: {trig_info.get('source', 'document')})",
                                    service_method=service_method,
                                    confidence_score=confidence_result['confidence_score'],
                                    confidence_level=confidence_result['confidence_level'],
                                    confidence_factors=confidence_result['factors'],
                                    verification_status='pending',
                                    extraction_method='rule-based',
                                    extraction_quality_score=min(10, confidence_result['confidence_score'] // 10),
                                    source_text=source_text[:500]
                                )

                                self.db.add(deadline)
                                all_deadlines.append(deadline)
                            except Exception as e:
                                logger.error(f"Error creating chain deadline: {e}")
                                continue

                    except Exception as e:
                        logger.error(f"Error processing trigger '{trig_info['trigger_event']}': {e}")

        # ═══════════════════════════════════════════════════════════════════════════
        # COMMIT ALL DEADLINES
        # ═══════════════════════════════════════════════════════════════════════════

        try:
            self._safe_commit()

            for deadline in all_deadlines:
                try:
                    self.db.refresh(deadline)
                except Exception as e:
                    logger.warning(f"Could not refresh deadline: {e}")
        except SQLAlchemyError as e:
            self._safe_rollback()
            logger.error(f"Failed to save deadlines: {e}")
            raise

        return {
            'deadlines': all_deadlines,
            'extraction_method': extraction_method,
            'trigger_info': trigger_info,
            'message': chatbot_message,
            'count': len(all_deadlines)
        }
