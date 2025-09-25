"""
Filter-Service für intelligente Dateierkennung und -zuordnung
"""
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from difflib import SequenceMatcher
from ..config.config_manager import ConfigManager


@dataclass
class FilterRule:
    """Datenstruktur für eine Filterregel"""
    id: str
    pattern: str
    target_path: str
    file_extensions: List[str]
    confidence_threshold: float
    created_at: str
    usage_count: int = 0
    success_rate: float = 1.0


@dataclass
class FilterSuggestion:
    """Vorschlag für Dateizuordnung"""
    target_path: str
    confidence: float
    reason: str
    rule_id: Optional[str] = None


class FilterService:
    """Service für intelligente Dateifilterung und Pattern-Learning"""

    def __init__(self):
        self.config = ConfigManager()
        self.rules_file = Path("learned_filters.json")
        self.rules: List[FilterRule] = []
        self.supported_extensions = {
            '.xlsx', '.xls', '.csv',  # Excel/Spreadsheets
            '.docx', '.doc', '.txt', '.pdf',  # Documents
            '.jpg', '.jpeg', '.png', '.gif', '.bmp',  # Images
            '.zip', '.rar', '.7z',  # Archives
            '.mp4', '.avi', '.mov',  # Videos
            '.mp3', '.wav', '.flac'  # Audio
        }
        self._load_rules()

    def suggest_filters(self, filename: str, file_path: str) -> List[FilterSuggestion]:
        """Generiert intelligente Vorschläge für eine Datei"""
        suggestions = []
        file_ext = Path(filename).suffix.lower()

        # 1. Prüfe gegen gelernte Regeln
        for rule in self.rules:
            if file_ext in rule.file_extensions:
                confidence = self._calculate_pattern_match(filename, rule.pattern)
                if confidence >= rule.confidence_threshold:
                    suggestions.append(FilterSuggestion(
                        target_path=rule.target_path,
                        confidence=confidence,
                        reason=f"Matches learned pattern: {rule.pattern}",
                        rule_id=rule.id
                    ))

        # 2. Ähnlichkeitsanalyse mit existierenden Dateien
        similar_suggestions = self._find_similar_files(filename, file_ext)
        suggestions.extend(similar_suggestions)

        # 3. Keyword-basierte Vorschläge
        keyword_suggestions = self._suggest_by_keywords(filename, file_ext)
        suggestions.extend(keyword_suggestions)

        # Nach Confidence sortieren und Top 3 zurückgeben
        suggestions.sort(key=lambda x: x.confidence, reverse=True)
        return suggestions[:3]

    def learn_pattern(self, filename: str, target_path: str, user_confirmed: bool = True) -> Optional[FilterRule]:
        """Lernt ein neues Pattern aus Benutzereingabe"""
        file_ext = Path(filename).suffix.lower()

        if not user_confirmed:
            return None

        # Generiere Pattern aus Filename
        pattern = self._generate_pattern_from_filename(filename)

        # Erstelle neue Regel
        rule = FilterRule(
            id=f"rule_{len(self.rules) + 1}_{int(datetime.now().timestamp())}",
            pattern=pattern,
            target_path=target_path,
            file_extensions=[file_ext],
            confidence_threshold=0.7,
            created_at=datetime.now().isoformat(),
            usage_count=1
        )

        # Prüfe auf ähnliche existierende Regeln
        existing_rule = self._find_similar_rule(rule)
        if existing_rule:
            # Erweitere existierende Regel
            existing_rule.file_extensions = list(set(existing_rule.file_extensions + [file_ext]))
            existing_rule.usage_count += 1
            self._save_rules()
            return existing_rule

        # Füge neue Regel hinzu
        self.rules.append(rule)
        self._save_rules()
        return rule

    def apply_filters(self, filename: str, file_path: str) -> Optional[str]:
        """Wendet gelernte Filter automatisch an"""
        suggestions = self.suggest_filters(filename, file_path)

        if suggestions and suggestions[0].confidence >= 0.9:
            # Hohe Confidence -> automatisch anwenden
            best_suggestion = suggestions[0]
            if best_suggestion.rule_id:
                # Aktualisiere Nutzungsstatistiken
                rule = next((r for r in self.rules if r.id == best_suggestion.rule_id), None)
                if rule:
                    rule.usage_count += 1
                    self._save_rules()

            return best_suggestion.target_path

        return None

    def get_confidence_score(self, filename: str, pattern: str) -> float:
        """Berechnet Confidence-Score für Pattern-Match"""
        return self._calculate_pattern_match(filename, pattern)

    def _calculate_pattern_match(self, filename: str, pattern: str) -> float:
        """Berechnet Pattern-Match mit Wildcard-Unterstützung"""
        # Konvertiere Pattern zu Regex
        regex_pattern = pattern.replace('*', '.*').replace('?', '.')
        regex_pattern = f"^{regex_pattern}$"

        try:
            if re.match(regex_pattern, filename, re.IGNORECASE):
                # Exakter Match
                return 0.95

            # Ähnlichkeitsberechnung
            similarity = SequenceMatcher(None, filename.lower(), pattern.lower()).ratio()
            return similarity * 0.8  # Dämpfung für nicht-exakte Matches

        except re.error:
            # Fallback bei Regex-Fehlern
            similarity = SequenceMatcher(None, filename.lower(), pattern.lower()).ratio()
            return similarity * 0.6

    def _find_similar_files(self, filename: str, file_ext: str) -> List[FilterSuggestion]:
        """Findet ähnliche Dateien in der Zielstruktur"""
        suggestions = []
        sorted_dir = self.config.get_path('SORTED_DIR')

        if not sorted_dir.exists():
            return suggestions

        # Suche nach ähnlichen Dateien in der Zielstruktur
        for file_path in sorted_dir.rglob(f"*{file_ext}"):
            similarity = SequenceMatcher(None, filename.lower(), file_path.name.lower()).ratio()

            if similarity > 0.6:  # Ähnlichkeitsschwelle
                target_dir = str(file_path.parent)
                suggestions.append(FilterSuggestion(
                    target_path=target_dir,
                    confidence=similarity * 0.7,
                    reason=f"Similar to existing file: {file_path.name}"
                ))

        return suggestions

    def _suggest_by_keywords(self, filename: str, file_ext: str) -> List[FilterSuggestion]:
        """Keyword-basierte Vorschläge"""
        suggestions = []
        filename_lower = filename.lower()

        keyword_mappings = {
            'rechnung': ('Steuern/Rechnungen', 0.8),
            'kontoauszug': ('Banken', 0.8),
            'vertrag': ('Verträge', 0.8),
            'versicherung': ('Versicherungen', 0.8),
            'steuer': ('Steuern', 0.8),
            'invoice': ('Steuern/Rechnungen', 0.7),
            'contract': ('Verträge', 0.7),
            'bank': ('Banken', 0.7)
        }

        for keyword, (category, confidence) in keyword_mappings.items():
            if keyword in filename_lower:
                sorted_dir = self.config.get_path('SORTED_DIR')
                target_path = str(sorted_dir / category)
                suggestions.append(FilterSuggestion(
                    target_path=target_path,
                    confidence=confidence,
                    reason=f"Keyword match: '{keyword}'"
                ))

        return suggestions

    def _generate_pattern_from_filename(self, filename: str) -> str:
        """Generiert ein wiederverwendbares Pattern aus einem Dateinamen"""
        # Entferne Dateiendung
        name_without_ext = Path(filename).stem

        # Ersetze Datumsangaben mit Wildcards
        pattern = re.sub(r'\d{4}[-_]\d{2}[-_]\d{2}', '*', name_without_ext)
        pattern = re.sub(r'\d{2}[-_.]\d{2}[-_.]\d{4}', '*', pattern)
        pattern = re.sub(r'\d{2}[-_.]\d{2}[-_.]\d{2}', '*', pattern)

        # Ersetze Nummern mit Wildcards
        pattern = re.sub(r'\d{3,}', '*', pattern)

        # Füge Dateiendung wieder hinzu
        pattern += Path(filename).suffix

        return pattern

    def _find_similar_rule(self, new_rule: FilterRule) -> Optional[FilterRule]:
        """Findet ähnliche existierende Regel"""
        for rule in self.rules:
            if (rule.target_path == new_rule.target_path and
                self._calculate_pattern_match(new_rule.pattern, rule.pattern) > 0.8):
                return rule
        return None

    def _load_rules(self):
        """Lädt gelernte Regeln aus JSON-Datei"""
        if self.rules_file.exists():
            try:
                with open(self.rules_file, 'r', encoding='utf-8') as f:
                    rules_data = json.load(f)
                    self.rules = [FilterRule(**rule) for rule in rules_data]
            except Exception as e:
                print(f"Error loading filter rules: {e}")
                self.rules = []

    def _save_rules(self):
        """Speichert Regeln in JSON-Datei"""
        try:
            with open(self.rules_file, 'w', encoding='utf-8') as f:
                rules_data = [asdict(rule) for rule in self.rules]
                json.dump(rules_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving filter rules: {e}")

    def get_all_rules(self) -> List[FilterRule]:
        """Gibt alle Filterregeln zurück"""
        return self.rules.copy()

    def delete_rule(self, rule_id: str) -> bool:
        """Löscht eine Filterregel"""
        initial_count = len(self.rules)
        self.rules = [rule for rule in self.rules if rule.id != rule_id]
        if len(self.rules) < initial_count:
            self._save_rules()
            return True
        return False

    def is_supported_file(self, filename: str) -> bool:
        """Prüft, ob Dateierweiterung unterstützt wird"""
        return Path(filename).suffix.lower() in self.supported_extensions