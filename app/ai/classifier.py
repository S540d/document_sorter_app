"""
AI Document Classification Module
Handles document classification using AI models via LM Studio
"""

import requests
from typing import List, Optional, Dict, Any
from .prompts import PromptManager
from ..settings import config


class DocumentClassifier:
    """Handles AI-powered document classification"""

    def __init__(self, lm_studio_url: str = None, timeout: int = 5):
        """
        Initialize document classifier

        Args:
            lm_studio_url: LM Studio API URL (uses config if not provided)
            timeout: Request timeout in seconds
        """
        self.lm_studio_url = lm_studio_url or config.lm_studio_url
        self.timeout = timeout
        self.prompt_manager = PromptManager()

    def parse_ai_response(self, raw_response: str, available_categories: List[str]) -> str:
        """
        Parse AI response and extract category name, handling reasoning tokens

        Args:
            raw_response: Raw response from AI model
            available_categories: List of valid categories

        Returns:
            Extracted category name
        """
        # First try exact match with available categories
        for category in available_categories:
            if category in raw_response:
                return category

        # Handle DeepSeek reasoning tokens - extract content after </think>
        if '</think>' in raw_response:
            parts = raw_response.split('</think>')
            if len(parts) > 1:
                final_answer = parts[-1].strip()
                # Check if final answer contains any category
                for category in available_categories:
                    if category in final_answer:
                        return category
                # If no category found, return the cleaned final answer
                return final_answer

        # Handle other reasoning patterns
        lines = raw_response.split('\n')
        for line in lines:
            line = line.strip()
            if line and not line.startswith('<') and not line.startswith('Okay') and not line.startswith('Ich'):
                for category in available_categories:
                    if category in line:
                        return category
                # If this line looks like a clean category answer, return it
                if len(line) < 50 and not line.endswith('?'):
                    return line

        # Fallback: return the cleaned raw response
        cleaned = raw_response.replace('<think>', '').replace('</think>', '').strip()
        lines = cleaned.split('\n')
        if lines:
            return lines[-1].strip()

        return raw_response.strip()

    def classify_document(self, text: str, filename: str, available_categories: List[str],
                         category_info: str) -> str:
        """
        Classify document using AI model

        Args:
            text: Document text content
            filename: Document filename
            available_categories: List of valid categories
            category_info: Formatted category information

        Returns:
            Classified category name
        """
        try:
            # Build classification prompt
            prompt = self.prompt_manager.build_classification_prompt(
                text, filename, category_info
            )

            # Prepare request
            request_config = self.prompt_manager.get_request_config()
            request_data = {
                **request_config,
                "messages": [
                    {"role": "system", "content": self.prompt_manager.get_system_message()},
                    {"role": "user", "content": prompt}
                ]
            }

            # Make API request
            response = requests.post(
                self.lm_studio_url,
                json=request_data,
                timeout=self.timeout
            )

            if response.status_code == 200:
                result = response.json()
                raw_response = result['choices'][0]['message']['content'].strip()

                # Parse response and extract category
                category = self.parse_ai_response(raw_response, available_categories)

                if category in available_categories:
                    return category
                else:
                    # Return first available category as fallback
                    return available_categories[0] if available_categories else 'Sonstiges'

            else:
                print(f"LM Studio API error: {response.status_code} - {response.text}")
                return available_categories[0] if available_categories else 'Sonstiges'

        except Exception as e:
            print(f"Error calling LM Studio: {e}")
            # Smart fallback based on filename and text analysis
            fallback_category = self._smart_fallback_classification(text, filename, available_categories)
            print(f"Using smart fallback classification: {fallback_category}")
            return fallback_category

    def _smart_fallback_classification(self, text: str, filename: str, available_categories: List[str]) -> str:
        """
        Smart fallback classification when AI is not available

        Args:
            text: Document text content
            filename: Document filename
            available_categories: List of valid categories

        Returns:
            Best guess category based on keywords
        """
        filename_lower = filename.lower() if filename else ""
        text_sample = text[:500].lower() if text else ""

        # Keyword mapping to common category patterns
        keyword_mappings = {
            'arbeit': ['arbeit', 'gehalt', 'lohn', 'arbeitsvertrag', 'job', 'deutsche bahn', 'evg', 'evoik'],
            'finanzen': ['rechnung', 'invoice', 'betrag', 'euro', 'umsatzsteuer', 'bank', 'steuer'],
            'versicherung': ['versicherung', 'police', 'schadensfall'],
            'wohnen': ['miete', 'wohnung', 'hausverwaltung', 'mietvertrag'],
            'fahrzeug': ['auto', 'kfz', 'fahrzeug', 'tüv', 'motorrad'],
            'medizin': ['arzt', 'behandlung', 'patient', 'medizin', 'gesundheit'],
            'kita': ['kita', 'kindergarten', 'betreuung']
        }

        # Check filename and text for keywords
        for pattern, keywords in keyword_mappings.items():
            for keyword in keywords:
                if keyword in filename_lower or keyword in text_sample:
                    # Find matching category
                    for category in available_categories:
                        category_lower = category.lower()
                        if (pattern in category_lower or
                            any(k in category_lower for k in keywords)):
                            return category

        # Default fallback to first non-blacklisted category
        preferred_fallbacks = ['Sonstiges', 'sonstiges', '12 schriftverkehr']
        for fallback in preferred_fallbacks:
            if fallback in available_categories:
                return fallback

        return available_categories[0] if available_categories else 'Sonstiges'

    def classify_with_analysis(self, text: str, filename: str, available_categories: List[str],
                              category_info: str) -> Dict[str, Any]:
        """
        Classify document and return detailed analysis

        Args:
            text: Document text content
            filename: Document filename
            available_categories: List of valid categories
            category_info: Formatted category information

        Returns:
            Dictionary with classification result and analysis
        """
        # Extract context hints
        context_hints = self.prompt_manager.extract_document_context(text, filename)

        # Classify document
        category = self.classify_document(text, filename, available_categories, category_info)

        # Return detailed analysis
        return {
            'category': category,
            'context_hints': context_hints,
            'text_length': len(text),
            'filename': filename,
            'confidence': 'high' if category in available_categories else 'low',
            'fallback_used': category not in available_categories
        }

    def test_connection(self) -> Dict[str, Any]:
        """
        Test connection to LM Studio

        Returns:
            Dictionary with connection test results
        """
        try:
            response = requests.post(
                self.lm_studio_url,
                json={
                    "model": "deepseek-r1-distill-qwen-7b",
                    "messages": [
                        {"role": "user", "content": "Test"}
                    ],
                    "max_tokens": 5
                },
                timeout=5
            )

            return {
                'connected': response.status_code == 200,
                'status_code': response.status_code,
                'url': self.lm_studio_url,
                'error': None if response.status_code == 200 else response.text
            }

        except Exception as e:
            return {
                'connected': False,
                'status_code': None,
                'url': self.lm_studio_url,
                'error': str(e)
            }


# Default instance for backward compatibility
default_classifier = DocumentClassifier()

def classify_document(text: str, filename: str = None) -> str:
    """
    Legacy function for backward compatibility
    This function needs to be called with proper context from the main app
    """
    # This is a simplified version for backward compatibility
    # The full implementation should be called from app.py with proper context
    return default_classifier.classify_document(
        text, filename or 'unknown', ['Sonstiges'], 'No categories available'
    )