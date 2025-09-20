"""
Integration tests for the complete document processing workflow
"""
import pytest
import tempfile
import shutil
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys
import os

# Import modules for integration testing
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

@pytest.mark.integration
class TestDocumentProcessingWorkflow:
    """Integration tests for the complete document processing workflow"""

    @pytest.fixture
    def integration_setup(self, temp_dirs, app_config):
        """Set up complete environment for integration testing"""
        # Create test directories
        scan_dir = Path(temp_dirs['scan_dir'])
        sorted_dir = Path(temp_dirs['sorted_dir'])

        # Create sample PDF files
        sample_files = {
            'invoice.pdf': b"Invoice content from Company ABC for $1000",
            'contract.pdf': b"Contract agreement between parties",
            'receipt.pdf': b"Receipt for purchase of office supplies"
        }

        for filename, content in sample_files.items():
            file_path = scan_dir / filename
            file_path.write_bytes(content)

        app_config.update({
            'SCAN_DIR': str(scan_dir),
            'SORTED_DIR': str(sorted_dir)
        })

        return {
            'scan_dir': scan_dir,
            'sorted_dir': sorted_dir,
            'config': app_config,
            'sample_files': sample_files
        }

    @patch('app.services.pdf_service.PDFService.extract_text')
    @patch('app.services.llm_service.LLMService.categorize_text')
    def test_complete_document_workflow(self, mock_categorize, mock_extract, integration_setup):
        """Test the complete document processing workflow"""
        from app.services.pdf_service import PDFService
        from app.services.llm_service import LLMService

        # Mock text extraction
        def extract_text_side_effect(file_path):
            if 'invoice.pdf' in file_path:
                return "Invoice from Company ABC dated 2024-01-15 for amount $1000"
            elif 'contract.pdf' in file_path:
                return "Service Agreement between Client and Provider effective 2024-01-01"
            elif 'receipt.pdf' in file_path:
                return "Receipt for office supplies purchased on 2024-01-10"
            return "Generic document content"

        mock_extract.side_effect = extract_text_side_effect

        # Mock categorization
        def categorize_side_effect(text):
            if 'invoice' in text.lower():
                return {
                    'category': 'invoices',
                    'confidence': 0.95,
                    'metadata': {'company': 'Company ABC', 'amount': '$1000'}
                }
            elif 'contract' in text.lower() or 'agreement' in text.lower():
                return {
                    'category': 'contracts',
                    'confidence': 0.92,
                    'metadata': {'type': 'Service Agreement'}
                }
            elif 'receipt' in text.lower():
                return {
                    'category': 'receipts',
                    'confidence': 0.88,
                    'metadata': {'type': 'Office Supplies'}
                }
            return {'category': 'other', 'confidence': 0.5}

        mock_categorize.side_effect = categorize_side_effect

        # Initialize services
        pdf_service = PDFService(integration_setup['config'])
        llm_service = LLMService(integration_setup['config'])

        # Get PDF files
        pdf_files = pdf_service.get_pdf_files()
        assert len(pdf_files) == 3

        # Process each file
        results = []
        for pdf_file in pdf_files:
            # Extract text
            text = pdf_service.extract_text(str(pdf_file))
            assert len(text) > 0

            # Categorize
            category_result = llm_service.categorize_text(text)
            assert category_result['confidence'] > 0.8

            # Move file
            filename = Path(pdf_file).name
            moved_path = pdf_service.move_file(
                str(pdf_file),
                category_result['category'],
                filename
            )

            results.append({
                'original_path': str(pdf_file),
                'moved_path': moved_path,
                'category': category_result['category'],
                'confidence': category_result['confidence']
            })

        # Verify results
        assert len(results) == 3

        # Check that files were moved to correct categories
        categories_found = {r['category'] for r in results}
        expected_categories = {'invoices', 'contracts', 'receipts'}
        assert categories_found == expected_categories

        # Verify physical file movement
        for result in results:
            assert not Path(result['original_path']).exists()  # Original should be gone
            assert Path(result['moved_path']).exists()  # Should exist in new location

        # Verify directory structure
        sorted_dir = Path(integration_setup['sorted_dir'])
        for category in expected_categories:
            category_dir = sorted_dir / category
            assert category_dir.exists()
            assert category_dir.is_dir()

    @patch('app.services.pdf_service.PDFService.extract_text')
    @patch('app.services.llm_service.LLMService.categorize_text')
    def test_error_handling_workflow(self, mock_categorize, mock_extract, integration_setup):
        """Test error handling in the document workflow"""
        from app.services.pdf_service import PDFService
        from app.services.llm_service import LLMService

        # Mock extraction failure
        mock_extract.side_effect = Exception("PDF extraction failed")

        pdf_service = PDFService(integration_setup['config'])
        llm_service = LLMService(integration_setup['config'])

        pdf_files = pdf_service.get_pdf_files()
        assert len(pdf_files) > 0

        # Should raise exception for extraction failure
        with pytest.raises(Exception, match="PDF extraction failed"):
            pdf_service.extract_text(str(pdf_files[0]))

    @patch('app.services.pdf_service.PDFService.extract_text')
    @patch('app.services.llm_service.LLMService.categorize_text')
    def test_caching_integration(self, mock_categorize, mock_extract, integration_setup):
        """Test that caching works across the workflow"""
        from app.services.pdf_service import PDFService
        from app.services.llm_service import LLMService

        mock_extract.return_value = "Test document content"
        mock_categorize.return_value = {
            'category': 'test',
            'confidence': 0.9
        }

        pdf_service = PDFService(integration_setup['config'])
        llm_service = LLMService(integration_setup['config'])

        pdf_files = pdf_service.get_pdf_files()
        test_file = str(pdf_files[0])

        # First extraction - should call mock
        text1 = pdf_service.extract_text(test_file)
        assert mock_extract.call_count == 1

        # Second extraction - should use cache
        text2 = pdf_service.extract_text(test_file)
        assert mock_extract.call_count == 1  # Still 1, cached
        assert text1 == text2

        # First categorization
        result1 = llm_service.categorize_text("same text content")
        assert mock_categorize.call_count == 1

        # Second categorization with same text - should use cache
        result2 = llm_service.categorize_text("same text content")
        assert mock_categorize.call_count == 1  # Still 1, cached
        assert result1 == result2

