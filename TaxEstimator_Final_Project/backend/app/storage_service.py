import json
import os
from datetime import UTC, datetime

from azure.storage.blob import BlobServiceClient
from pymongo import MongoClient

from .models import EstimateResponse


def save_estimate(response: EstimateResponse) -> str:
    payload = response.model_dump(mode="json")
    payload["created_at"] = datetime.now(UTC).isoformat()
    saved_anywhere = False

    mongo_uri = os.getenv("MONGODB_URI")
    if mongo_uri:
        database = os.getenv("MONGODB_DATABASE", "tax_estimator")
        collection = os.getenv("MONGODB_COLLECTION", "estimates")
        with MongoClient(mongo_uri, serverSelectionTimeoutMS=2500) as client:
            client[database][collection].insert_one(payload.copy())
        saved_anywhere = True

    storage_connection = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    container_name = os.getenv("AZURE_STORAGE_CONTAINER", "tax-estimates")
    if storage_connection:
        blob_service = BlobServiceClient.from_connection_string(storage_connection)
        container = blob_service.get_container_client(container_name)
        if not container.exists():
            container.create_container()
        blob_name = f"estimate-{datetime.now(UTC).strftime('%Y%m%d%H%M%S%f')}.json"
        container.upload_blob(blob_name, json.dumps(payload, indent=2), overwrite=False)
        saved_anywhere = True

    return "saved" if saved_anywhere else "not_configured"

