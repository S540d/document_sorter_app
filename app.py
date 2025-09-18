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
import threading
import time
import logging
import psutil  # Für CPU/RAM-Monitoring
import difflib
import re
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Konfiguration aus Environment Variables
def get_config():
    return {
        'LM_STUDIO_URL': os.getenv('LM_STUDIO_URL', 'http://localhost:1234/v1/chat/completions'),
        'LM_STUDIO_MODEL': os.getenv('LM_STUDIO_MODEL', 'deepseek-r1'),
        'SCAN_DIR': os.getenv('SCAN_DIR', './scanned_documents'),
        'SORTED_DIR': os.getenv('SORTED_DIR', './sorted_documents'),
        'FLASK_HOST': os.getenv('FLASK_HOST', '127.0.0.1'),
        'FLASK_PORT': int(os.getenv('FLASK_PORT', '5001')),
        'FLASK_DEBUG': os.getenv('FLASK_DEBUG', 'false').lower() == 'true',
        'PRELOAD_COUNT': int(os.getenv('PRELOAD_COUNT', '10')),
        'MAX_PAGES_TO_ANALYZE': int(os.getenv('MAX_PAGES_TO_ANALYZE', '3')),
        'AI_REQUEST_TIMEOUT': int(os.getenv('AI_REQUEST_TIMEOUT', '30')),
        'CATEGORIES': os.getenv('DOCUMENT_CATEGORIES',
            'Steuern,Versicherungen,Verträge,Banken,Medizin,Behörden,Dissertation,Notes,Arbeit,Schöffendienst,Fahrzeuge,Zeugnis,Lesekram,Studium,Wohnen,Sonstiges'
        ).split(','),
        'DIRECTORY_BLACKLIST': os.getenv('DIRECTORY_BLACKLIST',
            '.DS_Store,.git,node_modules,__pycache__,.vscode,venv,document_sorter_app,templates,.Trash'
        ).split(',')
    }

CONFIG = get_config()

# Cache für vorverarbeitete Dokumente
document_cache = {}
preload_complete = False

