"""Authentication module — password hashing, session tokens, FastAPI dependencies."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from meeting_agent.web.models import (
    create_session,
    create_web_user,
    get_session_by_token,
    get_web_user_by_id,
)

_SECURITY = HTTPBearer(auto_error=False)

# PBKDF2 parameters
_PBKDF2_ALGO = "sha256"
_PBKDF2_ITERATIONS = 600_000
_SALT_BYTES = 32


def hash_password(password: str) -> str:
    """Hash a password with a random salt using PBKDF2-HMAC-SHA256.
    Returns: $salt_hex$hash_hex
    """
    salt = secrets.token_hex(_SALT_BYTES)
    pwhash = hashlib.pbkdf2_hmac(_PBKDF2_ALGO, password.encode(), salt.encode(), _PBKDF2_ITERATIONS)
    return f"{salt}${pwhash.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Verify a password against a stored hash."""
    parts = stored.split("$", 1)
    if len(parts) != 2:
        return False
    salt, expected_hex = parts
    pwhash = hashlib.pbkdf2_hmac(_PBKDF2_ALGO, password.encode(), salt.encode(), _PBKDF2_ITERATIONS)
    return hmac.compare_digest(pwhash.hex(), expected_hex)


def create_session_token(user_id: int) -> str:
    """Create a new session token for the given user."""
    token = secrets.token_urlsafe(48)
    create_session(user_id, token)
    return token


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_SECURITY),
) -> Dict[str, Any]:
    """FastAPI dependency: extract the current user from the Bearer token."""
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录")

    session = get_session_by_token(credentials.credentials)
    if session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录已过期，请重新登录")

    user = get_web_user_by_id(session["user_id"])
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")

    return user


async def require_admin(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """FastAPI dependency: require admin role."""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限")
    return current_user
