# TTAB Opinion Analysis System

## Overview

This is a data processing system for analyzing Trademark Trial and Appeal Board (TTAB) opinions. The system downloads XML bulk data from the USPTO, parses TTAB case documents to extract structured information, and optionally matches cases with Federal Circuit appeals using the CourtListener API. It's designed to provide insights into trademark proceedings, outcomes, and appellate history.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Core Processing Pipeline
The system follows a three-stage pipeline architecture:
1. **Data Acquisition** - Downloads TTAB XML files from USPTO bulk data repository
2. **Data Parsing** - Extracts structured information from XML documents  
3. **Data Enrichment** - Optionally enhances data with Federal Circuit appeal information

### Data Models
Uses a structured dataclass-based approach for type safety and clarity:
- **TTABOpinion** - Core opinion data with parties, judges, outcomes, and metadata
- **FederalCircuitAppeal** - Appeal case information from Federal Circuit
- **Enums** - Standardized vocabularies for outcomes, party types, and proceeding types
- **Supporting Models** - Party, Judge, Attorney, TrademarkMark classes for detailed information

### XML Processing Strategy
Implements robust XML parsing with error handling:
- Supports compressed files (gzip, zip)
- Element-based extraction with fallback mechanisms
- Text cleaning and normalization utilities
- Validation of extracted data before storage

### API Integration Pattern
Uses a client-wrapper pattern for external services:
- **CourtListenerClient** - Handles Federal Circuit API interactions
- Built-in rate limiting and authentication management
- Graceful degradation when API is unavailable
- Configurable via environment variables

### Error Handling and Logging
Comprehensive logging strategy throughout the pipeline:
- Structured logging with different levels (INFO, WARNING, ERROR)
- Progress tracking for batch operations
- Statistics collection for processing metrics
- Graceful failure handling with detailed error reporting

## External Dependencies

