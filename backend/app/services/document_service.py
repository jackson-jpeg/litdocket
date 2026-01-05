from typing import Dict, Optional, List
from sqlalchemy.orm import Session
import uuid
from datetime import datetime

from app.services.ai_service import AIService
from app.services.firebase_service import firebase_service
from app.services.deadline_service import DeadlineService
from app.utils.pdf_parser import extract_text_from_pdf, get_pdf_metadata
from app.models.document import Document
from app.models.case import Case
from app.models.deadline import Deadline


class DocumentService:
    """Service for document processing and analysis"""

    def __init__(self, db: Session):
        self.db = db
        self.ai_service = AIService()
        self.deadline_service = DeadlineService()

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

        # Upload PDF to Firebase Storage
        try:
            storage_path, storage_url = firebase_service.upload_pdf(
                user_id=user_id,
                file_name=file_name,
                pdf_bytes=pdf_bytes
            )
        except Exception as e:
            return {
                'error': f'File upload failed: {str(e)}',
                'success': False
            }

        # Determine case routing
        target_case_id = case_id
        case_created = False
        case_number = analysis.get('case_number')

        if not case_id and case_number:
            # Check if case exists
            existing_case = self.db.query(Case).filter(
                Case.user_id == user_id,
                Case.case_number == case_number
            ).first()

            if existing_case:
                target_case_id = str(existing_case.id)
            else:
                # Create new case
                new_case = self.create_case_from_analysis(user_id, analysis)
                self.db.add(new_case)
                self.db.commit()
                self.db.refresh(new_case)
                target_case_id = str(new_case.id)
                case_created = True

        return {
            'success': True,
            'extracted_text': extracted_text,
            'pdf_metadata': pdf_metadata,
            'analysis': analysis,
            'case_id': target_case_id,
            'case_created': case_created,
            'file_size_bytes': len(pdf_bytes),
            'storage_path': storage_path,
            'storage_url': storage_url
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
            except:
                pass

        return case

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
            except:
                pass

        document.received_date = datetime.now().date()

        self.db.add(document)
        self.db.commit()
        self.db.refresh(document)

        return document

    async def extract_and_save_deadlines(
        self,
        document: Document,
        extracted_text: str,
        analysis: Dict
    ) -> List[Deadline]:
        """
        Extract deadlines from document and save to database
        Implements Jackson's comprehensive methodology
        """

        # Build document metadata for deadline extraction
        document_metadata = {
            'document_type': document.document_type,
            'jurisdiction': analysis.get('jurisdiction', 'state'),
            'court': analysis.get('court', ''),
            'filing_date': analysis.get('filing_date'),
            'service_method': analysis.get('service_method'),  # From certificate of service
            'service_date': analysis.get('service_date')
        }

        # Extract deadlines using Claude AI
        try:
            deadline_data_list = await self.deadline_service.extract_deadlines_from_document(
                document_text=extracted_text,
                document_metadata=document_metadata,
                case_id=document.case_id,
                user_id=document.user_id
            )
        except Exception as e:
            print(f"Error extracting deadlines: {e}")
            return []

        # Save deadlines to database
        deadlines = []
        for deadline_data in deadline_data_list:
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
                source_document=deadline_data.get('source_document'),
                service_method=deadline_data.get('service_method')
            )

            self.db.add(deadline)
            deadlines.append(deadline)

        self.db.commit()

        # Refresh all deadlines to get database IDs
        for deadline in deadlines:
            self.db.refresh(deadline)

        return deadlines
