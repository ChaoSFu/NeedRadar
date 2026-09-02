from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    ARRAY,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Created, Timestamped

GEO_PRECISIONS = ("country", "province", "city", "unknown")
GEO_BASES = ("search_origin", "audience_profile", "content_location", "platform_scope", "unknown")
COMPARABILITIES = ("absolute", "relative_within_request", "relative_within_platform", "ordinal")
REDISTRIBUTION_SCOPES = ("internal_only", "derived_only", "full")


def _in(column: str, allowed: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(value) for value in allowed)})"


class SignalSource(Timestamped):
    __tablename__ = "signal_sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(Text, unique=True)
    platform: Mapped[str] = mapped_column(Text)
    access_mode: Mapped[str] = mapped_column(Text)
    # Markets this source produces VALID demand data for. Google Trends must not
    # list 'CN': Google is unusable in mainland China, so its China slice reflects
    # a tiny unrepresentative population. Cross-source confirmation counts only
    # sources eligible for the market being scored.
    valid_markets: Mapped[list[str]] = mapped_column(ARRAY(Text))
    # Whether data derived from this source may be shown to end users. Paid data
    # products commonly restrict redistribution; as a column the constraint is
    # enforced by code rather than remembered by a person.
    redistribution_scope: Mapped[str] = mapped_column(Text, default="internal_only")
    is_active: Mapped[bool] = mapped_column(default=True)

    __table_args__ = (
        CheckConstraint(_in("redistribution_scope", REDISTRIBUTION_SCOPES), name="signal_sources_scope_check"),
    )


class ImportBatch(Created):
    __tablename__ = "import_batches"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("signal_sources.id"))
    adapter: Mapped[str] = mapped_column(Text)
    adapter_version: Mapped[str] = mapped_column(Text)
    collection_method: Mapped[str] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(Text)
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    accepted_count: Mapped[int] = mapped_column(Integer, default=0)
    rejected_count: Mapped[int] = mapped_column(Integer, default=0)
    error_summary: Mapped[str | None] = mapped_column(Text)


class RawSignal(Created):
    """Immutable source evidence. Carries no metrics: see SignalMetric."""

    __tablename__ = "raw_signals"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("signal_sources.id"))
    import_batch_id: Mapped[int] = mapped_column(ForeignKey("import_batches.id"))

    query_text: Mapped[str] = mapped_column(Text)
    content_excerpt: Mapped[str | None] = mapped_column(Text)
    source_record_id: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(Text)

    observed_at: Mapped[date] = mapped_column(Date)          # what the observation is ABOUT
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))  # when WE fetched it

    country_code: Mapped[str] = mapped_column(String(2))
    province_code: Mapped[str | None] = mapped_column(Text)
    city_code: Mapped[str | None] = mapped_column(Text)
    geo_precision: Mapped[str] = mapped_column(Text)
    # "Guangdong" means three different things and they must never be merged:
    # the search came from there, the audience lives there, the content mentions it.
    geo_basis: Mapped[str] = mapped_column(Text)
    language: Mapped[str | None] = mapped_column(Text)

    raw_payload: Mapped[dict] = mapped_column(JSONB)
    raw_payload_hash: Mapped[str] = mapped_column(Text)
    collector_version: Mapped[str] = mapped_column(Text)

    __table_args__ = (
        CheckConstraint(_in("geo_precision", GEO_PRECISIONS), name="raw_signals_geo_precision_check"),
        CheckConstraint(_in("geo_basis", GEO_BASES), name="raw_signals_geo_basis_check"),
        UniqueConstraint("source_id", "raw_payload_hash", name="raw_signals_dedupe"),
    )


class SignalMetric(Created):
    """Immutable measurement. One row per measured quantity per window."""

    __tablename__ = "signal_metrics"

    id: Mapped[int] = mapped_column(primary_key=True)
    raw_signal_id: Mapped[int] = mapped_column(ForeignKey("raw_signals.id"))
    # Never renamed to fit another source's vocabulary: a 千瓜 heat value is stored
    # as hot_keyword_index, never as search_interest.
    metric_name: Mapped[str] = mapped_column(Text)
    raw_value: Mapped[Decimal] = mapped_column(Numeric)
    unit: Mapped[str] = mapped_column(Text)
    window_start: Mapped[date] = mapped_column(Date)
    window_end: Mapped[date] = mapped_column(Date)
    # Whether this value may be compared with another at all. Google Trends is
    # relative_within_request: values from different requests are NOT comparable
    # unless the requests shared a scaling anchor.
    comparability: Mapped[str] = mapped_column(Text)

    __table_args__ = (
        CheckConstraint(_in("comparability", COMPARABILITIES), name="signal_metrics_comparability_check"),
        UniqueConstraint(
            "raw_signal_id", "metric_name", "window_start", "window_end", name="signal_metrics_unique"
        ),
    )


class MetricNormalization(Created):
    """Derived, versioned and recomputable. Never written into the immutable tables."""

    __tablename__ = "metric_normalizations"

    id: Mapped[int] = mapped_column(primary_key=True)
    signal_metric_id: Mapped[int] = mapped_column(ForeignKey("signal_metrics.id"))
    normalization_version: Mapped[str] = mapped_column(Text)
    method: Mapped[str] = mapped_column(Text)
    # Identity of the reference distribution this value was computed against.
    scope_key: Mapped[str] = mapped_column(Text)
    reference_n: Mapped[int] = mapped_column(Integer)
    normalized_value: Mapped[Decimal] = mapped_column(Numeric)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("signal_metric_id", "normalization_version", name="metric_normalizations_unique"),
    )
