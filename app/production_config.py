"""
Production Configuration Management
Handles environment-specific configuration with validation and security
"""

import os
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from pathlib import Path


@dataclass
class ProductionConfig:
    """Production configuration with validation"""

    # Flask settings
    debug: bool = False
    testing: bool = False
    secret_key: str = field(default_factory=lambda: os.urandom(32).hex())

    # Server settings
    host: str = '0.0.0.0'
    port: int = 5000
    workers: int = 4
    timeout: int = 120

    # Application directories
    scan_dir: str = '/documents/0001_scanbot'
    sorted_dir: str = '/app/data/sorted'
    log_dir: str = '/app/logs'
    temp_dir: str = '/app/temp'

    # AI/LM Studio settings
    lm_studio_url: str = 'http://localhost:1234'
    ai_timeout: int = 30
    ai_max_retries: int = 3

    # Performance settings
    max_pages_extract: int = 3
    preview_dpi: float = 1.5
    batch_workers: int = 3

    # Security settings
    max_file_size_mb: int = 50
    allowed_extensions: set = field(default_factory=lambda: {'.pdf', '.png', '.jpg', '.jpeg'})

    # Monitoring settings
    log_level: str = 'INFO'
    log_retention_days: int = 30
    performance_tracking: bool = True
    error_reporting: bool = True

    # Rate limiting
    rate_limit_per_minute: int = 60
    rate_limit_burst: int = 10

    # Database/Storage
    state_persistence: bool = True
    backup_interval_hours: int = 24

    def __post_init__(self):
        """Validate configuration after initialization"""
        self.validate()

    def validate(self):
        """Validate configuration values"""
        errors = []

        # Validate directories
        for dir_name, dir_path in [
            ('scan_dir', self.scan_dir),
            ('sorted_dir', self.sorted_dir),
            ('log_dir', self.log_dir),
            ('temp_dir', self.temp_dir)
        ]:
            if not dir_path:
                errors.append(f"{dir_name} cannot be empty")

        # Validate numeric values
        if self.port < 1 or self.port > 65535:
            errors.append("Port must be between 1 and 65535")

        if self.workers < 1:
            errors.append("Workers must be at least 1")

        if self.max_file_size_mb < 1:
            errors.append("Max file size must be at least 1 MB")

        if self.log_retention_days < 1:
            errors.append("Log retention must be at least 1 day")

        # Validate URLs
        if not self.lm_studio_url.startswith(('http://', 'https://')):
            errors.append("LM Studio URL must start with http:// or https://")

        if errors:
            raise ValueError(f"Configuration validation failed: {'; '.join(errors)}")

    def create_directories(self):
        """Create necessary directories if they don't exist"""
        dirs_to_create = [
            self.scan_dir,
            self.sorted_dir,
            self.log_dir,
            self.temp_dir
        ]

        for dir_path in dirs_to_create:
            try:
                Path(dir_path).mkdir(parents=True, exist_ok=True)
                print(f"✅ Directory ensured: {dir_path}")
            except Exception as e:
                print(f"❌ Failed to create directory {dir_path}: {e}")
                raise

    @classmethod
    def from_environment(cls) -> 'ProductionConfig':
        """Create configuration from environment variables"""
        config = cls()

        # Override with environment variables if present
        env_mappings = {
            'FLASK_DEBUG': ('debug', lambda x: x.lower() == 'true'),
            'FLASK_HOST': ('host', str),
            'FLASK_PORT': ('port', int),
            'FLASK_SECRET_KEY': ('secret_key', str),

            'WORKERS': ('workers', int),
            'TIMEOUT': ('timeout', int),

            'SCAN_DIR': ('scan_dir', str),
            'SORTED_DIR': ('sorted_dir', str),
            'LOG_DIR': ('log_dir', str),
            'TEMP_DIR': ('temp_dir', str),

            'LM_STUDIO_URL': ('lm_studio_url', str),
            'AI_TIMEOUT': ('ai_timeout', int),
            'AI_MAX_RETRIES': ('ai_max_retries', int),

            'MAX_PAGES_EXTRACT': ('max_pages_extract', int),
            'PREVIEW_DPI': ('preview_dpi', float),
            'BATCH_WORKERS': ('batch_workers', int),

            'MAX_FILE_SIZE_MB': ('max_file_size_mb', int),
            'LOG_LEVEL': ('log_level', str),
            'LOG_RETENTION_DAYS': ('log_retention_days', int),

            'PERFORMANCE_TRACKING': ('performance_tracking', lambda x: x.lower() == 'true'),
            'ERROR_REPORTING': ('error_reporting', lambda x: x.lower() == 'true'),

            'RATE_LIMIT_PER_MINUTE': ('rate_limit_per_minute', int),
            'RATE_LIMIT_BURST': ('rate_limit_burst', int),

            'STATE_PERSISTENCE': ('state_persistence', lambda x: x.lower() == 'true'),
            'BACKUP_INTERVAL_HOURS': ('backup_interval_hours', int),
        }

        for env_var, (attr_name, converter) in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                try:
                    converted_value = converter(value)
                    setattr(config, attr_name, converted_value)
                except ValueError as e:
                    print(f"Warning: Invalid value for {env_var}: {value} ({e})")

        # Handle allowed extensions separately
        allowed_ext = os.getenv('ALLOWED_EXTENSIONS')
        if allowed_ext:
            config.allowed_extensions = set(ext.strip() for ext in allowed_ext.split(','))

        return config

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        result = {}
        for key, value in self.__dict__.items():
            if isinstance(value, set):
                result[key] = list(value)
            else:
                result[key] = value
        return result

    def get_flask_config(self) -> Dict[str, Any]:
        """Get Flask-specific configuration"""
        return {
            'DEBUG': self.debug,
            'TESTING': self.testing,
            'SECRET_KEY': self.secret_key,
            'MAX_CONTENT_LENGTH': self.max_file_size_mb * 1024 * 1024  # Convert to bytes
        }