# Status-Tracking für Preloading
preload_status = {
    'total_documents': 0,
    'processed_documents': 0,
    'current_document': '',
    'is_running': False,
    'start_time': None
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
        
        # Maximal erste N Seiten für Performance
        for page_num in range(min(CONFIG['MAX_PAGES_TO_ANALYZE'], len(doc))):
            page = doc[page_num]
            text += page.get_text()
        
        doc.close()
        return text.strip()
    except Exception as e:
        print(f"Error extracting text: {e}")
        return ""

def classify_document(text):
    """Fragt DeepSeek R3 über LM Studio nach Dokumentenklassifizierung"""

    prompt = f"""Du bist ein Experte für Dokumentenklassifizierung.
Analysiere den folgenden Text und wähle die passendste Kategorie:

Verfügbare Kategorien: {', '.join(CONFIG['CATEGORIES'])}

Dokumententext:
{text[:2000]}  # Begrenzen auf 2000 Zeichen

Antworte nur mit der Kategorie, nichts anderes. Falls unsicher, wähle 'Sonstiges'."""

    try:
        response = requests.post(
            CONFIG['LM_STUDIO_URL'],
            json={
                "model": CONFIG['LM_STUDIO_MODEL'],
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.1,
                "max_tokens": 50
            },
            timeout=CONFIG['AI_REQUEST_TIMEOUT']
        )

        if response.status_code == 200:
            result = response.json()
            category = result['choices'][0]['message']['content'].strip()

            # Validierung: Ist die Antwort eine gültige Kategorie?
            if category in CONFIG['CATEGORIES']:
                return category
            else:
                return 'Sonstiges'
        else:
            print(f"LM Studio Error: {response.status_code}")
            return 'Sonstiges'

    except Exception as e:
        print(f"Error calling LM Studio: {e}")
        return 'Sonstiges'

def process_single_document(pdf_path):
    """Verarbeitet ein einzelnes PDF vollständig"""
    try:
        preview = pdf_to_preview_image(pdf_path)
        text = extract_text_from_pdf(pdf_path)
        suggested_category = classify_document(text)

        filename = os.path.basename(pdf_path)
        suggested_path = os.path.join(CONFIG['SORTED_DIR'], suggested_category, filename)

        return {
            'preview': preview,
            'extracted_text': text[:500],
            'suggested_category': suggested_category,
            'suggested_path': suggested_path,
            'original_path': pdf_path,
            'full_text': text
        }
    except Exception as e:
        print(f"Error processing {pdf_path}: {e}")
        return None

def preload_documents():
    """Lädt und verarbeitet die ersten N Dokumente sequenziell im Hintergrund"""
    global preload_complete, preload_status

    scan_dir = Path(CONFIG['SCAN_DIR'])
    if not scan_dir.exists():
        print(f"Scan directory {scan_dir} not found")
        return

    pdf_files = list(scan_dir.glob('*.pdf'))[:CONFIG['PRELOAD_COUNT']]

    # Status initialisieren
    preload_status.update({
        'total_documents': len(pdf_files),
        'processed_documents': 0,
        'is_running': True,
        'start_time': time.time()
    })

    print(f"Starting sequential preload of {len(pdf_files)} documents...")

    # Sequenzielle Verarbeitung (keine parallelen Threads)
    for i, pdf_file in enumerate(pdf_files):
        pdf_path = str(pdf_file)
        filename = os.path.basename(pdf_path)

        # Status aktualisieren
        preload_status['current_document'] = filename
        preload_status['processed_documents'] = i

        print(f"Processing {i+1}/{len(pdf_files)}: {filename}")

        try:
            result = process_single_document(pdf_path)
            if result:
                document_cache[pdf_path] = result
                print(f"✓ Preloaded: {filename}")
            else:
                print(f"✗ Failed: {filename}")
        except Exception as e:
            print(f"✗ Error preloading {filename}: {e}")

        # Kurze Pause zwischen Dokumenten für Ressourcenschonung
        time.sleep(0.5)

    preload_status.update({
        'is_running': False,
        'processed_documents': len(pdf_files),
        'current_document': ''
    })

    preload_complete = True
    elapsed = time.time() - preload_status['start_time']
    print(f"Preloading complete: {len(document_cache)} documents cached in {elapsed:.1f}s")

def get_directory_structure(base_path):
    """Erstellt eine Struktur aller Unterverzeichnisse mit Blacklist-Filterung"""
    structure = {}
    blacklist = CONFIG.get('DIRECTORY_BLACKLIST', [])

    try:
        base = Path(base_path)
        if not base.exists():
            return structure

        for item in base.rglob('*'):
            if item.is_dir():
                # Prüfe ob Verzeichnis oder ein übergeordnetes Verzeichnis auf der Blacklist steht
                rel_path = item.relative_to(base)
                parts = rel_path.parts

                # Überspringe wenn ein Teil des Pfads auf der Blacklist steht
                if any(part in blacklist for part in parts):
                    continue

                current = structure
                for part in parts:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
    except Exception as e:
        print(f"Error scanning directory structure: {e}")

    return structure

def calculate_similarity(text1, text2):
    """Berechnet Ähnlichkeit zwischen zwei Texten (0.0 - 1.0)"""
    # Normalisiere Texte
    text1 = text1.lower().strip()
    text2 = text2.lower().strip()

    # Entferne Sonderzeichen und Zahlen für bessere Vergleichbarkeit
    text1_clean = re.sub(r'[^\w\s]', '', text1)
    text2_clean = re.sub(r'[^\w\s]', '', text2)

    # Verwende difflib für Ähnlichkeitsvergleich
    similarity = difflib.SequenceMatcher(None, text1_clean, text2_clean).ratio()

    # Bonus für exakte Teilstring-Matches
    if text1_clean in text2_clean or text2_clean in text1_clean:
        similarity = min(1.0, similarity + 0.2)

    return similarity

def find_similar_paths(filename, directory_structure, base_path, threshold=0.3):
    """Findet ähnliche Pfade basierend auf Dateiname"""
    similar_paths = []

    # Extrahiere relevante Wörter aus Dateiname
    filename_base = os.path.splitext(filename)[0]
    filename_words = re.findall(r'\w+', filename_base.lower())

    def search_directories(structure, current_path, level=0):
        for dir_name, subdirs in structure.items():
            full_path = f"{current_path}/{dir_name}"

            # Berechne Ähnlichkeit
            similarity = calculate_similarity(filename_base, dir_name)

            # Prüfe auch auf Wort-Matches
            dir_words = re.findall(r'\w+', dir_name.lower())
            word_matches = len(set(filename_words) & set(dir_words))
            if word_matches > 0:
                similarity = max(similarity, word_matches / max(len(filename_words), len(dir_words)))

            if similarity >= threshold:
                similar_paths.append({
                    'path': full_path,
                    'directory': dir_name,
                    'similarity': similarity,
                    'level': level
                })

            # Rekursive Suche in Unterverzeichnissen
            if subdirs:
                search_directories(subdirs, full_path, level + 1)

    search_directories(directory_structure, base_path)

    # Sortiere nach Ähnlichkeit (absteigend)
    similar_paths.sort(key=lambda x: x['similarity'], reverse=True)

    return similar_paths[:10]  # Top 10 Ergebnisse

def suggest_path_combinations(similar_paths):
    """Schlägt Kombinationen von ähnlichen Pfaden vor"""
    combinations = []

    for i, path_a in enumerate(similar_paths):
        for path_b in similar_paths[i+1:]:
            # A + B Kombination
            combo_ab = {
                'path_a': path_a,
                'path_b': path_b,
                'combined_path_ab': f"{path_a['path']}/{path_b['directory']}",
                'combined_path_ba': f"{path_b['path']}/{path_a['directory']}",
                'combined_similarity': (path_a['similarity'] + path_b['similarity']) / 2
            }
            combinations.append(combo_ab)

    # Sortiere nach kombinierter Ähnlichkeit
    combinations.sort(key=lambda x: x['combined_similarity'], reverse=True)

    return combinations[:5]  # Top 5 Kombinationen

def get_system_stats():
    """Gibt aktuelle System-Statistiken zurück"""
    try:
        # CPU-Auslastung (über 1 Sekunde gemessen)
        cpu_percent = psutil.cpu_percent(interval=1)

        # RAM-Info
        memory = psutil.virtual_memory()
        ram_used_gb = memory.used / (1024**3)
        ram_total_gb = memory.total / (1024**3)
        ram_percent = memory.percent

        # Swap-Info (kritisch!)
        swap = psutil.swap_memory()
        swap_used_gb = swap.used / (1024**3)
        swap_percent = swap.percent

        return {
            'cpu_percent': round(cpu_percent, 1),
            'ram_used_gb': round(ram_used_gb, 2),
            'ram_total_gb': round(ram_total_gb, 2),
            'ram_percent': round(ram_percent, 1),
            'swap_used_gb': round(swap_used_gb, 2),
            'swap_percent': round(swap_percent, 1),
            'swap_warning': swap_percent > 1.0  # Warnung wenn Swap verwendet wird
        }
    except Exception as e:
        print(f"Error getting system stats: {e}")
        return {
            'cpu_percent': 0,
            'ram_used_gb': 0,
            'ram_total_gb': 16,
            'ram_percent': 0,
            'swap_used_gb': 0,
            'swap_percent': 0,
            'swap_warning': False
        }

@app.route('/')
def index():
    """Hauptseite der Webapp"""
    return render_template('index.html', categories=CONFIG['CATEGORIES'])

@app.route('/api/scan-files')
def scan_files():
    """Scannt das Eingangverzeichnis nach PDFs"""
    scan_dir = Path(CONFIG['SCAN_DIR'])

    if not scan_dir.exists():
        return jsonify({'error': 'Scan directory not found'}), 404

    pdf_files = []
    for pdf_file in scan_dir.glob('*.pdf'):
        file_path = str(pdf_file)
        file_info = {
            'name': pdf_file.name,
            'path': file_path,
            'size': pdf_file.stat().st_size,
            'modified': datetime.fromtimestamp(pdf_file.stat().st_mtime).isoformat(),
            'preloaded': file_path in document_cache
        }

        # Falls bereits vorverarbeitet, füge Kategorie hinzu
        if file_path in document_cache:
            file_info['suggested_category'] = document_cache[file_path]['suggested_category']

        pdf_files.append(file_info)

    return jsonify({
        'files': pdf_files,
        'preload_complete': preload_complete,
        'cached_count': len(document_cache),
        'preload_status': preload_status,
        'system_stats': get_system_stats()
    })

@app.route('/api/directory-structure')
def directory_structure():
    """Gibt die Verzeichnisstruktur des Zielordners zurück"""
    structure = get_directory_structure(CONFIG['SORTED_DIR'])
    return jsonify({
        'structure': structure,
        'base_path': CONFIG['SORTED_DIR'],
        'categories': CONFIG['CATEGORIES']
    })

@app.route('/api/system-status')
def system_status():
    """Gibt aktuellen System- und Preload-Status zurück"""
    return jsonify({
        'preload_status': preload_status,
        'system_stats': get_system_stats(),
        'preload_complete': preload_complete,
        'cached_count': len(document_cache)
    })

@app.route('/api/process-document', methods=['POST'])
def process_document():
    """Verarbeitet ein PDF: Preview + KI-Klassifizierung"""
    data = request.get_json()
    pdf_path = data.get('path')

    if not pdf_path or not os.path.exists(pdf_path):
        return jsonify({'error': 'PDF file not found'}), 404

    # Prüfen ob bereits im Cache
    if pdf_path in document_cache:
        print(f"Serving from cache: {os.path.basename(pdf_path)}")
        return jsonify(document_cache[pdf_path])

    # Falls nicht im Cache, verarbeiten
    result = process_single_document(pdf_path)
    if result:
        # Ins Cache einfügen für künftige Anfragen
        document_cache[pdf_path] = result
        return jsonify(result)
    else:
        return jsonify({'error': 'Failed to process document'}), 500

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

@app.route('/api/suggest-similar-paths', methods=['POST'])
def suggest_similar_paths():
    """Findet ähnliche Pfade basierend auf Dateiname"""
    data = request.get_json()
    filename = data.get('filename')

    if not filename:
        return jsonify({'error': 'Filename required'}), 400

    try:
        # Lade Verzeichnisstruktur
        structure = get_directory_structure(CONFIG['SORTED_DIR'])

        # Finde ähnliche Pfade
        similar_paths = find_similar_paths(filename, structure, CONFIG['SORTED_DIR'])

        # Erstelle Kombinationsvorschläge
        combinations = suggest_path_combinations(similar_paths)

        return jsonify({
            'filename': filename,
            'similar_paths': similar_paths,
            'combinations': combinations,
            'base_path': CONFIG['SORTED_DIR']
        })

    except Exception as e:
        return jsonify({'error': f'Similarity search failed: {str(e)}'}), 500

@app.route('/path-management')
def path_management():
    """Pfad-Management Unterseite"""
    return render_template('path_management.html', categories=CONFIG['CATEGORIES'])

if __name__ == '__main__':
    # Überprüfe ob Verzeichnisse existieren
    for dir_path in [CONFIG['SCAN_DIR'], CONFIG['SORTED_DIR']]:
        if not os.path.exists(dir_path):
            print(f"Warning: Directory {dir_path} does not exist")

    print("Starting Document Sorter...")
    print(f"Scan directory: {CONFIG['SCAN_DIR']}")
    print(f"Sorted directory: {CONFIG['SORTED_DIR']}")
    print(f"LM Studio URL: {CONFIG['LM_STUDIO_URL']}")
    print(f"Model: {CONFIG['LM_STUDIO_MODEL']}")

    # Validate required directories
    if not os.path.exists(CONFIG['SCAN_DIR']):
        print(f"ERROR: SCAN_DIR '{CONFIG['SCAN_DIR']}' does not exist!")
        print("Please check your .env file and create the directory.")
        exit(1)

    if not os.path.exists(CONFIG['SORTED_DIR']):
        print(f"ERROR: SORTED_DIR '{CONFIG['SORTED_DIR']}' does not exist!")
        print("Please check your .env file and create the directory.")
        exit(1)

    # Starte Preloading im Hintergrund
    preload_thread = threading.Thread(target=preload_documents, daemon=True)
    preload_thread.start()
    print(f"Starting background preload of first {CONFIG['PRELOAD_COUNT']} documents...")

    app.run(debug=CONFIG['FLASK_DEBUG'], host=CONFIG['FLASK_HOST'], port=CONFIG['FLASK_PORT'])
