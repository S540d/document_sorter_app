"""
Document Template Recognition System
Intelligente Erkennung von Dokumenttypen basierend auf Strukturmustern und Templates
"""

import re
import json
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from pathlib import Path
from datetime import datetime

from ..monitoring import get_logger


@dataclass
class DocumentTemplate:
    """Template für Dokumenttyp-Erkennung"""
    id: str
    name: str
    document_type: str
    patterns: List[str]
    keywords: List[str]
    structural_markers: List[str]
    language: str = "de"
    confidence_threshold: float = 0.7
    priority: int = 1
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


@dataclass
class DocumentTypeResult:
    """Ergebnis der Dokumenttyp-Erkennung"""
    document_type: str
    template_id: str
    confidence: float
    matched_patterns: List[str]
    matched_keywords: List[str]
    structural_matches: List[str]
    language: str
    metadata: Dict[str, Any]


class DocumentTemplateEngine:
    """Engine für Template-basierte Dokumenttyp-Erkennung"""

    def __init__(self):
        self.logger = get_logger('document_templates')
        self.templates: List[DocumentTemplate] = []
        self.templates_file = Path("document_templates.json")
        self._load_default_templates()
        self._load_custom_templates()

    def recognize_document_type(self, text: str, filename: str = "") -> Optional[DocumentTypeResult]:
        """
        Erkenne Dokumenttyp basierend auf Templates

        Args:
            text: Dokumentinhalt
            filename: Dateiname (optional)

        Returns:
            DocumentTypeResult oder None wenn kein Template passt
        """
        if not text:
            return None

        best_match = None
        best_confidence = 0.0

        # Sortiere Templates nach Priorität
        sorted_templates = sorted(self.templates, key=lambda t: t.priority, reverse=True)

        for template in sorted_templates:
            result = self._match_template(template, text, filename)

            if result and result.confidence >= template.confidence_threshold:
                if result.confidence > best_confidence:
                    best_confidence = result.confidence
                    best_match = result

        if best_match:
            self.logger.info("Document type recognized",
                           document_type=best_match.document_type,
                           template_id=best_match.template_id,
                           confidence=best_match.confidence)

        return best_match

    def _match_template(self, template: DocumentTemplate, text: str, filename: str) -> Optional[DocumentTypeResult]:
        """Prüfe Template gegen Dokumentinhalt"""
        text_lower = text.lower()
        filename_lower = filename.lower()

        matched_patterns = []
        matched_keywords = []
        structural_matches = []

        # Pattern-Matching
        pattern_score = 0.0
        for pattern in template.patterns:
            try:
                if re.search(pattern, text, re.IGNORECASE | re.MULTILINE):
                    matched_patterns.append(pattern)
                    pattern_score += 1.0
            except re.error:
                self.logger.warning("Invalid regex pattern", pattern=pattern, template_id=template.id)

        # Keyword-Matching
        keyword_score = 0.0
        for keyword in template.keywords:
            if keyword.lower() in text_lower or keyword.lower() in filename_lower:
                matched_keywords.append(keyword)
                keyword_score += 1.0

        # Structural Marker Matching
        structural_score = 0.0
        for marker in template.structural_markers:
            if marker.lower() in text_lower:
                structural_matches.append(marker)
                structural_score += 1.0

        # Berechne Gesamtconfidence
        total_patterns = len(template.patterns)
        total_keywords = len(template.keywords)
        total_structural = len(template.structural_markers)

        if total_patterns + total_keywords + total_structural == 0:
            return None

        # Gewichtete Confidence-Berechnung
        confidence = 0.0
        if total_patterns > 0:
            confidence += (pattern_score / total_patterns) * 0.4
        if total_keywords > 0:
            confidence += (keyword_score / total_keywords) * 0.4
        if total_structural > 0:
            confidence += (structural_score / total_structural) * 0.2

        if confidence < template.confidence_threshold:
            return None

        # Extrahiere Metadaten
        metadata = self._extract_metadata(template, text)

        return DocumentTypeResult(
            document_type=template.document_type,
            template_id=template.id,
            confidence=confidence,
            matched_patterns=matched_patterns,
            matched_keywords=matched_keywords,
            structural_matches=structural_matches,
            language=template.language,
            metadata=metadata
        )

    def _extract_metadata(self, template: DocumentTemplate, text: str) -> Dict[str, Any]:
        """Extrahiere spezifische Metadaten basierend auf Dokumenttyp"""
        metadata = {}

        # Datum-Extraktion
        date_patterns = [
            r'\b(\d{1,2})[./](\d{1,2})[./](\d{4})\b',
            r'\b(\d{4})-(\d{2})-(\d{2})\b',
            r'\b(\d{1,2})\.\s*([A-Za-z]{3,9})\s*(\d{4})\b'
        ]

        for pattern in date_patterns:
            matches = re.findall(pattern, text)
            if matches:
                metadata['dates'] = matches[:3]  # Maximal 3 Daten
                break

        # Beträge-Extraktion
        amount_patterns = [
            r'\b(\d{1,3}(?:[.,]\d{3})*[.,]\d{2})\s*€',
            r'€\s*(\d{1,3}(?:[.,]\d{3})*[.,]\d{2})',
            r'\b(\d{1,3}(?:[.,]\d{3})*[.,]\d{2})\s*EUR',
        ]

        amounts = []
        for pattern in amount_patterns:
            matches = re.findall(pattern, text)
            amounts.extend(matches)

        if amounts:
            metadata['amounts'] = amounts[:5]  # Maximal 5 Beträge

        # Dokumenttyp-spezifische Extraktion
        if template.document_type == "invoice":
            metadata.update(self._extract_invoice_metadata(text))
        elif template.document_type == "contract":
            metadata.update(self._extract_contract_metadata(text))
        elif template.document_type == "bank_statement":
            metadata.update(self._extract_bank_statement_metadata(text))

        return metadata

    def _extract_invoice_metadata(self, text: str) -> Dict[str, Any]:
        """Extrahiere Rechnungs-spezifische Metadaten"""
        metadata = {}

        # Rechnungsnummer
        invoice_patterns = [
            r'(?:rechnung|invoice)[^\w]*nr\.?\s*:?\s*([A-Z0-9\-/]+)',
            r'(?:rg|inv)[^\w]*nr\.?\s*:?\s*([A-Z0-9\-/]+)',
            r'nr\.?\s*([A-Z0-9\-/]{3,})'
        ]

        for pattern in invoice_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                metadata['invoice_number'] = match.group(1)
                break

        # Steuernummer/USt-ID
        tax_patterns = [
            r'ust[-\s]*id\.?\s*:?\s*([A-Z]{2}\d+)',
            r'steuer[-\s]*nr\.?\s*:?\s*([\d/\s]+)',
        ]

        for pattern in tax_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                metadata['tax_id'] = match.group(1)
                break

        return metadata

    def _extract_contract_metadata(self, text: str) -> Dict[str, Any]:
        """Extrahiere Vertrags-spezifische Metadaten"""
        metadata = {}

        # Vertragsnummer
        contract_patterns = [
            r'(?:vertrag|contract)[^\w]*nr\.?\s*:?\s*([A-Z0-9\-/]+)',
            r'(?:kunden|kunde)[^\w]*nr\.?\s*:?\s*([A-Z0-9\-/]+)',
        ]

        for pattern in contract_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                metadata['contract_number'] = match.group(1)
                break

        # Laufzeit
        duration_patterns = [
            r'(?:laufzeit|gültig)\s+(?:bis|until)\s+([0-9./\-]+)',
            r'(?:endet|ends)\s+(?:am|on)\s+([0-9./\-]+)',
        ]

        for pattern in duration_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                metadata['end_date'] = match.group(1)
                break

        return metadata

    def _extract_bank_statement_metadata(self, text: str) -> Dict[str, Any]:
        """Extrahiere Kontoauszug-spezifische Metadaten"""
        metadata = {}

        # Kontonummer/IBAN
        account_patterns = [
            r'IBAN\s*:?\s*([A-Z]{2}\d{2}\s?[\d\s]{15,})',
            r'(?:konto|account)[^\w]*nr\.?\s*:?\s*([\d\s]+)',
        ]

        for pattern in account_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                metadata['account_number'] = match.group(1).replace(' ', '')
                break

        return metadata

    def add_template(self, template: DocumentTemplate) -> bool:
        """Füge neues Template hinzu"""
        try:
            # Prüfe auf doppelte IDs
            if any(t.id == template.id for t in self.templates):
                self.logger.warning("Template with ID already exists", template_id=template.id)
                return False

            self.templates.append(template)
            self._save_custom_templates()

            self.logger.info("Template added successfully",
                           template_id=template.id,
                           document_type=template.document_type)
            return True

        except Exception as e:
            self.logger.error("Failed to add template", template_id=template.id, exception=e)
            return False

    def remove_template(self, template_id: str) -> bool:
        """Entferne Template"""
        try:
            initial_count = len(self.templates)
            self.templates = [t for t in self.templates if t.id != template_id]

            if len(self.templates) < initial_count:
                self._save_custom_templates()
                self.logger.info("Template removed successfully", template_id=template_id)
                return True
            else:
                self.logger.warning("Template not found", template_id=template_id)
                return False

        except Exception as e:
            self.logger.error("Failed to remove template", template_id=template_id, exception=e)
            return False

    def get_templates(self) -> List[DocumentTemplate]:
        """Hole alle Templates"""
        return self.templates.copy()

    def get_templates_by_type(self, document_type: str) -> List[DocumentTemplate]:
        """Hole Templates für spezifischen Dokumenttyp"""
        return [t for t in self.templates if t.document_type == document_type]

    def _load_default_templates(self):
        """Lade Standard-Templates"""
        default_templates = [
            # Rechnungen
            DocumentTemplate(
                id="invoice_de_standard",
                name="Deutsche Rechnung (Standard)",
                document_type="invoice",
                patterns=[
                    r"rechnung",
                    r"invoice",
                    r"rechnungs[-\s]*nr",
                    r"invoice[-\s]*number",
                    r"rg[-\s]*\d+",
                    r"betrag"
                ],
                keywords=[
                    "rechnung", "invoice", "betrag", "summe", "total", "netto", "brutto",
                    "umsatzsteuer", "mwst", "vat", "ust-id", "steuer-nr", "fälligkeitsdatum",
                    "rechnungsempfänger", "gesamtbetrag"
                ],
                structural_markers=[
                    "rechnungsdatum", "leistungsdatum", "fälligkeitsdatum",
                    "rechnungsempfänger", "rechnungssteller", "zahlungsziel",
                    "betrag netto", "gesamtbetrag"
                ],
                confidence_threshold=0.4,
                priority=10
            ),

            # Verträge
            DocumentTemplate(
                id="contract_de_standard",
                name="Deutscher Vertrag (Standard)",
                document_type="contract",
                patterns=[
                    r"\bvertrag\b",
                    r"\bcontract\b",
                    r"vertragspartner",
                    r"§\s*\d+"
                ],
                keywords=[
                    "vertrag", "contract", "vereinbarung", "agreement", "vertragspartner",
                    "laufzeit", "kündigung", "bedingungen", "pflichten", "rechte"
                ],
                structural_markers=[
                    "vertragsgegenstand", "vertragslaufzeit", "kündigungsfrist",
                    "§", "artikel", "ziffer", "absatz"
                ],
                confidence_threshold=0.7,
                priority=9
            ),

            # Kontoauszüge
            DocumentTemplate(
                id="bank_statement_de",
                name="Deutscher Kontoauszug",
                document_type="bank_statement",
                patterns=[
                    r"kontoauszug",
                    r"bank\s*statement",
                    r"IBAN\s*:\s*[A-Z]{2}\d{2}",
                    r"umsatzübersicht"
                ],
                keywords=[
                    "kontoauszug", "bank", "konto", "saldo", "buchung", "überweisung",
                    "lastschrift", "gutschrift", "iban", "bic"
                ],
                structural_markers=[
                    "buchungstag", "wertstellung", "verwendungszweck",
                    "empfänger", "betrag", "saldo"
                ],
                confidence_threshold=0.8,
                priority=8
            ),

            # Versicherungsdokumente
            DocumentTemplate(
                id="insurance_de",
                name="Versicherungsdokument",
                document_type="insurance",
                patterns=[
                    r"versicherung",
                    r"insurance",
                    r"police",
                    r"versicherungsschein"
                ],
                keywords=[
                    "versicherung", "police", "prämie", "beitrag", "schaden",
                    "schadensfall", "versicherungsnehmer", "leistung"
                ],
                structural_markers=[
                    "versicherungsnummer", "versicherungsnehmer", "versicherungsschutz",
                    "prämie", "selbstbeteiligung", "deckungssumme"
                ],
                confidence_threshold=0.7,
                priority=7
            ),

            # Arbeitsverträge
            DocumentTemplate(
                id="employment_contract_de",
                name="Arbeitsvertrag",
                document_type="employment_contract",
                patterns=[
                    r"arbeitsvertrag",
                    r"employment\s*contract",
                    r"arbeitsplatz",
                    r"gehalt"
                ],
                keywords=[
                    "arbeitsvertrag", "arbeitnehmer", "arbeitgeber", "gehalt", "lohn",
                    "arbeitszeit", "urlaub", "kündigung", "probezeit"
                ],
                structural_markers=[
                    "arbeitsort", "arbeitszeit", "vergütung", "probezeit",
                    "kündigungsfrist", "urlaubsanspruch"
                ],
                confidence_threshold=0.8,
                priority=8
            ),

            # Mietverträge
            DocumentTemplate(
                id="rental_contract_de",
                name="Mietvertrag",
                document_type="rental_contract",
                patterns=[
                    r"mietvertrag",
                    r"rental\s*contract",
                    r"miete",
                    r"vermieter"
                ],
                keywords=[
                    "mietvertrag", "mieter", "vermieter", "miete", "kaution",
                    "nebenkosten", "wohnung", "mietobjekt"
                ],
                structural_markers=[
                    "mietobjekt", "mietbeginn", "mietpreis", "kaution",
                    "nebenkosten", "kündigungsfrist"
                ],
                confidence_threshold=0.8,
                priority=8
            )
        ]

        self.templates.extend(default_templates)
        self.logger.info("Default templates loaded", count=len(default_templates))

    def _load_custom_templates(self):
        """Lade benutzerdefinierte Templates aus Datei"""
        if not self.templates_file.exists():
            return

        try:
            with open(self.templates_file, 'r', encoding='utf-8') as f:
                templates_data = json.load(f)

            custom_templates = [DocumentTemplate(**data) for data in templates_data]
            self.templates.extend(custom_templates)

            self.logger.info("Custom templates loaded", count=len(custom_templates))

        except Exception as e:
            self.logger.error("Failed to load custom templates", exception=e)

    def _save_custom_templates(self):
        """Speichere benutzerdefinierte Templates"""
        try:
            # Filtere nur custom templates (die nicht in default_templates enthalten sind)
            default_ids = {
                "invoice_de_standard", "contract_de_standard", "bank_statement_de",
                "insurance_de", "employment_contract_de", "rental_contract_de"
            }

            custom_templates = [t for t in self.templates if t.id not in default_ids]

            with open(self.templates_file, 'w', encoding='utf-8') as f:
                templates_data = [asdict(t) for t in custom_templates]
                json.dump(templates_data, f, indent=2, ensure_ascii=False)

            self.logger.info("Custom templates saved", count=len(custom_templates))

        except Exception as e:
            self.logger.error("Failed to save custom templates", exception=e)


# Global instance
document_template_engine = DocumentTemplateEngine()