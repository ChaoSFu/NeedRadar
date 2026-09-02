# NeedRadar / 需求雷达

NeedRadar is a separated front-end/back-end MVP for discovering AI product opportunities.

```text
frontend/  Next.js 15 UI; npm + committed package-lock.json
backend/   FastAPI; requirements.txt + .venv
```

The front end only consumes `/api/*`; it owns no database logic. The Python API owns demo data today and will own imports, PostgreSQL persistence, scoring, and the AI pipeline in the following phases.

The database design is documented in [backend/SCHEMA.md](backend/SCHEMA.md); it is intentionally separate from the front-end package.

## Local development

Start the backend in an isolated Python virtual environment:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install --requirement requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

In a second terminal, start the front end using the committed npm lockfile:

```bash
cd frontend
npm ci
npm run dev
```

Open `http://localhost:3000/radar`. The Next.js rewrite forwards `/api/*` to `127.0.0.1:8000`; verify it at `http://127.0.0.1:8000/api/health`.

## Alibaba Cloud deployment

Use two non-root systemd services. Each process binds to loopback; Nginx is the only public entry point.

```text
Nginx :80/:443 → Next.js :3000
                   └─ /api/* proxy → FastAPI :8000
```

The deployment recipe is in [deployment/systemd/needradar-api.service](deployment/systemd/needradar-api.service), [deployment/systemd/needradar-web.service](deployment/systemd/needradar-web.service), and [deployment/nginx/needradar.conf](deployment/nginx/needradar.conf).

See [architecture.md](architecture.md), [route-map.md](route-map.md), and [implementation-checklist.md](implementation-checklist.md).
