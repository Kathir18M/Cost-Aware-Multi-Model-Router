"""Pydantic data models for MongoDB collections and API schemas."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from pydantic import BaseModel, Field


class UserPreferences(BaseModel):
    default_model: str | None = None
    confidence_threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    complexity_threshold: float | None = Field(default=None, ge=0.0, le=1.0)


class UserDocument(BaseModel):
    clerk_user_id: str
    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    full_name: str | None = None
    image_url: str | None = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_login_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    preferences: UserPreferences = Field(default_factory=UserPreferences)


class UserProfileResponse(BaseModel):
    clerk_user_id: str
    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    full_name: str | None = None
    image_url: str | None = None
    created_at: str
    last_login_at: str
    preferences: UserPreferences


class UserPreferencesUpdate(BaseModel):
    default_model: str | None = None
    confidence_threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    complexity_threshold: float | None = Field(default=None, ge=0.0, le=1.0)


class ConnectorDocument(BaseModel):
    clerk_user_id: str
    provider: str
    status: str = "connected"  # connected | disconnected
    connected_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict[str, Any] = Field(default_factory=dict)


class UsageEventDocument(BaseModel):
    request_id: str
    clerk_user_id: str
    model: str | None = None
    status: str = "success"  # success | provider_unavailable | error | etc.
    confidence: float | None = None
    escalated: bool = False
    escalation_reason: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    actual_cost: float = 0.0
    baseline_cost: float = 0.0
    savings: float = 0.0
    savings_percentage: float = 0.0
    tools_used: list[str] = Field(default_factory=list)
    task_type: str | None = None
    complexity: str | None = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
