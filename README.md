# Document Sorter

Eine intelligente Web-Anwendung zur automatischen Sortierung von PDF-Dokumenten mit lokaler KI-Unterstützung.

## Features

- 🤖 **KI-basierte Klassifizierung** von PDF-Dokumenten
- 📁 **Automatische Sortierung** in vordefinierte oder ähnliche Verzeichnisse
- 🖼️ **PDF-Vorschau** für bessere Kontrolle
- 📊 **Performance-Monitoring** (CPU/RAM-Nutzung)
- 🔄 **Hintergrund-Preprocessing** für bessere Performance
- 🎯 **Intelligente Pfadvorschläge** basierend auf Dateinamen
- 🌐 **Benutzerfreundliche Web-Oberfläche**

## Voraussetzungen

- Python 3.8+
- [LM Studio](https://lmstudio.ai/) mit einem laufenden Sprachmodell (z.B. DeepSeek R1)
- PDF-Dokumente zum Sortieren

## Installation

1. **Repository klonen:**
   ```bash\n   git clone https://github.com/yourusername/document-sorter.git\n   cd document-sorter\n   ```

2. **Virtual Environment erstellen:**
   ```bash\n   python -m venv venv\n   source venv/bin/activate  # Linux/Mac\n   # oder\n   venv\\Scripts\\activate     # Windows\n   ```

3. **Dependencies installieren:**
   ```bash\n   pip install -r requirements.txt\n   ```

4. **Konfiguration erstellen:**
   ```bash\n   cp .env.example .env\n   ```

5. **.env Datei anpassen:**
   Bearbeiten Sie die `.env` Datei und passen Sie die Pfade an Ihr System an:
   ```env\n   SCAN_DIR=/path/to/your/scanned/documents\n   SORTED_DIR=/path/to/your/sorted/documents\n   LM_STUDIO_URL=http://localhost:1234/v1/chat/completions\n   ```

## LM Studio Setup

1. **LM Studio installieren** von https://lmstudio.ai/
2. **Modell herunterladen** (empfohlen: DeepSeek R1 oder ähnlich)
3. **Server starten** in LM Studio auf Port 1234
4. **Modellname** in der `.env` Datei anpassen falls nötig

## Nutzung

1. **Anwendung starten:**
   ```bash\n   python app.py\n   ```

2. **Web-Interface öffnen:**\n   Öffnen Sie http://127.0.0.1:5001 in Ihrem Browser

3. **Dokumente sortieren:**
   - PDFs werden automatisch aus dem Scan-Verzeichnis geladen
   - KI analysiert den Inhalt und schlägt Kategorien vor
   - Review und bestätigen Sie die Vorschläge
   - Dokumente werden automatisch sortiert

## Konfiguration

### Environment Variables

| Variable | Beschreibung | Default |
|----------|-------------|---------|
| `SCAN_DIR` | Verzeichnis mit zu sortierenden PDFs | `./scanned_documents` |
| `SORTED_DIR` | Zielverzeichnis für sortierte Dokumente | `./sorted_documents` |
| `LM_STUDIO_URL` | LM Studio API URL | `http://localhost:1234/v1/chat/completions` |
| `LM_STUDIO_MODEL` | Name des LM Studio Modells | `deepseek-r1` |
| `PRELOAD_COUNT` | Anzahl vorab zu verarbeitender Dokumente | `10` |
| `DOCUMENT_CATEGORIES` | Verfügbare Kategorien (komma-getrennt) | `Steuern,Versicherungen,...` |

### Kategorien anpassen

Die Standard-Kategorien können in der `.env` Datei angepasst werden:
```env\nDOCUMENT_CATEGORIES=Kategorie1,Kategorie2,Kategorie3\n```

## Entwicklung

### Projekt-Struktur
```
document-sorter/\n├── app.py              # Haupt-Anwendung\n├── templates/          # HTML-Templates\n├── requirements.txt    # Python Dependencies\n├── .env.example       # Konfigurationsvorlage\n├── .gitignore         # Git Ignore Regeln\n└── README.md          # Diese Datei\n```

### Tests ausführen
```bash\n# Tests hier hinzufügen\npytest tests/\n```

### Code-Style
```bash\n# Formatierung mit black\nblack app.py\n\n# Linting mit flake8\nflake8 app.py\n```

## Troubleshooting

### Häufige Probleme

**Problem:** LM Studio Connection Error
- **Lösung:** Stellen Sie sicher, dass LM Studio läuft und ein Modell geladen ist

**Problem:** PDF-Verarbeitung schlägt fehl
- **Lösung:** Überprüfen Sie die PDF-Datei auf Beschädigungen

**Problem:** Verzeichnisse nicht gefunden
- **Lösung:** Erstellen Sie die in der `.env` angegebenen Verzeichnisse

### Performance-Optimierung

- Reduzieren Sie `PRELOAD_COUNT` bei langsamen Systemen
- Verwenden Sie SSDs für bessere I/O-Performance
- Schließen Sie andere ressourcenintensive Anwendungen

## Beitragen

1. Fork das Repository
2. Erstellen Sie einen Feature-Branch (`git checkout -b feature/AmazingFeature`)
3. Commit Ihre Änderungen (`git commit -m 'Add some AmazingFeature'`)
4. Push zum Branch (`git push origin feature/AmazingFeature`)
5. Erstellen Sie einen Pull Request

## Lizenz

Dieses Projekt steht unter der MIT-Lizenz. Siehe `LICENSE` Datei für Details.

## Danksagungen

- [PyMuPDF](https://pymupdf.readthedocs.io/) für PDF-Verarbeitung
- [Flask](https://flask.palletsprojects.com/) für das Web-Framework
- [LM Studio](https://lmstudio.ai/) für lokale KI-Integration