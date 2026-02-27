#!/usr/bin/env python3
"""
Quick sanity check: print the first five rows of ttab_opinions.

Usage:
    uv run python check_db.py
"""

from src.database import get_session
from src.db_models import TTABOpinionRecord


def check_db():
    session = get_session()
    try:
        rows = session.query(TTABOpinionRecord).order_by(TTABOpinionRecord.id).limit(5).all()
        if not rows:
            print("No rows found in ttab_opinions.")
            return
        for row in rows:
            print(
                f"id={row.id}"
                f"  case_number={row.case_number}"
                f"  type={row.proceeding_type}"
                f"  outcome={row.outcome}"
                f"  decision_date={row.decision_date.date() if row.decision_date else None}"
                f"  title={row.case_title!r}"
            )
    finally:
        session.close()


if __name__ == "__main__":
    check_db()
