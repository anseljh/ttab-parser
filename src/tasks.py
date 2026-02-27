"""
Celery tasks for the TTAB pipeline.

Three tasks, chained in order:
  download_task  → parse_task  → enrich_task

Each task is a thin wrapper around the existing classes; no core logic lives
here.  Network/IO failures are retried up to 3 times with a 60-second delay.
"""

import logging
from dataclasses import asdict
from pathlib import Path

from celery import chain

from src.celery_app import app
from src.models import TTABOpinion, FederalCircuitAppeal

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _opinion_to_jsonb(opinion: TTABOpinion) -> dict:
    """Serialize a TTABOpinion dataclass to a plain dict suitable for JSONB storage."""

    def _serialize(obj):
        if hasattr(obj, "__dataclass_fields__"):
            return {k: _serialize(v) for k, v in asdict(obj).items()}
        if hasattr(obj, "value"):          # Enum
            return obj.value
        if hasattr(obj, "isoformat"):      # datetime
            return obj.isoformat()
        if isinstance(obj, list):
            return [_serialize(i) for i in obj]
        if isinstance(obj, dict):
            return {k: _serialize(v) for k, v in obj.items()}
        return obj

    return _serialize(opinion)


def _upsert_opinion(session, opinion: TTABOpinion) -> "TTABOpinionRecord":  # noqa: F821
    """Insert or update a TTABOpinionRecord, matched on case_number."""
    from src.db_models import TTABOpinionRecord

    record = (
        session.query(TTABOpinionRecord)
        .filter_by(case_number=opinion.case_number)
        .first()
    )
    if record is None:
        record = TTABOpinionRecord(case_number=opinion.case_number)
        session.add(record)

    record.proceeding_number = opinion.proceeding_number
    record.proceeding_type = opinion.proceeding_type.value if opinion.proceeding_type else None
    record.case_title = opinion.case_title
    record.filing_date = opinion.filing_date
    record.decision_date = opinion.decision_date
    record.outcome = opinion.outcome.value if opinion.outcome else None
    record.outcome_description = opinion.outcome_description
    record.winner = opinion.winner
    record.appeal_indicated = opinion.appeal_indicated
    record.source_file = opinion.source_file

    # Serialize nested lists to plain-dict JSONB
    serialized = _opinion_to_jsonb(opinion)
    record.parties = serialized.get("parties")
    record.judges = serialized.get("judges")
    record.subject_marks = serialized.get("subject_marks")
    record.law_firms = serialized.get("law_firms")

    return record


def _upsert_appeal(session, appeal: FederalCircuitAppeal) -> "FederalCircuitAppealRecord":  # noqa: F821
    """Insert or update a FederalCircuitAppealRecord, matched on case_number."""
    from src.db_models import FederalCircuitAppealRecord

    record = (
        session.query(FederalCircuitAppealRecord)
        .filter_by(case_number=appeal.case_number)
        .first()
    )
    if record is None:
        record = FederalCircuitAppealRecord(case_number=appeal.case_number)
        session.add(record)

    record.case_name = appeal.case_name
    record.filing_date = appeal.filing_date
    record.decision_date = appeal.decision_date
    record.outcome = appeal.outcome
    record.citation = appeal.citation
    record.courtlistener_url = appeal.courtlistener_url
    record.courtlistener_id = appeal.courtlistener_id
    record.docket_number = appeal.docket_number
    record.judges = appeal.judges  # list of strings — already JSON-serializable

    return record


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

@app.task(bind=True, max_retries=3, default_retry_delay=60)
def download_task(self, days: int = 1):
    """
    Download recent TTAB daily files from the USPTO.

    On success, chains parse_task → enrich_task.
    """
    from src.ttab_downloader import TTABDownloader

    logger.info("download_task started (days=%d)", days)
    try:
        downloader = TTABDownloader(output_dir="./ttab_data")
        count = downloader.download_recent_daily(days=days)
        logger.info("download_task finished: %d file(s) downloaded", count)
    except Exception as exc:
        logger.exception("download_task failed: %s", exc)
        raise self.retry(exc=exc)

    # Chain the remaining pipeline regardless of download count (files may
    # already exist from a prior run — parse/enrich should still run).
    chain(parse_task.si(), enrich_task.si()).delay()


@app.task(bind=True, max_retries=3, default_retry_delay=60)
def parse_task(self):
    """
    Parse XML files in ttab_data/ and upsert opinions into PostgreSQL.

    CourtListener enrichment is disabled here; enrich_task handles it
    separately so rate limiting does not block the parse phase.
    """
    from src.ttab_parser import TTABParser
    from src.database import get_session

    logger.info("parse_task started")
    try:
        parser = TTABParser(enable_courtlistener=False)
        session = get_session()
        upserted = 0
        try:
            for opinion in parser.parse_directory(Path("ttab_data")):
                _upsert_opinion(session, opinion)
                upserted += 1
                # Commit in batches of 100 to limit memory usage
                if upserted % 100 == 0:
                    session.commit()
                    logger.debug("Committed batch (%d so far)", upserted)
            session.commit()
        finally:
            session.close()

        logger.info("parse_task finished: %d opinion(s) upserted", upserted)
    except Exception as exc:
        logger.exception("parse_task failed: %s", exc)
        raise self.retry(exc=exc)


@app.task(bind=True, max_retries=3, default_retry_delay=60)
def enrich_task(self):
    """
    Enrich opinions with Federal Circuit appeal data from CourtListener.

    Only processes opinions where federal_circuit_appeal_id IS NULL, so
    re-runs skip already-enriched rows.
    """
    from src.courtlistener_client import CourtListenerClient
    from src.database import get_session
    from src.db_models import TTABOpinionRecord
    from src.models import TTABOpinion, Party, Judge, TrademarkMark, Attorney, ProceedingType

    logger.info("enrich_task started")
    try:
        client = CourtListenerClient()
        if not client.enabled:
            logger.warning(
                "CourtListener client is disabled (no API token). Skipping enrichment."
            )
            return

        session = get_session()
        enriched = 0
        try:
            unenriched = (
                session.query(TTABOpinionRecord)
                .filter(TTABOpinionRecord.federal_circuit_appeal_id.is_(None))
                .all()
            )
            logger.info(
                "enrich_task: %d opinion(s) pending enrichment", len(unenriched)
            )

            for record in unenriched:
                # Reconstruct a minimal TTABOpinion for the CourtListener lookup
                opinion = TTABOpinion(
                    case_number=record.case_number,
                    proceeding_number=record.proceeding_number,
                    case_title=record.case_title,
                    decision_date=record.decision_date,
                )
                # Rehydrate party names so the name-based search works.
                # Skip names longer than 100 chars — they're garbage strings
                # (IDs, addresses, etc.) from the XML parser, not real names,
                # and will produce URLs that cause 502 errors from CourtListener.
                if record.parties:
                    for p in record.parties:
                        name = p.get("name") or ""
                        if 0 < len(name) <= 100:
                            opinion.parties.append(Party(name=name))

                appeal = client.find_federal_circuit_appeal(opinion)
                if appeal is None:
                    continue

                appeal_record = _upsert_appeal(session, appeal)
                session.flush()  # get appeal_record.id before assigning FK
                record.federal_circuit_appeal_id = appeal_record.id
                session.commit()
                enriched += 1
                logger.debug(
                    "Enriched opinion %s with appeal %s",
                    record.case_number,
                    appeal.case_number,
                )
        finally:
            session.close()

        logger.info("enrich_task finished: %d opinion(s) enriched", enriched)
    except Exception as exc:
        logger.exception("enrich_task failed: %s", exc)
        raise self.retry(exc=exc)
