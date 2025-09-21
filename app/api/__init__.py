"""
API Blueprints Module
Organizes Flask routes into logical blueprints
"""

from .documents import documents_bp
from .directories import directories_bp
from .monitoring import monitoring_bp

__all__ = ['documents_bp', 'directories_bp', 'monitoring_bp']