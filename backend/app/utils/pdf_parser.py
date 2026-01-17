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


def detect_ocr_needed(extracted_text: str, min_text_length: int = 100) -> bool:
    """
    Detect if a PDF needs OCR processing.

    Returns True if the text appears to be from a scanned image or is unreadable:
    - Text is empty or too short (< min_text_length chars)
    - Text is mostly garbled/non-printable characters (> 50% non-alphanumeric)
    - Text is all symbols/numbers (common in scanned image artifacts)

    Args:
        extracted_text: Text extracted from PDF
        min_text_length: Minimum character count to consider readable (default: 100)

    Returns:
        bool: True if OCR is needed, False if text is readable
    """
    if not extracted_text or len(extracted_text.strip()) < min_text_length:
        return True

    # Check for gibberish (more than 50% non-alphanumeric)
    clean_text = extracted_text.strip()
    if len(clean_text) == 0:
        return True

    alphanumeric_chars = sum(c.isalnum() or c.isspace() for c in clean_text)
    gibberish_ratio = 1 - (alphanumeric_chars / len(clean_text))

    return gibberish_ratio > 0.5
