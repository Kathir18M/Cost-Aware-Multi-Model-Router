from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import Request
from starlette.responses import Response


def _jwt_algorithm() -> str:
    return (os.getenv("JWT_ALGORITHM") or "HS256").strip() or "HS256"


def _access_token_ttl_minutes() -> int:
    try:
        return max(1, int((os.getenv("JWT_ACCESS_TOKEN_EXPIRES_MINUTES") or "15").strip()))
    except ValueError:
        return 15


def _refresh_token_ttl_days() -> int:
    try:
        return max(1, int((os.getenv("JWT_REFRESH_TOKEN_EXPIRES_DAYS") or "7").strip()))
    except ValueError:
        return 7


def _secret_key(env_name: str, default_name: str) -> str:
    value = os.getenv(env_name)
    if value and value.strip():
        return value.strip()
    return default_name


def _token_expiry_seconds(ttl_minutes: int | None = None, ttl_days: int | None = None) -> int:
    if ttl_minutes is not None:
        return int(timedelta(minutes=ttl_minutes).total_seconds())
    if ttl_days is not None:
        return int(timedelta(days=ttl_days).total_seconds())
    return int(timedelta(minutes=_access_token_ttl_minutes()).total_seconds())


def generate_access_token(subject: str, extra_claims: dict[str, Any] | None = None) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=_access_token_ttl_minutes())).timestamp()),
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, _secret_key("JWT_SECRET_KEY", "dev-access-secret-change-me"), algorithm=_jwt_algorithm())


def generate_refresh_token(subject: str, extra_claims: dict[str, Any] | None = None) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "type": "refresh",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(days=_refresh_token_ttl_days())).timestamp()),
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, _secret_key("JWT_REFRESH_SECRET_KEY", "dev-refresh-secret-change-me"), algorithm=_jwt_algorithm())


def decode_access_token(token: str) -> dict[str, Any] | None:
    try:
        payload = jwt.decode(
            token,
            _secret_key("JWT_SECRET_KEY", "dev-access-secret-change-me"),
            algorithms=[_jwt_algorithm()],
            options={"require": ["sub", "exp", "type"]},
        )
        if payload.get("type") != "access":
            return None
        return payload
    except Exception:
        return None


def decode_refresh_token(token: str) -> dict[str, Any] | None:
    try:
        payload = jwt.decode(
            token,
            _secret_key("JWT_REFRESH_SECRET_KEY", "dev-refresh-secret-change-me"),
            algorithms=[_jwt_algorithm()],
            options={"require": ["sub", "exp", "type"]},
        )
        if payload.get("type") != "refresh":
            return None
        return payload
    except Exception:
        return None


def get_access_token_expiry_seconds() -> int:
    return _token_expiry_seconds(ttl_minutes=_access_token_ttl_minutes())


def get_refresh_token_expiry_seconds() -> int:
    return _token_expiry_seconds(ttl_days=_refresh_token_ttl_days())


def set_refresh_cookie(response: Response, refresh_token: str) -> None:
    secure = str(os.getenv("COOKIE_SECURE", "false")).strip().lower() in {"1", "true", "yes", "on"}
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/",
        max_age=get_refresh_token_expiry_seconds(),
    )


def clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key="refresh_token", path="/", httponly=True, samesite="lax")


def get_refresh_token_from_request(request: Request) -> str | None:
    return request.cookies.get("refresh_token")
