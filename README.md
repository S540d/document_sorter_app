# Document Sorter

An intelligent web application for automatic PDF document sorting with local AI support, featuring advanced workflow automation, batch processing, and production-ready deployment capabilities.

## Features

### 🤖 **AI-Powered Processing**
- **Template-based document recognition** with 6 built-in templates (invoices, contracts, bank statements, etc.)
- **AI-enhanced classification** with smart fallback systems
- **Workflow automation** with rule-based processing
- **Confidence scoring** and metadata extraction
- **Intelligent file renaming** with automatic date extraction and standardized naming

### ⚡ **Advanced Workflow System**
- **Batch processing** with multi-threaded workers and persistent state
- **Rule-based automation** with customizable conditions and actions
- **Template recognition** for automatic document type detection
- **Real-time progress tracking** with detailed job status
- **Queue management** with priority handling

### 🏭 **Production-Ready Features**
- **Comprehensive error handling** with global handlers and recovery mechanisms
- **Performance monitoring** with rate limiting and security middleware
- **Health checks** for service monitoring (`/api/monitoring/health`)
- **Configuration management** with environment variable support
- **Docker containerization** (optional) with multi-stage builds
- **Security features** including request validation and rate limiting

### 📊 **Monitoring & Analytics**
- **Real-time system metrics** with live CPU, memory, and disk usage monitoring
- **Performance tracking** with response time analysis and alerts
- **Error reporting** with structured logging and tracking IDs
- **Dashboard interface** with comprehensive overview
- **Export capabilities** for metrics and reports

### 🌐 **User Interface**
- **3-column workflow** with files, intelligent processing, and manual controls
- **Interactive web interface** with real-time status updates
- **Workflow management** for rule creation and testing
- **Batch processing interface** with progress visualization
- **Template management** for document type configuration

## Quick Start

