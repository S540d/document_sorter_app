"""
Document Processing API Blueprint
Handles document scanning, processing, and classification
"""

import os
import random
import shutil
from datetime import datetime
from pathlib import Path
from flask import Blueprint, request, jsonify

try:
    import psutil
except ImportError:
    psutil = None

from ..settings import CONFIG
from ..pdf import PDFProcessor, PDFPreviewGenerator
from ..ai import DocumentClassifier, PromptManager
from ..directory import CategoryManager
from ..monitoring import get_logger, log_performance
from ..services.file_renaming import file_renaming_service

# Create blueprint
documents_bp = Blueprint('documents', __name__, url_prefix='/api')

# Initialize components
logger = get_logger('documents_api')
pdf_processor = PDFProcessor(max_pages=3)
preview_generator = PDFPreviewGenerator(dpi=1.5)
document_classifier = DocumentClassifier()
category_manager = CategoryManager()


@documents_bp.route('/scan-files')
def scan_files():
    """Scannt das Eingangverzeichnis nach PDFs"""
    scan_dir = Path(CONFIG['SCAN_DIR'])

    if not scan_dir.exists():
        return jsonify({'error': 'Scan directory not found'}), 404

    pdf_files = []
    for pdf_file in scan_dir.glob('*.pdf'):
        pdf_files.append({
            'name': pdf_file.name,
            'path': str(pdf_file),
            'size': pdf_file.stat().st_size,
            'modified': datetime.fromtimestamp(pdf_file.stat().st_mtime).isoformat()
        })

    return jsonify({
        'files': pdf_files,
        'system_stats': {
            'cpu_percent': 0,
            'memory_percent': 0,
            'disk_usage': 0
        },
        'preload_status': {
            'is_running': False,
            'processed_documents': 0,
            'total_documents': 0,
            'current_document': ''
        },
        'cached_count': len(pdf_files)
    })


@documents_bp.route('/random-document')
def get_random_document():
    """Wählt ein zufälliges PDF aus dem Scan-Verzeichnis"""
    scan_dir = Path(CONFIG['SCAN_DIR'])

    if not scan_dir.exists():
        return jsonify({'error': 'Scan directory not found'}), 404

    pdf_files = list(scan_dir.glob('*.pdf'))

    if not pdf_files:
        return jsonify({'error': 'No PDF files found'}), 404

    # Zufällige Datei auswählen
    random_file = random.choice(pdf_files)

    return jsonify({
        'name': random_file.name,
        'path': str(random_file),
        'size': random_file.stat().st_size,
        'modified': datetime.fromtimestamp(random_file.stat().st_mtime).isoformat()
    })


@documents_bp.route('/process-document', methods=['POST'])
@log_performance("process_document")
def process_document():
    """Verarbeitet ein PDF: Preview + KI-Klassifizierung"""
    try:
        data = request.get_json()
        pdf_path = data.get('path')

        if not pdf_path or not os.path.exists(pdf_path):
            logger.warning("PDF processing failed: file not found",
                         pdf_path=pdf_path)
            return jsonify({'error': 'PDF file not found'}), 404

        logger.info("Processing PDF document",
                   pdf_path=pdf_path,
                   filename=os.path.basename(pdf_path))

        # Preview-Image generieren
        preview = preview_generator.generate_preview(pdf_path)

        # Text extrahieren
        text = pdf_processor.extract_text(pdf_path)

        # KI-Klassifizierung
        filename = os.path.basename(pdf_path)

        # Hole verfügbare Kategorien und erstelle Kontext
        categories = category_manager.get_smart_categories()
        category_info = category_manager.build_category_context_for_ai()

        # Klassifiziere Dokument
        result = document_classifier.classify_with_analysis(
            text, filename, categories, category_info
        )

        # Generate smart filename suggestion
        suggested_category = result['category']['category']
        filename_suggestion = file_renaming_service.suggest_filename(filename, text, suggested_category)

        # Vorgeschlagenen Pfad generieren mit AI-Unterverzeichnis
        suggested_subdirectory = result['category'].get('subdirectory', '')

        if suggested_subdirectory:
            suggested_path = os.path.join(CONFIG['SORTED_DIR'], suggested_category, suggested_subdirectory, filename_suggestion['suggested_filename'])
        else:
            suggested_path = os.path.join(CONFIG['SORTED_DIR'], suggested_category, filename_suggestion['suggested_filename'])

        logger.info("PDF processing completed successfully",
                   pdf_path=pdf_path,
                   suggested_category=suggested_category,
                   suggested_subdirectory=suggested_subdirectory,
                   text_length=len(text))

        return jsonify({
            'preview': preview,
            'suggested_category': suggested_category,
            'suggested_subdirectory': suggested_subdirectory,
            'suggested_path': suggested_path,
            'original_path': pdf_path,
            'context_hints': result['context_hints'],
            'confidence': result['confidence'],
            'filename_suggestion': filename_suggestion
        })

    except Exception as e:
        logger.error("PDF processing failed with exception",
                    pdf_path=pdf_path if 'pdf_path' in locals() else 'unknown',
                    exception=e)
        return jsonify({'error': 'PDF processing failed'}), 500


