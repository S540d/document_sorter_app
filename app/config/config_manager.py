"""
Zentrale Konfigurationsverwaltung für die Document Sorter App
"""
import os
from pathlib import Path
from typing import Dict, List, Any

class ConfigManager:
    """Singleton-Klasse für die zentrale Konfigurationsverwaltung"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            cls._instance._init_config()
        return cls._instance
    
    def _init_config(self):
        """Initialisiert die Standardkonfiguration"""
        try:
            from config_secret import (
                LM_STUDIO_URL, 
                SCAN_DIR, 
                SORTED_DIR, 
                DEBUG_MODE, 
                PORT, 
                HOST
            )
        except ImportError:
            print("Warning: config_secret.py nicht gefunden. Verwende Standardwerte.")
            LM_STUDIO_URL = 'http://localhost:1234/v1/chat/completions'
            SCAN_DIR = './scans'
            SORTED_DIR = './sorted'
            DEBUG_MODE = True
            PORT = 5000
            HOST = '127.0.0.1'
        
        self.config: Dict[str, Any] = {
            'LM_STUDIO_URL': LM_STUDIO_URL,
            'SCAN_DIR': SCAN_DIR,
            'SORTED_DIR': SORTED_DIR,
            'DEBUG_MODE': DEBUG_MODE,
            'PORT': PORT,
            'HOST': HOST,
            'BLACKLIST_DIRS': [
                '.SynologyWorkingDirectory',
                '#SynoRecycle',
                'diss',
                'geschenke für andere',
                '21_gifs',
                '.DS_Store',
                '__pycache__',
                '.git',
                'node_modules'
            ]
        }
    
    def get(self, key: str) -> Any:
        """Gibt den Wert für einen Konfigurationsschlüssel zurück"""
        return self.config.get(key)
    
    def set(self, key: str, value: Any) -> None:
        """Setzt den Wert für einen Konfigurationsschlüssel"""
        self.config[key] = value
    
    def get_path(self, key: str) -> Path:
        """Gibt einen Konfigurationswert als Path-Objekt zurück"""
        path_str = self.get(key)
        return Path(path_str) if path_str else None
    
    def ensure_directories(self) -> None:
        """Stellt sicher, dass alle benötigten Verzeichnisse existieren"""
        required_dirs = ['SCAN_DIR', 'SORTED_DIR']
        for dir_key in required_dirs:
            dir_path = self.get_path(dir_key)
            if dir_path:
                dir_path.mkdir(parents=True, exist_ok=True)
    
    def is_blacklisted(self, dirname: str) -> bool:
        """Prüft ob ein Verzeichnisname auf der Blacklist steht"""
        return dirname in self.config['BLACKLIST_DIRS']