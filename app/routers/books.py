import pymysql
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field

from app.auth import current_user
#from app.store import active_loan_count,books,book_ids
from app.db import transaction


router = APIRouter(prefix="/books", tags=["books"])

'''
books: dict[int, dict] = {}
book_ids = itertools.count(1)
'''

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




@router.post("", status_code=201)
def create_book(body: BookCreate, _user: str = Depends(current_user)):
    try:
        with transaction() as conn, conn.cursor() as cur:
            cur.execute(
                """INSERT INTO books (title, author, isbn, total_copies, available_copies)
                VALUES (%s, %s, %s, %s, %s)""",
                (body.title, body.author,body.isbn,body.total_copies,body.total_copies)
            )
            book_id = cur.lastrowid
            cur.execute("SELECT * FROM books WHERE id = %s", (book_id,))
            return cur.fetchone()
    except pymysql.err.IntegrityError:
        raise HTTPException(status_code=409, detail="isbn already exists")

def _escape_like(text: str) -> str:
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

@router.get("")
def list_books(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=50),   # size > 50, return 422
    q: str | None = None,):
    
    # Build the WHERE clause only when there is a search term.
    where = ""
    params: list = []
    if q:
        pattern = f"%{_escape_like(q)}%"
        where = "WHERE title LIKE %s OR author LIKE %s"
        params = [pattern, pattern]
    with transaction() as conn, conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) as n from books {where}",params)
        total = cur.fetchone()["n"]

        cur.execute(
            f"SELECT * FROM books {where} ORDER BY id LIMIT %s OFFSET %s",
            [*params, size, (page - 1) * size],
        )
        items = cur.fetchall()

    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
    }

def get_book_or_404(conn,book_id: int, for_update: bool = False)->dict:
    sql = "SELECT * FROM books WHERE id = %s"
    if for_update:
        sql += " FOR UPDATE "
    with conn.cursor() as cur:
        cur.execute(sql, (book_id,))
        book = cur.fetchone()
    if book is None:
        raise HTTPException(status_code=404, detail="book not found")
    return book

@router.get("/{book_id}")
def get_book(book_id: int):
    with transaction() as conn:
        return get_book_or_404(conn, book_id)

def active_loan_count(conn, book_id: int) -> int:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) AS n FROM loans WHERE book_id = %s AND status = 'active'",
            (book_id,),
        )
        return cur.fetchone()["n"]

@router.put("/{book_id}")
def update_book(book_id: int, body: BookUpdate, _user: str = Depends(current_user)):
    with transaction() as conn:
        get_book_or_404(conn,book_id,for_update=True)
        active = active_loan_count(conn,book_id)
        if body.total_copies < active:
            raise HTTPException(status_code=422, detail="total_copies is below active loans")
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE books 
                SET title = %s, author = %s, total_copies=%s, available_copies=%s
                WHERE id=%s""",
                (body.title, body.author, body.total_copies,body.total_copies-active,book_id)
            )
        return get_book_or_404(conn, book_id)

@router.delete("/{book_id}", status_code=204)
def delete_book(book_id: int, _user: str = Depends(current_user)):
    with transaction() as conn:
        book = get_book_or_404(conn,book_id,for_update=True)
        active = active_loan_count(conn,book_id)
        if active>0:
            raise HTTPException(status_code=409, detail="book has active loans")
        try:
            with conn.cursor() as cur:
                cur.execute( "DELETE FROM books where id =%s",(book_id) )
        except pymysql.err.IntegrityError:
            raise HTTPException(status_code=409, detail="book has loan history")
    return Response(status_code=204)


