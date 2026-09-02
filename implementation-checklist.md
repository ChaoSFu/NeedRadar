# Implementation Checklist

- [x] Phase 1: Front-end shell, FastAPI demo API, Radar feed, detail page
- [ ] Phase 2: CSV/JSON import, manual signal entry, adapters, AI processing endpoint
- [ ] Phase 3: Persistent scoring/snapshots/evidence linking and watchlist mutations
- [ ] Phase 4: Validation brief generation, result entry, evidence-level mapping
- [ ] Phase 5: Empty/error states, UI refinement, database setup verification, Docker optional

## Phase 1 files

- `backend/requirements.txt`, `backend/app/main.py`, `backend/app/demo_data.py`
- `frontend/package.json`, TypeScript/Tailwind/Next configuration
- `frontend/lib/api.ts`, `frontend/app/radar/page.tsx`, `frontend/app/opportunities/[id]/page.tsx`
- Shared UI components in `frontend/components/`
