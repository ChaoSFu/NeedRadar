# Phase 2 — Data Foundation

Phase 2 delivers one thing: **real market data enters NeedRadar, repeatedly, and
its meaning is never lost on the way in.** Watchlist mutations, validation
briefs, and UI refinement are explicitly out of scope.

This document supersedes the `raw_signals` metric columns described in
[backend/SCHEMA.md](backend/SCHEMA.md). It records the design decisions that are
expensive to reverse, so they are settled before code is written.

## The four failures this design exists to prevent

1. **Metric collapse.** Google Trends returns search interest on a 0–100 scale
   that is relative to the request; 百度指数 returns its own index; 千瓜 returns a
   heat value; Reddit returns upvotes. Storing these in one `search_volume`
   column is a category error that corrupts every downstream score silently.
2. **Derived values contaminating evidence.** `raw_signals` is declared immutable.
   A `normalized_value` written beside `raw_value` forces a choice between
   mutating immutable evidence and never changing the normalization algorithm.
3. **No time axis.** Momentum is 25% of Market Score and carries the entire "why
   now" claim. It is a time derivative. A one-shot import cannot produce it, and
   a pipeline that only ever ran once will still report green.
4. **Unstable clusters.** If a DemandTopic is not the same object across runs,
   its time series is meaningless — momentum silently measures cluster churn
   instead of demand.

## Layering

```text
Adapter (fetch only)
   └─ RawSignalDraft
        └─ Ingestion: dedupe → persist
             ├─ raw_signals      (immutable)
             └─ signal_metrics   (immutable)
                  └─ metric_normalizations  (derived, versioned, recomputable)
                       └─ Topic assignment (deterministic)
                            └─ demand_topics + topic_queries
                                 └─ Scoring (deterministic, versioned)
                                      └─ opportunities + opportunity_snapshots
                                           └─ LLM: label / JTBD / pain / AI fit
```

Two invariants hold across every layer:

- **Nothing above the ingestion line writes to the database.** Adapters return
  drafts; only the ingestion pipeline persists.
- **The LLM never produces a number that enters a score.** It labels, extracts,
  and explains. Demand and Momentum come from data.

## Schema

### `signal_sources`

```sql
CREATE TABLE signal_sources (
    id                    bigserial PRIMARY KEY,
    name                  text NOT NULL UNIQUE,
    platform              text NOT NULL,
    access_mode           text NOT NULL,   -- api | export | manual
    -- Markets this source produces VALID demand data for. Google Trends must
    -- not list 'CN': Google is not usable in mainland China, so its China slice
    -- reflects a tiny unrepresentative population. Cross-source confirmation
    -- counts only sources eligible for the market being scored.
    valid_markets         text[] NOT NULL,
    -- Whether data derived from this source may be shown to end users. Paid
    -- data products commonly restrict redistribution; making this a column
    -- means the constraint is enforced by code, not remembered by a person.
    redistribution_scope  text NOT NULL,   -- internal_only | derived_only | full
    is_active             boolean NOT NULL DEFAULT true,
    created_at            timestamptz NOT NULL DEFAULT now(),
    updated_at            timestamptz NOT NULL DEFAULT now()
);
```

### `import_batches`

Every persisted row traces to exactly one batch.

```sql
CREATE TABLE import_batches (
    id                bigserial PRIMARY KEY,
    source_id         bigint NOT NULL REFERENCES signal_sources(id),
    adapter           text NOT NULL,
    adapter_version   text NOT NULL,
    collection_method text NOT NULL,   -- api_pull | file_export | manual_entry
    started_at        timestamptz NOT NULL DEFAULT now(),
    completed_at      timestamptz,
    status            text NOT NULL,   -- running | succeeded | failed | partial
    row_count         integer NOT NULL DEFAULT 0,
    accepted_count    integer NOT NULL DEFAULT 0,
    rejected_count    integer NOT NULL DEFAULT 0,
    error_summary     text
);
```

### `raw_signals` — immutable, and carries no metrics

