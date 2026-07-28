"""JWT helpers compatíveis com o front Minimals."""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from app.db.models import User

ALGORITHM = "HS256"
DEFAULT_EXPIRE_DAYS = 3


def get_jwt_secret() -> str:
    secret = os.getenv("JWT_SECRET", "").strip()
    if not secret:
        # Fallback só para local; produção deve definir JWT_SECRET.
        secret = "laje-signature-dev-secret-change-me"
    return secret


def create_access_token(user: User, expires_days: int = DEFAULT_EXPIRE_DAYS) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role.value if hasattr(user.role, "value") else str(user.role),
        "displayName": user.full_name,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(days=expires_days)).timestamp()),
    }
    return jwt.encode(payload, get_jwt_secret(), algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, get_jwt_secret(), algorithms=[ALGORITHM])


def user_public_dict(user: User) -> dict[str, Any]:
    return {
        "id": str(user.id),
        "email": user.email,
        "displayName": user.full_name,
        "photoURL": None,
        "role": user.role.value if hasattr(user.role, "value") else str(user.role),
    }


def parse_user_id(payload: dict[str, Any]) -> uuid.UUID:
    return uuid.UUID(str(payload["sub"]))