### USPTO Data Source
- **USPTO Open Data Portal** - Primary source for TTAB XML files at `https://data.uspto.gov/`
- **API-based Access** - Uses REST API endpoints at `https://api.uspto.gov/api/v1/datasets/products/`
- **Daily TTAB Dataset (TTABTDXF)** - Current year daily XML files (2025+)
- **Annual TTAB Dataset (TTABYR)** - Historical backfile (October 1951 - December 2024)
- **Authentication** - Requires USPTO API key (free registration at https://data.uspto.gov/myodp)
- **Rate Limits** - 60 requests/minute (standard), 4 requests/minute (bulk file downloads)
- **Official TTAB DTD v1.0** - System fully compliant with USPTO TTAB XML DTD specification
- **Legacy URL Retired** - Old bulkdata.uspto.gov repository replaced by Open Data Portal

### CourtListener API
- **Federal Circuit Appeals Database** - REST API v4 for matching TTAB cases with Federal Circuit appeals
- Requires API token authentication (`COURTLISTENER_API_TOKEN` environment variable)
- Used for enriching TTAB opinions with appellate outcomes and citations

### Python Libraries
- **requests** - HTTP client for API calls and file downloads
- **xml.etree.ElementTree** - XML parsing and document processing
- **pathlib** - Modern file system path handling
- **dataclasses** - Structured data models with type hints
- **enum** - Standardized vocabulary definitions
- **PyPDF2** - PDF processing for documentation analysis

### File Format Support
- **XML** - Primary document format from USPTO (supports official TTAB DTD structure)
- **CSV** - Output format for structured data export
- **Compressed Files** - Support for gzip and zip compressed XML files
- **PDF** - Documentation and specification processing

## Recent Changes

### October 2025 - TTAB Decision Identification Update
- **Implemented correct TTAB decision identification**:
  - Parser now identifies TTAB decisions based on prosecution-entry codes
  - Valid decision codes: 802-849 and 855-894 (excluding 850-854)
  - Example: `<prosecution-entry><code>870</code></prosecution-entry>` indicates a TTAB decision
  - Legacy heuristics (document type, judge names, decision phrases) kept as fallback
  - Added 10 comprehensive unit tests for decision code validation
  - Fixed ElementTree boolean evaluation bug (elements with no children evaluate to False)
  - Total test count: 76 tests (all passing)

### October 2025 - Documentation Complete
- **Created comprehensive README.md**:
  - Complete command reference for downloader and parser
  - All command-line options documented with examples
  - Workflow examples for common use cases
  - Troubleshooting guide and best practices
  - Quick reference card for most common commands
  - Technical details on TTAB DTD compliance and threading model
- **Environment Configuration**:
  - Added `.env-sample` template file for API keys
  - Documented `.env` file setup (copy from sample and add keys)
  - Documented `uv run --env-file .env` usage for automatic environment loading
  - Updated all workflow examples with both uv and direct Python execution methods
  - `.env` properly listed in .gitignore for security

### October 2025 - Testing Framework Setup
- **Added comprehensive unit testing**:
  - Installed pytest and pytest-mock frameworks
  - Created 66 unit tests across all core modules
  - Test coverage for models, utils, downloader, and parser
  - Test fixtures and sample data in conftest.py
  - pytest configuration with organized test structure
- **Test Organization**:
  - `tests/test_models.py` - Data classes, enums, validation (26 tests)
  - `tests/test_utils.py` - Text cleaning, date parsing, XML handling (27 tests)
  - `tests/test_downloader.py` - File detection, duplicate checking, threading (11 tests)
  - `tests/test_parser.py` - XML parsing, party mapping, proceeding types (13 tests)
- **Code Quality Improvements**:
  - Fixed import paths to use absolute imports (src.* pattern)
  - Fixed case-insensitive XML file detection
  - All tests passing successfully
- **Running Tests**: Execute `pytest tests/` to run all unit tests

### October 2025 - USPTO Open Data Portal Migration
- **Migrated to new USPTO Open Data Portal API**:
  - Updated downloader to use REST API endpoints instead of web scraping
  - Implemented API key authentication using `USPTO_API_KEY` environment variable
  - Added support for both daily (TTABTDXF) and annual (TTABYR) datasets
  - Improved date filtering using API product metadata
  - Enhanced file download with proper headers and rate limiting (15s delay between downloads)
  - **Automatic ZIP extraction** - Downloads are automatically unzipped and XML files saved to data directory
  - **Threaded extraction** - ZIP files extract in parallel threads while downloads remain sequential
  - **Smart duplicate detection** - Skips downloads if ZIP or extracted XML already exists
- **New Features**:
  - `--annual` flag to download historical backfile dataset (1951-2024)
  - API-based file discovery with metadata (file size, release dates, data ranges)
  - Better error handling for API authentication failures
  - Progress tracking for file downloads with percentage completion
  - Automatic extraction of ZIP archives with cleanup (removes ZIP after extraction)
  - Parallel extraction threads for improved performance
  - Duplicate file detection (checks both ZIP and XML files before downloading)
- **Breaking Changes**:
  - Requires USPTO API key (set `USPTO_API_KEY` environment variable)
  - Old bulkdata.uspto.gov URLs no longer supported
  - Download URLs now use API endpoints with authentication

### August 2025 - TTAB DTD Compliance Update
- **Downloaded and analyzed official USPTO TTAB DTD documentation** (v1.0)
- **Updated XML parser to handle official DTD structure**:
  - Root element: `<ttab-proceedings>` with version info
  - Proceeding entries: `<proceeding-entry>` elements
  - Party information: `<party-information>` with role-code mapping (P=Plaintiff, D=Defendant)
  - Date format: YYYYMMDD handling for filing-date, event-date elements
  - Proceeding numbers: Official format validation (91=Opposition, 92=Cancellation, 70-74=Ex Parte Appeal)
- **Enhanced date parsing**: Added support for TTAB DTD YYYYMMDD format
- **Improved party type mapping**: Official role-code P/D to semantic party types
- **Fixed XML memory management**: Removed lxml-specific getparent() calls for compatibility

### System Status
- ✅ TTAB Downloader: Fully operational with USPTO Open Data Portal API
- ✅ TTAB Parser: DTD-compliant with comprehensive data extraction
- ✅ CourtListener Client: Ready (requires API token for appeals tracking)
- ✅ CSV Export: Functional with structured trademark litigation data
- ✅ Documentation: Complete with official DTD specification analysis

### Required Environment Variables
- **USPTO_API_KEY** - Required for downloading TTAB data from Open Data Portal (obtain at https://data.uspto.gov/myodp)
- **COURTLISTENER_API_TOKEN** - Optional for Federal Circuit appeals tracking