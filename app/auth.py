import hashlib
import os
import secrets
import time

from fastapi import Header, HTTPException

TOKEN_TTL_SECONDS = int(os.getenv("TOKEN_TTL_SECONDS", str(60 * 60)))

# In-memory stores. They reset when the server restarts.
users: dict[str, dict] = {}   # username -> {"salt": bytes, "password_hash": str}
tokens: dict[str, dict] = {}  # token -> {"username": str, "expires_at": float}


def hash_password(password: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000).hex()


def create_user(username: str, password: str) -> None:
    salt = secrets.token_bytes(16)
    users[username] = {
        "salt": salt,
        "password_hash": hash_password(password, salt),
    }


def verify_password(username: str, password: str) -> bool:
    user = users.get(username)
    if user is None:
        return False
    return hash_password(password, user["salt"]) == user["password_hash"]


def issue_token(username: str) -> str:
    token = secrets.token_urlsafe(32)
    tokens[token] = {
        "username": username,
        "expires_at": time.time() + TOKEN_TTL_SECONDS,
    }
    return token


def current_user(authorization: str | None = Header(default=None)) -> str:
    """FastAPI dependency: returns the username, or raises 401."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing or malformed token")

    token = authorization.removeprefix("Bearer ")
    info = tokens.get(token)
    if info is None:
        raise HTTPException(status_code=401, detail="invalid token")
    if time.time() > info["expires_at"]:
        raise HTTPException(status_code=401, detail="token expired")
    return info["username"]