"""
Teacher Authentication & Session Dependency for NetQuiz
Provides clean, stateless HMAC and in-memory token authentication
suitable for college mini-projects deployed on Render.
"""

import base64
import datetime
import hashlib
import hmac
import json
from typing import Any, Dict, Optional
from fastapi import Header, HTTPException, status

from backend.config import TEACHER_EMAIL, TEACHER_PASSWORD, TEACHER_SECRET_KEY

# In-memory store for active teacher tokens: { token -> { email, name, role, created_at, expires_at } }
active_teacher_tokens: Dict[str, Dict[str, Any]] = {}


def _create_hmac_signature(payload_str: str) -> str:
    """Computes SHA-256 HMAC signature for a payload."""
    return hmac.new(TEACHER_SECRET_KEY.encode(), payload_str.encode(), hashlib.sha256).hexdigest()


def authenticate_teacher(email: str, password: str) -> Optional[Dict[str, Any]]:
    """Validates teacher credentials and issues a secure bearer session token."""
    clean_email = email.strip().lower()
    clean_pass = password.strip()

    if clean_email == TEACHER_EMAIL.strip().lower() and clean_pass == TEACHER_PASSWORD.strip():
        now = datetime.datetime.now()
        exp = now + datetime.timedelta(days=7)
        payload = {
            "email": clean_email,
            "name": "Prof. Networks",
            "role": "teacher",
            "exp": int(exp.timestamp())
        }
        payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()
        sig = _create_hmac_signature(payload_b64)
        token = f"tkn_{payload_b64}.{sig}"

        session_info = {
            "email": clean_email,
            "name": "Prof. Networks",
            "role": "teacher",
            "created_at": now.strftime("%Y-%m-%d %H:%M:%S"),
            "expires_at": exp
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
    """
    Checks whether a token is active and unexpired.
    Supports in-memory cache and stateless HMAC verification to survive
    Render cloud container restarts.
    """
    # 1. In-memory fast cache check
    if token in active_teacher_tokens:
        session = active_teacher_tokens[token]
        if session.get("expires_at") > datetime.datetime.now():
            return session
        else:
            del active_teacher_tokens[token]
            return None

    # 2. Stateless HMAC check (survives Render restarts/cold starts)
    if token.startswith("tkn_") and "." in token:
        try:
            body = token[4:]
            payload_b64, sig = body.split(".", 1)
            expected_sig = _create_hmac_signature(payload_b64)
            if hmac.compare_digest(sig, expected_sig):
                payload_json = json.loads(base64.urlsafe_b64decode(payload_b64.encode()).decode())
                exp_ts = payload_json.get("exp", 0)
                if exp_ts > datetime.datetime.now().timestamp():
                    session = {
                        "email": payload_json.get("email", TEACHER_EMAIL),
                        "name": payload_json.get("name", "Prof. Networks"),
                        "role": payload_json.get("role", "teacher"),
                        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "expires_at": datetime.datetime.fromtimestamp(exp_ts)
                    }
                    active_teacher_tokens[token] = session
                    return session
        except Exception:
            pass

    return None


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
