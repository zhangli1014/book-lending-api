import os
import uuid
import random

import pytest
import requests

import pymysql
from pymysql.cursors import DictCursor

class ApiClient:
    #API Wrapper,Thin wrapper around the auth endpoints.
    def __init__(self, base_url: str, timeout: float):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout 

    def register(self, username: str, password: str)-> requests.Response:
        return requests.post(
            f"{self.base_url}/auth/register",
            json={"username":username, "password":password},
            timeout=self.timeout,
        )
        
    def login(self, username: str, password: str)-> requests.Response:
        return requests.post(
            f"{self.base_url}/auth/login",
            json = {"username":username, "password":password},
            timeout = self.timeout,
        )
        
    def me(self, headers:dict|None=None)->requests.Response:
        return requests.get(
            f"{self.base_url}/auth/me",
            headers = headers,
            timeout = self.timeout
        )

    #-----Book API
    def create_book(self, title:str, author:str, isbn:str, total_copies:int, headers:dict|None=None)->requests.Response:
        return requests.post(
            f"{self.base_url}/books",
            headers = headers,  #token
            json = {
                "title":title,
                "author":author,
                "isbn":isbn,
                "total_copies":total_copies,
            },       #new book data
            timeout = self.timeout
        )
    
    def list_books(self,page:int|None=None, size:int|None=None, q:str|None=None)->requests.Response:
        params = {
            key:value
            for key, value in {"page": page, "size": size, "q":q}.items()
            if value is not None
        }
        return requests.get(
            f"{self.base_url}/books",
            params= params,
            timeout = self.timeout
        )
    
    def get_book(self,book_id:int)->requests.Response:
        return requests.get(
            f"{self.base_url}/books/{book_id}",
            timeout = self.timeout
        )

    def update_book(self,book_id:int, title:str, author:str, total_copies:int, headers:dict|None=None)->requests.Response:
        return requests.put(
            f"{self.base_url}/books/{book_id}",
            headers = headers,  #token
            json = {
                "title":title,
                "author":author,
                "total_copies":total_copies,
            },       #updated book data
            timeout = self.timeout
        )

    def delete_book(self,book_id:int, headers:dict|None=None)->requests.Response:
        return requests.delete(
            f"{self.base_url}/books/{book_id}",
            headers = headers,  #token
            timeout = self.timeout
        )
    #--------loans API------------
    def borrow_book(self, book_id:int, headers:dict|None=None)->requests.Response:
        return requests.post(
            f"{self.base_url}/loans",
            headers = headers,  #token
            json = {"book_id": book_id},    
            timeout = self.timeout
        )
    
    def return_book(self, loan_id:int, headers:dict|None=None)->requests.Response:
        return requests.post(
            f"{self.base_url}/loans/{loan_id}/return",
            headers = headers,  #token
            timeout = self.timeout
        )
    def list_my_loans(self, headers:dict|None=None, status:str|None=None)->requests.Response:
        
        params = {"status":status} if status is not None else None
        return requests.get(
            f"{self.base_url}/loans/me",
            headers = headers,  #token
            params= params,  
            timeout = self.timeout
        )

# ---------- Clients and users ----------
@pytest.fixture(scope="session")
def api()->ApiClient:
    return ApiClient(        
        base_url=os.getenv("BASE_URL", "http://127.0.0.1:8000"),
        timeout=float(os.getenv("REQUEST_TIMEOUT", "5")),
    )

@pytest.fixture
def new_user(user_cleanup)->dict:
    # create a new user 
    user = {
        "username": f"user_{uuid.uuid4().hex[:8]}",
        "password": "abcd1234"
    }
    user_cleanup.append(user["username"])
    return user

@pytest.fixture
def registered_user(api,new_user,user_cleanup)->dict:

    resp = api.register(new_user["username"], new_user["password"])
    user_cleanup.append(new_user["username"])
    assert resp.status_code == 201, f"setup failed: {resp.status_code} {resp.text}"
    return new_user

@pytest.fixture
def token(api,registered_user)->dict:
    resp = api.login(registered_user["username"], registered_user["password"])
    assert resp.status_code == 200, f"setup failed: {resp.status_code} {resp.text}"
    return resp.json()["access_token"]

@pytest.fixture
def user_cleanup(db):
    """Removes users created during a test, with their tokens and loans."""
    usernames: list[str] = []
    yield usernames
    with db.cursor() as cur:
        for username in usernames:
            cur.execute(
                "DELETE t FROM tokens t JOIN users u ON u.id = t.user_id WHERE u.username = %s",
                (username,),
            )
            cur.execute(
                "DELETE l FROM loans l JOIN users u ON u.id = l.user_id WHERE u.username = %s",
                (username,),
            )
            cur.execute("DELETE FROM users WHERE username = %s", (username,))

#-------------------books----------------
@pytest.fixture
def new_book()->dict:
    # create a new book 
    suffix = uuid.uuid4().hex[:8]
    return{
        "title": f"title_{suffix}",
        "author": f"author_{suffix}",
        "isbn": f"isbn_{suffix}",
        "total_copies": random.randint(1, 100)
    }
