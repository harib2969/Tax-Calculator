"""
providers/storage/mongodb_adapter.py
Persists query history to MongoDB (Atlas or local).
"""

import os, uuid, logging
from datetime import datetime, timezone
from pymongo import MongoClient, DESCENDING
from providers.base import StorageAdapter

log = logging.getLogger(__name__)

class MongoDBAdapter(StorageAdapter):
    def __init__(self):
        uri = os.environ["MONGODB_URI"]
        db_name = os.environ.get("MONGODB_DB", "taxai")
        self.client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        # Ping to verify connection
        self.client.admin.command("ping")
        db = self.client[db_name]
        self.col = db["queries"]
        # Index for fast recency queries
        self.col.create_index([("created_at", DESCENDING)])
        log.info(f"MongoDB connected — db: {db_name}, collection: queries")

    def save_query(self, query: str, extracted: dict, result: dict) -> None:
        doc = {
            "_id":        str(uuid.uuid4()),
            "query":      query,
            "extracted":  extracted,
            "result":     result,
            "created_at": datetime.now(timezone.utc),
        }
        self.col.insert_one(doc)

    def load_history(self, limit: int = 10) -> list[dict]:
        cursor = self.col.find(
            {},
            {"_id": 0, "query": 1, "result.state_name": 1,
             "result.tax_amount": 1, "result.rate_pct": 1, "created_at": 1}
        ).sort("created_at", DESCENDING).limit(limit)

        return [
            {
                "query":      doc.get("query", ""),
                "state":      doc.get("result", {}).get("state_name", ""),
                "tax_amount": doc.get("result", {}).get("tax_amount", 0),
                "rate_pct":   doc.get("result", {}).get("rate_pct", 0),
                "at":         doc["created_at"].isoformat() if doc.get("created_at") else "",
            }
            for doc in cursor
        ]
