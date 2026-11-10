import hashlib
import os
import secrets
import time
import pymysql

from fastapi import Header, HTTPException
from app.db import transaction

TOKEN_TTL_SECONDS = int(os.getenv("TOKEN_TTL_SECONDS", str(60 * 60)))

# In-memory stores. They reset when the server restarts.
#users: dict[str, dict] = {}   # username -> {"salt": bytes, "password_hash": str}
#tokens: dict[str, dict] = {}  # token -> {"username": str, "expires_at": float}


def hash_password(password: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000).hex()


def create_user(conn, username: str, password: str) -> None:
    salt = secrets.token_bytes(16)
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO users (username, salt, password_hash) VALUES (%s, %s, %s)",
            (username, salt, hash_password(password, salt)),
        )


def verify_password(conn, username: str, password: str) -> int | None:
    with conn.cursor() as cur:
        cur.execute("SELECT id, salt, password_hash FROM users WHERE username = %s", (username,))
        row = cur.fetchone()
    if row is None:
        return None
    if hash_password(password, row["salt"]) != row["password_hash"]:
        return None
    return row["id"]


def issue_token(conn, user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    with conn.cursor() as cur:
        cur.execute(
            """ INSERT INTO tokens (token,user_id, expires_at) 
             VALUES (%s, %s,NOW() + INTERVAL %s SECOND)""",
            (token, user_id, TOKEN_TTL_SECONDS,)
            )
    return token


def current_user(authorization: str | None = Header(default=None)) -> str:
    """FastAPI dependency: returns the username, or raises 401."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing or malformed token")

    token = authorization.removeprefix("Bearer ")

    with transaction() as conn, conn.cursor() as cur:
        cur.execute(
            """SELECT u.username, t.expires_at > NOW() AS valid
               FROM tokens t JOIN users u ON u.id = t.user_id
               WHERE t.token = %s""",
            (token,)
        )
        row = cur.fetchone()

    if row is None:
        raise HTTPException(status_code=401, detail="invalid token")
    if not row["valid"]:
        raise HTTPException(status_code=401, detail="token expired")
    return row["username"]