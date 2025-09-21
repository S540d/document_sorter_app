"""
AI Prompt Management Module
Handles prompt templates and context building for document classification
"""

from typing import List, Dict, Any


class PromptManager:
    """Manages AI prompts and context building for document classification"""

    def __init__(self):
        """Initialize prompt manager with templates"""
        self.classification_template = self._get_classification_template()
        self.context_hints = self._get_context_hints()

    def _get_classification_template(self) -> str:
        """Get the main classification prompt template"""
        return """Du bist ein Experte für deutsche Dokumentenklassifizierung.
Analysiere das Dokument und wähle die beste Kategorie basierend auf Inhalt, Dateiname und verfügbaren Verzeichnissen.

DOKUMENT-KONTEXT:
- Dateiname: {filename}
- Textlänge: {text_length} Zeichen
- Erkannte Hinweise: {context_hints}

VERFÜGBARE KATEGORIEN MIT STRUKTUR:
{category_info}

KLASSIFIZIERUNGS-REGELN:
1. Wähle die spezifischste passende Kategorie aus der obigen Liste
2. Bei Kita/Kindergarten-Dokumenten → entsprechende Wohn- oder Schriftverkehr-Kategorie
3. Bei Arbeitsdokumenten → Arbeitskategorie
4. Bei Finanzen/Steuern/Versicherungen → Finanzkategorie
5. Bei Fahrzeugen → Fahrzeugkategorie
6. Bei Wissenschaft/Studium → Bildungskategorie
7. Bei Wohnen/Miete → Wohnkategorie

DOKUMENTENTEXT (erste 2000 Zeichen):
{text_sample}

WICHTIG: Antworte nur mit dem exakten Kategorienamen aus der Verzeichnisliste oben. Kein Text davor oder danach, nur der Kategoriename."""

    def _get_context_hints(self) -> Dict[str, List[str]]:
        """Get context hint patterns for document analysis"""
        return {
            'filename_patterns': {
                'rechnung': ['rechnung', 'invoice', 'bill'],
                'vertrag': ['vertrag', 'contract'],
                'kita': ['kita', 'kindergarten'],
                'arbeit': ['arbeit', 'job', 'gehalt'],
                'steuern': ['steuer', 'tax']
            },
            'content_patterns': {
                'finanzen': ['rechnung', 'betrag', 'euro', 'umsatzsteuer'],
                'arbeit': ['arbeitsvertrag', 'gehalt', 'lohn', 'arbeitgeber'],
                'wohnen': ['mietvertrag', 'miete', 'wohnung', 'hausverwaltung'],
                'fahrzeug': ['fahrzeug', 'auto', 'kfz', 'tüv', 'versicherung'],
                'kita': ['kindergarten', 'kita', 'betreuung']
            }
        }

    def extract_document_context(self, text: str, filename: str = None) -> str:
        """
        Extract context hints from document text and filename

        Args:
            text: Document text content
            filename: Document filename

        Returns:
            Comma-separated context hints
        """
        hints = []

        # Analyze filename
        if filename:
            filename_lower = filename.lower()
            for hint_type, patterns in self.context_hints['filename_patterns'].items():
                if any(pattern in filename_lower for pattern in patterns):
                    hints.append(hint_type.title())

        # Analyze text content (first 500 chars for performance)
        if text:
            text_sample = text[:500].lower()
            for hint_type, patterns in self.context_hints['content_patterns'].items():
                if any(pattern in text_sample for pattern in patterns):
                    hints.append(f"{hint_type.title()}dokument")

        return ", ".join(hints) if hints else "Keine spezifischen Hinweise"

    def build_classification_prompt(self, text: str, filename: str, category_info: str) -> str:
        """
        Build complete classification prompt

        Args:
            text: Document text content
            filename: Document filename
            category_info: Available categories information

        Returns:
            Complete prompt for AI classification
        """
        context_hints = self.extract_document_context(text, filename)

        return self.classification_template.format(
            filename=filename or 'Unbekannt',
            text_length=len(text),
            context_hints=context_hints,
            category_info=category_info,
            text_sample=text[:2000]
        )

    def get_system_message(self) -> str:
        """Get system message for AI classification"""
        return "Du bist ein Experte für deutsche Dokumentenklassifizierung. Antworte nur mit dem exakten Kategorienamen."

    def get_request_config(self) -> Dict[str, Any]:
        """Get standard request configuration for LM Studio"""
        return {
            "model": "deepseek-r1-distill-qwen-7b",
            "temperature": 0.1,
            "max_tokens": 100,
            "stop": ["\n", ".", "!", "?"]
        }


# Default instance for backward compatibility
default_prompt_manager = PromptManager()

def extract_document_context(text: str, filename: str = None) -> str:
    """
    Legacy function for backward compatibility
    Extract context hints from document text and filename
    """
    return default_prompt_manager.extract_document_context(text, filename)