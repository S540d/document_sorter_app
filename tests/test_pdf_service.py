"""
Tests for PDF service functionality
"""
import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import PyPDF2

# Import the services to test
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.pdf_service import PDFService
from app.services.cache_service import get_cache_service

class TestPDFService:
    """Test cases for PDFService"""

    @pytest.fixture
    def pdf_service(self, temp_dirs, app_config):
        """Create PDFService instance for testing"""
        app_config['SCAN_DIR'] = temp_dirs['scan_dir']
        app_config['SORTED_DIR'] = temp_dirs['sorted_dir']
        return PDFService(app_config)

    def test_init(self, pdf_service, temp_dirs):
        """Test PDFService initialization"""
        assert pdf_service.scan_dir == temp_dirs['scan_dir']
        assert pdf_service.sorted_dir == temp_dirs['sorted_dir']
        assert pdf_service.cache_service is not None

    @patch('PyPDF2.PdfReader')
    def test_extract_text_success(self, mock_pdf_reader, pdf_service, sample_pdf_file):
        """Test successful text extraction from PDF"""
        # Create temporary PDF file
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            tmp_file.write(sample_pdf_file)
            tmp_file_path = tmp_file.name

        try:
            # Mock PyPDF2 behavior
            mock_page = MagicMock()
            mock_page.extract_text.return_value = "Test Document Content"
            mock_pdf_reader.return_value.pages = [mock_page]

            text = pdf_service.extract_text(tmp_file_path)

            assert text == "Test Document Content"
            mock_pdf_reader.assert_called_once()

        finally:
            os.unlink(tmp_file_path)

    def test_extract_text_file_not_found(self, pdf_service):
        """Test text extraction with non-existent file"""
        with pytest.raises(FileNotFoundError):
            pdf_service.extract_text("/non/existent/file.pdf")

    @patch('PyPDF2.PdfReader')
    def test_extract_text_invalid_pdf(self, mock_pdf_reader, pdf_service):
        """Test text extraction with invalid PDF"""
        mock_pdf_reader.side_effect = Exception("Invalid PDF")

        with tempfile.NamedTemporaryFile(suffix='.pdf') as tmp_file:
            tmp_file.write(b"invalid pdf content")
            tmp_file.flush()

            with pytest.raises(Exception):
                pdf_service.extract_text(tmp_file.name)

    def test_get_pdf_files(self, pdf_service, temp_dirs):
        """Test getting PDF files from directory"""
        # Create test PDF files
        pdf_files = ['test1.pdf', 'test2.pdf', 'not_pdf.txt']
        for filename in pdf_files:
            file_path = Path(temp_dirs['scan_dir']) / filename
            file_path.write_bytes(b"dummy content")

        found_pdfs = pdf_service.get_pdf_files()

        assert len(found_pdfs) == 2
        assert any('test1.pdf' in str(path) for path in found_pdfs)
        assert any('test2.pdf' in str(path) for path in found_pdfs)
        assert not any('not_pdf.txt' in str(path) for path in found_pdfs)

    def test_move_file_success(self, pdf_service, temp_dirs):
        """Test successful file moving"""
        # Create source file
        source_file = Path(temp_dirs['scan_dir']) / 'test.pdf'
        source_file.write_bytes(b"test content")

        # Move file
        moved_path = pdf_service.move_file(str(source_file), 'invoices', 'test.pdf')

        # Check that file was moved
        assert not source_file.exists()
        assert Path(moved_path).exists()
        assert 'invoices' in str(moved_path)

    def test_move_file_create_category_dir(self, pdf_service, temp_dirs):
        """Test that category directory is created if it doesn't exist"""
        source_file = Path(temp_dirs['scan_dir']) / 'test.pdf'
        source_file.write_bytes(b"test content")

        category = 'new_category'
        moved_path = pdf_service.move_file(str(source_file), category, 'test.pdf')

        # Check that category directory was created
        category_dir = Path(temp_dirs['sorted_dir']) / category
        assert category_dir.exists()
        assert category_dir.is_dir()

    def test_move_file_source_not_exists(self, pdf_service):
        """Test moving non-existent file"""
        with pytest.raises(FileNotFoundError):
            pdf_service.move_file('/non/existent/file.pdf', 'category', 'file.pdf')

    @patch('app.services.pdf_service.PDFService.extract_text')
    def test_caching_behavior(self, mock_extract_text, pdf_service, temp_dirs):
        """Test that PDF text extraction results are cached"""
        # Create test file
        test_file = Path(temp_dirs['scan_dir']) / 'test.pdf'
        test_file.write_bytes(b"test content")

        mock_extract_text.return_value = "Cached text content"

        # First call - should call extract_text
        text1 = pdf_service.extract_text(str(test_file))
        assert text1 == "Cached text content"
        assert mock_extract_text.call_count == 1

        # Second call - should use cache
        text2 = pdf_service.extract_text(str(test_file))
        assert text2 == "Cached text content"
        # Should still be 1 because cached result is used
        assert mock_extract_text.call_count == 1

    def test_get_file_info(self, pdf_service, temp_dirs):
        """Test getting file information"""
        test_file = Path(temp_dirs['scan_dir']) / 'test.pdf'
        test_file.write_bytes(b"test content")

        info = pdf_service.get_file_info(str(test_file))

        assert 'filename' in info
        assert 'size_bytes' in info
        assert 'modified_time' in info
        assert info['filename'] == 'test.pdf'
        assert info['size_bytes'] > 0

class TestAsyncPDFService:
    """Test cases for AsyncPDFService if available"""

    @pytest.fixture
    def async_pdf_service(self, temp_dirs, app_config):
        """Create AsyncPDFService instance for testing"""
        try:
            from app.services.async_pdf_service import AsyncPDFService
            app_config['SCAN_DIR'] = temp_dirs['scan_dir']
            app_config['SORTED_DIR'] = temp_dirs['sorted_dir']
            return AsyncPDFService(app_config)
        except ImportError:
            pytest.skip("AsyncPDFService not available")

    @pytest.mark.asyncio
    async def test_async_extract_text(self, async_pdf_service, sample_pdf_file):
        """Test async text extraction"""
        if async_pdf_service is None:
            pytest.skip("AsyncPDFService not available")

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            tmp_file.write(sample_pdf_file)
            tmp_file_path = tmp_file.name

        try:
            with patch('PyPDF2.PdfReader') as mock_pdf_reader:
                mock_page = MagicMock()
                mock_page.extract_text.return_value = "Async Test Content"
                mock_pdf_reader.return_value.pages = [mock_page]

                text = await async_pdf_service.extract_text_async(tmp_file_path)
                assert text == "Async Test Content"

        finally:
            os.unlink(tmp_file_path)

    @pytest.mark.asyncio
    async def test_batch_processing(self, async_pdf_service, temp_dirs, sample_pdf_file):
        """Test batch PDF processing"""
        if async_pdf_service is None:
            pytest.skip("AsyncPDFService not available")

        # Create multiple test PDF files
        pdf_files = []
        for i in range(3):
            pdf_path = Path(temp_dirs['scan_dir']) / f'test_{i}.pdf'
            pdf_path.write_bytes(sample_pdf_file)
            pdf_files.append(str(pdf_path))

        with patch('PyPDF2.PdfReader') as mock_pdf_reader:
            mock_page = MagicMock()
            mock_page.extract_text.return_value = "Batch Test Content"
            mock_pdf_reader.return_value.pages = [mock_page]

            results = await async_pdf_service.process_batch(pdf_files)

            assert len(results) == 3
            for result in results:
                assert 'file_path' in result
                assert 'text' in result
                assert result['text'] == "Batch Test Content"