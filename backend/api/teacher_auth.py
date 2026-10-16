"""
Teacher Authentication & Session Dependency for NetQuiz
Provides clean, minimal token-based authentication suitable for college mini-projects.
"""

import datetime
import secrets
from typing import Any, Dict, Optional
from fastapi import Header, HTTPException, status

from backend.config import TEACHER_EMAIL, TEACHER_PASSWORD

# In-memory store for active teacher tokens: { token -> { email, name, role, created_at, expires_at } }
active_teacher_tokens: Dict[str, Dict[str, Any]] = {}


def authenticate_teacher(email: str, password: str) -> Optional[Dict[str, Any]]:
    """Validates teacher credentials and issues a secure bearer session token."""
    clean_email = email.strip().lower()
    clean_pass = password.strip()

    if clean_email == TEACHER_EMAIL.strip().lower() and clean_pass == TEACHER_PASSWORD.strip():
        token = f"tkn_{secrets.token_hex(24)}"
        now = datetime.datetime.now()
        session_info = {
            "email": clean_email,
            "name": "Prof. Networks",
            "role": "teacher",
            "created_at": now.strftime("%Y-%m-%d %H:%M:%S"),
            "expires_at": now + datetime.timedelta(days=7)
        }
        active_teacher_tokens[token] = session_info
        return {
            "token": token,
            "teacher": {
                "email": clean_email,
                "name": "Prof. Networks",
                "role": "teacher"
            }
        }
    return None


def verify_teacher_token(token: str) -> Optional[Dict[str, Any]]:
    """Checks whether a token is active and unexpired."""
    session = active_teacher_tokens.get(token)
    if not session:
        return None
    if session.get("expires_at") < datetime.datetime.now():
        del active_teacher_tokens[token]
        return None
    return session


def require_teacher(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    """
    FastAPI dependency that enforces teacher authentication.
    Extracts Bearer token from the HTTP Authorization header.
    Raises HTTP 401 Unauthorized if invalid or missing.
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Teacher authentication required. Missing Authorization header."
        )

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization format. Expected 'Bearer <token>'."
        )

    token = parts[1]
    session = verify_teacher_token(token)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired teacher session. Please log in again."
        )

    return session
