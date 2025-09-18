#!/usr/bin/env python3
"""
Document Sorter MVP
Webapp für automatische Dokumentensortierung mit DeepSeek R3
"""

import os
import shutil
import base64
from pathlib import Path
from flask import Flask, render_template, request, jsonify
import fitz  # PyMuPDF für PDF-Verarbeitung
import requests
import json
from datetime import datetime

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

# Konfiguration
CONFIG = {
    'LM_STUDIO_URL': LM_STUDIO_URL,
    'SCAN_DIR': SCAN_DIR,
    'SORTED_DIR': SORTED_DIR,
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

def classify_document(text):
    """Fragt DeepSeek R3 über LM Studio nach Dokumentenklassifizierung"""
    categories = get_smart_categories()

    prompt = f"""Du bist ein Experte für Dokumentenklassifizierung.
Analysiere den folgenden Text und wähle die passendste Kategorie:

Verfügbare Kategorien: {', '.join(categories)}

Dokumententext:
{text[:2000]}

Antworte nur mit der Kategorie, nichts anderes. Falls unsicher, wähle 'Sonstiges'."""

    try:
        response = requests.post(
            CONFIG['LM_STUDIO_URL'],
            json={
                "model": "deepseek-r1",
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.1,
                "max_tokens": 50
            },
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            category = result['choices'][0]['message']['content'].strip()

            if category in categories:
                return category
            else:
                return 'Sonstiges'
        else:
            print(f"LM Studio Error: {response.status_code}")
            return 'Sonstiges'

    except Exception as e:
        print(f"Error calling LM Studio: {e}")
        return 'Sonstiges'

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

@app.route('/api/process-document', methods=['POST'])
def process_document():
    """Verarbeitet ein PDF: Preview + KI-Klassifizierung"""
    data = request.get_json()
    pdf_path = data.get('path')

    if not pdf_path or not os.path.exists(pdf_path):
        return jsonify({'error': 'PDF file not found'}), 404

    # Preview-Image generieren
    preview = pdf_to_preview_image(pdf_path)

    # Text extrahieren
    text = extract_text_from_pdf(pdf_path)

    # KI-Klassifizierung
    suggested_category = classify_document(text)

    # Vorgeschlagenen Pfad generieren
    filename = os.path.basename(pdf_path)
    suggested_path = os.path.join(CONFIG['SORTED_DIR'], suggested_category, filename)

    return jsonify({
        'preview': preview,
        'suggested_category': suggested_category,
        'suggested_path': suggested_path,
        'original_path': pdf_path
    })

@app.route('/api/move-document', methods=['POST'])
def move_document():
    """Führt den Move-Befehl aus"""
    data = request.get_json()
    source_path = data.get('source_path')
    target_path = data.get('target_path')

    if not source_path or not target_path:
        return jsonify({'error': 'Missing paths'}), 400

    if not os.path.exists(source_path):
        return jsonify({'error': 'Source file not found'}), 404

    try:
        # Zielverzeichnis erstellen falls nicht vorhanden
        target_dir = os.path.dirname(target_path)
        os.makedirs(target_dir, exist_ok=True)

        # Datei verschieben
        shutil.move(source_path, target_path)

        return jsonify({'success': True, 'message': f'File moved to {target_path}'})

    except Exception as e:
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
    return jsonify(tree)

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

if __name__ == '__main__':
    # Überprüfe ob Verzeichnisse existieren
    for dir_path in [CONFIG['SCAN_DIR'], CONFIG['SORTED_DIR']]:
        if not os.path.exists(dir_path):
            print(f"Warning: Directory {dir_path} does not exist")

    print("Starting Document Sorter...")
    print(f"Scan directory: {CONFIG['SCAN_DIR']}")
    print(f"Sorted directory: {CONFIG['SORTED_DIR']}")
    print(f"LM Studio URL: {CONFIG['LM_STUDIO_URL']}")

    app.run(debug=DEBUG_MODE, host=HOST, port=PORT)