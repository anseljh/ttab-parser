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
- **TTAB Bulk Data Repository** - Primary source for XML files at `https://bulkdata.uspto.gov/data/trademark/dailyxml/ttab/`
- Provides daily and annual XML files containing TTAB proceedings and opinions

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

### File Format Support
- **XML** - Primary document format from USPTO
- **CSV** - Output format for structured data export
- **Compressed Files** - Support for gzip and zip compressed XML files