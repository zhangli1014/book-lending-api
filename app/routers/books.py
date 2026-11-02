import itertools

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field

from app.auth import current_user

router = APIRouter(prefix="/books", tags=["books"])

books: dict[int, dict] = {}
_ids = itertools.count(1)


class BookCreate(BaseModel):
    title: str = Field(min_length=1)
    author: str = Field(min_length=1)
    isbn: str = Field(min_length=1)
    total_copies: int = Field(ge=0)

class BookUpdate(BaseModel):
    # Only these fields are editable (FR-B5). ISBN is fixed after creation.
    title: str = Field(min_length=1)
    author: str = Field(min_length=1)
    total_copies: int = Field(ge=0)

def active_loan_count(book_id: int) -> int:
    """Placeholder until the loans module exists (stage 4).
    Replace the body with a real count of active loans for this book."""
    return 0

def get_book_or_404(book_id: int):
    book = books.get(book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="book not found")
    return book

@router.post("", status_code=201)
def create_book(body: BookCreate, _user: str = Depends(current_user)):
    global _next_id
    if any(b["isbn"] == body.isbn for b in books.values()):
        raise HTTPException(status_code=409, detail="isbn already exists")
    
    book_id = next(_ids)
    book = {
        "id": book_id,
        **body.model_dump(),
        "available_copies": body.total_copies,  # FR-B1
    }
    books[book_id] = book
    return book

@router.get("")
def list_books(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=50),   # size > 50 自动返回 422
    q: str | None = None,
):
    items = sorted(books.values(),key=lambda b:b["id"])

    if q:
        needle = q.lower()
        items = [b for b in items
                 if needle in b["title"].lower() or needle in b["author"].lower()]

    start = (page - 1) * size
    return {
        "items": items[start:start + size],
        "total": len(items),
        "page": page,
        "size": size,
    }

@router.get("/{book_id}")
def get_book(book_id: int):
    return get_book_or_404(book_id)

@router.put("/{book_id}")
def update_book(book_id: int, body: BookUpdate, _user: str = Depends(current_user)):
    book = get_book_or_404(book_id)
    active = active_loan_count(book_id)
    if body.total_copies < active:
        raise HTTPException(status_code=422, detail="total_copies is below active loans")

    book.update(
        title = body.title,
        author = body.author,
        total_copies = body.total_copies,
        available_copies = body.total_copies-active,  # FR-B1
    )
    books[book_id] = book
    return book

@router.delete("/{book_id}", status_code=204)
def update_book(book_id: int, _user: str = Depends(current_user)):
    book = get_book_or_404(book_id)
    active = active_loan_count(book_id)
    if active>0:
        raise HTTPException(status_code=409, detail="book has active loans")
    del books[book_id]
    return Response(status_code=204)


