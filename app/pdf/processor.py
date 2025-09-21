"""
PDF Text Processing Module
Handles PDF text extraction and content analysis
"""

import fitz  # PyMuPDF
from typing import Optional, Dict, List
from pathlib import Path


class PDFProcessor:
    """Handles PDF text extraction and processing"""

    def __init__(self, max_pages: int = 3, min_text_length: int = 10):
        """
        Initialize PDF processor

        Args:
            max_pages: Maximum number of pages to process for performance
            min_text_length: Minimum text length to consider valid
        """
        self.max_pages = max_pages
        self.min_text_length = min_text_length

    def extract_text(self, pdf_path: str, max_pages: Optional[int] = None) -> str:
        """
        Extract text content from PDF

        Args:
            pdf_path: Path to PDF file
            max_pages: Override default max pages limit

        Returns:
            Extracted text content
        """
        try:
            pdf_path = Path(pdf_path)
            if not pdf_path.exists():
                raise FileNotFoundError(f"PDF file not found: {pdf_path}")

            doc = fitz.open(str(pdf_path))
            text = ""

            # Use parameter or instance default
            page_limit = max_pages if max_pages is not None else self.max_pages

            # Extract text from first N pages for performance
            for page_num in range(min(page_limit, len(doc))):
                page = doc[page_num]
                page_text = page.get_text()
                text += page_text

            doc.close()
            return text.strip()

        except Exception as e:
            print(f"Error extracting text from PDF: {e}")
            return ""

    def extract_text_by_page(self, pdf_path: str, max_pages: Optional[int] = None) -> List[str]:
        """
        Extract text content from PDF, returning list of page texts

        Args:
            pdf_path: Path to PDF file
            max_pages: Override default max pages limit

        Returns:
            List of text content per page
        """
        try:
            pdf_path = Path(pdf_path)
            if not pdf_path.exists():
                raise FileNotFoundError(f"PDF file not found: {pdf_path}")

            doc = fitz.open(str(pdf_path))
            page_texts = []

            # Use parameter or instance default
            page_limit = max_pages if max_pages is not None else self.max_pages

            # Extract text from first N pages
            for page_num in range(min(page_limit, len(doc))):
                page = doc[page_num]
                page_text = page.get_text().strip()
                page_texts.append(page_text)

            doc.close()
            return page_texts

        except Exception as e:
            print(f"Error extracting text by page from PDF: {e}")
            return []

    def analyze_content(self, pdf_path: str) -> Dict[str, any]:
        """
        Analyze PDF content and extract metadata

        Args:
            pdf_path: Path to PDF file

        Returns:
            Dictionary with content analysis results
        """
        try:
            pdf_path = Path(pdf_path)
            if not pdf_path.exists():
                return {'error': f"PDF file not found: {pdf_path}"}

            # Extract text
            text = self.extract_text(pdf_path)
            page_texts = self.extract_text_by_page(pdf_path)

            # Basic analysis
            analysis = {
                'total_text_length': len(text),
                'page_count_processed': len(page_texts),
                'has_sufficient_text': len(text) >= self.min_text_length,
                'pages_with_text': sum(1 for page_text in page_texts if len(page_text) >= self.min_text_length),
                'average_chars_per_page': len(text) / len(page_texts) if page_texts else 0,
                'text_sample': text[:500] if text else "",
                'word_count': len(text.split()) if text else 0
            }

            # Content type indicators
            text_lower = text.lower()
            analysis['content_indicators'] = {
                'has_financial_terms': any(term in text_lower for term in ['euro', 'betrag', 'rechnung', 'umsatzsteuer', 'mehrwertsteuer']),
                'has_legal_terms': any(term in text_lower for term in ['vertrag', 'vereinbarung', 'rechtlich', 'paragraph']),
                'has_medical_terms': any(term in text_lower for term in ['patient', 'arzt', 'behandlung', 'medizin', 'gesundheit']),
                'has_work_terms': any(term in text_lower for term in ['arbeit', 'gehalt', 'lohn', 'arbeitsvertrag', 'arbeitgeber']),
                'has_date_patterns': any(pattern in text for pattern in ['2023', '2024', '2025', '.01.', '.02.', '.03.', '.04.', '.05.', '.06.', '.07.', '.08.', '.09.', '.10.', '.11.', '.12.'])
            }

            return analysis

        except Exception as e:
            return {'error': f"Error analyzing PDF content: {e}"}

    def is_valid_pdf(self, pdf_path: str) -> bool:
        """
        Check if file is a valid PDF

        Args:
            pdf_path: Path to PDF file

        Returns:
            True if valid PDF, False otherwise
        """
        try:
            pdf_path = Path(pdf_path)
            if not pdf_path.exists():
                return False

            doc = fitz.open(str(pdf_path))
            is_valid = len(doc) > 0
            doc.close()
            return is_valid

        except Exception:
            return False


# Default instance for backward compatibility
default_processor = PDFProcessor()

def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Legacy function for backward compatibility
    Extracts text from PDF for AI analysis
    """
    return default_processor.extract_text(pdf_path)