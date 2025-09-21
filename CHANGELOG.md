# Changelog

All notable changes to the Document Sorter project will be documented in this file.

## [Recent Updates] - 2025-01-25

### Added
- **New 3-Column Workflow Interface**: Complete redesign of the user interface
  - Files column (left): Document selection with metadata
  - Intelligent column (center): AI-powered workflow with one-click confirmation
  - Manual column (right): Traditional category selection and manual control
- **Enhanced Filename Suggestions**: Improved intelligent file renaming system
  - Flexible title extraction from PDF content and headers
  - Support for various document types (Rechnung, Kündigung, Vertrag, etc.)
  - Clickable date and filename options in intelligent workflow
  - Removal of category from filename suggestions (user requested)
- **Smart Title Recognition**: Enhanced patterns for document title extraction
  - Recognition of document type keywords anywhere in text, not just at beginning
  - Support for German document types and headers
  - Better handling of scanned document artifacts

### Fixed
- **Rename and Move Functionality**: Fixed "Umbenennen und verschieben" button issues
  - Corrected path construction problems
  - Added comprehensive debugging for move operations
  - Fixed trailing slash issues in target paths
- **Date Parsing Accuracy**: Improved date extraction from PDF content
  - Prioritized 4-digit year patterns to avoid ambiguity
  - Fixed parsing of dates like "15.03.1985" being incorrectly interpreted
  - Added negative lookahead to prevent partial date matches

### Changed
- **Filename Format**: Updated from `YYYY-MM-DD_category_description.pdf` to `YYYY-MM-DD_description.pdf`
- **User Interface**: Streamlined workflow requiring minimal user interaction
- **AI Integration**: Enhanced cross-column interaction between intelligent and manual workflows

### Technical Improvements
- Enhanced regex patterns for more flexible document type recognition
- Improved error handling and debugging for file operations
- Better integration between frontend JavaScript and backend Python services
- CSS Grid implementation for responsive 3-column layout

## Previous Features

### Core Functionality
- AI-based document classification using LM Studio
- PDF text extraction and preview generation
- Automatic directory management and sorting
- Real-time system monitoring and performance tracking
- Comprehensive logging and error reporting
- Modular architecture with RESTful API design