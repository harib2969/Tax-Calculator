"""
TaxAI Widget — FastAPI Backend
Entry point: auto-detects Azure OpenAI + MongoDB on startup
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from startup import get_llm_adapter, get_storage_adapter
from routers.analyze import router as analyze_router
from routers.history import router as history_router

logging.basicConfig(level=logging.INFO, format="%(levelname)s — %(message)s")
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Boot: resolve providers ──────────────────────────────────────────────
    app.state.llm     = get_llm_adapter()
    app.state.storage = get_storage_adapter()
    log.info("TaxAI backend ready")
    yield
    # ── Shutdown cleanup (if needed) ─────────────────────────────────────────


app = FastAPI(
    title="TaxAI — US Sales & Use Tax Estimator",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # tighten in production
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analyze_router, prefix="/api")
app.include_router(history_router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok"}
