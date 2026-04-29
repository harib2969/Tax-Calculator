"""
MongoDB session store. Falls back to in-memory dict if Mongo is unreachable so
the demo never crashes on a network blip.

Collections:
  - sessions:  { _id: session_id, messages: [...], created_at, updated_at }
  - tax_cache: optional, populated on startup with pre-computed tax results
"""
from datetime import datetime, timezone
from typing import Any
import os

try:
    from pymongo import MongoClient
    from pymongo.errors import PyMongoError
    PYMONGO_AVAILABLE = True
except ImportError:
    PYMONGO_AVAILABLE = False


_client = None
_db = None
_in_memory_sessions: dict[str, dict[str, Any]] = {}
_using_memory = False


def init_db(uri: str | None = None, db_name: str = "tax_lens") -> str:
    """Initialize Mongo connection. Falls back to in-memory if unavailable."""
    global _client, _db, _using_memory
    uri = uri or os.getenv("MONGO_URI", "")
    if not PYMONGO_AVAILABLE or not uri:
        _using_memory = True
        return "in-memory (no MONGO_URI or pymongo not installed)"
    try:
        _client = MongoClient(uri, serverSelectionTimeoutMS=3000)
        _client.admin.command("ping")
        _db = _client[db_name]
        _using_memory = False
        return f"connected to MongoDB: {db_name}"
    except Exception as e:
        _using_memory = True
        return f"in-memory fallback (Mongo error: {type(e).__name__})"


def is_using_memory() -> bool:
    return _using_memory


def _now() -> datetime:
    return datetime.now(timezone.utc)


def get_session(session_id: str) -> dict[str, Any]:
    """Fetch session with full message history. Creates one if missing."""
    if _using_memory:
        if session_id not in _in_memory_sessions:
            _in_memory_sessions[session_id] = {
                "_id": session_id,
                "messages": [],
                "created_at": _now(),
                "updated_at": _now(),
            }
        return _in_memory_sessions[session_id]

    coll = _db["sessions"]
    doc = coll.find_one({"_id": session_id})
    if not doc:
        doc = {
            "_id": session_id,
            "messages": [],
            "created_at": _now(),
            "updated_at": _now(),
        }
        coll.insert_one(doc)
    return doc


def append_messages(session_id: str, new_messages: list[dict[str, Any]]) -> None:
    """Append one or more messages to the session history."""
    if _using_memory:
        sess = get_session(session_id)
        sess["messages"].extend(new_messages)
        sess["updated_at"] = _now()
        return

    coll = _db["sessions"]
    coll.update_one(
        {"_id": session_id},
        {
            "$push": {"messages": {"$each": new_messages}},
            "$set": {"updated_at": _now()},
            "$setOnInsert": {"created_at": _now()},
        },
        upsert=True,
    )


def reset_session(session_id: str) -> None:
    if _using_memory:
        _in_memory_sessions.pop(session_id, None)
        return
    _db["sessions"].delete_one({"_id": session_id})


def list_sessions(limit: int = 50) -> list[dict[str, Any]]:
    if _using_memory:
        return [
            {"session_id": k, "message_count": len(v["messages"]),
             "updated_at": v["updated_at"].isoformat()}
            for k, v in _in_memory_sessions.items()
        ][:limit]
    coll = _db["sessions"]
    return [
        {"session_id": d["_id"], "message_count": len(d.get("messages", [])),
         "updated_at": d.get("updated_at").isoformat() if d.get("updated_at") else ""}
        for d in coll.find().sort("updated_at", -1).limit(limit)
    ]


def cache_tax_results(results: dict[str, dict[str, Any]]) -> None:
    """Optional: persist pre-computed tax results into Mongo for inspection."""
    if _using_memory or not _db:
        return
    coll = _db["tax_cache"]
    coll.delete_many({})
    if results:
        coll.insert_many([{"_id": name, **data} for name, data in results.items()])
