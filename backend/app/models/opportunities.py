from datetime import date, datetime

from sqlalchemy import (
    ARRAY,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Created, Timestamped

STATUSES = ("new", "watching", "testing", "validated", "rejected")


class Opportunity(Timestamped):
    """A region-specific decision object.

    Narrative fields are nullable on purpose. Until LLM extraction lands in Phase
    2b they stay empty and the UI says so, because real scores wrapped around a
    generic template would be worse than no narrative at all.
    """

    __tablename__ = "opportunities"

    id: Mapped[int] = mapped_column(primary_key=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("demand_topics.id"))
    market: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(Text)
    one_line_summary: Mapped[str | None] = mapped_column(Text)

    problem: Mapped[str | None] = mapped_column(Text)
    target_user: Mapped[str | None] = mapped_column(Text)
    job_to_be_done: Mapped[str | None] = mapped_column(Text)
    pain_points: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    workarounds: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    ai_angle: Mapped[str | None] = mapped_column(Text)
    possible_mvp: Mapped[str | None] = mapped_column(Text)
    why_now: Mapped[str | None] = mapped_column(Text)

    demand_score: Mapped[int | None] = mapped_column(Integer)
    momentum_score: Mapped[int | None] = mapped_column(Integer)
    intent_score: Mapped[int | None] = mapped_column(Integer)
    ai_fit_score: Mapped[int | None] = mapped_column(Integer)
    supply_gap_score: Mapped[int | None] = mapped_column(Integer)
    market_score: Mapped[int | None] = mapped_column(Integer)
    confidence_score: Mapped[int | None] = mapped_column(Integer)

    # True when the reference distribution was too small to trust a percentile.
    # The demand score is then absent rather than estimated, and market_score is
    # a partial result.
    demand_score_suppressed: Mapped[bool] = mapped_column(default=False)
    scoring_version: Mapped[str | None] = mapped_column(Text)
    normalization_version: Mapped[str | None] = mapped_column(Text)

    status: Mapped[str] = mapped_column(Text, default="new")
    is_demo: Mapped[bool] = mapped_column(default=False)

    __table_args__ = (
        CheckConstraint(
            f"status IN ({', '.join(repr(value) for value in STATUSES)})",
            name="opportunities_status_check",
        ),
        UniqueConstraint("topic_id", "market", name="opportunities_topic_market_unique"),
    )


class OpportunityEvidence(Created):
    __tablename__ = "opportunity_evidence"

    id: Mapped[int] = mapped_column(primary_key=True)
    opportunity_id: Mapped[int] = mapped_column(ForeignKey("opportunities.id"))
    raw_signal_id: Mapped[int] = mapped_column(ForeignKey("raw_signals.id"))
    evidence_type: Mapped[str] = mapped_column(Text)
    strength: Mapped[str | None] = mapped_column(Text)
    excerpt: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        UniqueConstraint("opportunity_id", "raw_signal_id", name="opportunity_evidence_unique"),
    )


class OpportunitySnapshot(Created):
    """Time series of scores.

    Two snapshots are comparable only when scoring_version and
    normalization_version match; the API must not chart across a version change
    without saying so.
    """

    __tablename__ = "opportunity_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    opportunity_id: Mapped[int] = mapped_column(ForeignKey("opportunities.id"))
    snapshot_date: Mapped[date] = mapped_column(Date)

    demand_score: Mapped[int | None] = mapped_column(Integer)
    momentum_score: Mapped[int | None] = mapped_column(Integer)
    intent_score: Mapped[int | None] = mapped_column(Integer)
    ai_fit_score: Mapped[int | None] = mapped_column(Integer)
    supply_gap_score: Mapped[int | None] = mapped_column(Integer)
    market_score: Mapped[int | None] = mapped_column(Integer)
    confidence_score: Mapped[int | None] = mapped_column(Integer)
    demand_score_suppressed: Mapped[bool] = mapped_column(default=False)

    signal_count: Mapped[int] = mapped_column(Integer, default=0)
    # Counted only among sources whose valid_markets contains this market.
    sources_confirming: Mapped[int] = mapped_column(Integer, default=0)
    sources_available: Mapped[int] = mapped_column(Integer, default=0)

    scoring_version: Mapped[str | None] = mapped_column(Text)
    normalization_version: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        UniqueConstraint("opportunity_id", "snapshot_date", name="opportunity_snapshots_unique"),
    )
