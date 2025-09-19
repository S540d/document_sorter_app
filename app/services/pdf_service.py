"""
PDF Verarbeitungsservice für Document Sorter
"""
import base64
from pathlib import Path
import fitz  # PyMuPDF

class PDFService:
    """Service für PDF-bezogene Operationen"""
    
    @staticmethod
    def create_preview(pdf_path: str) -> str:
        """Konvertiert erste Seite eines PDFs zu Base64-String für Preview"""
        try:
            doc = fitz.open(pdf_path)
            page = doc[0]
            
            # Render als PNG mit 150 DPI
            mat = fitz.Matrix(1.5, 1.5)
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("png")
            
            # Base64 encoding für HTML-Anzeige
            img_b64 = base64.b64encode(img_data).decode()
            doc.close()
            
            return f"data:image/png;base64,{img_b64}"
        except Exception as e:
            print(f"Error creating preview: {e}")
            return None
    
    @staticmethod
    def extract_text(pdf_path: str, max_pages: int = 3) -> str:
        """Extrahiert Text aus den ersten Seiten eines PDFs"""
        try:
            doc = fitz.open(pdf_path)
            text = ""
            
            # Maximal erste max_pages Seiten für Performance
            for page_num in range(min(max_pages, len(doc))):
                page = doc[page_num]
                text += page.get_text()
            
            doc.close()
            return text.strip()
        except Exception as e:
            print(f"Error extracting text: {e}")
            return ""