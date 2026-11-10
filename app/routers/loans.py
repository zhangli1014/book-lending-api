from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Literal

from app.auth import current_user
#from app.store import books, loans, loan_ids
from app.db import transaction
import pymysql

router = APIRouter(prefix="/loans", tags=["loans"])

MAX_ACTIVE_LOANS = 5            # FR-L1
LOAN_PERIOD = timedelta(days=14)  # FR-L4


class LoanCreate(BaseModel):
    book_id: int

def _user_id(cur, username: str) -> int:
    # Locking the user row serializes all of this user's loan requests,
    # so the "five active loans" count cannot be raced.
    cur.execute("SELECT id FROM users WHERE username = %s FOR UPDATE", (username,))
    return cur.fetchone()["id"]

def _loan_view(cur, loan_id: int) -> dict:
    cur.execute(
        """SELECT l.id, u.username, l.book_id, l.borrowed_at, l.due_date,
                  l.returned_at, l.status
           FROM loans l JOIN users u ON u.id = l.user_id
           WHERE l.id = %s""",
        (loan_id,),
    )
    return cur.fetchone()


@router.post("", status_code=201)
def borrow_book(body: LoanCreate, username: str = Depends(current_user)):
    
    with transaction() as conn, conn.cursor() as cur:
        user_id = _user_id(cur, username)

         # Lock the book row. Two users borrowing the last copy queue here.
        cur.execute("SELECT available_copies FROM books WHERE id = %s FOR UPDATE", (body.book_id,))
        book = cur.fetchone()
        if book is None:
            raise HTTPException(status_code=404, detail="book not found")

        # 2. The user cannot hold two active loans for the same book.
        cur.execute("""SELECT count(*) AS n from loans 
                    where user_id =%s and book_id=%s and status = 'active'"""
                    ,(user_id,body.book_id))
       
        if  cur.fetchone()["n"] > 0:
            raise HTTPException(status_code=409, detail="you already borrowed this book")

        # 3. The user can hold at most five active loans.
        cur.execute("SELECT count(*) AS n from loans where user_id =%s and status = 'active'",(user_id,))
        if cur.fetchone()["n"] >= MAX_ACTIVE_LOANS:
            raise HTTPException(status_code=422, detail="loan limit reached")

        # 4. At least one copy must be available.
        if book["available_copies"] <= 0:
            raise HTTPException(status_code=409, detail="no copies available")
        
        # All checks passed: create the loan and update the stock.
        cur.execute(
            "UPDATE books SET available_copies=available_copies-1 WHERE id=%s",(body.book_id)     
            )
        
        cur.execute(
                """INSERT INTO loans(user_id, book_id,borrowed_at, due_date,status)
                VALUES (%s, %s, NOW(), NOW() + INTERVAL 14 DAY,"active")""",
                (user_id, body.book_id)
            )
        return _loan_view(cur, cur.lastrowid)

@router.post("/{loan_id}/return")
def return_book(loan_id: int, username: str = Depends(current_user)):
    with transaction() as conn, conn.cursor() as cur:
        # 1. The book must exist in loans 
        user_id = _user_id(cur, username)
        cur.execute("SELECT user_id, book_id, status FROM loans where id =%s",(loan_id,))
        loan = cur.fetchone()
        if loan is None:
            raise HTTPException(status_code=404, detail="loan not found")

        #2 Only the user who borrowed the book can return it (403)
        if loan["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="book loan user mismatch")
    
        #3 A loan can be returned only once (409)
        if loan["status"]=="returned":
            raise HTTPException(status_code=409, detail="loan already returned")
    
        # All checks passed: update the loan and the stock.
        cur.execute(
        "UPDATE books SET available_copies=available_copies+1 WHERE id=%s",(loan["book_id"])     
        )

        cur.execute(
        "UPDATE loans SET returned_at=NOW(),status='returned' WHERE id =%s",(loan_id,)
        )
        return _loan_view(cur,loan_id)

@router.get("/me")
def list_my_loans(username: str = Depends(current_user),status: Literal["active", "returned"] | None = None,):
    sql = """SELECT l.id, u.username, l.book_id, l.borrowed_at, l.due_date,
                l.returned_at, l.status
            FROM loans l JOIN users u ON u.id = l.user_id
            WHERE u.username = %s"""
    params:list = [username]
    if status is not None:
        sql += "and l.status = %s"
        params.append(status)
    sql += "ORDER BY l.id"
    with transaction() as conn, conn.cursor() as cur:
        cur.execute(sql,params)
        return cur.fetchall()

