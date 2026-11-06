from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Literal

from app.auth import current_user
from app.store import books, loans, loan_ids

router = APIRouter(prefix="/loans", tags=["loans"])

MAX_ACTIVE_LOANS = 5            # FR-L1
LOAN_PERIOD = timedelta(days=14)  # FR-L4


class LoanCreate(BaseModel):
    book_id: int


@router.post("", status_code=201)
def borrow_book(body: LoanCreate, username: str = Depends(current_user)):
    # 1. The book must exist.
    book = books.get(body.book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="book not found")

    user_active = [
        loan for loan in loans.values()
        if loan["username"] == username and loan["status"] == "active"
    ]  # all active loans under the user

    # 2. The user cannot hold two active loans for the same book.
    if any(loan["book_id"] == body.book_id for loan in user_active):
        raise HTTPException(status_code=409, detail="you already borrowed this book")

    # 3. The user can hold at most five active loans.
    if len(user_active) >= MAX_ACTIVE_LOANS:
        raise HTTPException(status_code=422, detail="loan limit reached")

    # 4. At least one copy must be available.
    if book["available_copies"] <= 0:
        raise HTTPException(status_code=409, detail="no copies available")

    # All checks passed: create the loan and update the stock.
    now = datetime.now(timezone.utc)
    loan_id = next(loan_ids)
    loan = {
        "id": loan_id,
        "username": username,
        "book_id": body.book_id,
        "borrowed_at": now.isoformat(),
        "due_date": (now + LOAN_PERIOD).isoformat(),
        "returned_at": None,
        "status": "active",
    }
    loans[loan_id] = loan
    book["available_copies"] -= 1
    return loan

@router.post("/{loan_id}/return")
def return_book(loan_id: int, username: str = Depends(current_user)):
    # 1. The book must exist in loans 
    loan = loans.get(loan_id)
    if loan is None:
        raise HTTPException(status_code=404, detail="loan not found")

    #2 Only the user who borrowed the book can return it (403)
    if loan["username"] != username:
        raise HTTPException(status_code=403, detail="book loan user mismatch")
    
    #3 A loan can be returned only once (409)
    if loan["status"]=="returned":
        raise HTTPException(status_code=409, detail="loan already returned")
    if loan["status"] != "returned" and loan["status"] != "active":
        raise HTTPException(status_code=409, detail="unexpected loan status")
    
    # All checks passed: update the loan and the stock.
    now = datetime.now(timezone.utc)
    loan["returned_at"] = now.isoformat()
    loan["status"] = "returned"
    books[loan["book_id"]]["available_copies"] += 1
    return loan

@router.get("/me")
def list_my_loans(username: str = Depends(current_user),status: Literal["active", "returned"] | None = None,):
    
    items = sorted((loan for loan in loans.values() if loan["username"]==username),
                    key=lambda loan:loan["id"])
    if status is not None:
        items = [item for item in items if status == item["status"]]

    return items

