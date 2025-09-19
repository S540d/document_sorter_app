"""
Document Sorter App - Hauptanwendung
Integriert alle Services und stellt die Web-Oberfläche bereit

TODO: Zukünftige Verbesserungen und Features

1. Performance-Optimierungen:
   - Async/Await für LLM-Anfragen implementieren
   - Caching für häufig verwendete Kategorien
   - Batch-Verarbeitung für multiple Dokumente

2. Sicherheit:
   - Authentifizierung hinzufügen
   - Rate Limiting für API-Endpunkte
   - Input Validation verstärken
   - CSRF-Schutz implementieren

3. Benutzerfreundlichkeit:
   - Drag & Drop Upload
   - Vorschau für PDF-Dokumente
   - Fortschrittsanzeige bei Verarbeitung
   - Bulk-Aktionen für mehrere Dokumente
   - Undo/Redo Funktionalität

4. Kategorieverwaltung:
   - Hierarchische Kategorien
   - Kategorie-Tags
   - Automatische Kategorie-Vorschläge
   - Kategorie-Statistiken

5. LLM-Verbesserungen:
   - Kontext-Lernen aus Benutzeraktionen
   - Alternative LLM-Provider
   - Offline-Fallback
   - Konfidenz-Score für Klassifizierung

6. Dateimanagement:
   - Weitere Dateitypen unterstützen
   - Automatische OCR für Scans
   - Metadaten-Extraktion
   - Versionierung von Dokumenten

7. Integration:
   - REST API für externe Systeme
   - WebDAV/SMB Unterstützung
   - Email-Import
   - Cloud-Storage Anbindung

8. Monitoring:
   - Logging verbessern
   - Metriken sammeln
   - Error-Reporting
   - Performance-Monitoring

9. Tests:
   - Unit Tests erweitern
   - Integration Tests
   - End-to-End Tests
   - Performance Tests
"""
from flask import Flask, render_template, request, jsonify
from pathlib import Path

from app.config.config_manager import ConfigManager
from app.services.file_service import FileService
from app.services.llm_service import LLMService

# Flask App initialisieren
app = Flask(__name__)

# Services initialisieren
config = ConfigManager()
file_service = FileService()
llm_service = LLMService()

# Verzeichnisse sicherstellen
config.ensure_directories()

@app.route('/')
def index():
    """Hauptseite mit Dokumentenliste"""
    pdf_files = file_service.scan_directory()
    categories = file_service.get_categories()
    return render_template(
        'index.html',
        pdf_files=[p.name for p in pdf_files],
        categories=categories
    )

@app.route('/path_management')
def path_management():
    """Pfadverwaltungsseite"""
    return render_template(
        'path_management.html',
        scan_dir=config.get('SCAN_DIR'),
        sorted_dir=config.get('SORTED_DIR')
    )

@app.route('/classify', methods=['POST'])
def classify_document():
    """Endpunkt für die Dokumentklassifizierung"""
    filename = request.json.get('filename')
    if not filename:
        return jsonify({'error': 'Kein Dateiname angegeben'}), 400
        
    scan_dir = config.get_path('SCAN_DIR')
    file_path = scan_dir / filename
    
    # Kategorie vom LLM ermitteln
    category = llm_service.get_document_category(file_path)
    if not category:
        return jsonify({'error': 'Fehler bei der Klassifizierung'}), 500
        
    # Datei verschieben
    success, message = file_service.move_file(file_path, category)
    if not success:
        return jsonify({'error': message}), 500
        
    return jsonify({
        'success': True,
        'message': message,
        'category': category
    })

@app.route('/create_category', methods=['POST'])
def create_category():
    """Endpunkt zum Erstellen einer neuen Kategorie"""
    category = request.json.get('category', '').strip().lower()
    if not category:
        return jsonify({'error': 'Keine Kategorie angegeben'}), 400
        
    success, message = file_service.create_category(category)
    if not success:
        return jsonify({'error': message}), 500
        
    return jsonify({
        'success': True,
        'message': message,
        'category': category
    })

@app.route('/update_paths', methods=['POST'])
def update_paths():
    """Endpunkt zum Aktualisieren der Verzeichnispfade"""
    scan_dir = request.json.get('scan_dir')
    sorted_dir = request.json.get('sorted_dir')
    
    if scan_dir:
        config.set('SCAN_DIR', scan_dir)
    if sorted_dir:
        config.set('SORTED_DIR', sorted_dir)
        
    # Verzeichnisse anlegen falls nötig
    config.ensure_directories()
    
    return jsonify({
        'success': True,
        'scan_dir': config.get('SCAN_DIR'),
        'sorted_dir': config.get('SORTED_DIR')
    })

if __name__ == '__main__':
    app.run(
        host=config.get('HOST'),
        port=config.get('PORT'),
        debug=config.get('DEBUG_MODE')
    )