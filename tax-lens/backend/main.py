"""
FastAPI entry point — all REST endpoints for Tax Lens.

Endpoints are pre-defined with full implementations (Option C).
You can run this directly with: uvicorn main:app --reload --port 8000
"""
import os
import uuid
from contextlib import asynccontextmanager
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import tax_engine
import ai_layer
import db
from models import (
    ChatRequest, ChatResponse,
    WhatIfRequest, CompareRequest,
)

# ──────────────────────────────────────────────────────────────────────────────
# STARTUP / SHUTDOWN
# ──────────────────────────────────────────────────────────────────────────────
load_dotenv()

EXCEL_PATH = os.getenv("EXCEL_PATH", "data/sample-org-tax 1.xlsx")
MONGO_URI = os.getenv("MONGO_URI", "")
MONGO_DB = os.getenv("MONGO_DB", "tax_lens")


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("=" * 70)
    print("TAX LENS — starting up")
    print("=" * 70)

    # 1. Load Excel + pre-compute tax for every company
    try:
        n = tax_engine.load_companies_from_excel(EXCEL_PATH)
        print(f"[OK] Loaded {n} companies from {EXCEL_PATH}")
    except Exception as e:
        print(f"[WARN] Could not load Excel ({e}). Endpoints will return empty data.")

    # 2. Connect MongoDB
    status = db.init_db(MONGO_URI, MONGO_DB)
    print(f"[DB] {status}")

    # 3. Cache results in Mongo (optional, useful for inspection)
    db.cache_tax_results(tax_engine.TAX_RESULTS)

    # 4. Initialize Azure OpenAI
    ai_status = ai_layer.init_azure_openai()
    print(f"[AI] {ai_status}")
    print("=" * 70)
    yield
    print("TAX LENS — shutting down")


app = FastAPI(title="Tax Lens API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],     # tighten for production
    allow_methods=["*"],
    allow_headers=["*"],
)


# ──────────────────────────────────────────────────────────────────────────────
# HEALTH / META
# ──────────────────────────────────────────────────────────────────────────────
@app.get("/")
def root():
    return {
        "service": "Tax Lens API",
        "companies_loaded": len(tax_engine.COMPANIES),
        "mongo_status": "in-memory" if db.is_using_memory() else "connected",
        "endpoints": [
            "GET  /companies",
            "GET  /companies/{name}",
            "GET  /companies/{name}/tax",
            "POST /tax/whatif",
            "POST /tax/compare",
            "GET  /tax/portfolio",
            "POST /chat",
            "GET  /sessions",
            "DELETE /sessions/{session_id}",
        ],
    }


# ──────────────────────────────────────────────────────────────────────────────
# COMPANY ENDPOINTS
# ──────────────────────────────────────────────────────────────────────────────
@app.get("/companies")
def list_companies():
    """Return summary list of all companies with computed tax."""
    return {"count": len(tax_engine.COMPANIES), "companies": tax_engine.list_all_companies()}


@app.get("/companies/{name}")
def get_company(name: str):
    """Return raw company record."""
    rec = tax_engine.find_company(name)
    if not rec:
        raise HTTPException(status_code=404, detail=f"Company not found: {name}")
    return rec


@app.get("/companies/{name}/tax")
def get_company_tax(name: str):
    """Return full 7-step tax breakdown for one company."""
    rec = tax_engine.find_company(name)
    if not rec:
        raise HTTPException(status_code=404, detail=f"Company not found: {name}")
    return tax_engine.get_company_tax_breakdown(rec["CompanyName"])


# ──────────────────────────────────────────────────────────────────────────────
# TAX ENDPOINTS
# ──────────────────────────────────────────────────────────────────────────────
@app.post("/tax/whatif")
def tax_whatif(req: WhatIfRequest):
    """Run a what-if scenario with arbitrary overrides."""
    result = tax_engine.what_if_calculator(req.company_name, req.overrides)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@app.post("/tax/compare")
def tax_compare(req: CompareRequest):
    """Compare 2+ companies side-by-side."""
    if len(req.company_names) < 2:
        raise HTTPException(status_code=400, detail="Provide at least 2 company names")
    return tax_engine.compare_companies(req.company_names)


@app.get("/tax/portfolio")
def tax_portfolio():
    """Cross-portfolio analytics."""
    return tax_engine.portfolio_analysis()


@app.get("/tax/savings-opportunities")
def tax_opportunities(threshold: float = 1000.0):
    """Identify restructuring opportunities across the portfolio."""
    return tax_engine.tax_savings_opportunities(threshold)


# ──────────────────────────────────────────────────────────────────────────────
# CHAT ENDPOINTS
# ──────────────────────────────────────────────────────────────────────────────
@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """Send a message; returns the assistant's reply.

    Session memory is stored in MongoDB. Pass the same session_id across turns
    to maintain continuity. Use a new session_id (e.g., uuid4) to start fresh.
    """
    session_id = req.session_id or str(uuid.uuid4())
    session = db.get_session(session_id)
    history = session.get("messages", [])

    result = ai_layer.chat_turn(history=history, user_message=req.message)

    db.append_messages(session_id, result["new_messages"])
    new_history = db.get_session(session_id).get("messages", [])

    return ChatResponse(
        session_id=session_id,
        reply=result["reply"],
        tool_calls_made=result["tool_calls_made"],
        history_length=len(new_history),
    )


@app.get("/sessions")
def get_sessions():
    return {"sessions": db.list_sessions()}


@app.get("/sessions/{session_id}")
def get_session_detail(session_id: str):
    sess = db.get_session(session_id)
    return {
        "session_id": session_id,
        "message_count": len(sess.get("messages", [])),
        "messages": sess.get("messages", []),
    }


@app.delete("/sessions/{session_id}")
def delete_session(session_id: str):
    db.reset_session(session_id)
    return {"status": "deleted", "session_id": session_id}
