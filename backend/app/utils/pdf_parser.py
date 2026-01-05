import PyPDF2
from io import BytesIO
from typing import Optional


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """
    Extract text from PDF bytes using PyPDF2.

    Args:
        pdf_bytes: PDF file content as bytes

    Returns:
        Extracted text from all pages
    """
    try:
        pdf_file = BytesIO(pdf_bytes)
        pdf_reader = PyPDF2.PdfReader(pdf_file)

        text = ""
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n\n"

        return text.strip()
    except Exception as e:
        raise Exception(f"Failed to extract text from PDF: {str(e)}")


def get_pdf_metadata(pdf_bytes: bytes) -> dict:
    """
    Extract metadata from PDF.

    Args:
        pdf_bytes: PDF file content as bytes

    Returns:
        Dictionary with PDF metadata
    """
    try:
        pdf_file = BytesIO(pdf_bytes)
        pdf_reader = PyPDF2.PdfReader(pdf_file)

        metadata = {
            'num_pages': len(pdf_reader.pages),
            'pdf_metadata': {}
        }

        if pdf_reader.metadata:
            metadata['pdf_metadata'] = {
                'author': pdf_reader.metadata.get('/Author'),
                'creator': pdf_reader.metadata.get('/Creator'),
                'producer': pdf_reader.metadata.get('/Producer'),
                'subject': pdf_reader.metadata.get('/Subject'),
                'title': pdf_reader.metadata.get('/Title'),
                'creation_date': pdf_reader.metadata.get('/CreationDate'),
            }

        return metadata
    except Exception as e:
        return {'error': str(e)}
