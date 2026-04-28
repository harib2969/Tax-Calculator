"""routers/history.py — GET /api/history"""

from fastapi import APIRouter, Request
router = APIRouter()

@router.get("/history")
def history(request: Request, limit: int = 10):
    return request.app.state.storage.load_history(limit=min(limit, 50))
