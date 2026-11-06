from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

from app import auth
from app.routers import books,loans

app = FastAPI(title="Book Lending API")

app.include_router(books.router)
app.include_router(loans.router)

class Credentials(BaseModel):
    username: str = Field(min_length=3)
    password: str


@app.post("/auth/register", status_code=201)
def register(body: Credentials):
    if len(body.password) < 8:
        raise HTTPException(status_code=422, detail="password must be at least 8 characters")
    if body.username in auth.users:
        raise HTTPException(status_code=409, detail="username already exists")

    auth.create_user(body.username, body.password)
    return {"username": body.username}


@app.post("/auth/login")
def login(body: Credentials):
    if not auth.verify_password(body.username, body.password):
        raise HTTPException(status_code=401, detail="invalid username or password")

    return {
        "access_token": auth.issue_token(body.username),
        "token_type": "bearer",
    }


@app.get("/auth/me")
def me(username: str = Depends(auth.current_user)):
    return {"username": username}