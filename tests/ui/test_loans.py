from playwright.sync_api import expect

from tests.ui.pages.loans_page import LoansPage

from tests.ui.pages.books_page import BooksPage

def test_ui_return_updates_status_stock(logged_in_page, make_book,token, borrow, book_totals):
    headers = {"Authorization": f"Bearer {token}"}
    book = make_book(total_copies=2)

    loan = borrow(book['id'],headers)

    loans_page = LoansPage(logged_in_page).goto()
    loans_page.return_book(book['title'])

    expect(loans_page.message).to_have_text("Book returned.")
    expect(loans_page.status_of(book["title"])).to_have_text("returned")
    # Assert what was stored: one copy on loan, one available
    assert book_totals(book["id"]) == (2, 2)
    

def test_ui_returned_book_can_be_borrowed_again(logged_in_page, make_book,token, borrow, book_totals):
    headers = {"Authorization": f"Bearer {token}"}
    book = make_book(total_copies=2)

    loan = borrow(book['id'],headers)

    loans_page = LoansPage(logged_in_page).goto()
    loans_page.return_book(book['title'])
    expect(loans_page.message).to_have_text("Book returned.")

    books_page = BooksPage(logged_in_page).goto()
    books_page.borrow_by_title(book["title"])
    expect(books_page.message).to_have_text("Book borrowed.")

    # Assert what was stored: one copy on loan, one available
    assert book_totals(book["id"]) == (2, 1)

def test_ui_11_loans_show_only_own_loans(
    logged_in_page, make_book, token, make_headers, borrow 
):
    book1 = make_book(total_copies=1)
    book2 = make_book(total_copies=1)
    owner = {"Authorization": f"Bearer {token}"}
    borrow(book1['id'], owner)
    borrow(book2['id'],make_headers())

    owner_loans = LoansPage(logged_in_page).goto()
    owner_loans.wait_for_loans(1)
    owner_loans.filter_by("active")
    
    expect(owner_loans.row_for(book1["title"])).to_have_count(1)
    expect(owner_loans.row_for(book2["title"])).to_have_count(0)

def test_ui_12_filter_active_hides_returned(
    logged_in_page, make_book, token, borrow, api
):
    active = make_book(total_copies=1)
    retuerned = make_book(total_copies=1)
    owner = {"Authorization": f"Bearer {token}"}
    borrow(active['id'], owner)
    borrow(retuerned['id'], owner)
    
    owner_loans = LoansPage(logged_in_page).goto()
    owner_loans.return_book(retuerned["title"])

    owner_loans.filter_by("active")
    expect(owner_loans.row_for(active["title"])).to_have_count(1)
    expect(owner_loans.row_for(retuerned["title"])).to_have_count(0)

def test_ui_13_filter_returned_hides_active(
    logged_in_page, make_book, token, borrow, api
):
    active = make_book(total_copies=1)
    returned = make_book(total_copies=1)
    owner = {"Authorization": f"Bearer {token}"}
    borrow(active['id'], owner)
    borrow(returned['id'], owner)
    
    owner_loans = LoansPage(logged_in_page).goto()
    owner_loans.return_book(returned["title"])

    owner_loans.filter_by("returned")
    expect(owner_loans.row_for(active["title"])).to_have_count(0)
    expect(owner_loans.row_for(returned["title"])).to_have_count(1)

def test_ui_14_return_button_only_on_active_loans(
    logged_in_page, make_book, token, borrow, api
):
    active = make_book(total_copies=1)
    returned = make_book(total_copies=1)
    owner = {"Authorization": f"Bearer {token}"}
    borrow(active['id'], owner)
    borrow(returned['id'], owner)
    
    owner_loans = LoansPage(logged_in_page).goto()
    owner_loans.return_book(returned["title"])
    owner_loans.wait_for_loans(2)

    expect(owner_loans.row_for(active["title"]).get_by_test_id("return-button")).to_be_visible()
    expect(owner_loans.row_for(returned["title"]).get_by_test_id("return-button")).to_have_count(0)

def test_ui_15_empty_state_when_no_loans(logged_in_page):
    loans = LoansPage(logged_in_page).goto()
    
    expect(loans.page.get_by_text("No loans")).to_be_visible()
    expect(loans.row).to_have_count(0)

def test_ui_16_due_date_is_14_days_after_borrow(
    logged_in_page, make_book, token, borrow
):
    headers = {"Authorization": f"Bearer {token}"}
    book = make_book(total_copies=2)

    loan = borrow(book['id'],headers)

    loans = LoansPage(logged_in_page).goto()
    loans.wait_for_loans(1)
    row = loans.row_for(book["title"])

    # The UI shows minutes precision, so compare the dates as text the page renders.
    borrowed_text = row.locator("td").nth(1).inner_text()
    due_text = row.locator("td").nth(2).inner_text()

    from datetime import datetime
    fmt = "%Y-%m-%d %H:%M"
    gap = datetime.strptime(due_text, fmt) - datetime.strptime(borrowed_text, fmt)
    assert gap.days == 14

def test_ui_17_shows_book_title_not_id(logged_in_page, make_book, token, borrow):
    """UI-17: the loans table shows the title, never a raw id."""
    headers = {"Authorization": f"Bearer {token}"}
    book = make_book(total_copies=2)

    loan = borrow(book['id'],headers)

    loans = LoansPage(logged_in_page).goto()
    loans.wait_for_loans(1)

    expect(loans.row_for(book["title"])).to_have_count(1)
    expect(loans.row.first).not_to_contain_text(str(book["id"]))