"""
Category Management Module
Handles document categories and directory structure analysis
"""

from pathlib import Path
from typing import List, Dict, Any, Optional
from ..settings import config


class CategoryManager:
    """Manages document categories and directory structure"""

    def __init__(self, sorted_dir: str = None, blacklist_dirs: List[str] = None):
        """
        Initialize category manager

        Args:
            sorted_dir: Base directory for sorted documents (uses config if not provided)
            blacklist_dirs: List of directories to ignore (uses config if not provided)
        """
        self.sorted_dir = Path(sorted_dir or config.sorted_dir)
        self.blacklist_dirs = blacklist_dirs or config.blacklist_dirs
        self.fallback_categories = [
            'Steuern', 'Versicherungen', 'Verträge', 'Banken',
            'Medizin', 'Behörden', 'Sonstiges'
        ]

    def get_smart_categories(self) -> List[str]:
        """
        Generate intelligent categories based on existing directory structure

        Returns:
            Sorted list of available categories
        """
        categories = []

        if self.sorted_dir.exists():
            for item in self.sorted_dir.iterdir():
                if item.is_dir() and item.name not in self.blacklist_dirs:
                    categories.append(item.name)

        # Use fallback categories if directory is empty
        if not categories:
            categories = self.fallback_categories.copy()

        return sorted(categories)

    def get_directory_tree(self, base_path: Optional[Path] = None,
                          max_depth: int = 3, current_depth: int = 0) -> Dict[str, Any]:
        """
        Create directory tree with blacklist filtering

        Args:
            base_path: Base path to scan (uses sorted_dir if not provided)
            max_depth: Maximum depth to scan
            current_depth: Current recursion depth

        Returns:
            Dictionary representing directory tree
        """
        if current_depth >= max_depth:
            return {}

        if base_path is None:
            base_path = self.sorted_dir

        tree = {}

        if not base_path.exists():
            return tree

        try:
            for item in base_path.iterdir():
                if item.is_dir() and item.name not in self.blacklist_dirs:
                    subtree = self.get_directory_tree(
                        item, max_depth, current_depth + 1
                    )
                    tree[item.name] = {
                        'path': str(item),
                        'children': subtree,
                        'has_children': bool(subtree)
                    }
        except PermissionError:
            # Handle permission errors gracefully
            pass

        return tree

    def get_live_directory_structure(self) -> Dict[str, Any]:
        """
        Get real-time directory structure

        Returns:
            Dictionary representing current directory structure
        """
        try:
            if not self.sorted_dir.exists():
                return {}
            return self.get_directory_tree()
        except Exception:
            return {}

    def build_category_context_for_ai(self) -> str:
        """
        Build structured category information for AI classification

        Returns:
            Formatted string with category structure for AI
        """
        # Get real directory structure at runtime
        directory_structure = self.get_live_directory_structure()

        if not directory_structure:
            # Fallback: Use available categories
            categories = self.get_smart_categories()
            return "Verfügbare Kategorien: " + ", ".join(categories)

        category_lines = []
        for category, info in directory_structure.items():
            if not info.get('has_children', False):
                category_lines.append(f"📁 {category}")
            else:
                category_lines.append(f"📁 {category}")
                # Show first 5 subdirectories
                children = list(info.get('children', {}).keys())[:5]
                for child in children:
                    category_lines.append(f"   └── {child}")
                if len(info.get('children', {})) > 5:
                    remaining = len(info.get('children', {})) - 5
                    category_lines.append(f"   └── ... ({remaining} weitere)")

        return "\n".join(category_lines)

    def get_subdirectories(self, category: str) -> List[str]:
        """
        Get subdirectories for a specific category

        Args:
            category: Category name

        Returns:
            List of subdirectory names
        """
        subdirs = []
        category_path = self.sorted_dir / category

        if category_path.exists() and category_path.is_dir():
            try:
                for item in category_path.iterdir():
                    if item.is_dir() and item.name not in self.blacklist_dirs:
                        subdirs.append(item.name)
            except PermissionError:
                pass

        return sorted(subdirs)

    def validate_category(self, category: str) -> bool:
        """
        Check if category is valid and exists

        Args:
            category: Category name to validate

        Returns:
            True if category is valid
        """
        if not category:
            return False

        # Check if it's in blacklist
        if category in self.blacklist_dirs:
            return False

        # Check if category directory exists
        category_path = self.sorted_dir / category
        return category_path.exists() and category_path.is_dir()

    def get_category_stats(self) -> Dict[str, Any]:
        """
        Get statistics about categories

        Returns:
            Dictionary with category statistics
        """
        categories = self.get_smart_categories()
        tree = self.get_directory_tree()

        stats = {
            'total_categories': len(categories),
            'categories_with_subdirs': sum(1 for cat in tree.values() if cat['has_children']),
            'blacklisted_count': len(self.blacklist_dirs),
            'sorted_dir_exists': self.sorted_dir.exists(),
            'categories': categories
        }

        return stats

    def create_category_if_not_exists(self, category: str) -> bool:
        """
        Create category directory if it doesn't exist

        Args:
            category: Category name

        Returns:
            True if created successfully or already exists
        """
        if not category or category in self.blacklist_dirs:
            return False

        category_path = self.sorted_dir / category

        try:
            category_path.mkdir(parents=True, exist_ok=True)
            return True
        except Exception:
            return False


# Default instance for backward compatibility
default_category_manager = CategoryManager()

def get_smart_categories() -> List[str]:
    """Legacy function for backward compatibility"""
    return default_category_manager.get_smart_categories()

def get_directory_tree(base_path, max_depth=3, current_depth=0) -> Dict[str, Any]:
    """Legacy function for backward compatibility"""
    return default_category_manager.get_directory_tree(
        Path(base_path) if base_path else None, max_depth, current_depth
    )

def get_live_directory_structure() -> Dict[str, Any]:
    """Legacy function for backward compatibility"""
    return default_category_manager.get_live_directory_structure()

def build_category_context_for_ai() -> str:
    """Legacy function for backward compatibility"""
    return default_category_manager.build_category_context_for_ai()