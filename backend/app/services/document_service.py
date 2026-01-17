from typing import Dict, Optional, List, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy import text  # CRITICAL: For raw SQL to bypass ORM schema mismatches
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

    # =========================================================================
    # SMART CASE ROUTING - "Traffic Cop" Pattern
    # =========================================================================

    @staticmethod
    def normalize_case_number(case_number: str) -> str:
        """
        Normalize case number for fuzzy matching.

        Federal case numbers often have judge initials appended:
        - "1:25-cv-20757-JB" → "1:25-cv-20757"
        - "2:24-cv-12345-ABC-DEF" → "2:24-cv-12345"

        State case numbers may have various suffixes:
        - "2024-CA-001234-O" → "2024-CA-001234"
        - "50-2024-CA-001234-XXXX-MB" → "50-2024-CA-001234"

        This ensures documents from the same case match even if
        the AI extracts slightly different formats.
        """
        import re

        if not case_number:
            return ""

        # Strip whitespace
        normalized = case_number.strip().upper()

        # Pattern 1: Federal format "X:XX-cv-XXXXX-JJ" or "X:XX-cv-XXXXX-JJJ-JJJ"
        # Keep everything up to and including the 5+ digit number
        federal_match = re.match(r'^(\d+:\d{2}-\w+-\d{5,})(?:-[A-Z]+)*$', normalized)
        if federal_match:
            normalized = federal_match.group(1)
            logger.debug(f"Federal case number normalized: {case_number} → {normalized}")
            return normalized

        # Pattern 2: Florida state format "XX-XXXX-CA-XXXXXX-XXXX-XX"
        # Keep the core: circuit-year-type-sequence
        florida_match = re.match(r'^(\d{1,2}-\d{4}-[A-Z]{2}-\d{6})(?:-[A-Z0-9]+)*$', normalized)
        if florida_match:
            normalized = florida_match.group(1)
            logger.debug(f"Florida case number normalized: {case_number} → {normalized}")
            return normalized

        # Pattern 3: Simple state format "YYYY-CA-XXXXXX"
        simple_match = re.match(r'^(\d{4}-[A-Z]{2}-\d{4,})(?:-[A-Z0-9]+)*$', normalized)
        if simple_match:
            normalized = simple_match.group(1)
            logger.debug(f"Simple case number normalized: {case_number} → {normalized}")
            return normalized

        # No pattern matched - return cleaned version (strip trailing alpha suffixes)
        # This catches edge cases like "24-12345-CI-A" → "24-12345-CI"
        fallback_match = re.match(r'^([\d\-:A-Z]+\d{4,})(?:-[A-Z]+)?$', normalized)
        if fallback_match:
            normalized = fallback_match.group(1)
            logger.debug(f"Fallback case number normalized: {case_number} → {normalized}")
            return normalized

        # Return as-is if no patterns match
        return normalized

    def find_matching_case(
        self,
        user_id: str,
        extracted_case_number: str,
        extracted_court: Optional[str] = None
    ) -> Optional[Case]:
        """
        SMART CASE ROUTER: Find existing case using fuzzy matching.

        Step 1: Try exact match on case_number
        Step 2: Try normalized match (strips judge initials, suffixes)
        Step 3: (Future) Try court + partial number match

        Args:
            user_id: The user's ID
            extracted_case_number: Case number from AI extraction
            extracted_court: Court name from AI extraction (optional)

        Returns:
            Existing Case if found, None otherwise
        """
        if not extracted_case_number:
            return None

        # Normalize the extracted case number
        normalized_extracted = self.normalize_case_number(extracted_case_number)

        # Step 1: Exact match (fastest)
        exact_match = self.db.query(Case).filter(
            Case.user_id == user_id,
            Case.case_number == extracted_case_number
        ).first()

        if exact_match:
            logger.info(f"Smart Router: EXACT match found for '{extracted_case_number}' → Case {exact_match.id}")
            return exact_match

        # Step 2: Normalized match (fuzzy)
        # Query all user's cases and compare normalized versions
        user_cases = self.db.query(Case).filter(
            Case.user_id == user_id,
            Case.status != 'deleted'
        ).all()

        for case in user_cases:
            normalized_existing = self.normalize_case_number(case.case_number)

            # Check if normalized versions match
            if normalized_existing == normalized_extracted:
                logger.info(
                    f"Smart Router: FUZZY match found! "
                    f"'{extracted_case_number}' (normalized: '{normalized_extracted}') "
                    f"matches '{case.case_number}' (normalized: '{normalized_existing}') "
                    f"→ Case {case.id}"
                )
                return case

            # Also check if one contains the other (partial match)
            if (normalized_extracted in normalized_existing or
                normalized_existing in normalized_extracted):
                logger.info(
                    f"Smart Router: PARTIAL match found! "
                    f"'{extracted_case_number}' ↔ '{case.case_number}' → Case {case.id}"
                )
                return case

        logger.info(f"Smart Router: No match found for '{extracted_case_number}' (normalized: '{normalized_extracted}')")
        return None

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
    ) -> Tuple[str, bool, str]:
        """
        SMART CASE ROUTING: "Traffic Cop" pattern with fuzzy matching.

        This is the intelligent case router that decides whether to:
        - PATH A: ATTACH document to existing case (returns case_status="updated")
        - PATH B: CREATE new case (returns case_status="created")

        Uses fuzzy matching to handle case number variations:
        - "1:25-cv-20757-JB" matches "1:25-cv-20757"
        - "2024-CA-001234-O" matches "2024-CA-001234"

        Args:
            user_id: The user ID
            case_number: Case number from AI analysis (may be None)
            analysis: Document analysis dict
            file_name: Original filename for placeholder cases

        Returns:
            Tuple of (case_id, was_created, case_status)
            - case_status: "created" | "updated" | "attached" for frontend feedback

        Raises:
            SQLAlchemyError if case creation fails after all retries
        """
        extracted_court = analysis.get('court')

        # ═══════════════════════════════════════════════════════════════════════
        # STEP 1: SMART MATCH - Use fuzzy matching to find existing case
        # ═══════════════════════════════════════════════════════════════════════
        if case_number:
            try:
                existing_case = self.find_matching_case(
                    user_id=user_id,
                    extracted_case_number=case_number,
                    extracted_court=extracted_court
                )

                if existing_case:
                    # ═══════════════════════════════════════════════════════════
                    # PATH A: ATTACH - Found existing case
                    # ═══════════════════════════════════════════════════════════
                    logger.info(
                        f"Smart Router: PATH A (ATTACH) - "
                        f"Document for '{case_number}' → existing case {existing_case.id}"
                    )
                    return str(existing_case.id), False, "updated"

            except SQLAlchemyError as e:
                logger.error(f"Error in smart case matching: {e}")
                self._safe_rollback()
                raise

        # ═══════════════════════════════════════════════════════════════════════
        # STEP 2: CREATE NEW CASE - No match found
        # ═══════════════════════════════════════════════════════════════════════
        try:
            if case_number:
                # PATH B: CREATE with extracted case number
                logger.info(
                    f"Smart Router: PATH B (CREATE) - "
                    f"No match for '{case_number}'. Creating new case."
                )
                new_case = self.create_case_from_analysis(user_id, analysis)
            else:
                # No case number extracted - create placeholder
                logger.info(
                    f"Smart Router: PATH B (CREATE) - "
                    f"No case number extracted. Creating placeholder case."
                )
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
            logger.info(f"Smart Router: Created new case {new_case.id} (case_number: {new_case.case_number})")
            return str(new_case.id), True, "created"

        except IntegrityError as e:
            # Race condition - another request created the case between our check and insert
            logger.warning(f"Smart Router: Race condition detected - {e}")
            self._safe_rollback()

            # Re-query using smart matching
            if case_number:
                existing_case = self.find_matching_case(
                    user_id=user_id,
                    extracted_case_number=case_number,
                    extracted_court=extracted_court
                )

                if existing_case:
                    logger.info(f"Smart Router: Found case {existing_case.id} after race condition")
                    return str(existing_case.id), False, "updated"

            # If we still can't find it, something is wrong
            raise SQLAlchemyError(f"Failed to find or create case after IntegrityError: {e}")

        except SQLAlchemyError as e:
            logger.error(f"Smart Router: SQLAlchemyError creating case: {e}")
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

        # ═══════════════════════════════════════════════════════════════════════
        # SESSION SANITIZER: Clear any zombie transactions from upstream
        # This prevents InFailedSqlTransaction errors from previous requests
        # ═══════════════════════════════════════════════════════════════════════
        try:
            if self.db.is_active and self.db.in_transaction():
                logger.warning("Session Sanitizer: Found active transaction at start of analyze_document - rolling back")
                self._safe_rollback()
        except Exception as e:
            logger.warning(f"Session Sanitizer: Error checking transaction state: {e}")
            self._safe_rollback()

        # Extract text from PDF
        try:
            extracted_text = extract_text_from_pdf(pdf_bytes)
            pdf_metadata = get_pdf_metadata(pdf_bytes)

            # Check if OCR is needed (scanned PDF detection)
            from app.utils.pdf_parser import detect_ocr_needed
            needs_ocr = detect_ocr_needed(extracted_text)

            if needs_ocr:
                logger.warning(
                    f"Document {file_name} appears to need OCR - "
                    f"text extraction yielded minimal/garbled content (length: {len(extracted_text.strip())})"
                )

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
            # SESSION SANITIZER: Rollback to prevent zombie transaction from jurisdiction query
            self._safe_rollback()

        # Storage handled by API endpoint (local /tmp or S3)
        # Firebase Storage not used in MVP - files stored locally
        storage_path = f"pending/{user_id}/{file_name}"  # Placeholder, overwritten by endpoint
        storage_url = None  # Not used in MVP

        # ═══════════════════════════════════════════════════════════════════════
        # SMART CASE ROUTING - The "Traffic Cop" Decision
        # ═══════════════════════════════════════════════════════════════════════
        target_case_id = case_id
        case_created = False
        case_status = "attached"  # Default if case_id was provided
        case_number = analysis.get('case_number')

        if not case_id:
            # No case_id provided - use Smart Router to find or create case
            try:
                target_case_id, case_created, case_status = self.ensure_case_exists(
                    user_id=user_id,
                    case_number=case_number,
                    analysis=analysis,
                    file_name=file_name
                )
                logger.info(
                    f"Smart Router Decision: case_id={target_case_id}, "
                    f"case_status='{case_status}', case_created={case_created}"
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
            'case_status': case_status,  # NEW: "created" | "updated" | "attached"
            'file_size_bytes': len(pdf_bytes),
            'storage_path': storage_path,
            'storage_url': storage_url,
            'jurisdiction_detected': jurisdiction_result.detected if jurisdiction_result else False,
            'assigned_rule_sets': assigned_rule_sets,
            'needs_ocr': needs_ocr
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
        file_size_bytes: int,
        needs_ocr: bool = False
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
            needs_ocr=needs_ocr,
            analysis_status='needs_ocr' if needs_ocr else 'completed'
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

    # =========================================================================
    # GHOST-SAFE DELETION
    # =========================================================================

    def delete_document(self, document_id: str, user_id: str) -> bool:
        """
        NUCLEAR DELETE: Uses Raw SQL to bypass ORM schema mismatches.

        The DocumentEmbedding ORM model has columns (chunk_page) that don't exist
        in the actual database table. Using raw SQL bypasses this mismatch.

        "Ghost Documents" are DB records pointing to files that no longer exist.
        This method handles them gracefully.

        Deletion sequence:
        1. Fetch document from database (verify ownership)
        2. RAW SQL delete embeddings (bypasses chunk_page schema error)
        3. Delete from storage (ghost-safe)
        4. Delete document record

        Args:
            document_id: Document UUID
            user_id: User ID for ownership verification

        Returns:
            bool: True if document deleted, False if not found
        """
        try:
            # 1. Get document from DB with ownership check
            document = self.db.query(Document).filter(
                Document.id == document_id,
                Document.user_id == user_id
            ).first()

            if not document:
                logger.warning(f"Document {document_id} not found for user {user_id}")
                return False

            # 2. RAW SQL DELETE of Embeddings (Bypasses 'chunk_page' ORM error)
            # DO NOT use DocumentEmbedding ORM model - it has schema mismatches
            try:
                logger.info(f"Purging embeddings for {document_id} via Raw SQL")
                self.db.execute(
                    text("DELETE FROM document_embeddings WHERE document_id = :doc_id"),
                    {"doc_id": document_id}
                )
                self.db.flush()  # Force SQL execution before expunge
                logger.info(f"✓ Embeddings purged for document {document_id}")
            except Exception as e:
                # Non-critical - table might not exist or be empty
                logger.warning(f"Embedding cleanup failed (ignoring): {e}")

            # CRITICAL: Expunge document from session to prevent ORM cascade queries
            # This stops SQLAlchemy from trying to SELECT embeddings using the broken ORM model
            self.db.expunge(document)

            # 3. Delete from Storage (GHOST-SAFE: ignore errors)
            if document.storage_path:
                try:
                    if document.storage_path.startswith('documents/'):
                        logger.info(f"Deleting Firebase file: {document.storage_path}")
                        firebase_service.delete_file(document.storage_path)
                        logger.info(f"✓ Firebase file deleted: {document.storage_path}")
                    else:
                        import os
                        if os.path.exists(document.storage_path):
                            logger.info(f"Deleting local file: {document.storage_path}")
                            os.remove(document.storage_path)
                            logger.info(f"✓ Local file deleted: {document.storage_path}")
                        else:
                            logger.warning(f"⚠ Ghost Document: File not found at {document.storage_path}")
                except Exception as e:
                    logger.warning(f"⚠ Storage delete failed (Ghost?): {e}")
                    # DO NOT raise - continue with DB deletion

            # 4. Delete Document Record (Using Raw SQL to bypass ORM relationships)
            logger.info(f"Deleting document record {document_id} via Raw SQL")
            self.db.execute(
                text("DELETE FROM documents WHERE id = :doc_id"),
                {"doc_id": document_id}
            )
            self.db.commit()
            logger.info(f"✓ Document {document_id} successfully deleted")
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"✗ Critical error deleting document {document_id}: {e}")
            raise
