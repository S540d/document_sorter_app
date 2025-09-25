#!/usr/bin/env python3
"""
Einfacher Test für das neue Filter-System
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from app.services.filter_service import FilterService, FilterRule, FilterSuggestion
from app.services.file_service import FileService

def test_filter_service():
    """Test der FilterService Funktionalität"""
    print("🧪 Testing FilterService...")

    filter_service = FilterService()

    # Test: Unterstützte Dateierweiterungen
    test_files = [
        "Rechnung_Stadtwerke_2024.xlsx",
        "Kontoauszug_DKB_Januar.pdf",
        "Vertrag_Strom_2025.docx",
        "Foto_Urlaub.jpg",
        "unsupported_file.xyz"
    ]

    print("\n📋 Supported file check:")
    for filename in test_files:
        supported = filter_service.is_supported_file(filename)
        print(f"  {filename}: {'✅ Supported' if supported else '❌ Not supported'}")

    # Test: Pattern-Generierung
    print("\n🔍 Pattern generation test:")
    test_filenames = [
        "Rechnung_Stadtwerke_2024-03-15.xlsx",
        "Kontoauszug_DKB_2024_Januar.pdf",
        "Scanbot_2024_12_25_document.pdf"
    ]

    for filename in test_filenames:
        pattern = filter_service._generate_pattern_from_filename(filename)
        print(f"  {filename} → {pattern}")

    # Test: Keyword-basierte Vorschläge
    print("\n💡 Keyword suggestions test:")
    keyword_files = [
        "Rechnung_Telefon_2024.xlsx",
        "Versicherung_Auto_Police.pdf",
        "Vertrag_Internet_2025.docx"
    ]

    for filename in keyword_files:
        suggestions = filter_service._suggest_by_keywords(filename, Path(filename).suffix.lower())
        print(f"  {filename}:")
        for suggestion in suggestions:
            print(f"    → {suggestion.target_path} (confidence: {suggestion.confidence:.2f}) - {suggestion.reason}")

    print("✅ FilterService tests completed!")

def test_file_service():
    """Test der FileService Erweiterungen"""
    print("\n🧪 Testing FileService extensions...")

    file_service = FileService()

    # Test: Unterstützte Dateitypen
    print("\n📁 Supported extensions:")
    print(f"  {sorted(file_service.supported_extensions)}")

    # Test: Downloads-Scan (falls Downloads-Verzeichnis existiert)
    print("\n📥 Downloads directory scan:")
    try:
        downloads_files = file_service.scan_downloads_directory()
        print(f"  Found {len(downloads_files)} supported files in Downloads")

        if downloads_files:
            print("  Top 3 files:")
            for file_info in downloads_files[:3]:
                print(f"    {file_info['name']} ({file_info['type']}, {file_info['size']} bytes)")

    except Exception as e:
        print(f"  ⚠️  Could not scan Downloads: {e}")

    # Test: Dateityp-Erkennung
    print("\n🏷️  File type detection:")
    test_files = [
        "document.pdf",
        "spreadsheet.xlsx",
        "image.jpg",
        "archive.zip",
        "unknown.xyz"
    ]

    for filename in test_files:
        file_type = file_service._get_file_type(Path(filename))
        print(f"  {filename} → {file_type}")

    print("✅ FileService tests completed!")

def test_integration():
    """Test der Integration zwischen FilterService und FileService"""
    print("\n🔗 Testing integration...")

    filter_service = FilterService()
    file_service = FileService()

    # Erstelle Test-Regel
    test_rule = FilterRule(
        id="test_rule_1",
        pattern="Rechnung_*_*.xlsx",
        target_path="/Documents/Steuern/Rechnungen",
        file_extensions=[".xlsx"],
        confidence_threshold=0.7,
        created_at="2024-01-01T00:00:00"
    )

    filter_service.rules.append(test_rule)

    # Test: Vorschläge für ähnliche Datei
    test_filename = "Rechnung_Stadtwerke_Januar_2024.xlsx"
    suggestions = filter_service.suggest_filters(test_filename, f"/Downloads/{test_filename}")

    print(f"\n📋 Suggestions for '{test_filename}':")
    for suggestion in suggestions:
        print(f"  → {suggestion.target_path}")
        print(f"    Confidence: {suggestion.confidence:.2f}")
        print(f"    Reason: {suggestion.reason}")
        if suggestion.rule_id:
            print(f"    Rule ID: {suggestion.rule_id}")
        print()

    print("✅ Integration tests completed!")

if __name__ == "__main__":
    print("🚀 Starting Filter System Tests\n")

    try:
        test_filter_service()
        test_file_service()
        test_integration()

        print("\n🎉 All tests completed successfully!")

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()