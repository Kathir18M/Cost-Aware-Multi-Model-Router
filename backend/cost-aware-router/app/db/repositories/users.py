"""User repository for MongoDB users collection."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from pymongo.database import Database
from app.db.models import UserDocument, UserPreferences
from app.db.mongodb import get_db

logger = logging.getLogger(__name__)


class UserRepository:
    def __init__(self, db: Database | None = None) -> None:
        self._db = db

    @property
    def db(self) -> Database | None:
        return self._db if self._db is not None else get_db()

    def upsert_user(self, clerk_user_id: str, identity_data: dict[str, Any] | None = None) -> dict[str, Any] | None:
        """Find or create user document by clerk_user_id.

        Only stores fields available from Clerk identity. Never stores passwords or secrets.
        """
        db = self.db
        if db is None or not clerk_user_id:
            return None

        now = datetime.now(timezone.utc).isoformat()
        identity_data = identity_data or {}
        collection = db["users"]

        try:
            existing = collection.find_one({"clerk_user_id": clerk_user_id})
            if existing:
                update_fields: dict[str, Any] = {
                    "last_login_at": now,
                    "updated_at": now,
                }
                # Update optional fields if provided in identity_data and non-empty
                for field in ("email", "first_name", "last_name", "full_name", "image_url"):
                    val = identity_data.get(field)
                    if val and not existing.get(field):
                        update_fields[field] = val

                collection.update_one(
                    {"clerk_user_id": clerk_user_id},
                    {"$set": update_fields},
                )
                updated = collection.find_one({"clerk_user_id": clerk_user_id})
                if updated:
                    updated.pop("_id", None)
                return updated
            else:
                user_doc = UserDocument(
                    clerk_user_id=clerk_user_id,
                    email=identity_data.get("email"),
                    first_name=identity_data.get("first_name"),
                    last_name=identity_data.get("last_name"),
                    full_name=identity_data.get("full_name"),
                    image_url=identity_data.get("image_url"),
                    created_at=now,
                    updated_at=now,
                    last_login_at=now,
                    preferences=UserPreferences(),
                )
                doc_dict = user_doc.model_dump()
                collection.insert_one(doc_dict)
                doc_dict.pop("_id", None)
                return doc_dict
        except Exception as exc:
            logger.warning("MongoDB UserRepository.upsert_user failed for %s: %s", clerk_user_id, exc)
            return None

    def get_user_by_clerk_id(self, clerk_user_id: str) -> dict[str, Any] | None:
        db = self.db
        if db is None or not clerk_user_id:
            return None
        try:
            doc = db["users"].find_one({"clerk_user_id": clerk_user_id})
            if doc:
                doc.pop("_id", None)
            return doc
        except Exception as exc:
            logger.warning("MongoDB UserRepository.get_user_by_clerk_id failed for %s: %s", clerk_user_id, exc)
            return None

    def update_user_preferences(self, clerk_user_id: str, preferences: dict[str, Any]) -> dict[str, Any] | None:
        db = self.db
        if db is None or not clerk_user_id:
            return None
        now = datetime.now(timezone.utc).isoformat()
        try:
            current = self.get_user_by_clerk_id(clerk_user_id)
            if not current:
                current = self.upsert_user(clerk_user_id)
            if not current:
                return None

            pref_data = current.get("preferences", {})
            for key in ("default_model", "confidence_threshold", "complexity_threshold"):
                if key in preferences and preferences[key] is not None:
                    pref_data[key] = preferences[key]

            db["users"].update_one(
                {"clerk_user_id": clerk_user_id},
                {"$set": {"preferences": pref_data, "updated_at": now}},
            )
            updated = db["users"].find_one({"clerk_user_id": clerk_user_id})
            if updated:
                updated.pop("_id", None)
            return updated
        except Exception as exc:
            logger.warning("MongoDB UserRepository.update_user_preferences failed for %s: %s", clerk_user_id, exc)
            return None
