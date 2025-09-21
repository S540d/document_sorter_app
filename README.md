# Document Sorter

An intelligent web application for automatic PDF document sorting with local AI support.

## Features

- **AI-based classification** of PDF documents with smart fallback system
- **Intelligent file renaming** with automatic date extraction and standardized naming
- **Automatic sorting** into predefined or similar directories
- **PDF preview** for better control
- **Real-time system metrics** with live CPU, memory, and disk usage monitoring
- **Comprehensive monitoring** with logging, error reporting, and performance tracking
- **Modular architecture** with separate API blueprints
- **Intelligent path suggestions** based on filenames and existing directory structure
- **Smart category management** with enhanced blacklist filtering (including Scanbot artifacts)
- **RESTful API** for integration with other systems
- **User-friendly web interface** with real-time status updates

## Prerequisites

- Python 3.8+
- [LM Studio](https://lmstudio.ai/) with a running language model (e.g., DeepSeek R1)
- PDF documents to sort

## Installation

1. **Clone repository:**
   ```bash
   git clone https://github.com/yourusername/document-sorter.git
   cd document-sorter
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or
   venv\Scripts\activate     # Windows
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Create configuration:**
   ```bash
   cp .env.example .env
   ```

5. **Configure .env file:**
   Edit the `.env` file and adapt the paths to your system:
   ```env
   SCAN_DIR=/path/to/your/scanned/documents
   SORTED_DIR=/path/to/your/sorted/documents
   LM_STUDIO_URL=http://localhost:1234/v1/chat/completions
   ```

## LM Studio Setup

1. **Install LM Studio** from https://lmstudio.ai/
2. **Download model** (recommended: DeepSeek R1 or similar)
3. **Start server** in LM Studio on port 1234
4. **Adjust model name** in `.env` file if necessary

## Usage

1. **Start application:**
   ```bash
   python app.py
   ```

2. **Open web interface:**
   Open http://127.0.0.1:5001 in your browser

3. **Sort documents:**
   - PDFs are automatically loaded from the scan directory
   - AI analyzes content and suggests categories
   - **Intelligent file renaming** with automatic date extraction
   - Review and confirm suggestions with filename details
   - Documents are automatically sorted with optimized names

## Intelligent File Renaming

The application features an advanced file renaming system that automatically generates standardized, meaningful filenames:

### Features
- **📅 Date Extraction**: Automatically detects dates from document content using German date patterns
- **🧹 Clean Naming**: Removes scanner artifacts (Scanbot, "Gescanntes Dokument", etc.)
- **📊 Format Standardization**: Creates consistent `YYYY-MM-DD_category_description.pdf` format
- **🎯 Smart Date Selection**: Chooses the most recent past date from extracted content
- **💡 Visual Feedback**: Shows original vs suggested filename with extraction details

### Supported Date Formats
- `DD.MM.YYYY` and `DD/MM/YYYY` (German standard)
- `YYYY-MM-DD` (ISO format)
- `DD.MM.YY` and `DD/MM/YY` (short year)
- German month names: "15. März 2024", "10. Jan 2025"
- Month abbreviations: "Mär", "Apr", "Dez"

### Example Transformations
```
Original: "Scanbot_2024_03_15_document.pdf"
Suggested: "2024-03-15_finanzen_document.pdf"

Original: "Gescanntes Dokument 123.pdf"
Suggested: "2024-09-21_kategorie_dokument.pdf"
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SCAN_DIR` | Directory with PDFs to sort | `./scanned_documents` |
| `SORTED_DIR` | Target directory for sorted documents | `./sorted_documents` |
| `LM_STUDIO_URL` | LM Studio API URL | `http://localhost:1234/v1/chat/completions` |
| `LM_STUDIO_MODEL` | Name of LM Studio model | `deepseek-r1` |
| `PRELOAD_COUNT` | Number of documents to preprocess | `10` |
| `DOCUMENT_CATEGORIES` | Available categories (comma-separated) | `Taxes,Insurance,...` |

### Customize Categories

Default categories can be customized in the `.env` file:
```env
DOCUMENT_CATEGORIES=Category1,Category2,Category3
```

## Development

### Project Structure
```
document-sorter/
├── app.py                      # Main Flask application
├── main.py                     # Alternative entry point
├── config_secret.py            # Secret configuration
├── requirements.txt            # Python dependencies
├── .env.example               # Configuration template
├── app/                       # Main application package
│   ├── __init__.py
│   ├── settings.py            # Centralized configuration
│   ├── ai/                    # AI classification module
│   │   ├── __init__.py
│   │   ├── classifier.py      # Document classification logic
│   │   └── prompts.py         # AI prompt management
│   ├── api/                   # RESTful API blueprints
│   │   ├── __init__.py
│   │   ├── documents.py       # Document processing API
│   │   ├── directories.py     # Directory management API
│   │   └── monitoring.py      # Monitoring and logging API
│   ├── config/                # Configuration management
│   │   ├── __init__.py
│   │   └── config_manager.py
│   ├── directory/             # Directory and category management
│   │   ├── __init__.py
│   │   ├── categories.py      # Category management
│   │   └── manager.py         # Directory operations
│   ├── monitoring/            # Comprehensive monitoring system
│   │   ├── __init__.py
│   │   ├── logger.py          # Structured logging
│   │   ├── error_reporter.py  # Error tracking
│   │   ├── log_aggregator.py  # Log aggregation
│   │   └── performance_tracker.py # Performance metrics
│   ├── pdf/                   # PDF processing
│   │   ├── __init__.py
│   │   ├── processor.py       # Text extraction
│   │   └── preview.py         # Preview generation
│   └── services/              # Business services
│       ├── __init__.py
│       ├── file_renaming.py    # Intelligent file renaming with date extraction
│       ├── file_service.py
│       ├── llm_service.py
│       └── pdf_service.py
├── templates/                 # HTML templates
├── tests/                     # Test suite
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_app.py
│   ├── test_auth.py
│   ├── test_integration.py
│   ├── test_llm_service.py
│   ├── test_monitoring.py
│   └── test_pdf_service.py
├── .gitignore                 # Git ignore rules
└── README.md                  # This file
```

### Architecture Overview

The application follows a modular architecture with clear separation of concerns:

- **API Layer**: RESTful endpoints organized by functionality (documents, directories, monitoring)
- **Service Layer**: Business logic for file operations, LLM integration, and PDF processing
- **Data Layer**: Configuration management and directory structure handling
- **Monitoring Layer**: Comprehensive logging, error tracking, and performance monitoring

### Key Components

- **Smart AI Classification**: Automatic document categorization with intelligent fallback
- **Intelligent File Renaming**: Advanced filename generation with date extraction and artifact removal
- **Directory Management**: Dynamic category detection with enhanced blacklist filtering (Scanbot artifacts)
- **Real-time System Metrics**: Live CPU, memory, and disk usage monitoring with psutil integration
- **Performance Monitoring**: Comprehensive logging, error tracking, and system health monitoring
- **Modular Design**: Each module can be developed and tested independently

### API Endpoints

#### Document Processing
- `GET /api/scan-files` - List available PDF files
- `POST /api/process-document` - Process and classify a document (includes filename suggestions)
- `POST /api/move-document` - Move document to target directory
- `POST /api/suggest-filename` - Generate intelligent filename suggestions

#### Directory & System Management
- `GET /api/directory-structure` - Get current directory tree
- `GET /api/system-status` - Real-time system metrics and status

#### Monitoring & Performance
- `GET /api/monitoring/status` - System monitoring dashboard
- `GET /api/performance/current` - Current performance metrics

### Run Tests
```bash
pytest tests/ -v
# Run specific test modules
pytest tests/test_integration.py
pytest tests/test_monitoring.py
```

### Code Style
```bash
# Format with black
black app/ tests/

# Lint with flake8
flake8 app/ tests/
```

## Troubleshooting

### Common Issues

**Issue:** LM Studio Connection Error
- **Solution:** Ensure LM Studio is running and a model is loaded
- **Fallback:** Application uses smart keyword-based classification when AI is unavailable

**Issue:** PDF processing fails
- **Solution:** Check PDF file for corruption or unsupported format

**Issue:** Directories not found
- **Solution:** Create the directories specified in `.env` or let the app create them automatically

**Issue:** Subdirectories not showing
- **Solution:** Check API endpoint `/api/suggest-subdirs` and ensure categories exist

**Issue:** AI suggestions not appearing
- **Solution:** Verify LM Studio connection or check fallback classification system

### Performance Optimization

- Reduce `PRELOAD_COUNT` on slower systems
- Use SSDs for better I/O performance
- Close other resource-intensive applications

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Create a Pull Request

## License

This project is licensed under the MIT License. See `LICENSE` file for details.

## Acknowledgments

- [PyMuPDF](https://pymupdf.readthedocs.io/) for PDF processing
- [Flask](https://flask.palletsprojects.com/) for the web framework
- [LM Studio](https://lmstudio.ai/) for local AI integration