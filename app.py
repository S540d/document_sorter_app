#!/usr/bin/env python3
"""
Document Sorter MVP
Webapp für automatische Dokumentensortierung mit DeepSeek R3
"""

import os
import time
from flask import Flask, render_template, request
from app.pdf import PDFProcessor, PDFPreviewGenerator
from app.ai import DocumentClassifier, PromptManager
from app.directory import DirectoryManager, CategoryManager
from app.api import documents_bp, directories_bp, monitoring_bp
from app.monitoring import get_logger, ErrorReporter, LogAggregator
from app.monitoring.performance_tracker import get_performance_tracker

# Import centralized configuration
from app.settings import config, CONFIG


app = Flask(__name__)

# Register blueprints
app.register_blueprint(documents_bp)
app.register_blueprint(directories_bp)
app.register_blueprint(monitoring_bp)

# Monitoring Services initialisieren
logger = get_logger('document_sorter')
error_reporter = ErrorReporter()
log_aggregator = LogAggregator()
performance_tracker = get_performance_tracker()

# Request Logging und Performance Tracking Middleware
request_start_times = {}

@app.before_request
def log_request_info():
    request_start_times[request.path] = time.time()
    logger.info("HTTP Request received",
               method=request.method,
               path=request.path,
               remote_addr=request.remote_addr,
               user_agent=request.headers.get('User-Agent'))

@app.after_request
def log_response_info(response):
    # Performance Tracking
    if request.path in request_start_times:
        duration = time.time() - request_start_times[request.path]
        performance_tracker.record_response_time(request.path, duration)
        performance_tracker.record_error_rate(request.path, response.status_code >= 400)
        del request_start_times[request.path]

    logger.info("HTTP Response sent",
               status_code=response.status_code,
               path=request.path,
               duration=duration if 'duration' in locals() else None)
    return response

# API routes now handled by blueprints

# Configuration is now imported from app.settings
# PDF processing is now handled by app.pdf module

# Initialize PDF processing instances
pdf_processor = PDFProcessor(max_pages=3)
preview_generator = PDFPreviewGenerator(dpi=1.5)

# Initialize AI classification instances
document_classifier = DocumentClassifier()
prompt_manager = PromptManager()

# Initialize directory management instances
directory_manager = DirectoryManager()
category_manager = CategoryManager()

# Directory management functions now use the directory module

def classify_document(text, filename=None):
    """Klassifiziert Dokument mit AI-Modul (vereinfachte Wrapper-Funktion)"""

    # Hole verfügbare Kategorien
    categories = category_manager.get_smart_categories()

    # Erstelle Kategorieinformationen basierend auf echter Struktur (zur Laufzeit)
    category_info = category_manager.build_category_context_for_ai()

    # Verwende das AI-Modul für die Klassifizierung
    result = document_classifier.classify_with_analysis(
        text, filename or 'unknown', categories, category_info
    )

    # Logging für Kompatibilität
    logger.info("AI classification response",
               parsed_category=result['category'],
               context_hints=result['context_hints'],
               available_categories=categories[:5],  # Log first 5 for brevity
               filename=filename,
               confidence=result['confidence'])

    if result['category'] in categories:
        logger.info("AI category match found", selected_category=result['category'])
    elif result['fallback_used']:
        logger.warning("AI returned invalid category, using fallback",
                      parsed_category=result['category'],
                      available_categories=categories[:5],
                      fallback=result['category'])

    return result['category']

@app.route('/')
def index():
    """Hauptseite der Webapp"""
    categories = category_manager.get_smart_categories()
    return render_template('index.html', categories=categories)

# All API endpoints now handled by blueprints

if __name__ == '__main__':
    # Überprüfe ob Verzeichnisse existieren
    for dir_path in [CONFIG['SCAN_DIR'], CONFIG['SORTED_DIR']]:
        if not os.path.exists(dir_path):
            logger.warning(f"Directory does not exist: {dir_path}")
            print(f"Warning: Directory {dir_path} does not exist")

    # Initialisierung loggen
    logger.info("Starting Document Sorter application",
               scan_dir=CONFIG['SCAN_DIR'],
               sorted_dir=CONFIG['SORTED_DIR'],
               lm_studio_url=CONFIG['LM_STUDIO_URL'],
               debug_mode=config.debug_mode)

    print("Starting Document Sorter with comprehensive logging...")
    print(f"📁 Scan directory: {CONFIG['SCAN_DIR']}")
    print(f"📂 Sorted directory: {CONFIG['SORTED_DIR']}")
    print(f"🤖 LM Studio URL: {CONFIG['LM_STUDIO_URL']}")
    print(f"📊 Monitoring: /api/monitoring/status")
    print(f"📝 Logs: /api/monitoring/logs")

    try:
        app.run(debug=config.debug_mode, host=config.host, port=config.port)
    except Exception as e:
        logger.critical("Application startup failed", exception=e)
        error_reporter.report_error("application_startup_error", str(e), {
            'config': CONFIG
        })
        raise