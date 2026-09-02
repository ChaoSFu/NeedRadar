# NeedRadar Architecture (V0.1)

NeedRadar is an opportunity-first product: imported market signals are retained as immutable evidence, grouped into demand topics, and surfaced as region-specific opportunities. `Market Score` estimates market attractiveness; validation evidence remains a separate, user-entered record.

## Stack

- `frontend/`: Next.js App Router + TypeScript strict + Tailwind CSS
- `backend/`: FastAPI + Pydantic + SQLAlchemy/PostgreSQL; demo repository when no database is configured
- Zod validates browser/import boundaries; Pydantic validates API and LLM boundaries
- A provider-neutral Python AI interface will provide deterministic mock fallback

## Data flow

`SignalAdapter -> RawSignal -> clustering -> DemandTopic -> opportunity generation -> Opportunity + OpportunityEvidence -> Radar`

The first release supports manual, CSV, and demo adapters. Evidence stores both its signal relationship and the original source URL; generated reasoning never becomes evidence by itself.

## Boundaries

- `frontend/` owns presentation and typed API clients only.
- `backend/app/routers` owns HTTP concerns; `services` owns business logic; `models` owns persistence.
- `backend/app/scoring` will own transparent market/confidence calculations.
- `backend/app/ai` will own prompts, provider calls, JSON validation, and mock fallback.

## Runtime modes

`MOCK_AI=true` provides deterministic pipeline outputs. Without `DATABASE_URL`, the FastAPI API runs against explicitly marked demo data so first launch always works. With a database, SQLAlchemy migrations become the source of truth.
