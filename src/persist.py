"""
Shared persistence helpers for the TTAB pipeline.

Used by both the Celery task (src/tasks.py) and the CLI parser
(src/ttab_parser.py) so the upsert logic lives in one place.
"""

from dataclasses import asdict

from src.models import TTABOpinion, FederalCircuitAppeal


def opinion_to_jsonb(opinion: TTABOpinion) -> dict:
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


def upsert_opinion(session, opinion: TTABOpinion) -> "TTABOpinionRecord":  # noqa: F821
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
    serialized = opinion_to_jsonb(opinion)
    record.parties = serialized.get("parties")
    record.judges = serialized.get("judges")
    record.subject_marks = serialized.get("subject_marks")
    record.law_firms = serialized.get("law_firms")

    return record


def upsert_appeal(session, appeal: FederalCircuitAppeal) -> "FederalCircuitAppealRecord":  # noqa: F821
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
