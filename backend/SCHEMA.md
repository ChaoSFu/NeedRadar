# NeedRadar PostgreSQL schema

Database persistence belongs exclusively to the FastAPI backend. Phase 2 will materialize these tables through SQLAlchemy/Alembic migrations; the Phase 1 API deliberately runs only demo fixtures.

> The `raw_signals` metric fields below are superseded by [phase-2-data-foundation.md](../phase-2-data-foundation.md), which splits measurements into a separate `signal_metrics` table. A single `search_volume` column cannot hold Google Trends search interest, a 百度指数 value, and a 千瓜 heat value without losing what each one means.

| Table | Responsibility | Key fields |
| --- | --- | --- |
| `signal_sources` | Source configuration | `name`, `type`, `platform`, `country_code`, `is_active` |
| `raw_signals` | Immutable source evidence | `source_id`, query/content/source URL, country/province/city, `geo_precision`, observed/search/engagement fields, `raw_metadata`, `is_demo` |
| `demand_topics` | Signal cluster | name/slug/summary/category, region, language, first/last seen, status |
| `topic_signals` | Topic-to-signal link | composite `topic_id, signal_id`, relevance score |
| `opportunities` | Region-specific decision object | topic relation, problem/JTBD/pains/workarounds/AI angle/MVP, all six market component scores, status, `is_demo` |
| `opportunity_evidence` | Evidence traceability | `opportunity_id`, `signal_id`, type/strength/excerpt/source URL |
| `opportunity_snapshots` | Time-series scores | opportunity/date unique key, all scores, signal count |
| `validation_experiments` | Validation brief | hypothesis/persona/channel/three experiments/CTA/pass/kill/status |
| `validation_results` | Human-entered validation evidence | result metrics, notes, evidence level `L0`–`L5` |

All tables have creation timestamps; mutable entities also have update timestamps. `opportunities.status` is constrained to `new`, `watching`, `testing`, `validated`, or `rejected`. `raw_signals.geo_precision` is constrained to `country`, `province`, `city`, or `unknown`; no process may infer unsupported geographical data.

`market_score` is computed from Demand (30%), Momentum (25%), Intent (20%), AI Fit (15%), and Supply Gap (10%). It remains separate from `confidence_score` and from `validation_results.evidence_level`.
