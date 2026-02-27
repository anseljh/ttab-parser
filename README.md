# TTAB Opinion Analysis System

A Python toolkit for downloading and analyzing Trademark Trial and Appeal Board (TTAB) opinion documents from the USPTO Open Data Portal. The system extracts structured information including parties, judges, case outcomes, and trademark marks; optionally tracks Federal Circuit appeals; and can run fully automated on a schedule via Celery and Docker Compose.

## Features

- **Scheduled automation**: Celery Beat triggers a daily download → parse → enrich pipeline without manual intervention
- **PostgreSQL persistence**: Parsed opinions are upserted into a PostgreSQL database for querying
- **Data download**: Bulk data download from the USPTO Open Data Portal
- **XML parsing**: TTAB DTD-compliant XML document processing
- **Data extraction**: Comprehensive extraction of parties, judges, outcomes, and marks
- **Appeal tracking**: Optional Federal Circuit appeal matching via CourtListener API
- **CSV export**: Structured data export for ad-hoc analysis
- **Smart caching**: Duplicate detection and automatic ZIP extraction
- **Parallel extraction**: Threaded ZIP extraction for improved throughput
- **76 unit tests**: Comprehensive test coverage across all core modules

## Quickstart (Docker)

The simplest way to run the full pipeline is via Docker Compose:

```bash
# 1. Configure settings
cp settings-example.toml settings.toml
# Edit settings.toml — add USPTO api_key (and optionally CourtListener api_token)

# 2. Start all services (Redis, Postgres, worker, beat scheduler)
./bin/run.sh
```

`bin/run.sh` builds the images, starts the four services in the background, waits for each one to be healthy, then prints a ready message with connection strings and useful commands.

The Beat scheduler will fire the pipeline daily at **06:00 UTC**. To trigger it immediately:

```bash
docker compose exec worker uv run celery -A src.celery_app call src.tasks.download_task --kwargs '{"days":1}'
```

To stop everything:

```bash
docker compose down
```

## Manual / CLI Usage

The CLI commands work exactly as before — no Docker required.

### Prerequisites

