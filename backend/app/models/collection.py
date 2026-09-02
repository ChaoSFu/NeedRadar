from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, Created


class WatchQuery(Base):
    """The stable query set that gets collected repeatedly.

    Momentum is a time derivative, so it exists only because the same queries are
    collected again and again. A Phase 2 that imports once cannot produce it.
    """

    __tablename__ = "watch_queries"

    id: Mapped[int] = mapped_column(primary_key=True)
    query_text: Mapped[str] = mapped_column(Text)
    platform: Mapped[str] = mapped_column(Text)
    market: Mapped[str] = mapped_column(Text)
    topic_id: Mapped[int | None] = mapped_column(ForeignKey("demand_topics.id"))
    cadence: Mapped[str] = mapped_column(Text)
    # Deliberately uninteresting keywords, imported to widen the reference
    # distribution. Raising MIN_REFERENCE_N fixes variance; only control terms
    # fix the bias of having picked every keyword for being interesting.
    is_control: Mapped[bool] = mapped_column(default=False)
    is_active: Mapped[bool] = mapped_column(default=True)

    __table_args__ = (UniqueConstraint("query_text", "platform", "market", name="watch_queries_unique"),)


class CollectionRun(Created):
    __tablename__ = "collection_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(Text)
    import_batch_id: Mapped[int | None] = mapped_column(ForeignKey("import_batches.id"))
