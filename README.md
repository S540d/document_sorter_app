# Document Sorter

An intelligent web application for automatic PDF document sorting with local AI support.

## Features

- **AI-based classification** of PDF documents
- **Automatic sorting** into predefined or similar directories
- **PDF preview** for better control
- **Performance monitoring** (CPU/RAM usage)
- **Background preprocessing** for improved performance
- **Intelligent path suggestions** based on filenames
- **User-friendly web interface**

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
   - Review and confirm suggestions
   - Documents are automatically sorted

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
├── app.py              # Main application
├── templates/          # HTML templates
├── requirements.txt    # Python dependencies
├── .env.example       # Configuration template
├── .gitignore         # Git ignore rules
└── README.md          # This file
```

### Run Tests
```bash
# Add tests here
pytest tests/
```

### Code Style
```bash
# Format with black
black app.py

# Lint with flake8
flake8 app.py
```

## Troubleshooting

### Common Issues

**Issue:** LM Studio Connection Error
- **Solution:** Ensure LM Studio is running and a model is loaded

**Issue:** PDF processing fails
- **Solution:** Check PDF file for corruption

**Issue:** Directories not found
- **Solution:** Create the directories specified in `.env`

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