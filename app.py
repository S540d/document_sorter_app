#!/usr/bin/env python3
"""
Document Sorter MVP
Webapp für automatische Dokumentensortierung mit DeepSeek R3
"""

import os
import shutil
import base64
import random
import time
from pathlib import Path
from flask import Flask, render_template, request, jsonify
import fitz  # PyMuPDF für PDF-Verarbeitung
import requests
import json
from datetime import datetime
from app.monitoring import get_logger, log_performance, log_security_event, ErrorReporter, LogAggregator
from app.monitoring.performance_tracker import get_performance_tracker

try:
    from config_secret import LM_STUDIO_URL, SCAN_DIR, SORTED_DIR, DEBUG_MODE, PORT, HOST
except ImportError:
    print("Warning: config.secret.py nicht gefunden. Verwende Standardwerte.")
    LM_STUDIO_URL = 'http://localhost:1234/v1/chat/completions'
    SCAN_DIR = './scans'
    SORTED_DIR = './sorted'
    DEBUG_MODE = True
    PORT = 5000
    HOST = '127.0.0.1'


app = Flask(__name__)

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

# API: Unterverzeichnisse zu Kategorie vorschlagen
@app.route('/api/suggest-subdirs', methods=['POST'])
def suggest_subdirs():
    data = request.get_json()
    category = data.get('category', '')
    if not category:
        return jsonify({'error': 'Keine Kategorie angegeben'}), 400

    # Suche Unterverzeichnisse in der Kategorie
    base_path = os.path.join(CONFIG['SORTED_DIR'], category)
    subdirs = []
    if os.path.exists(base_path):
        for item in os.listdir(base_path):
            item_path = os.path.join(base_path, item)
            if os.path.isdir(item_path) and item not in CONFIG['BLACKLIST_DIRS']:
                subdirs.append(item)

    return jsonify({'subdirs': subdirs})

# Konfiguration
CONFIG = {
    'LM_STUDIO_URL': LM_STUDIO_URL,
    'SCAN_DIR': SCAN_DIR,
    'SORTED_DIR': SORTED_DIR,
    'BLACKLIST_DIRS': [
        '.SynologyWorkingDirectory',
        '#SynoRecycle',
        '21_gifs',
        '.DS_Store',
        '__pycache__',
        '.git',
        'node_modules',
        '.localized',
        'Programmierung'
    ]
}

def pdf_to_preview_image(pdf_path):
    """Konvertiert erste Seite eines PDFs zu Base64-String für Preview"""
    try:
        doc = fitz.open(pdf_path)
        page = doc[0]

        # Render als PNG mit 150 DPI
        mat = fitz.Matrix(1.5, 1.5)
        pix = page.get_pixmap(matrix=mat)
        img_data = pix.tobytes("png")

        # Base64 encoding für HTML-Anzeige
        img_b64 = base64.b64encode(img_data).decode()
        doc.close()

        return f"data:image/png;base64,{img_b64}"
    except Exception as e:
        print(f"Error creating preview: {e}")
        return None

def extract_text_from_pdf(pdf_path):
    """Extrahiert Text aus PDF für KI-Analyse"""
    try:
        doc = fitz.open(pdf_path)
        text = ""

        # Maximal erste 3 Seiten für Performance
        for page_num in range(min(3, len(doc))):
            page = doc[page_num]
            text += page.get_text()

        doc.close()
        return text.strip()
    except Exception as e:
        print(f"Error extracting text: {e}")
        return ""

def get_smart_categories():
    """Generiert intelligente Kategorien basierend auf Documents-Struktur"""
    sorted_dir = Path(CONFIG['SORTED_DIR'])
    categories = []

    if sorted_dir.exists():
        for item in sorted_dir.iterdir():
            if item.is_dir() and item.name not in CONFIG['BLACKLIST_DIRS']:
                categories.append(item.name)

    # Fallback-Kategorien falls Documents leer ist
    if not categories:
        categories = ['Steuern', 'Versicherungen', 'Verträge', 'Banken', 'Medizin', 'Behörden', 'Sonstiges']

    return sorted(categories)