@documents_bp.route('/move-document', methods=['POST'])
@log_performance("move_document")
def move_document():
    """Führt den Move-Befehl aus"""
    from ..directory import DirectoryManager

    try:
        data = request.get_json()
        source_path = data.get('source_path')
        target_path = data.get('target_path')

        if not source_path or not target_path:
            logger.warning("Document move failed: missing paths",
                         source_path=source_path,
                         target_path=target_path)
            return jsonify({'error': 'Missing paths'}), 400

        if not os.path.exists(source_path):
            logger.warning("Document move failed: source not found",
                         source_path=source_path)
            return jsonify({'error': 'Source file not found'}), 404

        logger.info("Moving document",
                   source_path=source_path,
                   target_path=target_path)

        # Use directory manager for move operation
        directory_manager = DirectoryManager()
        result = directory_manager.move_document(source_path, target_path)

        if result['success']:
            logger.info("Document moved successfully",
                       source_path=source_path,
                       target_path=result['target_path'])
            return jsonify(result)
        else:
            logger.error("Document move failed",
                        source_path=source_path,
                        target_path=target_path,
                        error=result['error'])
            return jsonify({'error': result['error']}), 500

    except Exception as e:
        logger.error("Document move failed with exception",
                    source_path=source_path if 'source_path' in locals() else 'unknown',
                    target_path=target_path if 'target_path' in locals() else 'unknown',
                    exception=e)
        return jsonify({'error': f'Move failed: {str(e)}'}), 500


@documents_bp.route('/suggest-filename', methods=['POST'])
@log_performance("suggest_filename")
def suggest_filename():
    """Generate intelligent filename suggestion based on content and category"""
    try:
        data = request.get_json()
        original_filename = data.get('filename')
        text_content = data.get('text', '')
        category = data.get('category', 'dokument')

        if not original_filename:
            return jsonify({'error': 'Missing filename'}), 400

        logger.info("Generating filename suggestion",
                   original_filename=original_filename,
                   category=category)

        # Generate filename suggestion
        suggestion = file_renaming_service.suggest_filename(
            original_filename, text_content, category
        )

        logger.info("Filename suggestion generated successfully",
                   original_filename=original_filename,
                   suggested_filename=suggestion['suggested_filename'])

        return jsonify(suggestion)

    except Exception as e:
        logger.error("Filename suggestion failed with exception",
                    original_filename=original_filename if 'original_filename' in locals() else 'unknown',
                    exception=e)
        return jsonify({'error': f'Filename suggestion failed: {str(e)}'}), 500


def get_system_stats():
    """Get real system metrics"""
    stats = {
        'cpu_percent': 0,
        'memory_percent': 0,
        'disk_usage': 0
    }

    if psutil:
        try:
            # CPU percentage (1 second interval for accuracy)
            stats['cpu_percent'] = round(psutil.cpu_percent(interval=0.1), 1)

            # Memory percentage
            memory = psutil.virtual_memory()
            stats['memory_percent'] = round(memory.percent, 1)

            # Disk usage for the sorted directory
            sorted_dir = CONFIG['SORTED_DIR']
            if os.path.exists(sorted_dir):
                total, used, free = shutil.disk_usage(sorted_dir)
                stats['disk_usage'] = round((used / total) * 100, 1)

        except Exception as e:
            logger.error("Error getting system stats", exception=e)

    return stats


@documents_bp.route('/system-status')
def system_status():
    """Systemstatus für Frontend"""
    scan_dir = Path(CONFIG['SCAN_DIR'])
    sorted_dir = Path(CONFIG['SORTED_DIR'])

    # Get real system stats
    system_stats = get_system_stats()

    # Count cached files
    cached_count = 0
    if scan_dir.exists():
        cached_count = len(list(scan_dir.glob('*.pdf')))

    return jsonify({
        'scan_dir_exists': scan_dir.exists(),
        'sorted_dir_exists': sorted_dir.exists(),
        'lm_studio_url': CONFIG['LM_STUDIO_URL'],
        'preload_status': {'is_running': False},
        'preload_complete': True,
        'system_stats': system_stats,
        'cached_count': cached_count
    })