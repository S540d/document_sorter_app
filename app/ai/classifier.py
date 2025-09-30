"""
AI Document Classification Module
Handles document classification using AI models via LM Studio
"""

import requests
from typing import List, Optional, Dict, Any
from .prompts import PromptManager
from .document_templates import document_template_engine, DocumentTypeResult
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

    def parse_ai_response(self, raw_response: str, available_categories: List[str]) -> Dict[str, str]:
        """
        Parse AI response and extract category and subdirectory

        Args:
            raw_response: Raw response from AI model
            available_categories: List of valid categories

        Returns:
            Dictionary with 'category' and 'subdirectory' keys
        """
        # Default response structure
        result = {'category': '', 'subdirectory': ''}

        # Handle DeepSeek reasoning tokens - extract content after </think>
        response_text = raw_response
        if '</think>' in raw_response:
            parts = raw_response.split('</think>')
            if len(parts) > 1:
                response_text = parts[-1].strip()

        # Clean the response
        response_text = response_text.replace('<think>', '').replace('</think>', '').strip()

        # Look for the new format: CATEGORY|SUBDIRECTORY
        if '|' in response_text:
            lines = response_text.split('\n')
            for line in lines:
                line = line.strip()
                if '|' in line and not line.startswith('<') and not line.startswith('Okay') and not line.startswith('Ich'):
                    parts = line.split('|', 1)  # Split only on first |
                    if len(parts) == 2:
                        category_part = parts[0].strip()
                        subdirectory_part = parts[1].strip()

                        # Validate category
                        for category in available_categories:
                            if category == category_part or category in category_part:
                                result['category'] = category
                                result['subdirectory'] = subdirectory_part
                                return result

                        # If no exact match, try partial match
                        for category in available_categories:
                            if category.lower() in category_part.lower():
                                result['category'] = category
                                result['subdirectory'] = subdirectory_part
                                return result

        # Fallback: try to find just the category (legacy format)
        for category in available_categories:
            if category in response_text:
                result['category'] = category
                return result

        # Final fallback: analyze lines for category names
        lines = response_text.split('\n')
        for line in lines:
            line = line.strip()
            if line and not line.startswith('<') and not line.startswith('Okay') and not line.startswith('Ich'):
                for category in available_categories:
                    if category in line:
                        result['category'] = category
                        return result
                # If this line looks like a clean category answer, use it
                if len(line) < 50 and not line.endswith('?'):
                    result['category'] = line
                    return result

        # Last resort: return first available category
        if available_categories:
            result['category'] = available_categories[0]

        return result

    def classify_document(self, text: str, filename: str, available_categories: List[str],
                         category_info: str) -> Dict[str, str]:
        """
        Classify document using AI model

        Args:
            text: Document text content
            filename: Document filename
            available_categories: List of valid categories
            category_info: Formatted category information

        Returns:
            Dictionary with 'category' and 'subdirectory' keys
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

                # Parse response and extract category + subdirectory
                classification_result = self.parse_ai_response(raw_response, available_categories)

                if classification_result['category'] in available_categories:
                    return classification_result
                else:
                    # Return first available category as fallback
                    return {
                        'category': available_categories[0] if available_categories else 'Sonstiges',
                        'subdirectory': ''
                    }

            else:
                print(f"LM Studio API error: {response.status_code} - {response.text}")
                return {
                    'category': available_categories[0] if available_categories else 'Sonstiges',
                    'subdirectory': ''
                }

        except Exception as e:
            print(f"Error calling LM Studio: {e}")
            # Smart fallback based on filename and text analysis
            fallback_category = self._smart_fallback_classification(text, filename, available_categories)
            print(f"Using smart fallback classification: {fallback_category}")
            return {
                'category': fallback_category,
                'subdirectory': ''
            }

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

        # Enhanced keyword mapping with partial matches
        keyword_mappings = {
            'arbeit': ['arbeit', 'gehalt', 'lohn', 'arbeitsvertrag', 'job', 'deutsche bahn', 'evg', 'evoik'],
            'rechnung': ['rechnung', 'invoice', 'betrag', 'euro', 'umsatzsteuer', 'rechnungen', 'faktura'],
            'finanzen': ['bank', 'steuer', 'finanz', 'geld', 'kapital', 'investment'],
            'versicherung': ['versicherung', 'police', 'schadensfall'],
            'wohnen': ['miete', 'wohnung', 'hausverwaltung', 'mietvertrag'],
            'fahrzeug': ['auto', 'kfz', 'fahrzeug', 'tüv', 'motorrad'],
            'medizin': ['arzt', 'behandlung', 'patient', 'medizin', 'gesundheit'],
            'kita': ['kita', 'kindergarten', 'betreuung'],
            'schöffe': ['schöffe', 'schöffin', 'schöffendienst', 'laienrichter', 'gericht', 'landgericht', 'amtsgericht'],
            'gericht': ['gericht', 'richter', 'urteil', 'verhandlung', 'justiz', 'landgericht', 'amtsgericht'],
            'politik': ['politik', 'politiker', 'partei', 'wahl', 'bundestag', 'landtag'],
            'verein': ['verein', 'vereinigung', 'club', 'mitgliedschaft', 'beitrag'],
            'immobilien': ['immobilie', 'haus', 'wohnung', 'grundstück', 'makler'],
            'bildung': ['schule', 'universität', 'studium', 'kurs', 'ausbildung'],
            'sport': ['sport', 'fitness', 'verein', 'training', 'wettkampf']
        }

        # Enhanced matching: Check filename and text for keywords
        best_match = None
        best_score = 0

        for pattern, keywords in keyword_mappings.items():
            for keyword in keywords:
                if keyword in filename_lower or keyword in text_sample:
                    # Find matching category with partial string matching
                    for category in available_categories:
                        category_lower = category.lower()

                        # Exact match gets highest score
                        if pattern in category_lower:
                            score = 10
                            # Boost score for specific court/legal categories
                            if pattern in ['schöffe', 'gericht'] and ('schöff' in category_lower or 'gericht' in category_lower):
                                score = 15
                        # Keyword match gets medium score
                        elif any(k in category_lower for k in keywords):
                            score = 5
                            # Boost score for court/legal matches
                            if any(legal_term in keyword for keyword in keywords for legal_term in ['schöff', 'gericht', 'landgericht', 'amtsgericht']) and \
                               any(legal_cat in category_lower for legal_cat in ['schöff', 'gericht']):
                                score = 12
                            # Boost score for invoice/billing matches
                            elif any(invoice_term in keyword for keyword in keywords for invoice_term in ['rechnung', 'rechnungen', 'invoice']) and \
                                 any(invoice_cat in category_lower for invoice_cat in ['rechnung', 'rechnungen']):
                                score = 12
                        # Partial match (important for cases like "schöffe" -> "schöffendienst")
                        elif any(category_part in keyword or keyword in category_part
                                for category_part in category_lower.split()
                                for keyword in keywords if len(keyword) > 3):
                            score = 3
                            # Special boost for schöffe matches
                            if 'schöff' in keyword and 'schöff' in category_lower:
                                score = 11
                        else:
                            continue

                        if score > best_score:
                            best_score = score
                            best_match = category

        if best_match:
            return best_match

        # Enhanced partial matching for directory names
        for category in available_categories:
            category_words = category.lower().split()
            text_words = text_sample.split()
            filename_words = filename_lower.split()

            for cat_word in category_words:
                if len(cat_word) > 4:  # Only consider longer words
                    for text_word in text_words + filename_words:
                        if len(text_word) > 3:
                            # Check if words have significant overlap
                            if (cat_word in text_word or text_word in cat_word) and len(text_word) > 3:
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
        Classify document and return detailed analysis with template recognition

        Args:
            text: Document text content
            filename: Document filename
            available_categories: List of valid categories
            category_info: Formatted category information

        Returns:
            Dictionary with classification result and analysis
        """
        # Step 1: Template-based document type recognition
        template_result = document_template_engine.recognize_document_type(text, filename)

        # Extract context hints
        context_hints = self.prompt_manager.extract_document_context(text, filename)

        # Step 2: Enhanced classification with template information
        classification_result = self.classify_document_enhanced(
            text, filename, available_categories, category_info, template_result
        )

        # Build detailed analysis
        analysis = {
            'category': classification_result,
            'context_hints': context_hints,
            'text_length': len(text),
            'filename': filename,
            'confidence': 'high' if classification_result['category'] in available_categories else 'low',
            'fallback_used': classification_result['category'] not in available_categories
        }

        # Add template information if available
        if template_result:
            analysis['template_recognition'] = {
                'document_type': template_result.document_type,
                'template_id': template_result.template_id,
                'template_confidence': template_result.confidence,
                'matched_patterns': template_result.matched_patterns,
                'matched_keywords': template_result.matched_keywords,
                'structural_matches': template_result.structural_matches,
                'metadata': template_result.metadata
            }

            # Update confidence based on template recognition
            if template_result.confidence > 0.8:
                analysis['confidence'] = 'very_high'
            elif template_result.confidence > 0.6:
                analysis['confidence'] = 'high'
        else:
            analysis['template_recognition'] = None

        return analysis

    def classify_document_enhanced(self, text: str, filename: str, available_categories: List[str],
                                 category_info: str, template_result: Optional[DocumentTypeResult] = None) -> Dict[str, str]:
        """
        Enhanced classification that considers template recognition results

        Args:
            text: Document text content
            filename: Document filename
            available_categories: List of valid categories
            category_info: Formatted category information
            template_result: Template recognition result (optional)

        Returns:
            Dictionary with 'category' and 'subdirectory' keys
        """
        # If we have high-confidence template recognition, use it to guide classification
        if template_result and template_result.confidence > 0.8:
            # Try to map document type to available categories
            category_mapping = self._map_document_type_to_category(
                template_result.document_type, available_categories
            )

            if category_mapping:
                return {
                    'category': category_mapping['category'],
                    'subdirectory': category_mapping.get('subdirectory', template_result.document_type)
                }

        # Fallback to regular AI classification
        try:
            # Build enhanced prompt with template information
            prompt = self._build_enhanced_prompt(text, filename, category_info, template_result)

            # Prepare request
            request_config = self.prompt_manager.get_request_config()
            request_data = {
                **request_config,
                "messages": [
                    {"role": "system", "content": self._get_enhanced_system_message()},
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

                # Parse response and extract category + subdirectory
                classification_result = self.parse_ai_response(raw_response, available_categories)

                if classification_result['category'] in available_categories:
                    return classification_result
                else:
                    # Return first available category as fallback
                    return {
                        'category': available_categories[0] if available_categories else 'Sonstiges',
                        'subdirectory': ''
                    }

            else:
                print(f"LM Studio API error: {response.status_code} - {response.text}")
                return self._enhanced_fallback_classification(text, filename, available_categories, template_result)

        except Exception as e:
            print(f"Error calling LM Studio: {e}")
            return self._enhanced_fallback_classification(text, filename, available_categories, template_result)

    def _map_document_type_to_category(self, document_type: str, available_categories: List[str]) -> Optional[Dict[str, str]]:
        """Map document type to available category"""
        type_mappings = {
            'invoice': ['Steuern', 'Finanzen', 'Rechnungen'],
            'contract': ['Verträge', 'Legal'],
            'bank_statement': ['Banken', 'Finanzen'],
            'insurance': ['Versicherungen'],
            'employment_contract': ['Arbeit', 'Personal', 'HR'],
            'rental_contract': ['Wohnen', 'Immobilien', 'Miete']
        }

        if document_type not in type_mappings:
            return None

        # Find best matching category
        for preferred_category in type_mappings[document_type]:
            for available_category in available_categories:
                if preferred_category.lower() in available_category.lower():
                    return {
                        'category': available_category,
                        'subdirectory': document_type
                    }

        return None

    def _build_enhanced_prompt(self, text: str, filename: str, category_info: str,
                             template_result: Optional[DocumentTypeResult] = None) -> str:
        """Build enhanced prompt with template information"""
        base_prompt = self.prompt_manager.build_classification_prompt(text, filename, category_info)

        if template_result:
            template_info = f"""

TEMPLATE ANALYSIS:
- Detected Document Type: {template_result.document_type}
- Template Confidence: {template_result.confidence:.2f}
- Matched Keywords: {', '.join(template_result.matched_keywords[:5])}
- Structural Elements: {', '.join(template_result.structural_matches[:3])}

Please consider this template analysis when making your classification decision."""

            return base_prompt + template_info

        return base_prompt

    def _get_enhanced_system_message(self) -> str:
        """Get enhanced system message with template awareness"""
        return """You are an expert document classifier with access to template analysis results.

You classify documents into categories and subdirectories based on:
1. Document content and structure
2. Template recognition results (when available)
3. Keywords and patterns
4. Available category structure

When template analysis is provided, use it to inform your decision but don't be bound by it.
Always respond in the format: CATEGORY|SUBDIRECTORY

Focus on accuracy and use the template information to improve classification confidence."""

    def _enhanced_fallback_classification(self, text: str, filename: str, available_categories: List[str],
                                        template_result: Optional[DocumentTypeResult] = None) -> Dict[str, str]:
        """Enhanced fallback classification with template information"""

        # If we have template result, try to use it
        if template_result and template_result.confidence > 0.5:
            category_mapping = self._map_document_type_to_category(
                template_result.document_type, available_categories
            )
            if category_mapping:
                return category_mapping

        # Fallback to regular smart classification
        fallback_category = self._smart_fallback_classification(text, filename, available_categories)

        # Add subdirectory based on template if available
        subdirectory = ''
        if template_result and template_result.confidence > 0.5:
            subdirectory = template_result.document_type

        return {
            'category': fallback_category,
            'subdirectory': subdirectory
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