@pytest.fixture
def book_cleanup(db):
     """Collects ids of books created during a test and deletes them afterwards."""
     create_ids: list[int] = []
     yield create_ids
     with db.cursor() as cur:     
        for book_id in create_ids:
            cur.execute("DELETE FROM loans WHERE book_id = %s", (book_id,))
            cur.execute("DELETE FROM books WHERE id = %s", (book_id,))

@pytest.fixture
def created_book(api, token, new_book,book_cleanup)->dict:
    headers = {"Authorization": f"Bearer {token}"}
    resp = api.create_book(**new_book,headers=headers)
    assert resp.status_code == 201, f"setup failed: {resp.status_code} {resp.text}"
    data = resp.json()
    book_cleanup.append(data["id"])
    return data

@pytest.fixture
def seeded_books(api, token, book_cleanup) -> list[dict]:
    """Create enough books that pagination has real data to split."""
    headers = {"Authorization": f"Bearer {token}"}
    books = []
    for i in range(12):
        suffix = uuid.uuid4().hex[:8]
        resp = api.create_book(
            title=f"seed_title_{suffix}",
            author=f"seed_author_{suffix}",
            isbn=f"seed_isbn_{suffix}",
            total_copies=1,
            headers=headers,
        )
        assert resp.status_code == 201, f"seed failed: {resp.status_code} {resp.text}"
        book = resp.json()
        book_cleanup.append(book["id"])
        books.append(book)
    return books

#--------------loans-------------------
@pytest.fixture
def make_headers(api,user_cleanup):
    """Factory: register a fresh user and return their auth headers."""
    def _make() -> dict:
        username = f"user_{uuid.uuid4().hex[:8]}"
        password = "abcd1234"
        assert api.register(username, password).status_code == 201
        user_cleanup.append(username)
        resp = api.login(username, password)
        assert resp.status_code == 200, f"setup failed: {resp.status_code} {resp.text}"
        return {"Authorization": f"Bearer {resp.json()['access_token']}"}
    return _make


@pytest.fixture
def make_book(api, token, book_cleanup):
    """Factory: create a book with a chosen number of copies."""
    auth_headers = {"Authorization": f"Bearer {token}"}
    def _make(total_copies: int = 1) -> dict:
        suffix = uuid.uuid4().hex[:8]
        resp = api.create_book(
            title=f"loan_title_{suffix}",
            author=f"loan_author_{suffix}",
            isbn=f"loan_isbn_{suffix}",
            total_copies=total_copies,
            headers=auth_headers,
        )
        assert resp.status_code == 201, f"setup failed: {resp.status_code} {resp.text}"
        book = resp.json()
        book_cleanup.append(book["id"])
        return book
    return _make


@pytest.fixture
def loan_cleanup(api, book_cleanup):
    """Return any loans still open at the end of a test.
    It depends on book_cleanup, so pytest tears it down first. A book with
    active loans cannot be deleted (FR-B6), so loans must be returned first.
    """
    open_loans: list[tuple[int, dict]] = []
    yield open_loans
    for loan_id, headers in open_loans:
        api.return_book(loan_id, headers=headers)  # 409 if already returned: ignored


@pytest.fixture
def borrow(api, loan_cleanup):
    """Factory: borrow a book as setup, and register the loan for cleanup."""
    def _borrow(book_id: int, headers: dict) -> dict:
        resp = api.borrow_book(book_id, headers=headers)
        assert resp.status_code == 201, f"setup failed: {resp.status_code} {resp.text}"
        loan = resp.json()
        loan_cleanup.append((loan["id"], headers))
        return loan
    return _borrow

#----------------db-----------
@pytest.fixture
def db():
    # autocommit=True: each query sees the latest committed data. Without it,
    # InnoDB's REPEATABLE READ snapshot can show stale values in a test.
    conn = pymysql.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "app"),
        password=os.getenv("DB_PASSWORD", "app_password"),
        database=os.getenv("DB_NAME", "book_lending"),
        cursorclass=DictCursor,
        autocommit=True,
    )
    yield conn
    conn.close()

'''
def db_available_copies(db, book_id: int) -> int:
    with db.cursor() as cur:
        cur.execute("SELECT available_copies FROM books WHERE id = %s", (book_id,))
        return cur.fetchone()["available_copies"]


def db_loan_count(db, book_id: int, status: str) -> int:
    with db.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) AS n FROM loans WHERE book_id = %s AND status = %s",
            (book_id, status),
        )
        return cur.fetchone()["n"]
'''

@pytest.fixture
def book_totals(db):
    """Return a function that reads (total_copies, available_copies) from the database."""
    def _read(book_id: int) -> tuple[int, int]:
        with db.cursor() as cur:
            cur.execute(
                "SELECT total_copies, available_copies FROM books WHERE id = %s",
                (book_id,),
            )
            row = cur.fetchone()
        return row["total_copies"], row["available_copies"]
    return _read