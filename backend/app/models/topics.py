from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, Timestamped


class DemandTopic(Timestamped):
    __tablename__ = "demand_topics"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(Text, unique=True)
    name: Mapped[str] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(Text)
    # 'identity@1' in Phase 2a: one (query_text, market) is one topic. Degenerate
    # but valid — deterministic and stable by construction, no model involved.
    # 'embedding@1' arrives in 2b, together with the centroid column and pgvector.
    clustering_version: Mapped[str] = mapped_column(Text)
    embedding_model: Mapped[str | None] = mapped_column(Text)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(Text, default="active")


class TopicQuery(Base):
    """Per-platform aliases of one demand.

    "AI 英文面试" (Xiaohongshu) and "AI interview practice" (Google Trends) are the
    same demand. Without this table cross-source confirmation cannot work at all.
    In 2a these are merged by hand, which also produces the labelled set that
    calibrating TOPIC_MATCH_THRESHOLD needs in 2b.
    """

    __tablename__ = "topic_queries"

    topic_id: Mapped[int] = mapped_column(ForeignKey("demand_topics.id"), primary_key=True)
    platform: Mapped[str] = mapped_column(Text, primary_key=True)
    query_text: Mapped[str] = mapped_column(Text, primary_key=True)
    market: Mapped[str] = mapped_column(Text)
    is_canonical: Mapped[bool] = mapped_column(default=False)


class TopicSignal(Base):
    __tablename__ = "topic_signals"

    topic_id: Mapped[int] = mapped_column(ForeignKey("demand_topics.id"), primary_key=True)
    raw_signal_id: Mapped[int] = mapped_column(ForeignKey("raw_signals.id"), primary_key=True)
    relevance: Mapped[Decimal] = mapped_column(Numeric)
