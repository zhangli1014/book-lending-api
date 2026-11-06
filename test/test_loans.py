from datetime import datetime, timedelta

import pytest

NOT_FOUND_ID = 999_999

#-----------test borrow--------------
def test_tc_l01_borrow_available_book_returns_201(api, make_book, make_headers, loan_cleanup):
    book = make_book(total_copies=3)
    headers = make_headers()

    resp = api.borrow_book(book["id"],headers=headers)
    assert resp.status_code == 201
    loan = resp.json()
    loan_cleanup.append((loan["id"], headers))

    assert loan["status"] == "active"
    assert loan["book_id"] == book["id"]
    assert loan["returned_at"] is None
    assert api.get_book(book["id"]).json()["available_copies"] == 2

def test_borrow_no_copies_book_returns_409(api, make_book, make_headers, borrow):
    book = make_book(total_copies=1)
    headers = make_headers()
    borrow(book["id"], make_headers())

    resp = api.borrow_book(book["id"],headers=headers)
    assert resp.status_code == 409

    assert api.get_book(book["id"]).json()["available_copies"] == 0

def test_same_user_borrow_book_twice_returns_409(api, make_book, make_headers, borrow):
    book = make_book(total_copies=2)
    headers = make_headers()
    borrow(book["id"],headers=headers)

    resp = api.borrow_book(book["id"],headers=headers)
    assert resp.status_code == 409
    active = api.list_my_loans(headers=headers,status="active").json()
    assert len(active) == 1

def test_sixth_active_loan_returns_422(api, make_book, make_headers, borrow):
    headers = make_headers()
    borrowed_ids = [
       borrow(make_book(total_copies=1)["id"],headers=headers)["book_id"] 
       for _ in range(5)
    ]

    sixth = make_book(total_copies=1)
    resp = api.borrow_book(sixth["id"], headers=headers)
    assert resp.status_code == 422
    assert api.get_book(sixth["id"]).json()["available_copies"] == 1

    active = api.list_my_loans(headers=headers, status="active").json()
    assert sorted(loan["book_id"] for loan in active) == sorted(borrowed_ids)
    

def test_unknown_book_returns_404(api, make_headers):
    headers = make_headers()
    resp = api.borrow_book(NOT_FOUND_ID,headers=headers)
    assert resp.status_code == 404

def test_without_token_returns_401(api, make_book):
    book = make_book()
    resp = api.borrow_book(book["id"])
    assert resp.status_code == 401

#--------------test return-----------
def test_return_own_book_returns_200(api, make_book, make_headers,borrow):
    headers = make_headers()
    book = make_book(total_copies=1)
    loan = borrow(book["id"],headers=headers)

    resp = api.return_book(loan["id"],headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["returned_at"] is not None
    assert data["status"] == "returned"
    assert api.get_book(book["id"]).json()["available_copies"]==1

def test_return_others_book_returns_403(api, make_book, make_headers,borrow):
    own = make_headers()
    other = make_headers()
    book = make_book(total_copies=1)
    loan = borrow(book["id"],headers=own)

    resp = api.return_book(loan["id"],headers=other)
    assert resp.status_code == 403

    origin = api.list_my_loans(headers=own,status="active").json()[0]
    assert origin["status"]=="active"

def test_return_same_book_twice_returns_409(api, make_book, make_headers,borrow):
    headers = make_headers()
    book = make_book(total_copies=1)
    loan = borrow(book["id"],headers=headers)

    assert api.return_book(loan["id"],headers=headers).status_code ==200
    resp = api.return_book(loan["id"],headers=headers)
    assert resp.status_code == 409
    assert api.get_book(book["id"]).json()["available_copies"]==1

def test_return_unknown_book_returns_404(api, make_headers):
    headers = make_headers()

    resp = api.return_book(NOT_FOUND_ID,headers=headers)
    assert resp.status_code == 404

def test_return_no_token_returns_401(api, make_book, make_headers,borrow):
    headers = make_headers()
    book = make_book(total_copies=1)
    loan = borrow(book["id"],headers=headers)

    assert api.return_book(loan["id"]).status_code ==401

def test_same_book_can_be_borrowed_again_after_return(api, make_book, make_headers, borrow):
    headers = make_headers()
    book = make_book(total_copies=1)
    loan = borrow(book["id"],headers=headers)

    assert api.return_book(loan["id"],headers).status_code == 200
    resp = api.borrow_book(book["id"],headers=headers)
    second = resp.json()
    assert resp.status_code == 201
    assert second["id"] != loan["id"]
    assert second["status"] == "active"



#------check due----------
def test_due_date_is_borrowed_at_plus_14_days(api, make_book, make_headers, borrow):
    headers = make_headers()
    book = make_book(total_copies=1)
    loan = borrow(book["id"],headers=headers)
    
    borrowed_at = datetime.fromisoformat(loan["borrowed_at"])
    due_date = datetime.fromisoformat(loan["due_date"])

    assert due_date - borrowed_at == timedelta(days=14)


#--------List loans-----------
def test_filter_active_excludes_returned(api, make_book, make_headers, borrow):
    headers = make_headers()
    returned = borrow(make_book(total_copies=1)["id"], headers)
    active = borrow(make_book(total_copies=1)["id"], headers)
    api.return_book(returned["id"], headers=headers)

    resp = api.list_my_loans(headers = headers, status = "active")
    assert resp.status_code == 200
    ids = [loan["id"] for loan in resp.json()]
    
    assert active["id"] in ids
    assert returned["id"] not in ids
    assert all(loan["status"] == "active" for loan in resp.json())

def test_list_my_loans_shows_only_own_loans(api, make_book, make_headers, borrow):
    alice =  make_headers()
    bob = make_headers()
    book1 = make_book(total_copies=1)
    book2 = make_book(total_copies=1)

    alice_loan = borrow(book1["id"], alice)
    bob_loan = borrow(book2["id"], bob)
   

    ids = [loan["id"] for loan in api.list_my_loans(headers=alice).json()]

    assert alice_loan["id"] in ids
    assert bob_loan["id"] not in ids  # privacy: no other user's loans

@pytest.mark.parametrize("status", ["foo", "ACTIVE"])
def test_list_my_loans_invalid_status_returns_422(api, make_headers, status):
    resp = api.list_my_loans(headers=make_headers(), status=status)
    assert resp.status_code == 422


def test_list_my_loans_without_token_returns_401(api):
    assert api.list_my_loans().status_code == 401