from __future__ import annotations

import os
from types import SimpleNamespace
from typing import Any

import jwt
from fastapi import Depends, HTTPException, Request


import logging

logger = logging.getLogger(__name__)


def _clerk_issuer() -> str | None:
    return os.getenv("CLERK_ISSUER") or os.getenv("NEXT_PUBLIC_CLERK_FRONTEND_API")


def _clerk_jwks_url() -> str:
    jwks_url = os.getenv("CLERK_JWKS_URL")
    if jwks_url and jwks_url != "https://api.clerk.com/v1/jwks":
        return jwks_url
    issuer = _clerk_issuer()
    if issuer:
        return f"{issuer.rstrip('/')}/.well-known/jwks.json"
    return "https://api.clerk.com/v1/jwks"


def _clerk_audience() -> str | None:
    return os.getenv("CLERK_AUDIENCE") or os.getenv("CLERK_API_URL")


def verify_clerk_token(token: str) -> dict[str, Any] | None:
    """Validate a Clerk JWT using Clerk's public JWKS."""
    if not token:
        return None
    try:
        jwks_url = _clerk_jwks_url()
        signing_key = jwt.PyJWKClient(jwks_url).get_signing_key_from_jwt(token)

        decode_kwargs: dict[str, Any] = {
            "algorithms": ["RS256"],
            "options": {"require": ["sub"], "verify_aud": False},
        }
        issuer = _clerk_issuer()
        if issuer:
            decode_kwargs["issuer"] = issuer

        payload = jwt.decode(
            token,
            signing_key.key,
            **decode_kwargs,
        )
        if not isinstance(payload, dict) or not payload.get("sub"):
            return None
        return payload
    except Exception as e:
        logger.error("Clerk JWT verification failed: %s", e)
        return None


def get_authenticated_user(request: Request) -> dict[str, Any]:
    if not hasattr(request, "state"):
        request.state = SimpleNamespace()
    if not hasattr(request, "session"):
        request.session = {}

    auth_header = request.headers.get("authorization", "")
    if not auth_header or not auth_header.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")

    token = auth_header.split(" ", 1)[1].strip()
    payload = verify_clerk_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired authentication token")

    user_id = payload.get("sub") or payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Authenticated user identity is missing")

    user_id = str(user_id)
    request.state.user_id = user_id
    request.session["user_id"] = user_id
    email = payload.get("email") or payload.get("primary_email") or payload.get("email_address")
    first_name = payload.get("first_name") or payload.get("given_name")
    last_name = payload.get("last_name") or payload.get("family_name")
    full_name = payload.get("full_name") or payload.get("name")
    image_url = payload.get("image_url") or payload.get("picture")

    identity_data = {
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "full_name": full_name,
        "image_url": image_url,
    }

    try:
        from app.db.repositories.users import UserRepository
        user_repo = UserRepository()
        user_repo.upsert_user(user_id, identity_data)
    except Exception as exc:
        logger.debug("Automatic MongoDB user upsert skipped/failed: %s", exc)

    request.state.user = {
        "user_id": user_id,
        "email": email,
        "session_id": payload.get("sid") or payload.get("session_id"),
    }
    return {
        "user_id": user_id,
        "email": email,
        "session_id": payload.get("sid") or payload.get("session_id"),
    }


def get_current_user(request: Request) -> dict[str, Any]:
    return get_authenticated_user(request)


def require_clerk_user(request: Request) -> dict[str, Any]:
    return get_authenticated_user(request)


def authenticated_user_dependency() -> Depends:
    return Depends(require_clerk_user)
