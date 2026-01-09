from typing import Dict, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
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

        # Determine case routing
        target_case_id = case_id
        case_created = False
        case_number = analysis.get('case_number')

        if not case_id:
            # No case_id provided, need to find or create a case
            if case_number:
                # Check if case exists
                existing_case = self.db.query(Case).filter(
                    Case.user_id == user_id,
                    Case.case_number == case_number
                ).first()

                if existing_case:
                    target_case_id = str(existing_case.id)
                else:
                    # Create new case from analysis
                    try:
                        new_case = self.create_case_from_analysis(user_id, analysis)
                        self.db.add(new_case)
                        self._safe_commit()
                        self.db.refresh(new_case)
                        target_case_id = str(new_case.id)
                        case_created = True
                    except SQLAlchemyError as e:
                        self._safe_rollback()
                        return {
                            'error': f'Failed to create case: {str(e)}',
                            'success': False
                        }
            else:
                # No case_number detected - create a new case with placeholder info
                # This ensures we always have a case_id to attach the document to
                try:
                    new_case = Case(
                        user_id=user_id,
                        case_number=f"NEW-{uuid.uuid4().hex[:8].upper()}",  # Placeholder
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
                    target_case_id = str(new_case.id)
                    case_created = True
                except SQLAlchemyError as e:
                    self._safe_rollback()
                    return {
                        'error': f'Failed to create case: {str(e)}',
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
    ) -> List[Deadline]:
        """
        Extract deadlines from document and save to database
        Implements comprehensive methodology with trigger detection
        """

        # Build document metadata for deadline extraction
        document_metadata = {
            'document_type': document.document_type,
            'jurisdiction': analysis.get('jurisdiction', 'state'),
            'court': analysis.get('court', ''),
            'filing_date': analysis.get('filing_date') or document.filing_date.isoformat() if document.filing_date else None,
            'service_method': analysis.get('service_method'),  # From certificate of service
            'service_date': analysis.get('service_date'),
            'parties': analysis.get('parties', [])
        }

        all_deadlines = []

        # PHASE 1: Extract deadlines using Claude AI (existing method)
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

        # Save AI-extracted deadlines to database with confidence scoring
        for deadline_data in deadline_data_list:
            try:
                # Calculate confidence score for this extraction
                rule_match = None
                if deadline_data.get('applicable_rule'):
                    # Create rule match object for confidence scoring
                    rule_match = {
                        'citation': deadline_data.get('applicable_rule'),
                        'confidence': 'high' if deadline_data.get('calculation_basis') else 'medium'
                    }

                # Calculate confidence score
                source_text = deadline_data.get('calculation_basis', '') + ' ' + deadline_data.get('description', '')
                confidence_result = confidence_scorer.calculate_confidence(
                    extraction=deadline_data,
                    source_text=source_text,
                    rule_match=rule_match,
                    document_type=document.document_type
                )

                # Create deadline with confidence metadata
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
                    is_calculated=False,  # AI-extracted, not rules-engine calculated
                    source_document=deadline_data.get('source_document'),
                    service_method=deadline_data.get('service_method'),
                    # Case OS: Confidence scoring
                    confidence_score=confidence_result['confidence_score'],
                    confidence_level=confidence_result['confidence_level'],
                    confidence_factors=confidence_result['factors'],
                    # Case OS: Verification gate (all AI extractions require approval)
                    verification_status='pending',
                    # Case OS: Extraction quality
                    extraction_method='ai',
                    extraction_quality_score=min(10, confidence_result['confidence_score'] // 10),
                    # Case OS: Source attribution (text snippet from calculation basis)
                    source_text=source_text[:500]  # Limit to 500 chars
                )

                self.db.add(deadline)
                all_deadlines.append(deadline)
            except Exception as e:
                logger.error(f"Error creating deadline: {e}")
                continue

        # PHASE 2: Extract ALL trigger events from AI analysis (V2.0 Feature!)
        # This includes hearing dates, trial dates, mediation dates, etc. found in key_dates or deadlines_mentioned
        trigger_events = self.deadline_service.extract_trigger_events_from_analysis(
            document_analysis=analysis,
            court_info=analysis.get('court', '')
        )

        # Also check if document type itself is a trigger (complaint, summons, etc.)
        document_type_trigger = self.deadline_service.detect_trigger_from_document(
            document_type=document.document_type or "",
            document_analysis=analysis,
            court_info=analysis.get('court', '')
        )

        # Add document-type trigger to the list if found
        if document_type_trigger:
            trigger_events.append(document_type_trigger)

        # Process each trigger event to generate deadline chains
        if trigger_events:
            logger.info(f"Detected {len(trigger_events)} trigger event(s) in document")

            # Get service method from analysis or metadata
            service_method = analysis.get('service_method', 'electronic')

            for trigger_info in trigger_events:
                logger.info(f"Processing trigger: {trigger_info['trigger_event']} on {trigger_info['trigger_date']} (Source: {trigger_info.get('source', 'Unknown')})")

                # Generate deadline chains using rules engine
                try:
                    chain_deadlines = await self.deadline_service.generate_deadline_chains(
                        trigger_event=trigger_info['trigger_event'],
                        trigger_date=trigger_info['trigger_date'],
                        jurisdiction=trigger_info['jurisdiction'],
                        court_type=trigger_info['court_type'],
                        case_id=document.case_id,
                        user_id=document.user_id,
                        service_method=service_method
                    )

                    logger.info(f"Generated {len(chain_deadlines)} deadline(s) from trigger")

                    # Save rules-engine generated deadlines with high confidence
                    for chain_deadline in chain_deadlines:
                        try:
                            # Calculate confidence for rules-engine deadlines (typically higher)
                            rule_match = {
                                'citation': chain_deadline.get('rule_citation', 'Rules Engine'),
                                'confidence': 'high'  # Rules-based calculations are highly confident
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
                                trigger_event=chain_deadline.get('trigger_event'),
                                trigger_date=chain_deadline.get('trigger_date'),
                                is_estimated=False,
                                is_calculated=True,  # Rules-engine calculated!
                                is_dependent=chain_deadline.get('is_dependent', False),
                                source_document=f"{document.document_type} (trigger: {trigger_info.get('source', 'document')})",
                                service_method=service_method,
                                # Case OS: Confidence scoring (typically higher for rules-based)
                                confidence_score=confidence_result['confidence_score'],
                                confidence_level=confidence_result['confidence_level'],
                                confidence_factors=confidence_result['factors'],
                                # Case OS: Verification gate (rules-based still need approval)
                                verification_status='pending',
                                # Case OS: Extraction quality (higher for rules-based)
                                extraction_method='rule-based',
                                extraction_quality_score=min(10, confidence_result['confidence_score'] // 10),
                                # Case OS: Source attribution
                                source_text=source_text[:500]
                            )

                            self.db.add(deadline)
                            all_deadlines.append(deadline)
                        except Exception as e:
                            logger.error(f"Error creating chain deadline: {e}")
                            continue

                except Exception as e:
                    logger.error(f"Error generating deadline chains for trigger '{trigger_info['trigger_event']}': {e}")

        # Commit all deadlines at once with rollback on failure
        try:
            self._safe_commit()

            # Refresh all deadlines to get database IDs
            for deadline in all_deadlines:
                try:
                    self.db.refresh(deadline)
                except Exception as e:
                    logger.warning(f"Could not refresh deadline: {e}")
        except SQLAlchemyError as e:
            self._safe_rollback()
            logger.error(f"Failed to save deadlines: {e}")
            raise

        return all_deadlines