### Prerequisites
- Python 3.8+
- [LM Studio](https://lmstudio.ai/) with a running language model (e.g., DeepSeek R1)
- PDF documents to sort

### Installation

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

4. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env file with your paths and settings
   ```

### Running the Application

**Development Mode:**
```bash
python app.py
```

**Production Mode:**
```bash
# With Gunicorn (recommended for production)
gunicorn --bind 0.0.0.0:5000 --workers 4 --timeout 120 app:app

# Or with environment configuration
FLASK_ENV=production python app.py
```

**Docker (Optional):**
```bash
# Development
docker-compose --profile dev up

# Production
docker-compose up -d
```

### Access the Application
- **Main Interface**: http://localhost:5000
- **Health Check**: http://localhost:5000/api/monitoring/health
- **Batch Processing**: http://localhost:5000/batch
- **Workflow Management**: http://localhost:5000/workflows
- **Templates**: http://localhost:5000/templates

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SCAN_DIR` | `./scanned_documents` | Directory containing PDFs to sort |
| `SORTED_DIR` | `./sorted_documents` | Target directory for sorted documents |
| `LM_STUDIO_URL` | `http://localhost:1234` | LM Studio API URL |
| `FLASK_ENV` | `development` | Environment mode (development/production) |
| `FLASK_DEBUG` | `true` | Debug mode |
| `WORKERS` | `4` | Number of Gunicorn workers |
| `MAX_FILE_SIZE_MB` | `50` | Maximum upload file size |
| `RATE_LIMIT_PER_MINUTE` | `60` | Rate limit per IP address |
| `LOG_LEVEL` | `INFO` | Logging level |
| `PERFORMANCE_TRACKING` | `true` | Enable performance monitoring |

### Production Configuration Example

```bash
# .env for production
FLASK_ENV=production
FLASK_DEBUG=false
WORKERS=8
SCAN_DIR=/data/documents/scan
SORTED_DIR=/data/documents/sorted
LM_STUDIO_URL=http://ai-service:1234
MAX_FILE_SIZE_MB=100
RATE_LIMIT_PER_MINUTE=120
LOG_LEVEL=WARNING
PERFORMANCE_TRACKING=true
ERROR_REPORTING=true
```

## Usage Guide

### 1. Document Processing Workflow

#### 📂 **Files Column (Left)**
- Automatically loads PDFs from scan directory
- Shows file metadata and preview
- Click to analyze documents

#### 🤖 **Intelligent Column (Center)**
- **AI-powered workflow** with template recognition
- **Smart filename suggestions** with date extraction
- **Category predictions** with confidence scores
- **One-click processing** with "Execute AI Workflow"
- **Rule-based automation** for consistent processing

#### ⚙️ **Manual Column (Right)**
- **Traditional category selection** with directory tree
- **Custom filename editing** and path control
- **Fallback option** when AI suggestions need adjustment

### 2. Workflow Management

Create custom rules for automatic document processing:

```json
{
  "conditions": {
    "document_type": ["invoice"],
    "min_template_confidence": 0.8
  },
  "actions": [
    {
      "type": "force_category",
      "category": "Finance/Invoices"
    }
  ]
}
```

### 3. Batch Processing

Process multiple documents automatically:
- Queue documents for batch processing
- Monitor progress in real-time
- View detailed processing results
- Handle errors and retries automatically

### 4. Template System

Built-in document templates:
- **Invoices**: Detects invoice patterns and amounts
- **Contracts**: Identifies contract terms and parties
- **Bank Statements**: Recognizes financial transactions
- **Tax Documents**: Finds tax-related information
- **Insurance**: Detects policy and claim documents
- **Letters**: General correspondence recognition

## API Reference

### Document Processing
- `GET /api/scan-files` - List available PDF files
- `POST /api/process-document` - Process and classify document
- `POST /api/move-document` - Move document to target directory
- `POST /api/suggest-filename` - Generate filename suggestions

### Workflow Management
- `GET /api/workflows/rules` - List workflow rules
- `POST /api/workflows/rules` - Create new workflow rule
- `POST /api/workflows/process` - Process document with workflows
- `POST /api/workflows/test` - Test workflow rules

### Batch Processing
- `POST /api/batch/create` - Create batch operation
- `GET /api/batch/operations` - List batch operations
- `GET /api/batch/operations/{id}` - Get operation status
- `POST /api/batch/operations/{id}/start` - Start batch operation

### Monitoring & Health
- `GET /api/monitoring/health` - Health check endpoint
- `GET /api/monitoring/status` - System status
- `GET /api/performance/current` - Current performance metrics
- `GET /api/performance/middleware` - Middleware performance
- `GET /api/security/rate-limits` - Rate limiting status

## Advanced Features

### Intelligent File Renaming

Automatically generates standardized, meaningful filenames:

- **📅 Date Extraction**: Detects dates from document content
- **🧹 Clean Naming**: Removes scanner artifacts (Scanbot, etc.)
- **📊 Format Standardization**: Creates consistent `YYYY-MM-DD_description.pdf` format
- **🎯 Smart Date Selection**: Chooses most relevant date
- **🏷️ Title Recognition**: Intelligent document title extraction

**Example Transformations:**
```
Original: "Scanbot_2024_03_15_document.pdf"
Result: "2024-03-15_document.pdf"

Original: "Gescanntes Dokument 123.pdf" (with "Invoice" detected)
Result: "2024-09-21_invoice.pdf"
```

### Security Features

- **Rate Limiting**: Per-IP request throttling with token bucket algorithm
- **Request Validation**: File size limits and path traversal protection
- **Security Headers**: CSRF, XSS, and content-type protection
- **Error Tracking**: Comprehensive error logging with unique IDs
- **Health Monitoring**: Real-time service health checks

### Performance Optimization

- **Multi-threaded Processing**: Parallel document processing
- **Middleware Monitoring**: Request/response time tracking
- **Resource Management**: Memory and CPU usage optimization
- **Caching**: Intelligent caching of processing results
- **Cleanup**: Automatic cleanup of old data and logs

## Architecture

### Project Structure
```
document-sorter/
├── app.py                          # Main Flask application
├── requirements.txt                # Python dependencies
├── PRODUCTION.md                   # Production deployment guide
├── app/                           # Main application package
│   ├── ai/                        # AI and template processing
│   │   ├── classifier.py          # Document classification
│   │   ├── document_templates.py  # Template recognition engine
│   │   └── prompts.py             # AI prompt management
│   ├── api/                       # RESTful API blueprints
│   │   ├── batch.py              # Batch processing API
│   │   ├── documents.py          # Document processing API
│   │   ├── monitoring.py         # Monitoring and health API
│   │   ├── templates.py          # Template management API
│   │   └── workflows.py          # Workflow management API
│   ├── services/                  # Business services
│   │   ├── batch_processor.py    # Batch processing engine
│   │   ├── file_renaming.py      # Intelligent file renaming
│   │   └── workflow_engine.py    # Workflow automation engine
│   ├── monitoring/               # Monitoring and logging
│   │   ├── logger.py            # Structured logging
│   │   ├── error_reporter.py    # Error tracking
│   │   └── performance_tracker.py # Performance metrics
│   ├── production_config.py      # Production configuration
│   ├── error_handlers.py         # Global error handling
│   └── middleware.py             # Security and performance middleware
├── templates/                     # HTML templates
├── tests/                        # Test suite
│   ├── test_production_features.py # Production feature tests
│   └── ...                      # Other test modules
├── Dockerfile                    # Docker configuration (optional)
├── docker-compose.yml           # Docker Compose setup (optional)
└── .dockerignore                # Docker ignore rules (optional)
```

### Key Components

- **Template Engine**: Document type recognition with pattern matching
- **Workflow Engine**: Rule-based automation with condition evaluation
- **Batch Processor**: Multi-threaded document processing with state persistence
- **Monitoring System**: Comprehensive logging, metrics, and health checks
- **Security Middleware**: Rate limiting, validation, and protection features

## Testing

Run the test suite:
```bash
# All tests
pytest tests/ -v

# Production features
pytest tests/test_production_features.py -v

# With coverage
pytest tests/ --cov=app --cov-report=html

# Specific test modules
pytest tests/test_integration.py
pytest tests/test_monitoring.py
```

## Deployment

### Production Deployment

See [PRODUCTION.md](PRODUCTION.md) for comprehensive production deployment guide including:
- Docker containerization
- Environment configuration
- Security considerations
- Monitoring setup
- Performance optimization
- Troubleshooting guide

### Quick Production Setup

```bash
# Install production dependencies
pip install gunicorn

# Set production environment
export FLASK_ENV=production
export WORKERS=4

# Start with Gunicorn
gunicorn --bind 0.0.0.0:5000 --workers 4 --timeout 120 app:app
```

## Monitoring & Maintenance

### Health Checks
```bash
# Basic health check
curl http://localhost:5000/api/monitoring/health

# Performance metrics
curl http://localhost:5000/api/performance/current

# System status
curl http://localhost:5000/api/monitoring/status
```

### Log Management
- Structured JSON logging
- Automatic log rotation
- Error tracking with unique IDs
- Performance metrics collection
- Export capabilities for analysis

## Troubleshooting

### Common Issues

**LM Studio Connection Error**
- Ensure LM Studio is running with a loaded model
- Check LM_STUDIO_URL configuration
- Application has fallback classification system

**High CPU/Memory Usage**
- Reduce number of workers
- Check batch processing queue size
- Monitor performance metrics at `/api/performance/current`

**Rate Limiting Issues**
- Check current rate limits at `/api/security/rate-limits`
- Adjust RATE_LIMIT_PER_MINUTE in configuration
- Monitor for unusual traffic patterns

**Document Processing Failures**
- Check PDF file integrity
- Verify file permissions
- Review error logs and tracking IDs

### Performance Optimization

- Use SSD storage for better I/O performance
- Adjust worker count based on CPU cores
- Monitor system resources with built-in metrics
- Configure appropriate rate limits for your use case

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
- [Gunicorn](https://gunicorn.org/) for production WSGI server