class ConfigManager:
    """Central configuration manager"""

    def __init__(self):
        self._config: Optional[ProductionConfig] = None
        self._is_production = os.getenv('FLASK_ENV') == 'production'

    @property
    def config(self) -> ProductionConfig:
        """Get current configuration"""
        if self._config is None:
            self._config = ProductionConfig.from_environment()
        return self._config

    @property
    def is_production(self) -> bool:
        """Check if running in production mode"""
        return self._is_production

    def initialize_app(self, app):
        """Initialize Flask app with configuration"""
        flask_config = self.config.get_flask_config()
        app.config.update(flask_config)

        # Create necessary directories
        try:
            self.config.create_directories()
        except Exception as e:
            print(f"Warning: Failed to create directories: {e}")

        return app

    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration"""
        return {
            'level': self.config.log_level,
            'log_dir': self.config.log_dir,
            'retention_days': self.config.log_retention_days,
            'error_reporting': self.config.error_reporting
        }

    def get_performance_config(self) -> Dict[str, Any]:
        """Get performance monitoring configuration"""
        return {
            'enabled': self.config.performance_tracking,
            'workers': self.config.workers,
            'timeout': self.config.timeout
        }

    def print_config_summary(self):
        """Print configuration summary for startup"""
        config = self.config
        print("\n🔧 Configuration Summary:")
        print(f"   Mode: {'Production' if self.is_production else 'Development'}")
        print(f"   Host: {config.host}:{config.port}")
        print(f"   Workers: {config.workers}")
        print(f"   Debug: {config.debug}")
        print(f"   📁 Scan: {config.scan_dir}")
        print(f"   📂 Sorted: {config.sorted_dir}")
        print(f"   📝 Logs: {config.log_dir}")
        print(f"   🤖 LM Studio: {config.lm_studio_url}")
        print(f"   📊 Performance Tracking: {config.performance_tracking}")
        print(f"   🚨 Error Reporting: {config.error_reporting}")
        print()


# Global configuration manager instance
config_manager = ConfigManager()