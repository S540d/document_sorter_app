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

app = Flask(__name__)

# Konfiguration
CONFIG = {
    'LM_STUDIO_URL': 'http://localhost:1234/v1/chat/completions',
    'SCAN_DIR': '/Users/svenstrohkark/Documents/doc-tag-test/scans',
    'SORTED_DIR': '/Users/svenstrohkark/Documents/doc-tag-test/sorted',
    'CATEGORIES': [
        'Steuern',
        'Versicherungen', 
        'Verträge',
        'Banken',
        'Medizin',
        'Behörden',
        'Sonstiges'
    ]
}

# [Rest der Funktionen wie im Original-Artifact]

if __name__ == '__main__':
    print("Starting Document Sorter...")
    app.run(debug=True, host='127.0.0.1', port=5001)
