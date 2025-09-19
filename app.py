#!/usr/bin/env python3#!/usr/bin/env python3

""""""

Document Sorter MVPDocument Sorter MVP

Webapp für automatische Dokumentensortierung mit DeepSeek R3Webapp für automatische Dokumentensortierung mit DeepSeek R3

""""""



import osimport os

from flask import Flask, render_template, request, jsonifyfrom flask import Flask, render_template, request, jsonify



from app.config import ConfigManagerfrom app.config import ConfigManager

from app.services import PDFService, FileService, LLMServicefrom app.services import PDFService, FileService, LLMService



# Konfiguration und Services initialisierentry:

config = ConfigManager()    from config_secret import LM_STUDIO_URL, SCAN_DIR, SORTED_DIR, DEBUG_MODE, PORT, HOST

pdf_service = PDFService()except ImportError:

file_service = FileService()    print("Warning: config.secret.py nicht gefunden. Verwende Standardwerte.")

llm_service = LLMService()    LM_STUDIO_URL = 'http://localhost:1234/v1/chat/completions'

    SCAN_DIR = './scans'

# Flask App initialisieren    SORTED_DIR = './sorted'

app = Flask(__name__)    DEBUG_MODE = True

    PORT = 5000

@app.route('/')    HOST = '127.0.0.1'

def index():

    """Hauptseite der Webapp"""

    categories = file_service.get_smart_categories()app = Flask(__name__)

    return render_template('index.html', categories=categories)

# API: Unterverzeichnisse zu Kategorie vorschlagen

@app.route('/api/scan-files')@app.route('/api/suggest-subdirs', methods=['POST'])

def scan_files():def suggest_subdirs():

    """Scannt das Eingangverzeichnis nach PDFs"""    data = request.get_json()

    files = file_service.scan_directory()    category = data.get('category', '')

        if not category:

    return jsonify({        return jsonify({'error': 'Keine Kategorie angegeben'}), 400

        'files': files,

        'system_stats': {    # Suche Unterverzeichnisse in der Kategorie

            'cpu_percent': 0,    base_path = os.path.join(CONFIG['SORTED_DIR'], category)

            'memory_percent': 0,    subdirs = []

            'disk_usage': 0    if os.path.exists(base_path):

        },        for item in os.listdir(base_path):

        'preload_status': {            item_path = os.path.join(base_path, item)

            'is_running': False,            if os.path.isdir(item_path) and item not in CONFIG['BLACKLIST_DIRS']:

            'processed_documents': 0,                subdirs.append(item)

            'total_documents': 0,

            'current_document': ''    return jsonify({'subdirs': subdirs})

        },

        'cached_count': len(files)# Konfiguration

    })CONFIG = {

    'LM_STUDIO_URL': LM_STUDIO_URL,

@app.route('/api/random-document')    'SCAN_DIR': SCAN_DIR,

def get_random_document():    'SORTED_DIR': SORTED_DIR,

    """Wählt ein zufälliges PDF aus dem Scan-Verzeichnis"""    'BLACKLIST_DIRS': [

    doc = file_service.get_random_document()        '.SynologyWorkingDirectory',

    if not doc:        '#SynoRecycle',

        return jsonify({'error': 'No PDF files found'}), 404        'diss',

    return jsonify(doc)        'geschenke für andere',

        '21_gifs',

@app.route('/api/process-document', methods=['POST'])        '.DS_Store',

def process_document():        '__pycache__',

    """Verarbeitet ein PDF: Preview + KI-Klassifizierung"""        '.git',

    data = request.get_json()        'node_modules'

    pdf_path = data.get('path')    ]

    }

    if not pdf_path or not os.path.exists(pdf_path):

        return jsonify({'error': 'PDF file not found'}), 404def pdf_to_preview_image(pdf_path):

            """Konvertiert erste Seite eines PDFs zu Base64-String für Preview"""

    # Preview-Image generieren    try:

    preview = pdf_service.create_preview(pdf_path)        doc = fitz.open(pdf_path)

            page = doc[0]

    # Text extrahieren

    text = pdf_service.extract_text(pdf_path)        # Render als PNG mit 150 DPI

            mat = fitz.Matrix(1.5, 1.5)

    # KI-Klassifizierung        pix = page.get_pixmap(matrix=mat)

    categories = file_service.get_smart_categories()        img_data = pix.tobytes("png")

    suggested_category = llm_service.classify_document(text, categories)

            # Base64 encoding für HTML-Anzeige

    # Vorgeschlagenen Pfad generieren        img_b64 = base64.b64encode(img_data).decode()

    filename = os.path.basename(pdf_path)        doc.close()

    suggested_path = os.path.join(

        config.get('SORTED_DIR'),        return f"data:image/png;base64,{img_b64}"

        suggested_category,    except Exception as e:

        filename        print(f"Error creating preview: {e}")

    )        return None

    

    return jsonify({def extract_text_from_pdf(pdf_path):

        'preview': preview,    """Extrahiert Text aus PDF für KI-Analyse"""

        'suggested_category': suggested_category,    try:

        'suggested_path': suggested_path,        doc = fitz.open(pdf_path)

        'original_path': pdf_path        text = ""

    })

        # Maximal erste 3 Seiten für Performance

