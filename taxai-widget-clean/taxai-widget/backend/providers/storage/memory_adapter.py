"""
providers/storage/memory_adapter.py
In-memory fallback — no setup needed, data lost on restart.
Activates automatically when MONGODB_URI is not set.
"""

from datetime import datetime, timezone
from providers.base import StorageAdapter


class InMemoryAdapter(StorageAdapter):
    def __init__(self):
        self._store: list[dict] = []

    def save_query(self, query: str, extracted: dict, result: dict) -> None:
        self._store.insert(0, {
            "query":      query,
            "state":      result.get("state_name", result.get("state", "")),
            "tax_amount": result.get("tax_amount", 0),
            "rate_pct":   result.get("rate_pct", 0),
            "at":         datetime.now(timezone.utc).isoformat(),
        })
        self._store = self._store[:100]  # keep last 100 in memory

    def load_history(self, limit: int = 10) -> list[dict]:
        return self._store[:limit]
