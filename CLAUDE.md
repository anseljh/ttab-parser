# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a data processing toolkit for USPTO Trademark Trial and Appeal Board (TTAB) opinions. It downloads XML bulk data from the USPTO Open Data Portal, parses TTAB case documents into structured data, and optionally enriches cases with Federal Circuit appeal data from CourtListener.

## Commands

### Setup

```bash
cp .env-sample .env  # then fill in API keys
uv sync              # install dependencies
```

### Run the downloader

```bash
uv run --env-file .env download                    # recent 7 days (default)
uv run --env-file .env download --recent 30        # last 30 days
uv run --env-file .env download --all              # all current-year daily files
uv run --env-file .env download --annual           # historical backfile (1951-2024)
uv run --env-file .env download --force            # redownload existing files
```

### Run the parser

```bash
uv run --env-file .env parse                       # parse ttab_data/ (default dir)
uv run --env-file .env parse /path/to/xml/dir      # specify directory
uv run --env-file .env parse --no-courtlistener    # skip Federal Circuit lookup
uv run --env-file .env parse --limit 10            # process only 10 opinions
uv run --env-file .env parse -o output.csv         # custom output file
uv run --env-file .env parse --verbose             # debug logging
```

### Tests

```bash
uv run pytest                           # all tests
uv run pytest tests/test_models.py     # single file
uv run pytest -k "test_parse_date"     # single test by name
uv run pytest -m "not integration"     # skip integration tests
```

## Architecture

The system is a three-stage pipeline:

1. **Download** (`src/ttab_downloader.py`) — Fetches TTAB XML files from the USPTO Open Data Portal API (`https://api.uspto.gov/api/v1/datasets/products/`). Downloads are sequential (rate limited to 4/min for bulk files), ZIP extraction runs in parallel threads. Outputs XML files to `ttab_data/`.

2. **Parse** (`src/ttab_parser.py`) — Reads XML files using `ET.iterparse` for memory efficiency, identifies opinion documents by TTAB decision codes (prosecution-entry codes 802–849, 855–894), and extracts structured data into `TTABOpinion` objects. Falls back to heuristics (judge names, decision phrases) for documents without prosecution entries. Outputs a CSV.

3. **Enrich** (`src/courtlistener_client.py`) — Optionally matches TTAB cases to Federal Circuit appeals by searching CourtListener's REST API v4. Searches first by case number, then by party names + "TTAB" terms. Rate limited to 1 req/sec.

### Key data structures (`src/models.py`)

- **`TTABOpinion`** — root object; contains parties, judges, marks, outcome, and optional `FederalCircuitAppeal`
- **`Party`**, **`Judge`**, **`Attorney`**, **`TrademarkMark`** — nested detail objects
- **Enums**: `OutcomeType`, `PartyType` (uses official DTD role-codes P=plaintiff/D=defendant mapped to semantic types), `ProceedingType`

### XML format notes

The official TTAB DTD v1.0 uses:
- Root: `<ttab-proceedings>` > `<proceeding-entry>`
- Parties: `<party-information>` with `<role-code>P</role-code>` (plaintiff) or `D` (defendant)
- Dates: YYYYMMDD format in `<filing-date>`, `<event-date>`
- Proceeding types inferred from case number prefix: 91=Opposition, 92=Cancellation, 70–74=Appeal
- Decision identification: `<prosecution-entry><code>NNN</code>` where NNN is 802–849 or 855–894

### Environment variables

| Variable | Required | Purpose |
|---|---|---|
| `USPTO_API_KEY` | Yes (downloader) | USPTO Open Data Portal auth |
| `COURTLISTENER_API_TOKEN` | No | Federal Circuit appeal lookup |

Obtain USPTO API key at https://data.uspto.gov/myodp.

### Important implementation notes

- Use `xml.etree.ElementTree` (not lxml) — `getparent()` is not available
- The `is_opinion_document()` check in `src/utils.py` is the gating function for what gets parsed as an opinion; it checks decision codes first, then falls back to heuristics
- XML element boolean evaluation bug: use `if elem is not None` not `if elem` (elements with no children evaluate to False)
- The `parse` entry point defaults to `ttab_data/` as input directory; no argument needed for the standard workflow