@pytest.mark.integration
class TestAPIIntegration:
    """Integration tests for API endpoints"""

    @pytest.fixture
    def api_client(self, temp_dirs, app_config):
        """Create Flask test client for API testing"""
        app_config.update({
            'SCAN_DIR': temp_dirs['scan_dir'],
            'SORTED_DIR': temp_dirs['sorted_dir']
        })

        with patch.dict(os.environ, {
            'SCAN_DIR': temp_dirs['scan_dir'],
            'SORTED_DIR': temp_dirs['sorted_dir'],
            'LM_STUDIO_URL': 'http://localhost:1234',
            'SECRET_KEY': 'test-secret-key'
        }):
            from app import app
            app.config['TESTING'] = True
            with app.test_client() as client:
                yield client

    @patch('app.services.pdf_service.PDFService.get_pdf_files')
    @patch('app.services.pdf_service.PDFService.extract_text')
    @patch('app.services.llm_service.LLMService.categorize_text')
    @patch('app.services.pdf_service.PDFService.move_file')
    def test_scan_api_integration(self, mock_move, mock_categorize, mock_extract, mock_get_files, api_client, temp_dirs):
        """Test the complete scan API workflow"""
        # Create test file
        test_file = Path(temp_dirs['scan_dir']) / 'test_document.pdf'
        test_file.write_bytes(b"test content")

        # Mock service responses
        mock_get_files.return_value = [str(test_file)]
        mock_extract.return_value = "Test invoice document content"
        mock_categorize.return_value = {
            'category': 'invoices',
            'confidence': 0.93,
            'metadata': {'type': 'business_invoice'}
        }
        mock_move.return_value = str(Path(temp_dirs['sorted_dir']) / 'invoices' / 'test_document.pdf')

        # Call scan API
        response = api_client.post('/scan')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert 'scanned_files' in data
        assert len(data['scanned_files']) == 1

        file_result = data['scanned_files'][0]
        assert file_result['filename'] == 'test_document.pdf'
        assert file_result['category'] == 'invoices'
        assert file_result['confidence'] == 0.93
        assert 'metadata' in file_result

    def test_status_api_integration(self, api_client):
        """Test status API integration"""
        response = api_client.get('/status')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert 'total_files' in data
        assert 'categories' in data
        assert 'last_scan' in data
        assert isinstance(data['categories'], dict)

    def test_performance_api_integration(self, api_client):
        """Test performance monitoring API integration"""
        # Test current metrics
        response = api_client.get('/api/performance/current')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert 'timestamp' in data
        assert 'system' in data
        assert 'monitoring_active' in data

        # Test historical metrics
        response = api_client.get('/api/performance/historical?hours=1')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert 'time_range_hours' in data
        assert data['time_range_hours'] == 1

        # Test performance summary
        response = api_client.get('/api/performance/summary?hours=24')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert 'system_health' in data
        assert 'application_performance' in data
        assert 'alerts' in data

@pytest.mark.integration
@pytest.mark.slow
class TestAsyncIntegration:
    """Integration tests for async functionality"""

    @pytest.mark.asyncio
    async def test_async_batch_processing(self, temp_dirs, app_config):
        """Test async batch processing integration"""
        try:
            from app.services.async_pdf_service import AsyncPDFService
            from app.services.async_llm_service import AsyncLLMService
        except ImportError:
            pytest.skip("Async services not available")

        # Create multiple test files
        scan_dir = Path(temp_dirs['scan_dir'])
        test_files = []
        for i in range(5):
            test_file = scan_dir / f'test_document_{i}.pdf'
            test_file.write_bytes(f"Test document content {i}".encode())
            test_files.append(str(test_file))

        app_config.update({
            'SCAN_DIR': str(scan_dir),
            'SORTED_DIR': temp_dirs['sorted_dir']
        })

        async_pdf_service = AsyncPDFService(app_config)
        async_llm_service = AsyncLLMService(app_config)

        with patch('PyPDF2.PdfReader') as mock_pdf_reader:
            # Mock PDF extraction
            mock_page = MagicMock()
            mock_page.extract_text.return_value = "Async test document content"
            mock_pdf_reader.return_value.pages = [mock_page]

            # Process files in batch
            results = await async_pdf_service.process_batch(test_files[:3])

            assert len(results) == 3
            for result in results:
                assert 'file_path' in result
                assert 'text' in result
                assert result['text'] == "Async test document content"

    @pytest.mark.asyncio
    async def test_async_error_handling(self, temp_dirs, app_config):
        """Test async error handling integration"""
        try:
            from app.services.async_pdf_service import AsyncPDFService
        except ImportError:
            pytest.skip("Async services not available")

        app_config.update({
            'SCAN_DIR': temp_dirs['scan_dir'],
            'SORTED_DIR': temp_dirs['sorted_dir']
        })

        async_pdf_service = AsyncPDFService(app_config)

        # Test with non-existent file
        with pytest.raises(FileNotFoundError):
            await async_pdf_service.extract_text_async('/non/existent/file.pdf')