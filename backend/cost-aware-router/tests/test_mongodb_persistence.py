"""Automated unit and integration tests for MongoDB persistent database layer."""

from __future__ import annotations

import mongomock
import pytest
from fastapi.testclient import TestClient

from api_server import app
from app.db.models import UserDocument, UserPreferences, ConnectorDocument, UsageEventDocument
from app.db.mongodb import MongoManager
from app.db.repositories.users import UserRepository
from app.db.repositories.connectors import ConnectorRepository
from app.db.repositories.usage import UsageRepository
from app.auth.clerk import verify_clerk_token


@pytest.fixture(autouse=True)
def setup_mock_db():
    """Setup a mocked MongoDB database before each test."""
    manager = MongoManager.get_instance()
    mock_client = mongomock.MongoClient()
    manager.set_mock_client(mock_client, database_name="cost_aware_router_test")
    yield manager
    MongoManager.reset_instance()


def test_mongodb_connection_and_health():
    manager = MongoManager.get_instance()
    health = manager.health_check()
    assert health == {"mongodb": "connected"}

    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["database"]["mongodb"] == "connected"


def test_user_upsert_and_retrieval():
    repo = UserRepository()
    user_id = "user_test_clerk_123"
    identity_data = {
        "email": "test@example.com",
        "first_name": "Test",
        "last_name": "User",
        "full_name": "Test User",
        "image_url": "https://example.com/photo.jpg",
    }

    # First upsert creates user
    user = repo.upsert_user(user_id, identity_data)
    assert user is not None
    assert user["clerk_user_id"] == user_id
    assert user["email"] == "test@example.com"
    assert user["preferences"]["default_model"] is None

    # Subsequent upsert updates last_login_at without duplicating user
    updated_user = repo.upsert_user(user_id, identity_data)
    assert updated_user["clerk_user_id"] == user_id

    # Retrieve user
    retrieved = repo.get_user_by_clerk_id(user_id)
    assert retrieved is not None
    assert retrieved["full_name"] == "Test User"


def test_user_preferences_update():
    repo = UserRepository()
    user_id = "user_pref_test_456"
    repo.upsert_user(user_id, {"email": "pref@example.com"})

    new_prefs = {
        "default_model": "gemini-2.0-flash",
        "confidence_threshold": 0.85,
        "complexity_threshold": 0.65,
    }
    updated = repo.update_user_preferences(user_id, new_prefs)
    assert updated is not None
    assert updated["preferences"]["default_model"] == "gemini-2.0-flash"
    assert updated["preferences"]["confidence_threshold"] == 0.85
    assert updated["preferences"]["complexity_threshold"] == 0.65


def test_connector_repository_user_isolation():
    repo = ConnectorRepository()
    user_a = "user_a_111"
    user_b = "user_b_222"

    # User A connects github
    repo.save_connector_state(user_a, "github", "connected", {"login": "user_a_git"})
    # User B connects github with different account
    repo.save_connector_state(user_b, "github", "connected", {"login": "user_b_git"})

    conn_a = repo.get_connector_state(user_a, "github")
    conn_b = repo.get_connector_state(user_b, "github")

    assert conn_a is not None
    assert conn_b is not None
    assert conn_a["metadata"]["login"] == "user_a_git"
    assert conn_b["metadata"]["login"] == "user_b_git"
    assert conn_a["clerk_user_id"] == user_a
    assert conn_b["clerk_user_id"] == user_b

    # User A disconnects github
    repo.disconnect_connector(user_a, "github")
    assert repo.get_connector_state(user_a, "github")["status"] == "disconnected"
    # User B's connector state remains untouched
    assert repo.get_connector_state(user_b, "github")["status"] == "connected"


def test_usage_repository_persistence_and_dashboard_aggregation():
    repo = UsageRepository()
    user_id = "user_usage_999"

    # Save 2 Gemini requests
    repo.save_usage_event(
        user_id,
        {
            "request_id": "req_001",
            "model": "gemini-2.0-flash",
            "status": "success",
            "confidence": 0.95,
            "escalated": False,
            "actual_cost": 0.001,
            "baseline_cost": 0.003,
            "savings": 0.002,
            "savings_percentage": 66.67,
        },
    )
    repo.save_usage_event(
        user_id,
        {
            "request_id": "req_002",
            "model": "gemini-2.0-flash",
            "status": "success",
            "confidence": 0.85,
            "escalated": False,
            "actual_cost": 0.001,
            "baseline_cost": 0.003,
            "savings": 0.002,
            "savings_percentage": 66.67,
        },
    )
    # Save 1 Escalated Mistral request
    repo.save_usage_event(
        user_id,
        {
            "request_id": "req_003",
            "model": "mistral-small-latest",
            "status": "success",
            "confidence": 0.60,
            "escalated": True,
            "escalation_reason": "Low confidence",
            "actual_cost": 0.003,
            "baseline_cost": 0.003,
            "savings": 0.0,
            "savings_percentage": 0.0,
        },
    )

    metrics = repo.get_user_dashboard_metrics(user_id)
    assert metrics is not None
    assert metrics["total_requests"] == 3
    assert metrics["gemini_requests"] == 2
    assert metrics["mistral_requests"] == 1
    assert metrics["escalation_rate"] == round(1 / 3, 4)
    assert metrics["total_cost"] == 0.005
    assert metrics["baseline_cost"] == 0.009
    assert metrics["total_savings"] == 0.004

    logs = repo.get_user_logs(user_id)
    assert len(logs) == 3


def test_user_profile_api_endpoints(monkeypatch):
    user_id = "user_api_test_777"
    monkeypatch.setattr(
        "app.auth.clerk.verify_clerk_token",
        lambda token: {"sub": user_id, "email": "api_test@example.com"},
    )

    client = TestClient(app)
    headers = {"Authorization": f"Bearer fake_jwt_token_{user_id}"}

    # GET /api/user/profile
    resp = client.get("/api/user/profile", headers=headers)
    assert resp.status_code == 200
    profile = resp.json()
    assert profile["clerk_user_id"] == user_id
    assert profile["email"] == "api_test@example.com"

    # PATCH /api/user/profile
    patch_payload = {
        "default_model": "mistral-small-latest",
        "confidence_threshold": 0.8,
    }
    resp_patch = client.patch("/api/user/profile", json=patch_payload, headers=headers)
    assert resp_patch.status_code == 200
    updated_profile = resp_patch.json()
    assert updated_profile["preferences"]["default_model"] == "mistral-small-latest"
    assert updated_profile["preferences"]["confidence_threshold"] == 0.8


def test_graceful_db_offline_handling(monkeypatch):
    # Force DB offline helper returning None
    monkeypatch.setattr("app.db.repositories.users.get_db", lambda: None)
    monkeypatch.setattr("app.db.repositories.connectors.get_db", lambda: None)
    monkeypatch.setattr("app.db.repositories.usage.get_db", lambda: None)

    repo = UserRepository(db=None)
    assert repo.get_user_by_clerk_id("user_xyz") is None

    conn_repo = ConnectorRepository(db=None)
    assert conn_repo.get_connector_state("user_xyz", "github") is None

    usage_repo = UsageRepository(db=None)
    assert usage_repo.get_user_dashboard_metrics("user_xyz") is None
