"""
Celery tasks for the TTAB pipeline.

Three tasks, chained in order:
  download_task  → parse_task  → enrich_task

Each task is a thin wrapper around the existing classes; no core logic lives
here.  Network/IO failures are retried up to 3 times with a 60-second delay.
"""

import logging
from pathlib import Path

from celery import chain

from src.celery_app import app
from src.models import TTABOpinion, FederalCircuitAppeal
from src.persist import opinion_to_jsonb, upsert_opinion, upsert_appeal

logger = logging.getLogger(__name__)

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

    logger.info(f"download_task started (days={days})")
    try:
        downloader = TTABDownloader(output_dir="./ttab_data")
        count = downloader.download_recent_daily(days=days)
        logger.info(f"download_task finished: {count} file(s) downloaded")
    except Exception as exc:
        logger.exception(f"download_task failed: {exc}")
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
                upsert_opinion(session, opinion)
                upserted += 1
                # Commit in batches of 100 to limit memory usage
                if upserted % 100 == 0:
                    session.commit()
                    logger.debug(f"Committed batch ({upserted} so far)")
            session.commit()
        finally:
            session.close()

        logger.info(f"parse_task finished: {upserted} opinion(s) upserted")
    except Exception as exc:
        logger.exception(f"parse_task failed: {exc}")
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
            total = len(unenriched)
            logger.info(f"enrich_task: {total} opinion(s) pending enrichment")

            for checked, record in enumerate(unenriched, 1):
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
                    if checked % 50 == 0:
                        logger.info(f"enrich_task: checked {checked}/{total}, {enriched} match(es) so far")
                    continue

                appeal_record = upsert_appeal(session, appeal)
                session.flush()  # get appeal_record.id before assigning FK
                record.federal_circuit_appeal_id = appeal_record.id
                session.commit()
                enriched += 1
                logger.info(
                    f"enrich_task: matched {record.case_number} → appeal {appeal.case_number} ({enriched} total)"
                )
        finally:
            session.close()

        logger.info(f"enrich_task finished: {enriched} opinion(s) enriched")
    except Exception as exc:
        logger.exception(f"enrich_task failed: {exc}")
        raise self.retry(exc=exc)
