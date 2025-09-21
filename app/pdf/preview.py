"""
PDF Preview Generation Module
Handles conversion of PDF pages to preview images
"""

import base64
import fitz  # PyMuPDF
from typing import Optional
from pathlib import Path


class PDFPreviewGenerator:
    """Handles PDF preview image generation"""

    def __init__(self, dpi: float = 1.5, format: str = "png"):
        """
        Initialize PDF preview generator

        Args:
            dpi: DPI scaling factor (1.5 = 150 DPI)
            format: Output image format (png, jpeg)
        """
        self.dpi = dpi
        self.format = format.lower()

    def generate_preview(self, pdf_path: str, page_num: int = 0) -> Optional[str]:
        """
        Generate base64-encoded preview image of PDF page

        Args:
            pdf_path: Path to PDF file
            page_num: Page number to convert (0-indexed)

        Returns:
            Base64-encoded image data URL or None if error
        """
        try:
            pdf_path = Path(pdf_path)
            if not pdf_path.exists():
                raise FileNotFoundError(f"PDF file not found: {pdf_path}")

            doc = fitz.open(str(pdf_path))

            # Check if page exists
            if page_num >= len(doc):
                raise IndexError(f"Page {page_num} does not exist (PDF has {len(doc)} pages)")

            page = doc[page_num]

            # Render page as image with specified DPI
            mat = fitz.Matrix(self.dpi, self.dpi)
            pix = page.get_pixmap(matrix=mat)

            # Convert to bytes
            img_data = pix.tobytes(self.format)
            doc.close()

            # Base64 encode for HTML display
            img_b64 = base64.b64encode(img_data).decode()

            return f"data:image/{self.format};base64,{img_b64}"

        except Exception as e:
            print(f"Error creating PDF preview: {e}")
            return None

    def get_pdf_info(self, pdf_path: str) -> dict:
        """
        Get basic information about PDF file

        Args:
            pdf_path: Path to PDF file

        Returns:
            Dictionary with PDF metadata
        """
        try:
            pdf_path = Path(pdf_path)
            if not pdf_path.exists():
                return {'error': f"PDF file not found: {pdf_path}"}

            doc = fitz.open(str(pdf_path))

            info = {
                'page_count': len(doc),
                'metadata': doc.metadata,
                'file_size': pdf_path.stat().st_size,
                'has_text': False
            }

            # Check if PDF has extractable text (sample first page)
            if len(doc) > 0:
                page = doc[0]
                text = page.get_text().strip()
                info['has_text'] = len(text) > 10  # Arbitrary threshold

            doc.close()
            return info

        except Exception as e:
            return {'error': f"Error reading PDF info: {e}"}


# Default instance for backward compatibility
default_preview_generator = PDFPreviewGenerator()

def pdf_to_preview_image(pdf_path: str) -> Optional[str]:
    """
    Legacy function for backward compatibility
    Converts first page of PDF to base64 preview image
    """
    return default_preview_generator.generate_preview(pdf_path)