"""
Tests for Flask application endpoints
"""
import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys
import os

# Import the Flask app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import Flask app for testing
@pytest.fixture
def client(temp_dirs, app_config):
    """Create test client"""
    # Set up temporary directories
    app_config['SCAN_DIR'] = temp_dirs['scan_dir']
    app_config['SORTED_DIR'] = temp_dirs['sorted_dir']

    # Mock environment variables
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

class TestFlaskApp:
    """Test cases for Flask application"""

    def test_index_page(self, client):
        """Test main index page"""
        response = client.get('/')
        assert response.status_code == 200
        assert b'Document Sorter' in response.data or b'<!DOCTYPE html>' in response.data

    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get('/health')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['status'] == 'healthy'
        assert 'timestamp' in data
        assert 'version' in data

    def test_scan_endpoint_no_files(self, client):
        """Test scan endpoint with no PDF files"""
        response = client.post('/scan')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert 'scanned_files' in data
        assert data['scanned_files'] == []

    @patch('app.services.pdf_service.PDFService.get_pdf_files')
    @patch('app.services.pdf_service.PDFService.extract_text')
    @patch('app.services.llm_service.LLMService.categorize_text')
    @patch('app.services.pdf_service.PDFService.move_file')
    def test_scan_endpoint_with_files(self, mock_move, mock_categorize, mock_extract, mock_get_files, client, temp_dirs):
        """Test scan endpoint with PDF files"""
        # Create a test PDF file
        test_pdf = Path(temp_dirs['scan_dir']) / 'test.pdf'
        test_pdf.write_bytes(b"dummy pdf content")

        # Mock the service calls
        mock_get_files.return_value = [str(test_pdf)]
        mock_extract.return_value = "Test document content"
        mock_categorize.return_value = {
            'category': 'invoice',
            'confidence': 0.95,
            'metadata': {'company': 'Test Corp'}
        }
        mock_move.return_value = str(Path(temp_dirs['sorted_dir']) / 'invoice' / 'test.pdf')

        response = client.post('/scan')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert len(data['scanned_files']) == 1

        file_result = data['scanned_files'][0]
        assert file_result['filename'] == 'test.pdf'
        assert file_result['category'] == 'invoice'
        assert file_result['confidence'] == 0.95

    def test_status_endpoint(self, client):
        """Test status endpoint"""
        response = client.get('/status')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert 'total_files' in data
        assert 'categories' in data
        assert 'last_scan' in data

    def test_files_endpoint(self, client):
        """Test files listing endpoint"""
        response = client.get('/files')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert 'files' in data
        assert isinstance(data['files'], list)

    def test_categorize_endpoint_missing_text(self, client):
        """Test categorize endpoint without text parameter"""
        response = client.post('/categorize')
        assert response.status_code == 400

        data = json.loads(response.data)
        assert 'error' in data

    @patch('app.services.llm_service.LLMService.categorize_text')
    def test_categorize_endpoint_success(self, mock_categorize, client):
        """Test successful categorization"""
        mock_categorize.return_value = {
            'category': 'contract',
            'confidence': 0.88,
            'metadata': {}
        }

        response = client.post('/categorize', data={'text': 'Test contract content'})
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['category'] == 'contract'
        assert data['confidence'] == 0.88

    def test_move_file_missing_params(self, client):
        """Test move file endpoint with missing parameters"""
        response = client.post('/move_file')
        assert response.status_code == 400

    @patch('app.services.pdf_service.PDFService.move_file')
    def test_move_file_success(self, mock_move, client, temp_dirs):
        """Test successful file moving"""
        # Create test file
        test_file = Path(temp_dirs['scan_dir']) / 'test.pdf'
        test_file.write_bytes(b"test content")

        mock_move.return_value = str(Path(temp_dirs['sorted_dir']) / 'invoices' / 'test.pdf')

        response = client.post('/move_file', data={
            'filepath': str(test_file),
            'category': 'invoices',
            'filename': 'test.pdf'
        })

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True

    def test_nonexistent_endpoint(self, client):
        """Test accessing non-existent endpoint"""
        response = client.get('/nonexistent')
        assert response.status_code == 404

class TestPerformanceEndpoints:
    """Test performance monitoring endpoints"""

    def test_performance_current(self, client):
        """Test current performance metrics endpoint"""
        response = client.get('/api/performance/current')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert 'timestamp' in data
        assert 'system' in data
        assert 'monitoring_active' in data

    def test_performance_historical(self, client):
        """Test historical performance metrics endpoint"""
        response = client.get('/api/performance/historical?hours=1')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert 'time_range_hours' in data
        assert 'system' in data

    def test_performance_summary(self, client):
        """Test performance summary endpoint"""
        response = client.get('/api/performance/summary')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert 'time_range_hours' in data
        assert 'system_health' in data

    def test_dashboard_overview(self, client):
        """Test dashboard overview endpoint"""
        response = client.get('/api/dashboard/overview')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert 'system_health' in data
        assert 'application_stats' in data

class TestErrorHandling:
    """Test error handling in the application"""

    @patch('app.services.pdf_service.PDFService.get_pdf_files')
    def test_scan_with_service_error(self, mock_get_files, client):
        """Test scan endpoint when service throws error"""
        mock_get_files.side_effect = Exception("Service error")

        response = client.post('/scan')
        assert response.status_code == 500

        data = json.loads(response.data)
        assert 'error' in data

    @patch('app.services.llm_service.LLMService.categorize_text')
    def test_categorize_with_llm_error(self, mock_categorize, client):
        """Test categorize endpoint when LLM service fails"""
        mock_categorize.side_effect = Exception("LLM service error")

        response = client.post('/categorize', data={'text': 'Test content'})
        assert response.status_code == 500

        data = json.loads(response.data)
        assert 'error' in data