def get_directory_tree(base_path, max_depth=3, current_depth=0):
    """Erstellt Verzeichnisbaum mit Blacklist-Filter"""
    if current_depth >= max_depth:
        return {}

    tree = {}
    base = Path(base_path)

    if not base.exists():
        return tree

    for item in base.iterdir():
        if item.is_dir() and item.name not in CONFIG['BLACKLIST_DIRS']:
            subtree = get_directory_tree(item, max_depth, current_depth + 1)
            tree[item.name] = {
                'path': str(item),
                'children': subtree,
                'has_children': bool(subtree)
            }

    return tree

def get_live_directory_structure():
    """Hole die echte Verzeichnisstruktur zur Laufzeit (lokal für KI)"""
    try:
        sorted_dir = Path(CONFIG['SORTED_DIR'])
        if not sorted_dir.exists():
            return {}
        return get_directory_tree(sorted_dir)
    except Exception as e:
        logger.error("Failed to get live directory structure", exception=e)
        return {}

def build_category_context_for_ai():
    """Erstelle strukturierte Kategorieinformationen basierend auf echter Verzeichnisstruktur"""
    # Hole echte Verzeichnisstruktur zur Laufzeit
    directory_structure = get_live_directory_structure()

    if not directory_structure:
        # Fallback: Verwende verfügbare Kategorien
        categories = get_smart_categories()
        return "Verfügbare Kategorien: " + ", ".join(categories)

    category_lines = []
    for category, info in directory_structure.items():
        if not info.get('has_children', False):
            category_lines.append(f"📁 {category}")
        else:
            category_lines.append(f"📁 {category}")
            # Zeige die ersten 5 Unterverzeichnisse
            children = list(info.get('children', {}).keys())[:5]
            for child in children:
                category_lines.append(f"   └── {child}")
            if len(info.get('children', {})) > 5:
                category_lines.append(f"   └── ... ({len(info.get('children', {})) - 5} weitere)")

    return "\n".join(category_lines)

def extract_document_context(text, filename):
    """Extrahiere Kontext-Hinweise aus Dokumententext und Dateiname"""
    hints = []

    # Dateiname-Analyse
    if filename:
        filename_lower = filename.lower()
        if any(word in filename_lower for word in ['rechnung', 'invoice', 'bill']):
            hints.append("Rechnung")
        if any(word in filename_lower for word in ['vertrag', 'contract']):
            hints.append("Vertrag")
        if any(word in filename_lower for word in ['kita', 'kindergarten']):
            hints.append("Kita/Kindergarten")
        if any(word in filename_lower for word in ['arbeit', 'job', 'gehalt']):
            hints.append("Arbeit")
        if any(word in filename_lower for word in ['steuer', 'tax']):
            hints.append("Steuern")

    # Text-Analyse (erste 500 Zeichen für Performance)
    text_sample = text[:500].lower() if text else ""
    if any(word in text_sample for word in ['rechnung', 'betrag', 'euro', 'umsatzsteuer']):
        hints.append("Finanzdokument")
    if any(word in text_sample for word in ['arbeitsvertrag', 'gehalt', 'lohn', 'arbeitgeber']):
        hints.append("Arbeitsdokument")
    if any(word in text_sample for word in ['mietvertrag', 'miete', 'wohnung', 'hausverwaltung']):
        hints.append("Wohndokument")
    if any(word in text_sample for word in ['fahrzeug', 'auto', 'kfz', 'tüv', 'versicherung']):
        hints.append("Fahrzeug")
    if any(word in text_sample for word in ['kindergarten', 'kita', 'betreuung']):
        hints.append("Kita")

    return ", ".join(hints) if hints else "Keine spezifischen Hinweise"

def parse_ai_response(raw_response, available_categories):
    """Parse AI response and extract the category name, handling DeepSeek reasoning tokens"""

    # First try exact match with available categories
    for category in available_categories:
        if category in raw_response:
            return category

    # Handle DeepSeek reasoning tokens - extract content after </think>
    if '</think>' in raw_response:
        parts = raw_response.split('</think>')
        if len(parts) > 1:
            final_answer = parts[-1].strip()
            # Check if final answer contains any category
            for category in available_categories:
                if category in final_answer:
                    return category
            # If no category found, return the cleaned final answer
            return final_answer

    # Handle other reasoning patterns
    lines = raw_response.split('\n')
    for line in lines:
        line = line.strip()
        if line and not line.startswith('<') and not line.startswith('Okay') and not line.startswith('Ich'):
            for category in available_categories:
                if category in line:
                    return category
            # If this line looks like a clean category answer, return it
            if len(line) < 50 and not line.endswith('?'):
                return line

    # Fallback: return the cleaned raw response
    cleaned = raw_response.replace('<think>', '').replace('</think>', '').strip()
    lines = cleaned.split('\n')
    if lines:
        return lines[-1].strip()

    return raw_response.strip()

