import os
import time
import uuid

import pytest

NOT_FOUND_ID = 999_999

# ---------- Create Books test cases ----------
def test_create_book_return_201(api,token,new_book,book_cleanup):
    headers = {"Authorization": f"Bearer {token}"}
    resp = api.create_book(**new_book,headers=headers)
    assert resp.status_code == 201
    body = resp.json()
    book_cleanup.append(body["id"])
    assert resp.headers["Content-Type"].startswith("application/json")
    assert body["author"] == new_book["author"]
    assert body["title"] == new_book["title"]
    assert body["isbn"] == new_book["isbn"]
    assert body["total_copies"] == body["available_copies"]== new_book["total_copies"]

def test_create_book_notoken_401(api,new_book):
    resp = api.create_book(**new_book)
    assert resp.status_code == 401

def test_create_book_dup_isbn_return_409(api,token,new_book,created_book):
    headers = {"Authorization": f"Bearer {token}"}
    duplicate = {**new_book,"title":"Different title", "author":"Different author"}
    resp = api.create_book(**duplicate,headers=headers)
    assert resp.status_code == 409
    # The original book must be unchanged.
    stored = api.get_book(created_book["id"]).json()
    assert stored["title"] == created_book["title"]

@pytest.mark.parametrize("total_copies",[-1,-99])
def test_create_book_neg_copies_return_422(api,token,new_book,total_copies):
    headers = {"Authorization": f"Bearer {token}"}

    resp = api.create_book(**{**new_book,"total_copies":total_copies},headers=headers)
    assert resp.status_code == 422

# ---------- List and pagination
def test_list_books_default_pagination_200(api,seeded_books):
    resp = api.list_books()
    assert resp.status_code == 200
    data = resp.json()
    assert data['page'] == 1
    assert data['size'] == 10
    assert len(data['items']) == 10
    assert data['total'] >= len(seeded_books)
    

@pytest.mark.parametrize("page,size", [(1,1),(1,10),(1,50),(2,5)])
def test_list_books_valid_pagination_200(api,page,size,seeded_books):
    resp = api.list_books(page=page,size=size)
    assert resp.status_code == 200
    data = resp.json()
    assert data['page'] == page
    assert data['size'] == size
    assert len(data['items']) <= size
    assert data['total'] >= len(seeded_books)

def test_list_books_size_50_200(api,seeded_books):
    resp = api.list_books(size=50)
    assert resp.status_code == 200

@pytest.mark.parametrize("size",[51,100,200])
def test_list_books_size_greater_50(api,size):
    resp = api.list_books(size == size)
    assert resp.status_code == 422

def test_page_beyond_end_returns_empty_items(api):
    resp = api.list_books(page=999_999, size=10)
    assert resp.status_code == 200
    assert resp.json()["items"] == []

#-------------search--------------
def test_list_books_partial_mixed_case_title(api,created_book):
    fragment = created_book["title"][-8:].upper()
    resp = api.list_books(q=fragment)
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert created_book["id"] in [b["id"] for b in items]
    needle = fragment.lower()
    for b in items:
        assert needle in b["author"].lower() or needle in b["title"].lower()

@pytest.mark.parametrize("field",["author","title"])
def test_list_books_search_by_author_or_title(api,created_book,field):
    para = created_book[field]
    resp = api.list_books(q=para)
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert created_book["id"] in [b["id"] for b in items]
    needle = para.lower()
    for b in items:
        assert needle in b["author"].lower() or needle in b["title"].lower()

def test_list_books_mismatch_200(api):
    resp = api.list_books(q=f"no-such-book-{NOT_FOUND_ID}")
    assert resp.status_code == 200
    assert resp.json()["items"] == []
    assert resp.json()["total"] == 0

def test_list_books_empty_query_200(api,created_book):
    with_empty = api.list_books(q="").json()
    without = api.list_books().json()
    assert with_empty["total"] == without["total"]


#-----------------list book by ID
def test_get_book_id_returns_200(api, created_book):
    book_id = created_book["id"]
    resp = api.get_book(book_id)
    assert resp.status_code == 200
    assert resp.headers["Content-Type"].startswith("application/json")

    body = resp.json()
    assert body["author"] == created_book["author"]
    assert body["title"] == created_book["title"]
    assert body["isbn"] == created_book["isbn"]
    assert body["total_copies"] == created_book["total_copies"]
    assert body["total_copies"] >= created_book["available_copies"]

def test_get_book_id_not_exist_returns_404(api):
    book_id = NOT_FOUND_ID
    resp = api.get_book(book_id)
    assert resp.status_code == 404

#------------update book----------------
def test_update_book_return_201(api,token,created_book,book_cleanup):
    headers = {"Authorization": f"Bearer {token}"}
    new_title = f"updated_{created_book['id']}"
    new_total = created_book["total_copies"]+1

    resp = api.update_book(
        created_book["id"],
        title = new_title,
        author = created_book["author"],
        total_copies = new_total,
        headers=headers)
    assert resp.status_code == 200
    body = resp.json()

    assert body["title"] == new_title
    assert body["total_copies"] == new_total
    # Confirm the change is stored, not just echoed back.
    stored = api.get_book(created_book["id"]).json()
    assert stored["title"] == new_title
    assert stored["total_copies"] == new_total
    assert stored["isbn"] == created_book["isbn"]  # ISBN is not editable

def test_update_missing_book_return_404(api,token,created_book,book_cleanup):
    headers = {"Authorization": f"Bearer {token}"}
    resp = api.update_book(
        NOT_FOUND_ID,
        title = 'test',
        author = 'test',
        total_copies = 1,
        headers=headers)
    assert resp.status_code == 404

def test_update_book_without_token_return_401(api,created_book,book_cleanup):
    resp = api.update_book(
        created_book["id"],
        title = 'test',
        author = 'test',
        total_copies = 1,)
    assert resp.status_code == 401

def test_update_total_less_loan_return_422(api,token,created_book,book_cleanup):
    pass
    """
    headers = {"Authorization": f"Bearer {token}"}
    new_total = active_loan_count(created_book["id"])-1
    resp = api.update_book(
        created_book["id"],
        title = created_book["title"],
        author = created_book["author"],
        total_copies = new_total,
        headers=headers)
    assert resp.status_code == 422
    """
#------delete book-----------
def test_delete_valid_book_return_204(api,token,created_book):
    headers = {"Authorization": f"Bearer {token}"}
    resp = api.delete_book(created_book["id"],headers=headers)
    assert resp.status_code == 204

    data = api.get_book(created_book["id"])
    assert data.status_code == 404

def test_delete_book_without_token_return_401(api,created_book):
    resp = api.delete_book(created_book["id"])
    assert resp.status_code == 401
    assert api.get_book(created_book["id"]).status_code == 200

def test_delete_missing_book_return_404(api,token,created_book):
    headers = {"Authorization": f"Bearer {token}"}
    resp = api.delete_book(NOT_FOUND_ID,headers=headers)
    assert resp.status_code == 404