```sql
CREATE TABLE raw_signals (
    id                bigserial PRIMARY KEY,
    source_id         bigint NOT NULL REFERENCES signal_sources(id),
    import_batch_id   bigint NOT NULL REFERENCES import_batches(id),

    query_text        text NOT NULL,
    content_excerpt   text,
    source_record_id  text,
    source_url        text,

    observed_at       date NOT NULL,        -- what the observation is ABOUT
    collected_at      timestamptz NOT NULL, -- when WE fetched it

    country_code      text NOT NULL,        -- ISO 3166-1 alpha-2
    province_code     text,                 -- ISO 3166-2 subdivision
    city_code         text,                 -- GB/T 2260 for CN; no ad-hoc codes
    geo_precision     text NOT NULL,        -- country | province | city | unknown
    -- "Guangdong" means three different things and they must not be merged:
    geo_basis         text NOT NULL,        -- search_origin | audience_profile
                                            -- | content_location | platform_scope
                                            -- | unknown
    language          text,

    raw_payload       jsonb NOT NULL,
    raw_payload_hash  text NOT NULL,
    collector_version text NOT NULL,
    created_at        timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT raw_signals_geo_precision_check
        CHECK (geo_precision IN ('country','province','city','unknown')),
    CONSTRAINT raw_signals_geo_basis_check
        CHECK (geo_basis IN ('search_origin','audience_profile',
                             'content_location','platform_scope','unknown')),
    CONSTRAINT raw_signals_dedupe UNIQUE (source_id, raw_payload_hash)
);
```

Rows are `INSERT`-only. There is no `UPDATE` path in the repository layer.

### `signal_metrics` — immutable, one row per measured quantity

```sql
CREATE TABLE signal_metrics (
    id             bigserial PRIMARY KEY,
    raw_signal_id  bigint NOT NULL REFERENCES raw_signals(id),
    metric_name    text NOT NULL,   -- search_interest | hot_keyword_index
                                    -- | engagement_count | note_count | rank | ...
    raw_value      numeric NOT NULL,
    unit           text NOT NULL,   -- index_0_100 | platform_index | count | rank
    window_start   date NOT NULL,
    window_end     date NOT NULL,

    -- Whether this value may be compared with another value at all. Google
    -- Trends is relative_within_request: two values from different requests are
    -- NOT comparable unless the requests shared a scaling anchor. The
    -- normalizer refuses to combine values whose comparability forbids it.
    comparability  text NOT NULL,   -- absolute | relative_within_request
                                    -- | relative_within_platform | ordinal
    created_at     timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT signal_metrics_unique
        UNIQUE (raw_signal_id, metric_name, window_start, window_end)
);
```

No metric is ever renamed to fit another source's vocabulary. A 千瓜 heat value
is stored as `hot_keyword_index`, never as `search_interest`.

### `metric_normalizations` — derived, versioned, recomputable

```sql
CREATE TABLE metric_normalizations (
    id                    bigserial PRIMARY KEY,
    signal_metric_id      bigint NOT NULL REFERENCES signal_metrics(id),
    normalization_version text NOT NULL,   -- e.g. 'demand-percentile@3'
    method                text NOT NULL,   -- percentile | zscore | minmax
    -- Identity of the reference distribution this value was computed against.
    scope_key             text NOT NULL,   -- 'platform=xhs;market=CN;
                                           --  category=education;window=2026-W35'
    reference_n           integer NOT NULL,
    normalized_value      numeric NOT NULL,  -- 0..100
    computed_at           timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT metric_normalizations_unique
        UNIQUE (signal_metric_id, normalization_version)
);
```

**Versioning rule.** Normalizations are never updated in place. Changing the
algorithm means writing rows under a new `normalization_version`, backfilling,
then flipping the active version in configuration. The previous version stays
readable, so historical snapshots remain interpretable instead of silently
changing meaning.

