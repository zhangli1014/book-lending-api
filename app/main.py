from pathlib import Path

import pymysql
from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app import auth, ui
from app.db import transaction
from app.routers import books, loans

app = FastAPI(title="Book Lending API")

app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")
app.include_router(books.router)
app.include_router(loans.router)
app.include_router(ui.router)

@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse("/ui/login")

    
class Credentials(BaseModel):
    username: str = Field(min_length=3)
    password: str


@app.post("/auth/register", status_code=201)
def register(body: Credentials):
    if len(body.password) < 8:
        raise HTTPException(status_code=422, detail="password must be at least 8 characters")
    try:
        with transaction() as conn:
            auth.create_user(conn, body.username, body.password)
    except pymysql.err.IntegrityError:
        raise HTTPException(status_code=409, detail="username already exists")
    
    return {"username": body.username}


@app.post("/auth/login")
def login(body: Credentials):
    with transaction() as conn:
        user_id = auth.verify_password(conn,body.username, body.password)
        if user_id is None:
            raise HTTPException(status_code=401, detail="invalid username or password")

        return {
            "access_token": auth.issue_token(conn,user_id),
            "token_type": "bearer",
        }


@app.get("/auth/me")
def me(username: str = Depends(auth.current_user)):
    return {"username": username}