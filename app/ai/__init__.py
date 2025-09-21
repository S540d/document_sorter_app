"""
AI Classification Module
Handles document classification and AI integration
"""

from .classifier import DocumentClassifier
from .prompts import PromptManager

__all__ = ['DocumentClassifier', 'PromptManager']