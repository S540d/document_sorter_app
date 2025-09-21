"""
Directory Operations Manager
Handles file operations and directory management
"""

import os
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from ..settings import config


class DirectoryManager:
    """Manages directory operations and file movements"""

    def __init__(self, scan_dir: str = None, sorted_dir: str = None):
        """
        Initialize directory manager

        Args:
            scan_dir: Directory for scanned documents (uses config if not provided)
            sorted_dir: Directory for sorted documents (uses config if not provided)
        """
        self.scan_dir = Path(scan_dir or config.scan_dir)
        self.sorted_dir = Path(sorted_dir or config.sorted_dir)

    def ensure_directories(self) -> Dict[str, bool]:
        """
        Ensure that required directories exist

        Returns:
            Dictionary with creation results
        """
        results = {}

        try:
            self.scan_dir.mkdir(parents=True, exist_ok=True)
            results['scan_dir'] = True
        except Exception as e:
            results['scan_dir'] = False
            results['scan_dir_error'] = str(e)

        try:
            self.sorted_dir.mkdir(parents=True, exist_ok=True)
            results['sorted_dir'] = True
        except Exception as e:
            results['sorted_dir'] = False
            results['sorted_dir_error'] = str(e)

        return results

    def get_pdf_files(self, directory: Optional[Path] = None) -> List[Dict[str, Any]]:
        """
        Get list of PDF files in directory

        Args:
            directory: Directory to scan (uses scan_dir if not provided)

        Returns:
            List of PDF file information dictionaries
        """
        if directory is None:
            directory = self.scan_dir

        pdf_files = []

        if not directory.exists():
            return pdf_files

        try:
            for pdf_file in directory.glob('*.pdf'):
                file_stat = pdf_file.stat()
                pdf_files.append({
                    'name': pdf_file.name,
                    'path': str(pdf_file),
                    'size': file_stat.st_size,
                    'modified': file_stat.st_mtime
                })
        except Exception:
            pass

        return sorted(pdf_files, key=lambda x: x['modified'], reverse=True)

    def move_document(self, source_path: str, target_path: str) -> Dict[str, Any]:
        """
        Move document from source to target location

        Args:
            source_path: Source file path
            target_path: Target file path

        Returns:
            Dictionary with operation result
        """
        try:
            source = Path(source_path)
            target = Path(target_path)

            # Validate source exists
            if not source.exists():
                return {
                    'success': False,
                    'error': f'Source file not found: {source_path}'
                }

            # Create target directory if needed
            target.parent.mkdir(parents=True, exist_ok=True)

            # Handle file name conflicts
            if target.exists():
                target = self._get_unique_filename(target)

            # Move file
            shutil.move(str(source), str(target))

            return {
                'success': True,
                'source_path': source_path,
                'target_path': str(target),
                'message': f'File moved to {target}'
            }

        except Exception as e:
            return {
                'success': False,
                'error': f'Move failed: {str(e)}',
                'source_path': source_path,
                'target_path': target_path
            }

    def _get_unique_filename(self, file_path: Path) -> Path:
        """
        Get unique filename if file already exists

        Args:
            file_path: Original file path

        Returns:
            Unique file path
        """
        if not file_path.exists():
            return file_path

        base = file_path.stem
        suffix = file_path.suffix
        parent = file_path.parent
        counter = 1

        while True:
            new_name = f"{base}_{counter}{suffix}"
            new_path = parent / new_name
            if not new_path.exists():
                return new_path
            counter += 1

    def copy_document(self, source_path: str, target_path: str) -> Dict[str, Any]:
        """
        Copy document from source to target location

        Args:
            source_path: Source file path
            target_path: Target file path

        Returns:
            Dictionary with operation result
        """
        try:
            source = Path(source_path)
            target = Path(target_path)

            # Validate source exists
            if not source.exists():
                return {
                    'success': False,
                    'error': f'Source file not found: {source_path}'
                }

            # Create target directory if needed
            target.parent.mkdir(parents=True, exist_ok=True)

            # Handle file name conflicts
            if target.exists():
                target = self._get_unique_filename(target)

            # Copy file
            shutil.copy2(str(source), str(target))

            return {
                'success': True,
                'source_path': source_path,
                'target_path': str(target),
                'message': f'File copied to {target}'
            }

        except Exception as e:
            return {
                'success': False,
                'error': f'Copy failed: {str(e)}',
                'source_path': source_path,
                'target_path': target_path
            }

    def delete_document(self, file_path: str) -> Dict[str, Any]:
        """
        Delete document file

        Args:
            file_path: File path to delete

        Returns:
            Dictionary with operation result
        """
        try:
            file = Path(file_path)

            if not file.exists():
                return {
                    'success': False,
                    'error': f'File not found: {file_path}'
                }

            file.unlink()

            return {
                'success': True,
                'file_path': file_path,
                'message': f'File deleted: {file_path}'
            }

        except Exception as e:
            return {
                'success': False,
                'error': f'Delete failed: {str(e)}',
                'file_path': file_path
            }

    def get_directory_info(self, directory: Optional[Path] = None) -> Dict[str, Any]:
        """
        Get information about directory

        Args:
            directory: Directory to analyze (uses sorted_dir if not provided)

        Returns:
            Dictionary with directory information
        """
        if directory is None:
            directory = self.sorted_dir

        info = {
            'path': str(directory),
            'exists': directory.exists(),
            'total_files': 0,
            'total_dirs': 0,
            'total_size': 0,
            'pdf_count': 0
        }

        if not directory.exists():
            return info

        try:
            for item in directory.rglob('*'):
                if item.is_file():
                    info['total_files'] += 1
                    info['total_size'] += item.stat().st_size
                    if item.suffix.lower() == '.pdf':
                        info['pdf_count'] += 1
                elif item.is_dir():
                    info['total_dirs'] += 1

        except Exception:
            pass

        return info

    def suggest_alternative_paths(self, filename: str, categories: List[str]) -> List[Dict[str, Any]]:
        """
        Suggest alternative file paths based on available categories

        Args:
            filename: Name of the file
            categories: Available categories

        Returns:
            List of suggested path dictionaries
        """
        suggestions = []

        for category in categories[:5]:  # Limit to top 5 for better UX
            category_path = self.sorted_dir / category / filename
            confidence = 0.7 if category != 'Sonstiges' else 0.3

            suggestions.append({
                'path': str(category_path),
                'category': category,
                'confidence': confidence
            })

        return suggestions

    def cleanup_empty_directories(self, directory: Optional[Path] = None) -> Dict[str, Any]:
        """
        Remove empty directories

        Args:
            directory: Directory to clean (uses sorted_dir if not provided)

        Returns:
            Dictionary with cleanup results
        """
        if directory is None:
            directory = self.sorted_dir

        removed_dirs = []

        try:
            # Walk bottom-up to handle nested empty directories
            for root, dirs, files in os.walk(str(directory), topdown=False):
                root_path = Path(root)

                # Skip if not empty
                if files or dirs:
                    continue

                # Skip if it's the base directory
                if root_path == directory:
                    continue

                try:
                    root_path.rmdir()
                    removed_dirs.append(str(root_path))
                except Exception:
                    pass

            return {
                'success': True,
                'removed_count': len(removed_dirs),
                'removed_dirs': removed_dirs
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'removed_count': len(removed_dirs),
                'removed_dirs': removed_dirs
            }


# Default instance for backward compatibility
default_directory_manager = DirectoryManager()

def move_document(source_path: str, target_path: str) -> Dict[str, Any]:
    """Legacy function for backward compatibility"""
    return default_directory_manager.move_document(source_path, target_path)