**Refusal rule.** A percentile over a self-selected keyword set is a percentile
of your own sampling bias, not of the market. When `reference_n <
MIN_REFERENCE_N`, **no row is written** and the downstream demand score is
absent rather than guessed. Absent is a legitimate, displayable state.

### `demand_topics`, `topic_queries`, `topic_signals`

```sql
CREATE TABLE demand_topics (
    id                 bigserial PRIMARY KEY,
    slug               text NOT NULL UNIQUE,
    name               text NOT NULL,
    summary            text,
    category           text,
    centroid           vector(1536) NOT NULL,   -- pgvector
    clustering_version text NOT NULL,
    first_seen_at      timestamptz NOT NULL,
    last_seen_at       timestamptz NOT NULL,
    status             text NOT NULL DEFAULT 'active',
    created_at         timestamptz NOT NULL DEFAULT now(),
    updated_at         timestamptz NOT NULL DEFAULT now()
);

-- The same demand is phrased differently per platform and per language.
-- "AI 英文面试" (XHS) and "AI interview practice" (Google Trends) are aliases of
-- one topic. Without this table, cross-source confirmation cannot work at all.
CREATE TABLE topic_queries (
    topic_id     bigint NOT NULL REFERENCES demand_topics(id),
    query_text   text NOT NULL,
    platform     text NOT NULL,
    market       text NOT NULL,
    is_canonical boolean NOT NULL DEFAULT false,
    PRIMARY KEY (topic_id, platform, query_text)
);

CREATE TABLE topic_signals (
    topic_id      bigint NOT NULL REFERENCES demand_topics(id),
    raw_signal_id bigint NOT NULL REFERENCES raw_signals(id),
    relevance     numeric NOT NULL,
    PRIMARY KEY (topic_id, raw_signal_id)
);
```

**Stability rule.** Assignment is deterministic and incremental: embed the
query, compare against existing centroids, attach to the nearest topic above
`TOPIC_MATCH_THRESHOLD`, and create a new topic only when nothing matches. An
LLM never decides cluster membership — non-deterministic grouping would make a
topic a different object between runs, and every momentum figure would then be
measuring cluster churn. The LLM names the topic after it exists.

### `opportunities` and `opportunity_snapshots`

Carry forward the columns in [backend/SCHEMA.md](backend/SCHEMA.md), plus:

| Column | On | Purpose |
| --- | --- | --- |
| `market` | both | The market being scored (`CN`, `SG`, `US`), not a display string |
| `scoring_version` | both | Which weights and formula produced these numbers |
| `normalization_version` | both | Which normalization the inputs came from |
| `demand_score_suppressed` | both | True when the reference set was too small |
| `sources_confirming` | snapshot | Eligible sources that moved together |
| `sources_available` | snapshot | Eligible sources for this market at that time |

Two snapshots are comparable only when `scoring_version` and
`normalization_version` match. The API must not chart across a version change
without saying so.

### `watch_queries` and `collection_runs` — the time axis

```sql
CREATE TABLE watch_queries (
    id         bigserial PRIMARY KEY,
    query_text text NOT NULL,
    platform   text NOT NULL,
    market     text NOT NULL,
    topic_id   bigint REFERENCES demand_topics(id),
    cadence    text NOT NULL,   -- daily | weekly
    is_active  boolean NOT NULL DEFAULT true,
    UNIQUE (query_text, platform, market)
);

CREATE TABLE collection_runs (
    id              bigserial PRIMARY KEY,
    scheduled_for   timestamptz NOT NULL,
    started_at      timestamptz,
    completed_at    timestamptz,
    status          text NOT NULL,
    import_batch_id bigint REFERENCES import_batches(id)
);
```

Repeated collection over a **stable query set** is what makes Momentum exist. A
Phase 2 that imports once is not a Phase 2 that works.

## Adapter interface

An adapter fetches and shapes. It does not persist, normalize, score, or
deduplicate.