- Python 3.14+
- [uv](https://github.com/astral-sh/uv) package manager
- USPTO API key (free registration at [https://data.uspto.gov/myodp](https://data.uspto.gov/myodp))

### Setup

```bash
# Install dependencies
uv sync

# Configure settings
cp settings-example.toml settings.toml
# Edit settings.toml and add your API keys
```

### Downloader

```bash
uv run download                    # recent 7 days (default)
uv run download --recent 30        # last 30 days
uv run download --all              # all current-year daily files
uv run download --annual           # historical backfile (1951-2024)
uv run download --force            # redownload existing files
uv run download --verbose          # debug logging
```

| Option | Short | Description |
|--------|-------|-------------|
| `--output-dir` | `-o` | Output directory (default: `./ttab_data`) |
| `--api-key` | `-k` | USPTO API key (overrides settings.toml) |
| `--year` | `-y` | Specific year (current year only, daily dataset) |
| `--recent` | `-r` | Download files from the last N days |
| `--all` | `-a` | Download all available files from daily dataset |
| `--annual` | | Download annual/historical dataset (1951-2024) |
| `--force` | `-f` | Force redownload of existing files |
| `--verbose` | `-v` | Enable verbose logging |

### Parser

```bash
uv run parse                       # parse ttab_data/ (default)
uv run parse /path/to/xml/dir      # custom directory
uv run parse --no-courtlistener    # skip Federal Circuit lookup
uv run parse --limit 10            # process only 10 opinions
uv run parse -o output.csv         # custom output file
uv run parse --verbose             # debug logging
```

| Option | Short | Description |
|--------|-------|-------------|
| `input_dir` | | Directory containing TTAB XML files |
| `--output` | `-o` | Output CSV file (default: `ttab_opinions.csv`) |
| `--no-courtlistener` | | Disable Federal Circuit appeal lookup |
| `--log-file` | | Path to log file (default: console only) |
| `--verbose` | `-v` | Enable verbose logging |
| `--limit` | | Limit number of opinions to process |

### Typical CLI workflow

```bash
# Download last 30 days
uv run download --recent 30 --verbose

# Parse and export CSV
uv run parse --output ttab_results.csv --verbose

# Inspect results
head -n 20 ttab_results.csv
```

## Configuration

Copy `settings-example.toml` to `settings.toml` (gitignored) and fill in values.

```toml
[USPTO]
api_key = "your-uspto-api-key"

[CourtListener]
api_token = "your-courtlistener-token"   # optional

[database]
url = "postgresql://ttab:ttab@localhost:5432/ttab"

[redis]
url = "redis://localhost:6379/0"
```

`DATABASE_URL` and `REDIS_URL` environment variables override the TOML values — this is how Docker Compose injects the container hostnames.

### Settings reference

| Section | Key | Required | Description |
|---------|-----|----------|-------------|
| `[USPTO]` | `api_key` | **Yes** (downloader) | USPTO Open Data Portal key |
| `[CourtListener]` | `api_token` | No | CourtListener token for Federal Circuit lookups |
| `[database]` | `url` | Yes (worker) | PostgreSQL connection URL |
| `[redis]` | `url` | Yes (worker/beat) | Redis connection URL |

## Automated pipeline (Celery)

The three pipeline stages run as Celery tasks and are chained on success:

```
download_task  →  parse_task  →  enrich_task
```

| Task | What it does |
|------|-------------|
| `download_task` | Calls `TTABDownloader.download_recent_daily()`, then chains the next two tasks |
| `parse_task` | Calls `TTABParser.parse_directory()`, upserts each `TTABOpinion` into PostgreSQL |
| `enrich_task` | Queries opinions where `federal_circuit_appeal_id IS NULL`, calls CourtListener, updates the FK |

Each task retries up to 3 times (60-second delay) on network/IO failures. Re-runs are idempotent — `case_number` is the upsert key for both opinion and appeal records.

The worker calls `init_db()` on startup (via the `worker_ready` signal), which creates the database tables if they don't exist.

### Docker services

| Service | Image | Role |
|---------|-------|------|
| `redis` | `redis:8-alpine` | Celery broker and result backend |
| `postgres` | `postgres:17-alpine` | Persistent opinion storage |
| `worker` | (built from `Dockerfile`) | Executes tasks from the queue |
| `beat` | (built from `Dockerfile`) | Fires the daily schedule (exactly one instance) |

Beat and worker are separate containers so that scaling worker replicas does not duplicate the scheduler.

## Database schema

Two tables, created automatically at worker startup:

**`ttab_opinions`** — one row per TTAB opinion

| Column | Type | Notes |
|--------|------|-------|
| `case_number` | `varchar` | Unique, upsert key |
| `proceeding_type` | `varchar` | opposition, cancellation, appeal, … |
| `filing_date`, `decision_date` | `timestamp` | |
| `outcome`, `winner` | `varchar` / `text` | |
| `parties`, `judges`, `subject_marks`, `law_firms` | `jsonb` | Nested data |
| `federal_circuit_appeal_id` | FK | Null until enriched |

**`federal_circuit_appeals`** — one row per matched Federal Circuit case

| Column | Type |
|--------|------|
| `case_number` | Unique, upsert key |
| `case_name`, `citation`, `docket_number` | `text` |
| `filing_date`, `decision_date` | `timestamp` |
| `outcome`, `courtlistener_url`, `courtlistener_id` | `text` |
| `judges` | `jsonb` |

## Testing

```bash
uv run pytest                           # all tests
uv run pytest -m "not integration"     # skip integration tests (no network)
uv run pytest tests/test_models.py     # single file
uv run pytest -k "test_parse_date"     # single test by name
uv run pytest -v                       # verbose output
```

76 unit tests cover all core modules:

| File | Tests | What's covered |
|------|-------|----------------|
| `tests/test_models.py` | 26 | Data classes, enums, validation |
| `tests/test_utils.py` | 27 | Text cleaning, date parsing, XML handling |
| `tests/test_downloader.py` | 11 | File detection, duplicate checking |
| `tests/test_parser.py` | 13 | XML parsing, party mapping |

## Project structure

```
.
├── bin/
│   └── run.sh                   # Start Docker services and wait for ready
├── src/
│   ├── ttab_downloader.py       # USPTO data download
│   ├── ttab_parser.py           # XML parser and data extractor
│   ├── courtlistener_client.py  # Federal Circuit API client
│   ├── models.py                # Dataclasses and enums
│   ├── utils.py                 # Utility functions
│   ├── celery_app.py            # Celery app instance and Beat schedule
│   ├── tasks.py                 # download_task, parse_task, enrich_task
│   ├── database.py              # SQLAlchemy engine and session factory
│   ├── db_models.py             # ORM models (TTABOpinionRecord, etc.)
│   └── settings.py              # Settings loader (TOML + env var override)
├── tests/
│   ├── conftest.py
│   ├── test_downloader.py
│   ├── test_models.py
│   ├── test_parser.py
│   └── test_utils.py
├── ttab_data/                   # Downloaded XML files (created automatically)
├── Dockerfile                   # Worker and beat container image
├── docker-compose.yml           # redis, postgres, worker, beat services
├── pyproject.toml               # Dependencies and entry points
├── settings-example.toml        # Settings template
├── settings.toml                # Your API keys (gitignored — create from example)
└── README.md
```

## Data sources

### USPTO Open Data Portal

- **Daily dataset (TTABTDXF)**: Current-year daily XML files
- **Annual dataset (TTABYR)**: Historical backfile (October 1951 – December 2024)
- **API endpoint**: `https://api.uspto.gov/api/v1/datasets/products/`
- **Rate limits**: 60 req/min (standard), 4 req/min (bulk file downloads)

### CourtListener API

- **Federal Circuit appeals**: REST API v4, searched by case number then party names
- **Authentication**: `api_token` under `[CourtListener]` in `settings.toml`
- **Rate limit**: 1 request/second (enforced inside `CourtListenerClient`)
- **Optional**: omit the token or use `--no-courtlistener` to skip

## Troubleshooting

**`API access forbidden` / 403** — Set `api_key` under `[USPTO]` in `settings.toml`.

**No XML files found** — Verify `ttab_data/` has files (`ls ttab_data/`); re-run the downloader with `--verbose`.

**Worker can't connect to postgres/redis** — Confirm the services are running (`docker compose ps`) and that `DATABASE_URL` / `REDIS_URL` are set correctly.

**Memory issues parsing large files** — Use `--limit` to process a subset, or disable CourtListener with `--no-courtlistener`.

## License

Software license TBD.

TTAB data is public domain from the USPTO.
