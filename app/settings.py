"""
Configuration Management for Document Sorter
Centralized configuration handling with environment-specific settings
"""

import os
from pathlib import Path
from typing import List, Dict, Any


class Config:
    """Base configuration class with default values"""

    # Default values (fallbacks)
    DEFAULT_LM_STUDIO_URL = 'http://localhost:1234/v1/chat/completions'
    DEFAULT_SCAN_DIR = '/documents/0001_scanbot'
    DEFAULT_SORTED_DIR = './sorted'
    DEFAULT_DEBUG_MODE = True
    DEFAULT_PORT = 5000
    DEFAULT_HOST = '127.0.0.1'

    # Global blacklist directories (system-wide)
    GLOBAL_BLACKLIST_DIRS = [
        '.SynologyWorkingDirectory',
        '#SynoRecycle',
        '.DS_Store',
        '__pycache__',
        '.git',
        'node_modules',
        '.localized',
        'Scanbot',
        'scanbot'
    ]

    def __init__(self):
        """Initialize configuration by loading from config_secret.py or using defaults"""
        self._load_configuration()
        self._setup_paths()
        self._validate_configuration()

    def _load_configuration(self):
        """Load configuration from config_secret.py or use defaults"""
        try:
            from config_secret import (
                LM_STUDIO_URL, SCAN_DIR, SORTED_DIR, DEBUG_MODE,
                PORT, HOST, PERSONAL_BLACKLIST_DIRS
            )
            self.lm_studio_url = LM_STUDIO_URL
            self.scan_dir = SCAN_DIR
            self.sorted_dir = SORTED_DIR
            self.debug_mode = DEBUG_MODE
            self.port = PORT
            self.host = HOST
            self.personal_blacklist_dirs = PERSONAL_BLACKLIST_DIRS
            self._config_source = "config_secret.py"

        except ImportError:
            print("Warning: config_secret.py nicht gefunden. Verwende Standardwerte.")
            self.lm_studio_url = self.DEFAULT_LM_STUDIO_URL
            self.scan_dir = self.DEFAULT_SCAN_DIR
            self.sorted_dir = self.DEFAULT_SORTED_DIR
            self.debug_mode = self.DEFAULT_DEBUG_MODE
            self.port = self.DEFAULT_PORT
            self.host = self.DEFAULT_HOST
            self.personal_blacklist_dirs = []
            self._config_source = "defaults"

    def _setup_paths(self):
        """Setup and normalize paths"""
        self.scan_path = Path(self.scan_dir)
        self.sorted_path = Path(self.sorted_dir)

    def _validate_configuration(self):
        """Validate configuration values"""
        # Validate port
        if not isinstance(self.port, int) or not (1 <= self.port <= 65535):
            raise ValueError(f"Invalid port: {self.port}")

        # Validate URLs
        if not self.lm_studio_url.startswith(('http://', 'https://')):
            raise ValueError(f"Invalid LM Studio URL: {self.lm_studio_url}")

    @property
    def blacklist_dirs(self) -> List[str]:
        """Get combined blacklist directories (global + personal)"""
        return self.GLOBAL_BLACKLIST_DIRS + self.personal_blacklist_dirs

    @property
    def config_dict(self) -> Dict[str, Any]:
        """Get configuration as dictionary (backward compatibility)"""
        return {
            'LM_STUDIO_URL': self.lm_studio_url,
            'SCAN_DIR': self.scan_dir,
            'SORTED_DIR': self.sorted_dir,
            'BLACKLIST_DIRS': self.blacklist_dirs,
            'DEBUG_MODE': self.debug_mode,
            'PORT': self.port,
            'HOST': self.host
        }

    def get_summary(self) -> Dict[str, Any]:
        """Get configuration summary for logging"""
        return {
            'config_source': self._config_source,
            'lm_studio_url': self.lm_studio_url,
            'scan_dir': self.scan_dir,
            'sorted_dir': self.sorted_dir,
            'debug_mode': self.debug_mode,
            'port': self.port,
            'host': self.host,
            'blacklist_count': len(self.blacklist_dirs),
            'personal_blacklist_count': len(self.personal_blacklist_dirs),
            'paths_exist': {
                'scan_dir': self.scan_path.exists(),
                'sorted_dir': self.sorted_path.exists()
            }
        }

    def ensure_directories(self):
        """Create directories if they don't exist"""
        try:
            self.scan_path.mkdir(parents=True, exist_ok=True)
            self.sorted_path.mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            print(f"Error creating directories: {e}")
            return False


# Global configuration instance
config = Config()

# Backward compatibility exports
CONFIG = config.config_dict
LM_STUDIO_URL = config.lm_studio_url
SCAN_DIR = config.scan_dir
SORTED_DIR = config.sorted_dir
DEBUG_MODE = config.debug_mode
PORT = config.port
HOST = config.host
BLACKLIST_DIRS = config.blacklist_dirs