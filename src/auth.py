"""
Authentication & Authorization Module

Handles JWT token lifecycle, API key management, and role-based
access control for the payment service. All endpoints except
/health and /webhooks require a valid token or API key.

Security notes:
  - Tokens expire after 3600s (configurable via JWT_EXPIRY_SECONDS)
  - API keys are hashed with bcrypt before storage
  - Service accounts bypass MFA but have scoped permissions
"""

from __future__ import annotations

import os
import functools
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Callable, Optional

import bcrypt
import jwt
from flask import request, jsonify, g, current_app

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

JWT_SECRET = os.environ.get("JWT_SECRET", "")  # MUST be set in production
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_SECONDS = int(os.environ.get("JWT_EXPIRY_SECONDS", "3600"))


class Role(str, Enum):
    ADMIN = "ADMIN"
    USER = "USER"
    SERVICE_ACCOUNT = "SERVICE_ACCOUNT"

    @classmethod
    def from_string(cls, value: str) -> "Role":
        try:
            return cls(value.upper())
        except ValueError:
            raise ValueError(f"Invalid role: {value!r}. Must be one of {[r.value for r in cls]}")


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------

def generate_token(user_id: str, role: Role, extra_claims: Optional[dict] = None) -> str:
    """Issue a signed JWT for the given user / role pair."""
    if not JWT_SECRET:
        raise RuntimeError("JWT_SECRET environment variable is not configured")
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "role": role.value,
        "iat": now,
        "exp": now + timedelta(seconds=JWT_EXPIRY_SECONDS),
        **(extra_claims or {}),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def validate_token(token: str) -> dict:
    """Decode and validate a JWT. Raises on expired / invalid / tampered tokens."""
    if not JWT_SECRET:
        raise RuntimeError("JWT_SECRET environment variable is not configured")
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


# ---------------------------------------------------------------------------
# API key management
# ---------------------------------------------------------------------------

def hash_api_key(plain_key: str) -> str:
    """Return a bcrypt hash of the given API key."""
    return bcrypt.hashpw(plain_key.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_api_key(plain_key: str, hashed_key: str) -> bool:
    """Check whether *plain_key* matches the stored *hashed_key*."""
    try:
        return bcrypt.checkpw(plain_key.encode("utf-8"), hashed_key.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# ---------------------------------------------------------------------------
# Decorators
# ---------------------------------------------------------------------------

def require_role(*allowed_roles: Role) -> Callable:
    """Flask route decorator — rejects requests whose token role is not in *allowed_roles*."""
    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            token_claims = getattr(g, "token_claims", None)
            if token_claims is None:
                return jsonify({"error": "missing_token_claims"}), 500

            request_role = Role.from_string(token_claims.get("role", ""))
            if request_role not in allowed_roles:
                current_app.logger.warning(
                    "Forbidden: role=%s required=%s user=%s",
                    request_role, [r.value for r in allowed_roles], token_claims.get("sub"),
                )
                return jsonify({"error": "insufficient_permissions"}), 403

            return fn(*args, **kwargs)
        return wrapper
    return decorator


def authenticate(fn: Callable) -> Callable:
    """Extract and validate JWT from the Authorization header (Bearer scheme)."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "missing_or_invalid_authorization_header"}), 401

        token = auth_header[len("Bearer "):]
        try:
            g.token_claims = validate_token(token)
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "token_expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "invalid_token"}), 401

        return fn(*args, **kwargs)
    return wrapper
