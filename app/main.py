import hashlib
import secrets
import time

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="Book Lending API")

TOKEN_TTL_SECONDS = 60 * 60  # 60 minutes, per FR-U4

users = {}   # username -> {"salt": bytes, "password_hash": str}
tokens = {}  # token -> {"username": str, "expires_at": float}


class Credentials(BaseModel):
    username: str = Field(min_length=3)
    password: str


def hash_password(password: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000).hex()


@app.post("/auth/register", status_code=201)
def register(body: Credentials):
    if len(body.password) < 8:
        raise HTTPException(status_code=422, detail="password must be at least 8 characters")
    if body.username in users:
        raise HTTPException(status_code=409, detail="username already exists")
    salt = secrets.token_bytes(16)
    users[body.username] = {
        "salt": salt,
        "password_hash": hash_password(body.password, salt),
    }
    return {"username": body.username}


@app.post("/auth/login")
def login(body: Credentials):
    user = users.get(body.username)
    if user is None or hash_password(body.password, user["salt"]) != user["password_hash"]:
        raise HTTPException(status_code=401, detail="invalid username or password")
    token = secrets.token_urlsafe(32)
    tokens[token] = {
        "username": body.username,
        "expires_at": time.time() + TOKEN_TTL_SECONDS,
    }
    return {"access_token": token, "token_type": "bearer"}


def current_user(authorization: str | None = Header(default=None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing or malformed token")
    token = authorization.removeprefix("Bearer ")
    info = tokens.get(token)
    if info is None:
        raise HTTPException(status_code=401, detail="invalid token")
    if time.time() > info["expires_at"]:
        raise HTTPException(status_code=401, detail="token expired")
    return info["username"]


@app.get("/auth/me")
def me(username: str = Depends(current_user)):
    return {"username": username}
