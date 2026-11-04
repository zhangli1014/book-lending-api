import os
import uuid
import random

import pytest
import requests


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

# ---------- Clients and users ----------
@pytest.fixture(scope="session")
def api()->ApiClient:
    return ApiClient(        
        base_url=os.getenv("BASE_URL", "http://127.0.0.1:8000"),
        timeout=float(os.getenv("REQUEST_TIMEOUT", "5")),
    )

@pytest.fixture
def new_user()->dict:
    # create a new user 
    return{
        "username": f"user_{uuid.uuid4().hex[:8]}",
        "password": "abcd1234"
    }

@pytest.fixture
def registered_user(api,new_user)->dict:

    resp = api.register(new_user["username"], new_user["password"])
    assert resp.status_code == 201, f"setup failed: {resp.status_code} {resp.text}"
    return new_user

@pytest.fixture
def token(api,registered_user)->dict:
    resp = api.login(registered_user["username"], registered_user["password"])
    assert resp.status_code == 200, f"setup failed: {resp.status_code} {resp.text}"
    return resp.json()["access_token"]

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
def book_cleanup(api,token):
     """Collects ids of books created during a test and deletes them afterwards."""
     create_ids: list[int] = []
     yield create_ids
     headers = {"Authorization": f"Bearer {token}"}
     for book in create_ids:
        api.delete_book(book,headers)

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