def classify_document(text, filename=None):
    """Fragt DeepSeek R3 über LM Studio nach Dokumentenklassifizierung mit Live-Verzeichnisstruktur"""

    # Hole verfügbare Kategorien
    categories = get_smart_categories()

    # Erstelle Kategorieinformationen basierend auf echter Struktur (zur Laufzeit)
    category_info = build_category_context_for_ai()

    # Extrahiere zusätzliche Kontext-Hinweise
    context_hints = extract_document_context(text, filename)

    prompt = f"""Du bist ein Experte für deutsche Dokumentenklassifizierung.
Analysiere das Dokument und wähle die beste Kategorie basierend auf Inhalt, Dateiname und verfügbaren Verzeichnissen.

DOKUMENT-KONTEXT:
- Dateiname: {filename or 'Unbekannt'}
- Textlänge: {len(text)} Zeichen
- Erkannte Hinweise: {context_hints}

VERFÜGBARE KATEGORIEN MIT STRUKTUR:
{category_info}

KLASSIFIZIERUNGS-REGELN:
1. Wähle die spezifischste passende Kategorie aus der obigen Liste
2. Bei Kita/Kindergarten-Dokumenten → entsprechende Wohn- oder Schriftverkehr-Kategorie
3. Bei Arbeitsdokumenten → Arbeitskategorie
4. Bei Finanzen/Steuern/Versicherungen → Finanzkategorie
5. Bei Fahrzeugen → Fahrzeugkategorie
6. Bei Wissenschaft/Studium → Bildungskategorie
7. Bei Wohnen/Miete → Wohnkategorie

DOKUMENTENTEXT (erste 2000 Zeichen):
{text[:2000]}

WICHTIG: Antworte nur mit dem exakten Kategorienamen aus der Verzeichnisliste oben. Kein Text davor oder danach, nur der Kategoriename."""

    try:
        response = requests.post(
            CONFIG['LM_STUDIO_URL'],
            json={
                "model": "deepseek-r1-distill-qwen-7b",
                "messages": [
                    {"role": "system", "content": "Du bist ein Experte für deutsche Dokumentenklassifizierung. Antworte nur mit dem exakten Kategorienamen."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.1,
                "max_tokens": 100,
                "stop": ["\n", ".", "!", "?"]
            },
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            raw_response = result['choices'][0]['message']['content'].strip()

            # Parse DeepSeek reasoning tokens - extract final answer
            category = parse_ai_response(raw_response, categories)

            logger.info("AI classification response",
                       ai_response=raw_response[:100] + "..." if len(raw_response) > 100 else raw_response,
                       parsed_category=category,
                       available_categories=categories[:5],  # Log first 5 for brevity
                       filename=filename)

            if category in categories:
                logger.info("AI category match found", selected_category=category)
                return category
            else:
                logger.warning("AI returned invalid category, using fallback",
                              ai_response=raw_response[:100] + "..." if len(raw_response) > 100 else raw_response,
                              parsed_category=category,
                              available_categories=categories[:5],
                              fallback=categories[0] if categories else '0001_scanbot')
                # Falls AI eine ungültige Kategorie zurückgibt, verwende erste verfügbare
                if categories:
                    return categories[0]
                else:
                    return '0001_scanbot'  # Fallback für temporäre Dateien
        else:
            logger.error("LM Studio API error", status_code=response.status_code, response_text=response.text)
            return categories[0] if categories else '0001_scanbot'

    except Exception as e:
        print(f"Error calling LM Studio: {e}")
        return categories[0] if categories else '0001_scanbot'

@app.route('/')
def index():
    """Hauptseite der Webapp"""
    categories = get_smart_categories()
    return render_template('index.html', categories=categories)

@app.route('/api/scan-files')
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

@app.route('/api/random-document')
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

@app.route('/api/process-document', methods=['POST'])
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
        preview = pdf_to_preview_image(pdf_path)

        # Text extrahieren
        text = extract_text_from_pdf(pdf_path)

        # KI-Klassifizierung
        filename = os.path.basename(pdf_path)
        suggested_category = classify_document(text, filename)

        # Vorgeschlagenen Pfad generieren
        suggested_path = os.path.join(CONFIG['SORTED_DIR'], suggested_category, filename)

        logger.info("PDF processing completed successfully",
                   pdf_path=pdf_path,
                   suggested_category=suggested_category,
                   text_length=len(text))

        return jsonify({
            'preview': preview,
            'suggested_category': suggested_category,
            'suggested_path': suggested_path,
            'original_path': pdf_path
        })

    except Exception as e:
        logger.error("PDF processing failed with exception",
                    pdf_path=pdf_path,
                    exception=e)
        error_reporter.report_error("pdf_processing_error", str(e), {
            'pdf_path': pdf_path,
            'operation': 'process_document'
        })
        return jsonify({'error': 'PDF processing failed'}), 500

@app.route('/api/move-document', methods=['POST'])
@log_performance("move_document")
def move_document():
    """Führt den Move-Befehl aus"""
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

        # Zielverzeichnis erstellen falls nicht vorhanden
        target_dir = os.path.dirname(target_path)
        os.makedirs(target_dir, exist_ok=True)

        # Datei verschieben
        shutil.move(source_path, target_path)

        logger.info("Document moved successfully",
                   source_path=source_path,
                   target_path=target_path)

        return jsonify({'success': True, 'message': f'File moved to {target_path}'})

    except Exception as e:
        logger.error("Document move failed with exception",
                    source_path=source_path,
                    target_path=target_path,
                    exception=e)
        error_reporter.report_error("document_move_error", str(e), {
            'source_path': source_path,
            'target_path': target_path,
            'operation': 'move_document'
        })
        return jsonify({'error': f'Move failed: {str(e)}'}), 500

@app.route('/api/system-status')
def system_status():
    """Systemstatus für Frontend"""
    scan_dir = Path(CONFIG['SCAN_DIR'])
    sorted_dir = Path(CONFIG['SORTED_DIR'])

    return jsonify({
        'scan_dir_exists': scan_dir.exists(),
        'sorted_dir_exists': sorted_dir.exists(),
        'lm_studio_url': CONFIG['LM_STUDIO_URL'],
        'preload_status': {'is_running': False},
        'preload_complete': True,
        'system_stats': {
            'cpu_percent': 0,
            'memory_percent': 0,
            'disk_usage': 0
        }
    })

@app.route('/api/directory-structure')
def directory_structure():
    """Verzeichnisstruktur für Frontend mit Blacklist-Filter"""
    tree = get_directory_tree(CONFIG['SORTED_DIR'])
    return jsonify({
        'structure': tree,
        'base_path': CONFIG['SORTED_DIR']
    })

@app.route('/api/suggest-alternative-paths', methods=['POST'])
def suggest_alternative_paths():
    """Schlägt alternative Zielpfade vor"""
    data = request.get_json()
    filename = data.get('filename', '')

    # Intelligente Pfadvorschläge basierend auf existierenden Verzeichnissen
    suggestions = []
    categories = get_smart_categories()

    for category in categories[:5]:  # Nur Top 5 für bessere UX
        category_path = os.path.join(CONFIG['SORTED_DIR'], category, filename)
        suggestions.append({
            'path': category_path,
            'category': category,
            'confidence': 0.7 if category != 'Sonstiges' else 0.3
        })

    return jsonify({'suggestions': suggestions})


# Neue Route für Pfad-Management-Seite
@app.route('/path-management')
def path_management():
    return render_template('path_management.html')

# API für ähnliche Pfade und Kombinationsvorschläge
@app.route('/api/suggest-similar-paths', methods=['POST'])
def suggest_similar_paths():
    data = request.get_json()
    filename = data.get('filename', '')
    if not filename:
        return jsonify({'error': 'Kein Dateiname angegeben'}), 400

    # Hole alle Kategorien/Verzeichnisse
    categories = get_smart_categories()
    similar_paths = []
    combinations = []

    # Suche existierende Verzeichnisse im SORTED_DIR (max. 2 Ebenen tief)
    existing_dirs = []
    for root, dirs, files in os.walk(CONFIG['SORTED_DIR']):
        depth = root[len(CONFIG['SORTED_DIR']):].count(os.sep)
        if depth <= 2:
            for d in dirs:
                dir_path = os.path.join(root, d)
                if d not in CONFIG['BLACKLIST_DIRS']:
                    existing_dirs.append(dir_path)

    # String-Similarity für Kategorien
    for cat in categories:
        similarity = 1.0 if cat.lower() in filename.lower() else 0.5 if filename.lower()[:3] in cat.lower() else 0.2
        path = os.path.join(CONFIG['SORTED_DIR'], cat, filename)
        similar_paths.append({
            'directory': cat,
            'path': path,
            'similarity': similarity
        })

    # String-Similarity für existierende Verzeichnisse
    for dir_path in existing_dirs:
        dir_name = os.path.basename(dir_path)
        similarity = 1.0 if dir_name.lower() in filename.lower() else 0.5 if filename.lower()[:3] in dir_name.lower() else 0.2
        path = os.path.join(dir_path, filename)
        similar_paths.append({
            'directory': dir_name,
            'path': path,
            'similarity': similarity
        })

    # Kombinationsvorschläge: Jede Kategorie mit jeder anderen
    for i, cat_a in enumerate(categories):
        for j, cat_b in enumerate(categories):
            if i != j:
                combined_path_ab = os.path.join(CONFIG['SORTED_DIR'], cat_a, cat_b, filename)
                combined_path_ba = os.path.join(CONFIG['SORTED_DIR'], cat_b, cat_a, filename)
                combined_similarity = (similar_paths[i]['similarity'] + similar_paths[j]['similarity']) / 2
                combinations.append({
                    'path_a': similar_paths[i],
                    'path_b': similar_paths[j],
                    'combined_path_ab': combined_path_ab,
                    'combined_path_ba': combined_path_ba,
                    'combined_similarity': combined_similarity
                })

    return jsonify({
        'similar_paths': similar_paths,
        'combinations': combinations
    })

# Monitoring Endpoints
@app.route('/api/monitoring/logs')
def get_logs():
    """Gibt aggregierte Log-Daten zurück"""
    try:
        hours = request.args.get('hours', 24, type=int)
        # Note: In production würde dies async laufen
        # Für jetzt simulieren wir die Aggregation

        stats = {
            'time_range_hours': hours,
            'summary': {
                'total_entries': 150,
                'by_level': {'INFO': 100, 'WARNING': 30, 'ERROR': 15, 'DEBUG': 5},
                'by_logger': {'document_sorter': 80, 'performance': 40, 'security': 30}
            },
            'recent_errors': error_reporter.get_error_statistics()
        }

        logger.info("Log data requested", hours=hours)
        return jsonify(stats)
    except Exception as e:
        logger.error("Failed to get logs", exception=e)
        return jsonify({'error': 'Failed to retrieve logs'}), 500

@app.route('/api/monitoring/errors')
def get_error_stats():
    """Gibt Error-Statistiken zurück"""
    try:
        stats = error_reporter.get_error_statistics()
        return jsonify(stats)
    except Exception as e:
        logger.error("Failed to get error statistics", exception=e)
        return jsonify({'error': 'Failed to retrieve error statistics'}), 500

@app.route('/api/monitoring/logs/search')
def search_logs():
    """Durchsucht Logs nach Pattern"""
    try:
        pattern = request.args.get('pattern', '')
        hours = request.args.get('hours', 24, type=int)
        log_level = request.args.get('level')

        if not pattern:
            return jsonify({'error': 'Search pattern required'}), 400

        # Note: In production würde dies async laufen
        results = []  # Placeholder - echte Suche würde log_aggregator.search_logs verwenden

        logger.info("Log search performed", pattern=pattern, hours=hours, level=log_level)
        return jsonify({'results': results, 'pattern': pattern})
    except Exception as e:
        logger.error("Log search failed", exception=e)
        return jsonify({'error': 'Log search failed'}), 500

@app.route('/api/monitoring/logs/export', methods=['POST'])
def export_error_report():
    """Exportiert Error-Report"""
    try:
        data = request.get_json() or {}
        hours = data.get('hours', 24)
        filepath = f"logs/error_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        success = error_reporter.export_error_report(filepath, hours)

        if success:
            logger.info("Error report exported", filepath=filepath, hours=hours)
            return jsonify({'success': True, 'filepath': filepath})
        else:
            return jsonify({'error': 'Export failed'}), 500
    except Exception as e:
        logger.error("Error report export failed", exception=e)
        return jsonify({'error': 'Export failed'}), 500

@app.route('/api/monitoring/logs/cleanup', methods=['POST'])
def cleanup_logs():
    """Führt Log-Cleanup durch"""
    try:
        data = request.get_json() or {}
        days = data.get('days', 7)

        # Komprimiere alte Logs
        compressed_count = log_aggregator.compress_old_logs()

        # Entferne sehr alte Logs
        removed_count, freed_space = log_aggregator.cleanup_old_logs()

        # Cleanup alte Errors
        cleaned_errors = error_reporter.cleanup_old_errors(days)

        result = {
            'compressed_logs': compressed_count,
            'removed_logs': removed_count,
            'freed_space_mb': round(freed_space / (1024 * 1024), 2),
            'cleaned_errors': cleaned_errors
        }

        logger.info("Log cleanup completed", **result)
        return jsonify(result)
    except Exception as e:
        logger.error("Log cleanup failed", exception=e)
        return jsonify({'error': 'Cleanup failed'}), 500

@app.route('/api/monitoring/status')
def monitoring_status():
    """Gibt Monitoring-System Status zurück"""
    try:
        log_stats = log_aggregator.get_log_statistics()
        error_stats = error_reporter.get_error_statistics()

        status = {
            'logging': {
                'enabled': True,
                'log_files': log_stats['file_count'],
                'total_size_mb': log_stats['total_size_mb']
            },
            'error_reporting': {
                'enabled': True,
                'total_error_types': len(error_stats['error_types']),
                'total_errors': sum(error_stats['total_errors'].values())
            },
            'log_aggregation': {
                'enabled': True,
                'retention_days': log_aggregator.retention_days
            }
        }

        return jsonify(status)
    except Exception as e:
        logger.error("Failed to get monitoring status", exception=e)
        return jsonify({'error': 'Failed to retrieve status'}), 500

# Performance Monitoring Endpoints
@app.route('/api/performance/current')
def get_current_performance():
    """Gibt aktuelle Performance-Metriken zurück"""
    try:
        metrics = performance_tracker.get_current_metrics()
        logger.info("Current performance metrics requested")
        return jsonify(metrics)
    except Exception as e:
        logger.error("Failed to get current performance metrics", exception=e)
        return jsonify({'error': 'Failed to retrieve performance metrics'}), 500

@app.route('/api/performance/historical')
def get_historical_performance():
    """Gibt historische Performance-Metriken zurück"""
    try:
        hours = request.args.get('hours', 24, type=int)
        metrics = performance_tracker.get_historical_metrics(hours)
        logger.info("Historical performance metrics requested", hours=hours)
        return jsonify(metrics)
    except Exception as e:
        logger.error("Failed to get historical performance metrics", exception=e)
        return jsonify({'error': 'Failed to retrieve historical metrics'}), 500

@app.route('/api/performance/summary')
def get_performance_summary():
    """Gibt Performance-Zusammenfassung zurück"""
    try:
        hours = request.args.get('hours', 24, type=int)
        summary = performance_tracker.get_performance_summary(hours)
        logger.info("Performance summary requested", hours=hours)
        return jsonify(summary)
    except Exception as e:
        logger.error("Failed to get performance summary", exception=e)
        return jsonify({'error': 'Failed to retrieve performance summary'}), 500

@app.route('/api/performance/alerts')
def get_performance_alerts():
    """Gibt Performance-Alerts zurück"""
    try:
        hours = request.args.get('hours', 24, type=int)
        summary = performance_tracker.get_performance_summary(hours)
        alerts = summary.get('alerts', [])

        logger.info("Performance alerts requested", hours=hours, alert_count=len(alerts))
        return jsonify({'alerts': alerts, 'count': len(alerts)})
    except Exception as e:
        logger.error("Failed to get performance alerts", exception=e)
        return jsonify({'error': 'Failed to retrieve performance alerts'}), 500

@app.route('/api/performance/export', methods=['POST'])
def export_performance_metrics():
    """Exportiert Performance-Metriken"""
    try:
        data = request.get_json() or {}
        hours = data.get('hours', 24)
        filepath = f"logs/performance_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        success = performance_tracker.export_metrics(filepath, hours)

        if success:
            logger.info("Performance metrics exported", filepath=filepath, hours=hours)
            return jsonify({'success': True, 'filepath': filepath})
        else:
            return jsonify({'error': 'Export failed'}), 500
    except Exception as e:
        logger.error("Performance metrics export failed", exception=e)
        return jsonify({'error': 'Export failed'}), 500

@app.route('/api/performance/custom-metric', methods=['POST'])
def record_custom_metric():
    """Zeichnet benutzerdefinierte Metrik auf"""
    try:
        data = request.get_json()
        if not data or 'name' not in data or 'value' not in data:
            return jsonify({'error': 'Missing name or value'}), 400

        name = data['name']
        value = data['value']
        tags = data.get('tags', {})

        performance_tracker.record_custom_metric(name, value, tags)

        logger.info("Custom metric recorded", name=name, value=value, tags=tags)
        return jsonify({'success': True, 'message': f'Metric {name} recorded'})
    except Exception as e:
        logger.error("Failed to record custom metric", exception=e)
        return jsonify({'error': 'Failed to record metric'}), 500

# Dashboard Endpoint
@app.route('/api/dashboard/overview')
def dashboard_overview():
    """Gibt Dashboard-Übersicht zurück"""
    try:
        # Sammle verschiedene Metriken für Dashboard
        current_perf = performance_tracker.get_current_metrics()
        error_stats = error_reporter.get_error_statistics()
        log_stats = log_aggregator.get_log_statistics()
        perf_summary = performance_tracker.get_performance_summary(24)

        overview = {
            'timestamp': time.time(),
            'system_health': {
                'cpu_percent': current_perf['system'].get('cpu_percent', 0),
                'memory_percent': current_perf['system'].get('memory_percent', 0),
                'disk_usage': current_perf['system'].get('disk_usage', 0),
                'status': perf_summary['system_health']['overall_status']
            },
            'application_stats': {
                'total_requests': sum(current_perf.get('request_counts', {}).values()),
                'average_response_time': _calculate_overall_avg_response_time(current_perf),
                'error_count': sum(error_stats.get('total_errors', {}).values()),
                'monitoring_active': current_perf.get('monitoring_active', False)
            },
            'log_stats': {
                'total_log_files': log_stats.get('file_count', 0),
                'total_size_mb': log_stats.get('total_size_mb', 0)
            },
            'alerts': perf_summary.get('alerts', [])[:5]  # Top 5 alerts
        }

        logger.info("Dashboard overview requested")
        return jsonify(overview)
    except Exception as e:
        logger.error("Failed to get dashboard overview", exception=e)
        return jsonify({'error': 'Failed to retrieve dashboard overview'}), 500

def _calculate_overall_avg_response_time(current_perf):
    """Berechnet durchschnittliche Response Time über alle Endpoints"""
    response_times = current_perf.get('response_times', {})
    if not response_times:
        return 0

    total_time = 0
    total_requests = 0

    for endpoint, stats in response_times.items():
        total_time += stats['avg'] * stats['count']
        total_requests += stats['count']

    return total_time / total_requests if total_requests > 0 else 0

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
               debug_mode=DEBUG_MODE)

    print("Starting Document Sorter with comprehensive logging...")
    print(f"📁 Scan directory: {CONFIG['SCAN_DIR']}")
    print(f"📂 Sorted directory: {CONFIG['SORTED_DIR']}")
    print(f"🤖 LM Studio URL: {CONFIG['LM_STUDIO_URL']}")
    print(f"📊 Monitoring: /api/monitoring/status")
    print(f"📝 Logs: /api/monitoring/logs")

    try:
        app.run(debug=DEBUG_MODE, host=HOST, port=PORT)
    except Exception as e:
        logger.critical("Application startup failed", exception=e)
        error_reporter.report_error("application_startup_error", str(e), {
            'config': CONFIG
        })
        raise