```python
# backend/app/adapters/base.py
class CollectionRequest(BaseModel):
    queries: list[str]
    market: str
    window_start: date
    window_end: date


class MetricDraft(BaseModel):
    metric_name: str
    raw_value: Decimal
    unit: str
    window_start: date
    window_end: date
    comparability: str


class RawSignalDraft(BaseModel):
    query_text: str
    content_excerpt: str | None = None
    source_record_id: str | None = None
    source_url: str | None = None
    observed_at: date
    country_code: str
    province_code: str | None = None
    city_code: str | None = None
    geo_precision: str
    geo_basis: str
    language: str | None = None
    raw_payload: dict
    metrics: list[MetricDraft]


class SignalAdapter(Protocol):
    name: str
    version: str

    def fetch(self, request: CollectionRequest) -> Iterable[RawSignalDraft]: ...
```

**Sequencing rule.** `csv` and `manual` are the reference adapters and the only
ones Phase 2 requires. Every named source — 千瓜, 新红, 百度指数, Google Trends,
巨量算数 — is one more implementation of the same protocol, and **none of them may
sit on the critical path for "Phase 2 complete"**. Their access is commercial,
contractual, or gated on a closed alpha, and none of that is under our control.
The data layer must be complete and testable without them.

Access terms are a separate, parallel track: what each source permits regarding
redistribution and derived commercial products must be confirmed before any
data from it reaches an end user. `signal_sources.redistribution_scope` is where
that answer is recorded once it exists.

## Scoring during the cold-start period

The weights in [backend/SCHEMA.md](backend/SCHEMA.md) — Demand 30%, Momentum
25%, Intent 20%, AI Fit 15%, Supply Gap 10% — stay. What changes is what may be
trusted before a reference distribution exists.

**Level is biased; change is not.** A cross-keyword comparison inherits every
bias in which keywords were chosen to import. A within-keyword comparison over
time does not. So while `reference_n` is small:

- Momentum is computed from slope, acceleration, and persistence over the
  topic's own history, and is trusted.
- Demand is suppressed rather than estimated, and the Market Score is reported
  as partial with `demand_score_suppressed = true`.
- A deliberately broad keyword baseline, including uninteresting control terms,
  is imported specifically to widen the reference distribution.

**Cross-source confirmation is market-scoped.** For a `CN` opportunity the
eligible sources are those whose `valid_markets` contains `CN`; Google Trends is
not among them. Counting an ineligible source toward confirmation would inflate
confidence using noise, which is the exact failure the mechanism exists to
prevent.

## Acceptance criteria

| Capability | Required |
| --- | --- |
| PostgreSQL + Alembic migrations | ✅ |
| `import_batches` with full provenance | ✅ |
| `raw_signals` / `signal_metrics` separated; both insert-only | ✅ |
| `raw_payload_hash` deduplication proven by a repeated import | ✅ |
| Structured geo with `geo_basis` | ✅ |
| Normalization versioned, recomputable, outside the immutable tables | ✅ |
| Demand suppressed when `reference_n < MIN_REFERENCE_N` | ✅ |
| CSV adapter, as the only adapter Phase 2 requires | ✅ |
| **Same query set collected at ≥3 distinct times** | ✅ |
| **Momentum computed from that history, non-trivially** | ✅ |
| **Topic assignment stable: same input, same topic ids across runs** | ✅ |
| Cross-source confirmation counts only market-eligible sources | ✅ |
| Radar renders opportunities carrying real signals | ✅ |

Volume targets for any specific commercial source are deliberately absent. They
measure vendor negotiation, not whether the data foundation works.

## Decisions still open

These need a human answer before implementation, not a default:

1. **Target market for v0.1.** CN-first and international-first imply different
   primary sources and different cold-start paths. Google Trends is the only
   source here with an official API and true search-interest semantics, and it
   is unusable for mainland China.
2. **`MIN_REFERENCE_N`,** and what the UI shows when demand is suppressed.
3. **Embedding model and `TOPIC_MATCH_THRESHOLD`.** Threshold too low merges
   distinct demands; too high fragments one demand across runs and destroys the
   time series.
4. **Redistribution scope per source,** once terms are confirmed.
