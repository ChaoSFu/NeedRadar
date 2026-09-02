from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers.opportunities import router as opportunities_router

settings = get_settings()
app = FastAPI(title="NeedRadar API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Content-Type", "Authorization"],
)
app.include_router(opportunities_router)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "mode": "demo" if settings.mock_ai else "configured"}
