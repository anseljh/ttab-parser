"""
SQLAlchemy ORM models for persisting TTAB opinions to PostgreSQL.

Two tables:
  - ttab_opinions             (mirrors TTABOpinion dataclass)
  - federal_circuit_appeals   (mirrors FederalCircuitAppeal dataclass)

Nested list/object data (parties, judges, marks, law_firms) is stored as
JSONB for query flexibility without full normalization overhead.
case_number is the upsert key — re-runs are idempotent.
"""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class FederalCircuitAppealRecord(Base):
    __tablename__ = "federal_circuit_appeals"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    case_number: Mapped[str | None] = mapped_column(String(100), unique=True, index=True)
    case_name: Mapped[str | None] = mapped_column(Text)
    filing_date: Mapped[datetime | None] = mapped_column(DateTime)
    decision_date: Mapped[datetime | None] = mapped_column(DateTime)
    outcome: Mapped[str | None] = mapped_column(String(50))
    citation: Mapped[str | None] = mapped_column(String(200))
    courtlistener_url: Mapped[str | None] = mapped_column(Text)
    courtlistener_id: Mapped[str | None] = mapped_column(String(100))
    docket_number: Mapped[str | None] = mapped_column(String(100))
    # List of judge name strings
    judges: Mapped[list | None] = mapped_column(JSONB)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Back-reference from opinions
    opinions: Mapped[list["TTABOpinionRecord"]] = relationship(
        "TTABOpinionRecord", back_populates="federal_circuit_appeal"
    )


class TTABOpinionRecord(Base):
    __tablename__ = "ttab_opinions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # Case identification
    case_number: Mapped[str | None] = mapped_column(String(100), unique=True, index=True)
    proceeding_number: Mapped[str | None] = mapped_column(String(100))
    proceeding_type: Mapped[str | None] = mapped_column(String(50))
    case_title: Mapped[str | None] = mapped_column(Text)

    # Dates
    filing_date: Mapped[datetime | None] = mapped_column(DateTime)
    decision_date: Mapped[datetime | None] = mapped_column(DateTime)

    # Outcome
    outcome: Mapped[str | None] = mapped_column(String(50))
    outcome_description: Mapped[str | None] = mapped_column(Text)
    winner: Mapped[str | None] = mapped_column(Text)
    appeal_indicated: Mapped[bool] = mapped_column(Boolean, default=False)

    # Nested data stored as JSONB (list of dicts matching the dataclass fields)
    parties: Mapped[list | None] = mapped_column(JSONB)
    judges: Mapped[list | None] = mapped_column(JSONB)
    subject_marks: Mapped[list | None] = mapped_column(JSONB)
    law_firms: Mapped[list | None] = mapped_column(JSONB)

    # Source
    source_file: Mapped[str | None] = mapped_column(Text)

    # FK to Federal Circuit appeal (nullable — most opinions have no appeal)
    federal_circuit_appeal_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("federal_circuit_appeals.id"), nullable=True, index=True
    )
    federal_circuit_appeal: Mapped[FederalCircuitAppealRecord | None] = relationship(
        "FederalCircuitAppealRecord", back_populates="opinions"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_ttab_opinions_decision_date", "decision_date"),
        Index("ix_ttab_opinions_proceeding_type", "proceeding_type"),
    )