@app.route('/api/move-document', methods=['POST'])        for page_num in range(min(3, len(doc))):

def move_document():            page = doc[page_num]

    """Führt den Move-Befehl aus"""            text += page.get_text()

    data = request.get_json()

    source_path = data.get('source_path')        doc.close()

    target_path = data.get('target_path')        return text.strip()

        except Exception as e:

    if not source_path or not target_path:        print(f"Error extracting text: {e}")

        return jsonify({'error': 'Missing paths'}), 400        return ""

        

    if not os.path.exists(source_path):def get_smart_categories():

        return jsonify({'error': 'Source file not found'}), 404    """Generiert intelligente Kategorien basierend auf Documents-Struktur"""

            sorted_dir = Path(CONFIG['SORTED_DIR'])

    success = file_service.move_document(source_path, target_path)    categories = []

    

    if success:    if sorted_dir.exists():

        return jsonify({        for item in sorted_dir.iterdir():

            'success': True,            if item.is_dir() and item.name not in CONFIG['BLACKLIST_DIRS']:

            'message': f'File moved to {target_path}'                categories.append(item.name)

        })

    else:    # Fallback-Kategorien falls Documents leer ist

        return jsonify({    if not categories:

            'error': 'Move operation failed'        categories = ['Steuern', 'Versicherungen', 'Verträge', 'Banken', 'Medizin', 'Behörden', 'Sonstiges']

        }), 500

    return sorted(categories)

@app.route('/api/system-status')

def system_status():def get_directory_tree(base_path, max_depth=3, current_depth=0):

    """Systemstatus für Frontend"""    """Erstellt Verzeichnisbaum mit Blacklist-Filter"""

    scan_dir = config.get_path('SCAN_DIR')    if current_depth >= max_depth:

    sorted_dir = config.get_path('SORTED_DIR')        return {}

    

    return jsonify({    tree = {}

        'scan_dir_exists': scan_dir.exists(),    base = Path(base_path)

        'sorted_dir_exists': sorted_dir.exists(),

        'lm_studio_url': config.get('LM_STUDIO_URL'),    if not base.exists():

        'preload_status': {'is_running': False},        return tree

        'preload_complete': True,

        'system_stats': {    for item in base.iterdir():

            'cpu_percent': 0,        if item.is_dir() and item.name not in CONFIG['BLACKLIST_DIRS']:

            'memory_percent': 0,            subtree = get_directory_tree(item, max_depth, current_depth + 1)

            'disk_usage': 0            tree[item.name] = {

        }                'path': str(item),

    })                'children': subtree,

                'has_children': bool(subtree)

@app.route('/api/directory-structure')            }

def directory_structure():

    """Verzeichnisstruktur für Frontend mit Blacklist-Filter"""    return tree

    tree = file_service.get_directory_tree(

        config.get_path('SORTED_DIR')def classify_document(text):

    )    """Fragt DeepSeek R3 über LM Studio nach Dokumentenklassifizierung"""

    return jsonify(tree)    categories = get_smart_categories()



@app.route('/api/suggest-alternative-paths', methods=['POST'])    prompt = f"""Du bist ein Experte für Dokumentenklassifizierung.

def suggest_alternative_paths():Analysiere den folgenden Text und wähle die passendste Kategorie:

    """Schlägt alternative Zielpfade vor"""

    data = request.get_json()Verfügbare Kategorien: {', '.join(categories)}

    filename = data.get('filename', '')

    Dokumententext:

    if not filename:{text[:2000]}

        return jsonify({'error': 'No filename provided'}), 400

        Antworte nur mit der Kategorie, nichts anderes. Falls unsicher, wähle 'Sonstiges'."""

    # Intelligente Pfadvorschläge basierend auf existierenden Verzeichnissen

    suggestions = []    try:

    categories = file_service.get_smart_categories()        response = requests.post(

                CONFIG['LM_STUDIO_URL'],

    for category in categories[:5]:  # Nur Top 5 für bessere UX            json={

        category_path = os.path.join(                "model": "deepseek-r1",

            config.get('SORTED_DIR'),                "messages": [

            category,                    {"role": "user", "content": prompt}

            filename                ],

        )                "temperature": 0.1,

        suggestions.append({                "max_tokens": 50

            'path': category_path,            },

            'category': category,            timeout=30

            'confidence': 0.7 if category != 'Sonstiges' else 0.3        )

        })

                if response.status_code == 200:

    return jsonify({'suggestions': suggestions})            result = response.json()

            category = result['choices'][0]['message']['content'].strip()

if __name__ == '__main__':

    # Verzeichnisse erstellen falls nicht vorhanden            if category in categories:

    config.ensure_directories()                return category

                else:

    print("Starting Document Sorter...")                return 'Sonstiges'

    print(f"Scan directory: {config.get('SCAN_DIR')}")        else:

    print(f"Sorted directory: {config.get('SORTED_DIR')}")            print(f"LM Studio Error: {response.status_code}")

    print(f"LM Studio URL: {config.get('LM_STUDIO_URL')}")            return 'Sonstiges'

    

    app.run(    except Exception as e:

        debug=config.get('DEBUG_MODE'),        print(f"Error calling LM Studio: {e}")

        host=config.get('HOST'),        return 'Sonstiges'

        port=config.get('PORT')

    )@app.route('/')
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