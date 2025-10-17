# TTAB Opinion Analysis System

A Python application for downloading and analyzing Trademark Trial and Appeal Board (TTAB) opinion documents from the USPTO Open Data Portal. The system extracts structured information including parties, judges, case outcomes, and trademark, and optionally tracks Federal Circuit appeals.

## Features

- **Data Download**: Automated bulk data download from USPTO Open Data Portal
- **XML Parsing**: TTAB DTD-compliant XML document processing
- **Data Extraction**: Comprehensive extraction of parties, judges, outcomes, and marks
- **Appeal Tracking**: Optional Federal Circuit appeal matching via CourtListener API
- **CSV Export**: Structured data export for analysis
- **Smart Caching**: Duplicate detection and automatic ZIP extraction
- **Parallel Processing**: Threaded extraction for improved performance
- **Comprehensive Testing**: 66 unit tests ensuring code quality

## Installation

### Prerequisites

- Python 3.11+
- USPTO API Key (free registration at [https://data.uspto.gov/myodp](https://data.uspto.gov/myodp))

### Setup

1. **Clone or download this repository**

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up your API keys using .env file:**
   
   Copy the sample environment file:
   ```bash
   cp .env-sample .env
   ```
   
   Edit `.env` and add your API keys:
   ```bash
   USPTO_API_KEY=your-uspto-api-key-here
   COURTLISTENER_API_TOKEN=your-courtlistener-token-here
   ```
   
   **Note**: The CourtListener token is optional. If you don't need Federal Circuit appeal tracking, you can leave it empty.

4. **Alternative: Set environment variables directly** (optional):
   
   Instead of using a `.env` file, you can export variables directly:
   ```bash
   export USPTO_API_KEY="your-api-key-here"
   export COURTLISTENER_API_TOKEN="your-token-here"
   ```

## Usage

### Running Scripts with Environment Variables

If you created a `.env` file (recommended), you have two options to run the scripts:

#### Option 1: Using uv with Shortcut Commands (Recommended)

If you have `uv` installed, you can use convenient shortcut commands:

```bash
# Download recent files
uv run --env-file .env download --recent 7

# Parse downloaded files
uv run --env-file .env parse ./ttab_data
```

**Benefits of using uv with shortcuts:**
- Short, easy-to-remember commands (`download` and `parse`)
- Automatically loads environment variables with `--env-file .env`
- Works consistently across different shells and systems
- Environment is isolated to the command execution

**Alternative: Full module path**
```bash
# Also works (longer syntax)
uv run --env-file .env python -m src.ttab_downloader --recent 7
uv run --env-file .env python -m src.ttab_parser ./ttab_data
```

#### Option 2: Using Direct Execution

If you exported environment variables in your shell, run scripts directly:

```bash
python -m src.ttab_downloader --recent 7
python -m src.ttab_parser ./ttab_data
```

**Note**: All examples below show direct Python execution. If using uv, use: `uv run --env-file .env python -m` instead of `python -m`.

### TTAB Downloader

The downloader fetches TTAB XML files from the USPTO Open Data Portal. It supports both daily (current year) and annual (historical) datasets.

#### Basic Commands

**Download recent files (last 7 days):**
```bash
python -m src.ttab_downloader --recent 7
# OR with uv:
uv run --env-file .env python -m src.ttab_downloader --recent 7
```

**Download recent files (last 30 days):**
```bash
python -m src.ttab_downloader --recent 30
```

**Download all available daily files:**
```bash
python -m src.ttab_downloader --all
```

**Download annual/historical dataset (1951-2024):**
```bash
python -m src.ttab_downloader --annual
```

#### Advanced Options

**Custom output directory:**
```bash
python -m src.ttab_downloader --output-dir ./my_data --recent 7
```

**Specify API key directly:**
```bash
python -m src.ttab_downloader --api-key YOUR_API_KEY --recent 7
```

**Download specific year (daily dataset only):**
```bash
python -m src.ttab_downloader --year 2025 --all
```

**Force redownload of existing files:**
```bash
python -m src.ttab_downloader --force --recent 7
```

**Verbose logging:**
```bash
python -m src.ttab_downloader --verbose --recent 7
```

#### Downloader Options Summary

| Option | Short | Description |
|--------|-------|-------------|
| `--output-dir` | `-o` | Output directory for downloaded files (default: ./ttab_data) |
| `--api-key` | `-k` | USPTO API key (or set USPTO_API_KEY environment variable) |
| `--year` | `-y` | Specific year to download (current year only, for daily dataset) |
| `--recent` | `-r` | Download files from the last N days (default: 7) |
| `--all` | `-a` | Download all available files from daily dataset |
| `--annual` | | Download annual/historical dataset (1951-2024) |
| `--force` | `-f` | Force redownload of existing files |
| `--verbose` | `-v` | Enable verbose logging |

#### Download Behavior

- **Automatic ZIP extraction**: Downloads are automatically unzipped
- **Parallel extraction**: ZIP files extract in separate threads while downloads remain sequential
- **Smart duplicate detection**: Skips downloads if ZIP or extracted XML already exists
- **Rate limiting**: 15-second delay between downloads (USPTO rate limit compliance)

### TTAB Parser

The parser processes TTAB XML files and extracts structured opinion data.

#### Basic Commands

**Parse downloaded files and create CSV:**
```bash
python -m src.ttab_parser ./ttab_data
```

**Specify custom output file:**
```bash
python -m src.ttab_parser ./ttab_data --output my_results.csv
```

**Disable Federal Circuit appeal lookup:**
```bash
python -m src.ttab_parser ./ttab_data --no-courtlistener
```

#### Advanced Options

**Limit processing (for testing):**
```bash
python -m src.ttab_parser ./ttab_data --limit 100
```

**Enable verbose logging:**
```bash
python -m src.ttab_parser ./ttab_data --verbose
```

**Write logs to file:**
```bash
python -m src.ttab_parser ./ttab_data --log-file parsing.log
```

**Combine options:**
```bash
python -m src.ttab_parser ./ttab_data \
  --output results_2025.csv \
  --verbose \
  --log-file parsing.log \
  --limit 1000
```

#### Parser Options Summary

| Option | Short | Description |
|--------|-------|-------------|
| `input_dir` | | Directory containing TTAB XML files (required) |
| `--output` | `-o` | Output CSV file (default: ttab_opinions.csv) |
| `--no-courtlistener` | | Disable Federal Circuit appeal lookup |
| `--log-file` | | Path to log file (default: console only) |
| `--verbose` | `-v` | Enable verbose logging |
| `--limit` | | Limit number of opinions to process (for testing) |

## Complete Workflow Example

Here's a typical workflow for downloading and analyzing TTAB data:

### Using uv (Recommended)

```bash
# 1. Download recent TTAB data (last 30 days)
uv run --env-file .env src/ttab_downloader.py --recent 30 --verbose

# 2. Parse the downloaded files
uv run --env-file .env src/ttab_parser.py ./ttab_data --output ttab_results.csv --verbose

# 3. View the results
head -n 20 ttab_results.csv
```

### Using Direct Python Execution

```bash
# 1. Download recent TTAB data (last 30 days)
python -m src.ttab_downloader --recent 30 --verbose

# 2. Parse the downloaded files
python -m src.ttab_parser ./ttab_data --output ttab_results.csv --verbose

# 3. View the results
head -n 20 ttab_results.csv
```

### Advanced Workflow with Historical Data

```bash
# Using uv:
# 1. Download annual historical dataset
uv run --env-file .env src/ttab_downloader.py --annual --output-dir ./ttab_historical

# 2. Parse with Federal Circuit appeals disabled (faster)
uv run --env-file .env src/ttab_parser.py ./ttab_historical \
  --output historical_results.csv \
  --no-courtlistener \
  --verbose

# OR using direct Python:
# 1. Download annual historical dataset
python -m src.ttab_downloader --annual --output-dir ./ttab_historical

# 2. Parse with Federal Circuit appeals disabled (faster)
python -m src.ttab_parser ./ttab_historical \
  --output historical_results.csv \
  --no-courtlistener \
  --verbose
```

## Output Data Structure

The parser generates a CSV file with the following fields:

- **Case Information**: case_number, proceeding_type, filing_date, decision_date
- **Parties**: plaintiff_name, defendant_name, plaintiff_attorney, defendant_attorney
- **Outcome**: outcome, prevailing_party
- **Judges**: judges (comma-separated list)
- **Marks**: challenged_marks, asserted_marks (semicolon-separated)
- **Appeals**: appeal_indicated, federal_circuit_case_number, federal_circuit_outcome

## Data Sources

### USPTO Open Data Portal

- **Daily Dataset (TTABTDXF)**: Current year daily XML files (2025+)
- **Annual Dataset (TTABYR)**: Historical backfile (October 1951 - December 2024)
- **API Endpoint**: `https://api.uspto.gov/api/v1/datasets/products/`
- **Rate Limits**: 60 requests/min (standard), 4 requests/min (bulk files)

### CourtListener API

- **Federal Circuit Appeals**: REST API v4 for matching TTAB cases with appeals
- **Authentication**: Requires `COURTLISTENER_API_TOKEN` environment variable
- **Optional**: Can be disabled with `--no-courtlistener` flag

## Testing

Run the comprehensive test suite:

```bash
# Run all tests
pytest tests/

# Run with verbose output
pytest tests/ -v

# Run specific test file
pytest tests/test_downloader.py

# Run with coverage report
pytest tests/ --cov=src
```

### Test Coverage

- **66 unit tests** covering all core modules:
  - `tests/test_models.py` - Data classes, enums, validation (26 tests)
  - `tests/test_utils.py` - Text cleaning, date parsing, XML handling (27 tests)
  - `tests/test_downloader.py` - File detection, duplicate checking (11 tests)
  - `tests/test_parser.py` - XML parsing, party mapping (13 tests)

## Project Structure

```
.
├── src/
│   ├── ttab_downloader.py      # USPTO data download utility
│   ├── ttab_parser.py           # XML parser and data extractor
│   ├── models.py                # Data models and enums
│   ├── utils.py                 # Utility functions
│   └── courtlistener_client.py  # Federal Circuit API client
├── tests/
│   ├── test_downloader.py       # Downloader tests
│   ├── test_parser.py           # Parser tests
│   ├── test_models.py           # Model tests
│   ├── test_utils.py            # Utility tests
│   └── conftest.py              # Test fixtures
├── ttab_data/                   # Downloaded XML files (created automatically)
├── .env-sample                  # Environment variable template
├── .env                         # Your API keys (create from .env-sample, not committed)
├── pytest.ini                   # Test configuration
├── requirements.txt             # Python dependencies
└── README.md                    # This file
```

## Environment Variables

You can configure environment variables either through a `.env` file (recommended) or by exporting them in your shell.

### Using .env File (Recommended)

1. Copy `.env-sample` to `.env`: `cp .env-sample .env`
2. Edit `.env` and add your API keys
3. Run scripts with: `uv run --env-file .env src/script.py`

### Environment Variable Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `USPTO_API_KEY` | **Yes** | USPTO Open Data Portal API key ([Get one here](https://data.uspto.gov/myodp)) |
| `COURTLISTENER_API_TOKEN` | No | CourtListener API token for Federal Circuit appeals |

**Security Note**: Never commit your `.env` file to version control. The `.env-sample` file is provided as a template.

## Rate Limits and Best Practices

### USPTO API Rate Limits

- **Standard API calls**: 60 requests per minute
- **Bulk file downloads**: 4 requests per minute (enforced with 15-second delay)

### Download Best Practices

1. **Start small**: Test with `--recent 7` before downloading larger datasets
2. **Use annual dataset for historical data**: More efficient than daily files
3. **Monitor disk space**: Annual dataset files can exceed 100MB each
4. **Check existing files**: System automatically skips duplicates

### Parsing Best Practices

1. **Test with --limit**: Use `--limit 100` to test parsing on a subset
2. **Disable CourtListener for speed**: Use `--no-courtlistener` for faster parsing
3. **Enable verbose logging**: Use `--verbose` to track progress on large datasets
4. **Log to file**: Use `--log-file` to preserve detailed processing logs

## Troubleshooting

### Authentication Errors

**Problem**: `API access forbidden` or `403 Forbidden`
```
Solution: Set your USPTO_API_KEY environment variable
export USPTO_API_KEY="your-api-key-here"
```

### No Files Found

**Problem**: `No XML files found in directory`
```
Solution: 
1. Verify files were downloaded: ls -la ./ttab_data
2. Check download logs for errors
3. Run downloader with --verbose flag
```

### Memory Issues

**Problem**: Parser runs out of memory on large files
```
Solution:
1. Process files in batches using --limit
2. Disable CourtListener with --no-courtlistener
3. Process one file at a time by creating subdirectories
```

### Rate Limit Errors

**Problem**: `Too many requests` or rate limit warnings
```
Solution:
1. System automatically handles rate limits with delays
2. Wait a few minutes before retrying
3. Check if you're running multiple download processes
```

### Module Import Error with uv

**Problem**: `ModuleNotFoundError: No module named 'src'` when running with uv
```bash
$ uv run --env-file .env src/ttab_parser.py data
ModuleNotFoundError: No module named 'src'
```

**Solution**: Use the `-m` flag to run as a Python module:
```bash
# Correct way
uv run --env-file .env python -m src.ttab_parser data

# OR without uv
python -m src.ttab_parser data
```

**Why this happens**: The codebase uses absolute imports (`from src.models import ...`) which require running as a module with `-m` rather than running the file directly.

## Technical Details

### TTAB DTD Compliance

The parser is fully compliant with USPTO TTAB XML DTD v1.0:
- Root element: `<ttab-proceedings>`
- Proceeding entries: `<proceeding-entry>`
- Party information: `<party-information>` with role codes (P=Plaintiff, D=Defendant)
- Date format: YYYYMMDD for filing-date and event-date elements
- Proceeding numbers: Official formats (91=Opposition, 92=Cancellation, 70-74=Ex Parte Appeal)

### TTAB Decision Identification

The parser identifies TTAB decisions using prosecution-entry codes:

**Valid Decision Codes:**
- **802-849** (inclusive) - TTAB decision codes
- **855-894** (inclusive) - TTAB decision codes  
- **EXCLUDING 850-854** - Not decision codes

**Example XML Structure:**
```xml
<proceeding-entry>
  <prosecution-entry>
    <code>870</code>  <!-- This indicates a TTAB decision -->
  </prosecution-entry>
</proceeding-entry>
```

**Fallback Method:**  
For legacy data without prosecution-entry codes, the parser falls back to heuristics:
- Document type keywords (opinion, decision, ruling, judgment)
- Presence of judge information
- Decision-making language in text content

### Threading Model

- **Downloads**: Sequential with 15-second delay (rate limit compliance)
- **Extraction**: Parallel threads per ZIP file
- **Main thread**: Waits for all extractions before completing

### Duplicate Detection

The system checks for both:
1. Existing ZIP files (`[filename].zip`)
2. Extracted XML files (`[filename].xml`)

Use `--force` to override and redownload.

## Contributing

### Running Tests

Before submitting changes, ensure all tests pass:

```bash
pytest tests/ -v
```

### Code Style

- Follow PEP 8 guidelines
- Use absolute imports (`from src.module import ...`)
- Add type hints to function signatures
- Document new functions with docstrings

## License

This project is for research and educational purposes. TTAB data is public domain from the USPTO.

## Support

For issues or questions:

- **USPTO API Issues**: Visit [https://data.uspto.gov/myodp](https://data.uspto.gov/myodp)
- **CourtListener API**: Visit [https://www.courtlistener.com/api/](https://www.courtlistener.com/api/)
- **Project Issues**: Check project documentation or replit.md

## Quick Reference Card

### Most Common Commands

```bash
# ===== Setup =====
# Copy environment file and add your API keys
cp .env-sample .env
# Edit .env and add: USPTO_API_KEY=your-key-here

# ===== Using uv with Shortcuts (Recommended) =====
# Download last 7 days of data
uv run --env-file .env download --recent 7

# Download last 30 days with verbose output
uv run --env-file .env download --recent 30 --verbose

# Parse downloaded data
uv run --env-file .env parse ./ttab_data

# Parse with custom output and verbose logging
uv run --env-file .env parse ./ttab_data --output results.csv --verbose

# Download historical data
uv run --env-file .env download --annual

# Test parsing on small sample
uv run --env-file .env parse ./ttab_data --limit 100

# ===== OR Using Direct Python =====
# (After setting: export USPTO_API_KEY="your-key-here")
python -m src.ttab_downloader --recent 7
python -m src.ttab_parser ./ttab_data

# ===== Testing =====
# Run all tests
pytest tests/
```
