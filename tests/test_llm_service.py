"""
Tests for LLM service functionality
"""
import pytest
import json
from unittest.mock import patch, MagicMock
import sys
import os

# Import the services to test
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.llm_service import LLMService

class TestLLMService:
    """Test cases for LLMService"""

    @pytest.fixture
    def llm_service(self, app_config):
        """Create LLMService instance for testing"""
        return LLMService(app_config)

    def test_init(self, llm_service, app_config):
        """Test LLMService initialization"""
        assert llm_service.lm_studio_url == app_config['LM_STUDIO_URL']
        assert llm_service.cache_service is not None

    @patch('requests.post')
    def test_categorize_text_success(self, mock_post, llm_service, mock_llm_response):
        """Test successful text categorization"""
        # Mock successful API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'choices': [{
                'message': {
                    'content': json.dumps(mock_llm_response)
                }
            }]
        }
        mock_post.return_value = mock_response

        result = llm_service.categorize_text("Test document content")

        assert result['category'] == 'invoice'
        assert result['confidence'] == 0.95
        assert 'metadata' in result
        mock_post.assert_called_once()

    @patch('requests.post')
    def test_categorize_text_api_error(self, mock_post, llm_service):
        """Test API error handling"""
        # Mock API error
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = Exception("API Error")
        mock_post.return_value = mock_response

        with pytest.raises(Exception):
            llm_service.categorize_text("Test content")

    @patch('requests.post')
    def test_categorize_text_invalid_json(self, mock_post, llm_service):
        """Test handling of invalid JSON response"""
        # Mock response with invalid JSON
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'choices': [{
                'message': {
                    'content': 'Invalid JSON response'
                }
            }]
        }
        mock_post.return_value = mock_response

        result = llm_service.categorize_text("Test content")

        # Should return default category on JSON parse error
        assert result['category'] == 'other'
        assert result['confidence'] < 1.0

    @patch('requests.post')
    def test_categorize_text_empty_response(self, mock_post, llm_service):
        """Test handling of empty API response"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'choices': []}
        mock_post.return_value = mock_response

        result = llm_service.categorize_text("Test content")

        assert result['category'] == 'other'
        assert result['confidence'] < 1.0

    @patch('requests.post')
    def test_caching_behavior(self, mock_post, llm_service):
        """Test that LLM responses are cached"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'choices': [{
                'message': {
                    'content': json.dumps({
                        'category': 'invoice',
                        'confidence': 0.95
                    })
                }
            }]
        }
        mock_post.return_value = mock_response

        text = "Same content for caching test"

        # First call
        result1 = llm_service.categorize_text(text)
        assert mock_post.call_count == 1

        # Second call with same content - should use cache
        result2 = llm_service.categorize_text(text)
        # Should still be 1 because cached result is used
        assert mock_post.call_count == 1

        assert result1 == result2

    def test_build_categorization_prompt(self, llm_service):
        """Test prompt building for categorization"""
        text = "Invoice from Company ABC for $100"
        prompt = llm_service._build_categorization_prompt(text)

        assert "categorize" in prompt.lower()
        assert "invoice" in prompt.lower() or "category" in prompt.lower()
        assert text in prompt

    @patch('requests.post')
    def test_categorize_text_timeout(self, mock_post, llm_service):
        """Test timeout handling"""
        import requests
        mock_post.side_effect = requests.exceptions.Timeout("Request timeout")

        with pytest.raises(requests.exceptions.Timeout):
            llm_service.categorize_text("Test content")

    @patch('requests.post')
    def test_categorize_text_connection_error(self, mock_post, llm_service):
        """Test connection error handling"""
        import requests
        mock_post.side_effect = requests.exceptions.ConnectionError("Connection failed")

        with pytest.raises(requests.exceptions.ConnectionError):
            llm_service.categorize_text("Test content")

class TestAsyncLLMService:
    """Test cases for AsyncLLMService if available"""

    @pytest.fixture
    def async_llm_service(self, app_config):
        """Create AsyncLLMService instance for testing"""
        try:
            from app.services.async_llm_service import AsyncLLMService
            return AsyncLLMService(app_config)
        except ImportError:
            pytest.skip("AsyncLLMService not available")

    @pytest.mark.asyncio
    async def test_async_categorize_text(self, async_llm_service, mock_llm_response):
        """Test async text categorization"""
        if async_llm_service is None:
            pytest.skip("AsyncLLMService not available")

        with patch('aiohttp.ClientSession.post') as mock_post:
            # Mock async response
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.json = MagicMock(return_value={
                'choices': [{
                    'message': {
                        'content': json.dumps(mock_llm_response)
                    }
                }]
            })

            # Mock context manager behavior
            mock_post.return_value.__aenter__.return_value = mock_response
            mock_post.return_value.__aexit__.return_value = None

            result = await async_llm_service.categorize_text_async("Test document content")

            assert result['category'] == 'invoice'
            assert result['confidence'] == 0.95

    @pytest.mark.asyncio
    async def test_batch_categorization(self, async_llm_service):
        """Test batch text categorization"""
        if async_llm_service is None:
            pytest.skip("AsyncLLMService not available")

        texts = ["Invoice text", "Contract text", "Receipt text"]

        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.json = MagicMock(return_value={
                'choices': [{
                    'message': {
                        'content': json.dumps({
                            'category': 'invoice',
                            'confidence': 0.9
                        })
                    }
                }]
            })

            mock_post.return_value.__aenter__.return_value = mock_response
            mock_post.return_value.__aexit__.return_value = None

            results = await async_llm_service.batch_categorize(texts)

            assert len(results) == 3
            for result in results:
                assert 'text' in result
                assert 'category' in result
                assert 'confidence' in result