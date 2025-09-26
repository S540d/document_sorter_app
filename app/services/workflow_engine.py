"""
Workflow Engine für intelligente Dokumentverarbeitung
Kombiniert Template-Erkennung, AI-Klassifizierung und Automatisierung
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum

from ..ai.document_templates import document_template_engine, DocumentTypeResult
from ..ai.classifier import DocumentClassifier
from ..directory import CategoryManager, DirectoryManager
from ..services.file_renaming import file_renaming_service
from ..monitoring import get_logger


class WorkflowAction(Enum):
    AUTO_CLASSIFY = "auto_classify"
    FORCE_CATEGORY = "force_category"
    MANUAL_REVIEW = "manual_review"
    SKIP = "skip"


@dataclass
class WorkflowRule:
    """Regel für automatisierte Dokumentverarbeitung"""
    id: str
    name: str
    conditions: Dict[str, Any]
    actions: List[Dict[str, Any]]
    priority: int = 1
    enabled: bool = True
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


@dataclass
class WorkflowResult:
    """Ergebnis einer Workflow-Verarbeitung"""
    success: bool
    action_taken: WorkflowAction
    target_category: Optional[str]
    target_path: Optional[str]
    confidence: float
    template_result: Optional[DocumentTypeResult]
    ai_result: Optional[Dict[str, Any]]
    applied_rules: List[str]
    metadata: Dict[str, Any]
    processing_time: float


class WorkflowEngine:
    """Engine für intelligente Dokumentverarbeitung mit Regeln"""

    def __init__(self):
        self.logger = get_logger('workflow_engine')
        self.rules: List[WorkflowRule] = []
        self.rules_file = Path("workflow_rules.json")

        # Initialize components
        self.document_classifier = DocumentClassifier()
        self.category_manager = CategoryManager()
        self.directory_manager = DirectoryManager()

        self._load_default_rules()
        self._load_custom_rules()

    def process_document(self, file_path: str, context: Dict[str, Any] = None) -> WorkflowResult:
        """
        Verarbeite Dokument mit vollständiger Workflow-Pipeline

        Args:
            file_path: Pfad zur Datei
            context: Zusätzlicher Kontext (z.B. Batch-Operation Info)

        Returns:
            WorkflowResult mit allen Verarbeitungsdetails
        """
        start_time = datetime.now()
        file_path_obj = Path(file_path)
        context = context or {}

        try:
            # Step 1: Template-basierte Dokumenttyp-Erkennung
            text = self._extract_text(file_path)
            template_result = document_template_engine.recognize_document_type(text, file_path_obj.name)

            # Step 2: Evaluiere Workflow-Regeln
            applicable_rules = self._evaluate_rules(file_path_obj, template_result, context)

            # Step 3: Führe Aktionen basierend auf Regeln aus
            workflow_result = self._execute_workflow(
                file_path_obj, text, template_result, applicable_rules, context
            )

            # Step 4: Berechne Verarbeitungszeit
            processing_time = (datetime.now() - start_time).total_seconds()
            workflow_result.processing_time = processing_time

            self.logger.info("Document workflow completed",
                           file_path=file_path,
                           action_taken=workflow_result.action_taken.value,
                           success=workflow_result.success,
                           processing_time=processing_time)

            return workflow_result

        except Exception as e:
            self.logger.error("Workflow processing failed",
                            file_path=file_path,
                            exception=e)

            processing_time = (datetime.now() - start_time).total_seconds()
            return WorkflowResult(
                success=False,
                action_taken=WorkflowAction.MANUAL_REVIEW,
                target_category=None,
                target_path=None,
                confidence=0.0,
                template_result=template_result if 'template_result' in locals() else None,
                ai_result=None,
                applied_rules=[],
                metadata={'error': str(e)},
                processing_time=processing_time
            )

    def _evaluate_rules(self, file_path: Path, template_result: Optional[DocumentTypeResult],
                       context: Dict[str, Any]) -> List[WorkflowRule]:
        """Evaluiere welche Regeln auf das Dokument anwendbar sind"""
        applicable_rules = []

        for rule in sorted(self.rules, key=lambda r: r.priority, reverse=True):
            if not rule.enabled:
                continue

            if self._rule_matches(rule, file_path, template_result, context):
                applicable_rules.append(rule)

        return applicable_rules

    def _rule_matches(self, rule: WorkflowRule, file_path: Path,
                     template_result: Optional[DocumentTypeResult],
                     context: Dict[str, Any]) -> bool:
        """Prüfe ob eine Regel auf das Dokument zutrifft"""
        conditions = rule.conditions

        # Template-basierte Bedingungen
        if 'document_type' in conditions:
            if not template_result or template_result.document_type not in conditions['document_type']:
                return False

        if 'min_template_confidence' in conditions:
            if not template_result or template_result.confidence < conditions['min_template_confidence']:
                return False

        # Dateiname-basierte Bedingungen
        if 'filename_patterns' in conditions:
            filename_lower = file_path.name.lower()
            if not any(pattern.lower() in filename_lower for pattern in conditions['filename_patterns']):
                return False

        # Dateierweiterungs-Bedingungen
        if 'file_extensions' in conditions:
            if file_path.suffix.lower() not in conditions['file_extensions']:
                return False

        # Kontext-basierte Bedingungen
        if 'batch_mode' in conditions:
            if context.get('is_batch', False) != conditions['batch_mode']:
                return False

        return True

    def _execute_workflow(self, file_path: Path, text: str,
                         template_result: Optional[DocumentTypeResult],
                         applicable_rules: List[WorkflowRule],
                         context: Dict[str, Any]) -> WorkflowResult:
        """Führe Workflow-Aktionen aus"""

        applied_rule_ids = [rule.id for rule in applicable_rules]

        # Bestimme Aktion basierend auf Regeln
        action = self._determine_action(applicable_rules, template_result)

        if action == WorkflowAction.AUTO_CLASSIFY:
            return self._auto_classify_document(file_path, text, template_result, applied_rule_ids)

        elif action == WorkflowAction.FORCE_CATEGORY:
            # Hole erzwungene Kategorie aus Regeln
            forced_category = self._get_forced_category(applicable_rules)
            return self._force_category_document(file_path, text, forced_category, applied_rule_ids)

        elif action == WorkflowAction.MANUAL_REVIEW:
            return self._manual_review_document(file_path, template_result, applied_rule_ids)

        else:  # SKIP
            return self._skip_document(file_path, template_result, applied_rule_ids)

    def _determine_action(self, applicable_rules: List[WorkflowRule],
                         template_result: Optional[DocumentTypeResult]) -> WorkflowAction:
        """Bestimme die auszuführende Aktion"""

        if not applicable_rules:
            # Keine Regeln -> Standard-Verhalten
            if template_result and template_result.confidence > 0.8:
                return WorkflowAction.AUTO_CLASSIFY
            else:
                return WorkflowAction.MANUAL_REVIEW

        # Verwende die Aktion der Regel mit höchster Priorität
        highest_priority_rule = max(applicable_rules, key=lambda r: r.priority)

        for action_def in highest_priority_rule.actions:
            if action_def.get('type') == 'classify':
                return WorkflowAction.AUTO_CLASSIFY
            elif action_def.get('type') == 'force_category':
                return WorkflowAction.FORCE_CATEGORY
            elif action_def.get('type') == 'manual_review':
                return WorkflowAction.MANUAL_REVIEW
            elif action_def.get('type') == 'skip':
                return WorkflowAction.SKIP

        return WorkflowAction.AUTO_CLASSIFY

    def _auto_classify_document(self, file_path: Path, text: str,
                              template_result: Optional[DocumentTypeResult],
                              applied_rules: List[str]) -> WorkflowResult:
        """Automatische Klassifizierung mit AI + Templates"""
        try:
            # Hole verfügbare Kategorien
            categories = self.category_manager.get_smart_categories()
            category_info = self.category_manager.build_category_context_for_ai()

            # Klassifiziere mit Template-Integration
            ai_result = self.document_classifier.classify_with_analysis(
                text, file_path.name, categories, category_info
            )

            target_category = ai_result['category']['category']
            suggested_subdirectory = ai_result['category'].get('subdirectory', '')

            # Generiere Filename-Suggestion
            filename_suggestion = file_renaming_service.suggest_filename(
                file_path.name, text, target_category
            )

            # Bestimme Zielpfad
            from ..settings import CONFIG
            if suggested_subdirectory:
                target_path = Path(CONFIG['SORTED_DIR']) / target_category / suggested_subdirectory / filename_suggestion['suggested_filename']
            else:
                target_path = Path(CONFIG['SORTED_DIR']) / target_category / filename_suggestion['suggested_filename']

            # Führe Move-Operation aus
            move_result = self.directory_manager.move_document(str(file_path), str(target_path))

            return WorkflowResult(
                success=move_result.get('success', False),
                action_taken=WorkflowAction.AUTO_CLASSIFY,
                target_category=target_category,
                target_path=str(target_path) if move_result.get('success') else None,
                confidence=self._calculate_combined_confidence(template_result, ai_result),
                template_result=template_result,
                ai_result=ai_result,
                applied_rules=applied_rules,
                metadata={
                    'filename_suggestion': filename_suggestion,
                    'move_result': move_result
                },
                processing_time=0.0  # Will be set by caller
            )

        except Exception as e:
            return WorkflowResult(
                success=False,
                action_taken=WorkflowAction.MANUAL_REVIEW,
                target_category=None,
                target_path=None,
                confidence=0.0,
                template_result=template_result,
                ai_result=None,
                applied_rules=applied_rules,
                metadata={'error': str(e)},
                processing_time=0.0
            )

    def _force_category_document(self, file_path: Path, text: str,
                               forced_category: str, applied_rules: List[str]) -> WorkflowResult:
        """Erzwinge spezifische Kategorie"""
        try:
            # Generiere Filename-Suggestion
            filename_suggestion = file_renaming_service.suggest_filename(
                file_path.name, text, forced_category
            )

            # Bestimme Zielpfad
            from ..settings import CONFIG
            target_path = Path(CONFIG['SORTED_DIR']) / forced_category / filename_suggestion['suggested_filename']

            # Führe Move-Operation aus
            move_result = self.directory_manager.move_document(str(file_path), str(target_path))

            return WorkflowResult(
                success=move_result.get('success', False),
                action_taken=WorkflowAction.FORCE_CATEGORY,
                target_category=forced_category,
                target_path=str(target_path) if move_result.get('success') else None,
                confidence=1.0,  # Forced = 100% confidence
                template_result=None,
                ai_result=None,
                applied_rules=applied_rules,
                metadata={
                    'filename_suggestion': filename_suggestion,
                    'move_result': move_result,
                    'forced_category': forced_category
                },
                processing_time=0.0
            )

        except Exception as e:
            return WorkflowResult(
                success=False,
                action_taken=WorkflowAction.MANUAL_REVIEW,
                target_category=None,
                target_path=None,
                confidence=0.0,
                template_result=None,
                ai_result=None,
                applied_rules=applied_rules,
                metadata={'error': str(e)},
                processing_time=0.0
            )

    def _manual_review_document(self, file_path: Path,
                              template_result: Optional[DocumentTypeResult],
                              applied_rules: List[str]) -> WorkflowResult:
        """Markiere für manuelle Überprüfung"""
        return WorkflowResult(
            success=True,  # Success = marked for manual review
            action_taken=WorkflowAction.MANUAL_REVIEW,
            target_category=None,
            target_path=None,
            confidence=0.0,
            template_result=template_result,
            ai_result=None,
            applied_rules=applied_rules,
            metadata={'reason': 'Marked for manual review by workflow rules'},
            processing_time=0.0
        )

    def _skip_document(self, file_path: Path,
                      template_result: Optional[DocumentTypeResult],
                      applied_rules: List[str]) -> WorkflowResult:
        """Überspringe Dokument"""
        return WorkflowResult(
            success=True,
            action_taken=WorkflowAction.SKIP,
            target_category=None,
            target_path=None,
            confidence=0.0,
            template_result=template_result,
            ai_result=None,
            applied_rules=applied_rules,
            metadata={'reason': 'Skipped by workflow rules'},
            processing_time=0.0
        )

    def _get_forced_category(self, applicable_rules: List[WorkflowRule]) -> str:
        """Hole erzwungene Kategorie aus Regeln"""
        for rule in sorted(applicable_rules, key=lambda r: r.priority, reverse=True):
            for action in rule.actions:
                if action.get('type') == 'force_category':
                    return action.get('category', 'Sonstiges')
        return 'Sonstiges'

    def _calculate_combined_confidence(self, template_result: Optional[DocumentTypeResult],
                                     ai_result: Optional[Dict[str, Any]]) -> float:
        """Berechne kombinierte Confidence aus Template + AI"""
        template_confidence = template_result.confidence if template_result else 0.0
        ai_confidence = 0.8 if ai_result and ai_result.get('confidence') == 'high' else 0.5

        # Gewichtete Kombination
        return (template_confidence * 0.6) + (ai_confidence * 0.4)

    def _extract_text(self, file_path: str) -> str:
        """Extrahiere Text aus PDF"""
        try:
            from ..pdf import PDFProcessor
            pdf_processor = PDFProcessor(max_pages=3)
            return pdf_processor.extract_text(file_path)
        except Exception as e:
            self.logger.error("Text extraction failed", file_path=file_path, exception=e)
            return ""

    def add_rule(self, rule: WorkflowRule) -> bool:
        """Füge neue Workflow-Regel hinzu"""
        try:
            if any(r.id == rule.id for r in self.rules):
                self.logger.warning("Rule with ID already exists", rule_id=rule.id)
                return False

            self.rules.append(rule)
            self._save_custom_rules()

            self.logger.info("Workflow rule added", rule_id=rule.id, name=rule.name)
            return True

        except Exception as e:
            self.logger.error("Failed to add workflow rule", rule_id=rule.id, exception=e)
            return False

    def remove_rule(self, rule_id: str) -> bool:
        """Entferne Workflow-Regel"""
        try:
            initial_count = len(self.rules)
            self.rules = [r for r in self.rules if r.id != rule_id]

            if len(self.rules) < initial_count:
                self._save_custom_rules()
                self.logger.info("Workflow rule removed", rule_id=rule_id)
                return True
            else:
                return False

        except Exception as e:
            self.logger.error("Failed to remove workflow rule", rule_id=rule_id, exception=e)
            return False

    def get_rules(self) -> List[WorkflowRule]:
        """Hole alle Workflow-Regeln"""
        return self.rules.copy()

    def _load_default_rules(self):
        """Lade Standard-Workflow-Regeln"""
        default_rules = [
            # High-confidence Template -> Auto-classify
            WorkflowRule(
                id="template_high_confidence",
                name="Auto-classify high-confidence templates",
                conditions={
                    'min_template_confidence': 0.8
                },
                actions=[
                    {'type': 'classify'}
                ],
                priority=10
            ),

            # Invoice Documents -> Force Finance Category
            WorkflowRule(
                id="invoice_to_finance",
                name="Route invoices to finance category",
                conditions={
                    'document_type': ['invoice']
                },
                actions=[
                    {'type': 'force_category', 'category': 'Finanzen'}
                ],
                priority=9
            ),

            # Contracts -> Force Legal Category
            WorkflowRule(
                id="contracts_to_legal",
                name="Route contracts to legal category",
                conditions={
                    'document_type': ['contract', 'employment_contract', 'rental_contract']
                },
                actions=[
                    {'type': 'force_category', 'category': 'Verträge'}
                ],
                priority=9
            ),

            # Bank Statements -> Force Banking
            WorkflowRule(
                id="bank_to_banking",
                name="Route bank statements to banking",
                conditions={
                    'document_type': ['bank_statement']
                },
                actions=[
                    {'type': 'force_category', 'category': 'Banken'}
                ],
                priority=9
            ),

            # Low confidence or no template -> Manual review
            WorkflowRule(
                id="low_confidence_manual",
                name="Manual review for uncertain documents",
                conditions={
                    'min_template_confidence': 0.0  # Catches all
                },
                actions=[
                    {'type': 'manual_review'}
                ],
                priority=1  # Lowest priority (fallback)
            )
        ]

        self.rules.extend(default_rules)
        self.logger.info("Default workflow rules loaded", count=len(default_rules))

    def _load_custom_rules(self):
        """Lade benutzerdefinierte Regeln"""
        if not self.rules_file.exists():
            return

        try:
            with open(self.rules_file, 'r', encoding='utf-8') as f:
                rules_data = json.load(f)

            custom_rules = [WorkflowRule(**data) for data in rules_data]
            self.rules.extend(custom_rules)

            self.logger.info("Custom workflow rules loaded", count=len(custom_rules))

        except Exception as e:
            self.logger.error("Failed to load custom workflow rules", exception=e)

    def _save_custom_rules(self):
        """Speichere benutzerdefinierte Regeln"""
        try:
            # Filtere nur custom rules (nicht default)
            default_ids = {
                "template_high_confidence", "invoice_to_finance", "contracts_to_legal",
                "bank_to_banking", "low_confidence_manual"
            }

            custom_rules = [r for r in self.rules if r.id not in default_ids]

            with open(self.rules_file, 'w', encoding='utf-8') as f:
                rules_data = [asdict(r) for r in custom_rules]
                json.dump(rules_data, f, indent=2, ensure_ascii=False)

            self.logger.info("Custom workflow rules saved", count=len(custom_rules))

        except Exception as e:
            self.logger.error("Failed to save custom workflow rules", exception=e)


# Global instance
workflow_engine = WorkflowEngine()