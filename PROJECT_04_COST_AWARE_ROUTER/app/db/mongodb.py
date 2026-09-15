"""Centralized MongoDB Connection Manager with health checks and index creation."""

from __future__ import annotations

import logging
import os
from typing import Any
from pymongo import MongoClient, ASCENDING
from pymongo.database import Database
from pymongo.errors import ConnectionFailure, PyMongoError

logger = logging.getLogger(__name__)


class MongoManager:
    """Singleton connection manager for MongoDB."""

    _instance: MongoManager | None = None

    def __init__(self, uri: str | None = None, database_name: str | None = None) -> None:
        self.uri = uri or os.getenv("MONGODB_URI", "mongodb://localhost:27017")
        self.database_name = database_name or os.getenv("MONGODB_DATABASE", "cost_aware_router")
        self._client: MongoClient | None = None
        self._db: Database | None = None
        self._is_connected: bool = False

    @classmethod
    def get_instance(cls, uri: str | None = None, database_name: str | None = None) -> MongoManager:
        if cls._instance is None:
            cls._instance = MongoManager(uri, database_name)
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        if cls._instance and cls._instance._client:
            try:
                cls._instance._client.close()
            except Exception:
                pass
        cls._instance = None

    def set_mock_client(self, client: Any, database_name: str | None = None) -> Database:
        """Helper for testing with mongomock or custom mock clients."""
        self._client = client
        self.database_name = database_name or self.database_name or "cost_aware_router_test"
        self._db = self._client[self.database_name]
        self._is_connected = True
        self.ensure_indexes()
        return self._db

    def connect(self) -> Database | None:
        if self._client is not None and self._is_connected:
            return self._db

        try:
            # 2 second timeout for connection checks to prevent API hangs if DB is offline
            self._client = MongoClient(
                self.uri,
                serverSelectionTimeoutMS=2000,
                connectTimeoutMS=2000,
                maxPoolSize=50,
            )
            # Ping database to verify connection
            self._client.admin.command("ping")
            self._db = self._client[self.database_name]
            self._is_connected = True
            logger.info("MongoDB client connected successfully to database: %s", self.database_name)
            self.ensure_indexes()
            return self._db
        except (ConnectionFailure, PyMongoError, Exception) as exc:
            logger.warning("MongoDB connection failed or service unavailable: %s", exc)
            self._is_connected = False
            self._db = None
            return None

    def ensure_indexes(self) -> None:
        if self._db is None:
            return
        try:
            # Users collection unique index on clerk_user_id
            users_col = self._db["users"]
            users_col.create_index([("clerk_user_id", ASCENDING)], unique=True, name="uniq_clerk_user_id")

            # Connectors collection unique compound index on (clerk_user_id, provider)
            connectors_col = self._db["connectors"]
            connectors_col.create_index(
                [("clerk_user_id", ASCENDING), ("provider", ASCENDING)],
                unique=True,
                name="uniq_user_provider",
            )

            # Usage events collection index on (clerk_user_id, created_at)
            usage_col = self._db["usage_events"]
            usage_col.create_index(
                [("clerk_user_id", ASCENDING), ("created_at", ASCENDING)],
                name="idx_user_created",
            )
            usage_col.create_index([("request_id", ASCENDING)], name="idx_request_id")
            logger.info("MongoDB collection indexes initialized successfully.")
        except Exception as exc:
            logger.warning("Failed to create MongoDB indexes: %s", exc)

    def close(self) -> None:
        if self._client:
            try:
                self._client.close()
                logger.info("MongoDB client closed.")
            except Exception as exc:
                logger.warning("Error closing MongoDB client: %s", exc)
            finally:
                self._client = None
                self._db = None
                self._is_connected = False

    def health_check(self) -> dict[str, str]:
        if not self._is_connected or self._client is None or self._db is None:
            return {"mongodb": "disconnected"}
        try:
            self._client.admin.command("ping")
            return {"mongodb": "connected"}
        except Exception:
            self._is_connected = False
            return {"mongodb": "disconnected"}

    @property
    def db(self) -> Database | None:
        if not self._is_connected:
            return self.connect()
        return self._db


def get_mongo_manager() -> MongoManager:
    return MongoManager.get_instance()


def get_db() -> Database | None:
    return get_mongo_manager().db
