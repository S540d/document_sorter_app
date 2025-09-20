"""
Test configuration and fixtures
"""
import pytest
import os
import tempfile
import shutil
from pathlib import Path

@pytest.fixture
def temp_dirs():
    """Create temporary directories for testing"""
    scan_dir = tempfile.mkdtemp(prefix='test_scan_')
    sorted_dir = tempfile.mkdtemp(prefix='test_sorted_')

    yield {
        'scan_dir': scan_dir,
        'sorted_dir': sorted_dir
    }

    # Cleanup
    shutil.rmtree(scan_dir, ignore_errors=True)
    shutil.rmtree(sorted_dir, ignore_errors=True)

@pytest.fixture
def sample_pdf_file():
    """Create a sample PDF file for testing"""
    content = b"""
    %PDF-1.4
    1 0 obj
    <<
    /Type /Catalog
    /Pages 2 0 R
    >>
    endobj

    2 0 obj
    <<
    /Type /Pages
    /Kids [3 0 R]
    /Count 1
    >>
    endobj

    3 0 obj
    <<
    /Type /Page
    /Parent 2 0 R
    /MediaBox [0 0 612 792]
    /Contents 4 0 R
    >>
    endobj

    4 0 obj
    <<
    /Length 44
    >>
    stream
    BT
    /F1 12 Tf
    72 720 Td
    (Test Document) Tj
    ET
    endstream
    endobj

    xref
    0 5
    0000000000 65535 f
    0000000009 00000 n
    0000000074 00000 n
    0000000120 00000 n
    0000000179 00000 n
    trailer
    <<
    /Size 5
    /Root 1 0 R
    >>
    startxref
    238
    %%EOF
    """
    return content

@pytest.fixture
def app_config():
    """Test application configuration"""
    return {
        'SCAN_DIR': '',
        'SORTED_DIR': '',
        'LM_STUDIO_URL': 'http://localhost:1234',
        'DEBUG_MODE': True,
        'SECRET_KEY': 'test-secret-key'
    }

@pytest.fixture
def mock_llm_response():
    """Mock LLM response for testing"""
    return {
        'category': 'invoice',
        'confidence': 0.95,
        'metadata': {
            'company': 'Test Company',
            'date': '2024-01-15',
            'amount': '$100.00'
        }
    }