from __future__ import annotations
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.responses import HTMLResponse

from app.api.routes import router
from app.dependencies import get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

_BASE_DIR = Path(__file__).parent.parent
_TEMPLATES_DIR = Path(__file__).parent / "templates"
_STATIC_DIR = _BASE_DIR / "static"

templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    if not settings.ANTHROPIC_API_KEY:
        logger.warning("ANTHROPIC_API_KEY is not set — estimations will fail until configured via /settings")
    # Purge stale report files from previous sessions (jobs are in-memory only)
    reports_dir = settings.REPORTS_DIR
    if reports_dir.exists():
        removed = 0
        for f in reports_dir.glob("*.md"):
            f.unlink()
            removed += 1
        if removed:
            logger.info("Cleaned up %d stale report file(s) from %s", removed, reports_dir)
    logger.info("Estimate app started. ANTHROPIC_API_KEY is set.")
    yield


app = FastAPI(title="AI Estimate", version="0.1.0", lifespan=lifespan)

app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")
app.include_router(router)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/history", response_class=HTMLResponse)
async def history(request: Request):
    return templates.TemplateResponse("history.html", {"request": request})


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    return templates.TemplateResponse("settings.html", {"request": request})
