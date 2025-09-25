"""
Datei-Service für Document Sorter
"""
import os
import shutil
import random
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from ..config.config_manager import ConfigManager

class FileService:
    """Service für Dateioperationen"""

    def __init__(self):
        self.config = ConfigManager()
        self.supported_extensions = {
            '.pdf',  # Existing PDF support
            '.xlsx', '.xls', '.csv',  # Excel/Spreadsheets
            '.docx', '.doc', '.txt',  # Documents
            '.jpg', '.jpeg', '.png', '.gif', '.bmp',  # Images
            '.zip', '.rar', '.7z',  # Archives
            '.mp4', '.avi', '.mov',  # Videos
            '.mp3', '.wav', '.flac'  # Audio
        }
    
    def scan_directory(self) -> List[Dict[str, Any]]:
        """Scannt das Eingangsverzeichnis nach PDFs"""
        scan_dir = self.config.get_path('SCAN_DIR')
        
        if not scan_dir.exists():
            return []
        
        pdf_files = []
        for pdf_file in scan_dir.glob('*.pdf'):
            pdf_files.append({
                'name': pdf_file.name,
                'path': str(pdf_file),
                'size': pdf_file.stat().st_size,
                'modified': datetime.fromtimestamp(pdf_file.stat().st_mtime).isoformat()
            })
        
        return pdf_files
    
    def get_random_document(self) -> Optional[Dict[str, Any]]:
        """Wählt ein zufälliges PDF aus dem Scan-Verzeichnis"""
        pdf_files = list(self.config.get_path('SCAN_DIR').glob('*.pdf'))
        
        if not pdf_files:
            return None
        
        random_file = random.choice(pdf_files)
        return {
            'name': random_file.name,
            'path': str(random_file),
            'size': random_file.stat().st_size,
            'modified': datetime.fromtimestamp(random_file.stat().st_mtime).isoformat()
        }
    
    def move_document(self, source_path: str, target_path: str) -> bool:
        """Verschiebt ein Dokument von source_path nach target_path"""
        try:
            source = Path(source_path)
            target = Path(target_path)
            
            if not source.exists():
                return False
            
            # Zielverzeichnis erstellen falls nicht vorhanden
            target.parent.mkdir(parents=True, exist_ok=True)
            
            # Datei verschieben
            shutil.move(str(source), str(target))
            return True
            
        except Exception as e:
            print(f"Error moving file: {e}")
            return False
    
    def get_directory_tree(self, base_path: Path, max_depth: int = 3, current_depth: int = 0) -> Dict[str, Any]:
        """Erstellt einen Verzeichnisbaum mit Blacklist-Filter"""
        if current_depth >= max_depth:
            return {}
            
        tree = {}
        
        if not base_path.exists():
            return tree
            
        for item in base_path.iterdir():
            if item.is_dir() and not self.config.is_blacklisted(item.name):
                subtree = self.get_directory_tree(item, max_depth, current_depth + 1)
                tree[item.name] = {
                    'path': str(item),
                    'children': subtree,
                    'has_children': bool(subtree)
                }
        
        return tree
    
    def get_smart_categories(self) -> List[str]:
        """Generiert intelligente Kategorien basierend auf Documents-Struktur"""
        sorted_dir = self.config.get_path('SORTED_DIR')
        categories = []
        
        if sorted_dir.exists():
            for item in sorted_dir.iterdir():
                if item.is_dir() and not self.config.is_blacklisted(item.name):
                    categories.append(item.name)
        
        # Fallback-Kategorien falls Documents leer ist
        if not categories:
            categories = [
                'Steuern', 
                'Versicherungen', 
                'Verträge', 
                'Banken', 
                'Medizin', 
                'Behörden', 
                'Sonstiges'
            ]
        
        return sorted(categories)

    def scan_downloads_directory(self) -> List[Dict[str, Any]]:
        """Scannt das Downloads-Verzeichnis nach unterstützten Dateien"""
        downloads_dir = Path.home() / "Downloads"

        if not downloads_dir.exists():
            return []

        files = []
        for file_path in downloads_dir.iterdir():
            if file_path.is_file() and self._is_supported_file(file_path):
                files.append({
                    'name': file_path.name,
                    'path': str(file_path),
                    'size': file_path.stat().st_size,
                    'modified': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
                    'type': self._get_file_type(file_path),
                    'extension': file_path.suffix.lower()
                })

        # Nach Änderungsdatum sortieren (neueste zuerst)
        files.sort(key=lambda x: x['modified'], reverse=True)
        return files

    def scan_all_files(self, directory_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """Scannt Verzeichnis nach allen unterstützten Dateien (PDFs + andere)"""
        if directory_path:
            scan_dir = Path(directory_path)
        else:
            scan_dir = self.config.get_path('SCAN_DIR')

        if not scan_dir.exists():
            return []

        all_files = []
        for file_path in scan_dir.iterdir():
            if file_path.is_file() and self._is_supported_file(file_path):
                all_files.append({
                    'name': file_path.name,
                    'path': str(file_path),
                    'size': file_path.stat().st_size,
                    'modified': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
                    'type': self._get_file_type(file_path),
                    'extension': file_path.suffix.lower()
                })

        return all_files

    def get_random_file(self, directory_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Wählt eine zufällige unterstützte Datei aus dem Verzeichnis"""
        if directory_path:
            scan_dir = Path(directory_path)
        else:
            scan_dir = self.config.get_path('SCAN_DIR')

        supported_files = [
            f for f in scan_dir.iterdir()
            if f.is_file() and self._is_supported_file(f)
        ]

        if not supported_files:
            return None

        random_file = random.choice(supported_files)
        return {
            'name': random_file.name,
            'path': str(random_file),
            'size': random_file.stat().st_size,
            'modified': datetime.fromtimestamp(random_file.stat().st_mtime).isoformat(),
            'type': self._get_file_type(random_file),
            'extension': random_file.suffix.lower()
        }

    def _is_supported_file(self, file_path: Path) -> bool:
        """Prüft, ob eine Datei unterstützt wird"""
        return file_path.suffix.lower() in self.supported_extensions

    def _get_file_type(self, file_path: Path) -> str:
        """Bestimmt den Dateityp basierend auf der Erweiterung"""
        ext = file_path.suffix.lower()

        if ext == '.pdf':
            return 'pdf'
        elif ext in {'.xlsx', '.xls', '.csv'}:
            return 'spreadsheet'
        elif ext in {'.docx', '.doc', '.txt'}:
            return 'document'
        elif ext in {'.jpg', '.jpeg', '.png', '.gif', '.bmp'}:
            return 'image'
        elif ext in {'.zip', '.rar', '.7z'}:
            return 'archive'
        elif ext in {'.mp4', '.avi', '.mov'}:
            return 'video'
        elif ext in {'.mp3', '.wav', '.flac'}:
            return 'audio'
        else:
            return 'unknown'

    def get_file_stats(self, directory_path: Optional[str] = None) -> Dict[str, Any]:
        """Erstellt Statistiken über Dateien im Verzeichnis"""
        files = self.scan_all_files(directory_path)

        stats = {
            'total_files': len(files),
            'total_size': sum(f['size'] for f in files),
            'file_types': {},
            'file_extensions': {},
            'oldest_file': None,
            'newest_file': None
        }

        if files:
            # Dateityp-Statistiken
            for file_info in files:
                file_type = file_info['type']
                ext = file_info['extension']

                stats['file_types'][file_type] = stats['file_types'].get(file_type, 0) + 1
                stats['file_extensions'][ext] = stats['file_extensions'].get(ext, 0) + 1

            # Älteste und neueste Datei
            sorted_files = sorted(files, key=lambda x: x['modified'])
            stats['oldest_file'] = sorted_files[0]
            stats['newest_file'] = sorted_files[-1]

        return stats