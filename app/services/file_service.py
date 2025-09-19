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