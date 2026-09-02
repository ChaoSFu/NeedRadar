# Route and Page Map

| Route | Purpose | Phase |
| --- | --- | --- |
| `/radar` | Filterable opportunity feed (Next.js) | 1 |
| `/opportunities/[id]` | Opportunity explanation and original evidence (Next.js) | 1 |
| `/watchlist` | Watching/testing/validated/rejected opportunities | 3 |
| `/validation` | Validation briefs and results | 4 |
| `/import` | CSV/JSON preview, validation, and import | 2 |
| `/settings` | Data/AI runtime configuration information | 5 |
| `/api/health` | FastAPI health/readiness endpoint | 1 |
| `/api/opportunities` | Opportunity feed API | 1 |
| `/api/signals/import` | Validated FastAPI import endpoint | 2 |
| `/api/pipeline/run` | FastAPI signal-to-opportunity pipeline | 2 |
