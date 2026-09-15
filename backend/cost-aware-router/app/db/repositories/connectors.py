"""Connector repository for MongoDB connectors collection."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from pymongo.database import Database
from app.db.models import ConnectorDocument
from app.db.mongodb import get_db

logger = logging.getLogger(__name__)


class ConnectorRepository:
    def __init__(self, db: Database | None = None) -> None:
        self._db = db

    @property
    def db(self) -> Database | None:
        return self._db if self._db is not None else get_db()

    def save_connector_state(
        self,
        clerk_user_id: str,
        provider: str,
        status: str = "connected",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Upsert connector state scoped to clerk_user_id and provider."""
        db = self.db
        if db is None or not clerk_user_id or not provider:
            return None

        provider_key = provider.strip().lower().replace("-", "_").replace(" ", "_")
        now = datetime.now(timezone.utc).isoformat()
        metadata = metadata or {}
        collection = db["connectors"]

        try:
            query = {"clerk_user_id": clerk_user_id, "provider": provider_key}
            existing = collection.find_one(query)
            if existing:
                update_fields = {
                    "status": status,
                    "updated_at": now,
                    "metadata": metadata,
                }
                collection.update_one(query, {"$set": update_fields})
            else:
                doc = ConnectorDocument(
                    clerk_user_id=clerk_user_id,
                    provider=provider_key,
                    status=status,
                    connected_at=now,
                    updated_at=now,
                    metadata=metadata,
                )
                doc_dict = doc.model_dump()
                collection.insert_one(doc_dict)

            updated = collection.find_one(query)
            if updated:
                updated.pop("_id", None)
            return updated
        except Exception as exc:
            logger.warning(
                "MongoDB ConnectorRepository.save_connector_state failed for %s/%s: %s",
                clerk_user_id,
                provider,
                exc,
            )
            return None

    def get_connector_state(self, clerk_user_id: str, provider: str) -> dict[str, Any] | None:
        db = self.db
        if db is None or not clerk_user_id or not provider:
            return None
        provider_key = provider.strip().lower().replace("-", "_").replace(" ", "_")
        try:
            doc = db["connectors"].find_one({"clerk_user_id": clerk_user_id, "provider": provider_key})
            if doc:
                doc.pop("_id", None)
            return doc
        except Exception as exc:
            logger.warning(
                "MongoDB ConnectorRepository.get_connector_state failed for %s/%s: %s",
                clerk_user_id,
                provider,
                exc,
            )
            return None

    def list_user_connectors(self, clerk_user_id: str) -> list[dict[str, Any]]:
        db = self.db
        if db is None or not clerk_user_id:
            return []
        try:
            cursor = db["connectors"].find({"clerk_user_id": clerk_user_id})
            results = []
            for doc in cursor:
                doc.pop("_id", None)
                results.append(doc)
            return results
        except Exception as exc:
            logger.warning("MongoDB ConnectorRepository.list_user_connectors failed for %s: %s", clerk_user_id, exc)
            return []

    def disconnect_connector(self, clerk_user_id: str, provider: str) -> bool:
        db = self.db
        if db is None or not clerk_user_id or not provider:
            return False
        provider_key = provider.strip().lower().replace("-", "_").replace(" ", "_")
        now = datetime.now(timezone.utc).isoformat()
        try:
            result = db["connectors"].update_one(
                {"clerk_user_id": clerk_user_id, "provider": provider_key},
                {"$set": {"status": "disconnected", "updated_at": now}},
            )
            return result.modified_count > 0 or result.matched_count > 0
        except Exception as exc:
            logger.warning(
                "MongoDB ConnectorRepository.disconnect_connector failed for %s/%s: %s",
                clerk_user_id,
                provider,
                exc,
            )
            return False
