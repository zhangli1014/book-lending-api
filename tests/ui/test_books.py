from playwright.sync_api import expect

from tests.ui.pages.books_page import BooksPage

#---------borrow books---------------
def test_ui_borrow_book_updates_stock(logged_in_page, make_book, book_totals):
    book = make_book(total_copies=2)

    books = BooksPage(logged_in_page).goto()
    books.borrow_by_title(book["title"])

    expect(books.message).to_have_text("Book borrowed.")

    # Assert what was stored: one copy on loan, one available
    assert book_totals(book["id"]) == (2, 1)


def test_ui_borrow_book_no_copies(logged_in_page, make_book, make_headers,borrow,book_totals):
    book = make_book(total_copies=1)
    borrow(book["id"],make_headers()) # copies = 0
    
    books = BooksPage(logged_in_page).goto()
    books.borrow_by_title(book["title"])

    expect(books.message).to_have_text("no copies available")

    # Assert what was stored: one copy on loan, none available
    assert book_totals(book["id"]) == (1, 0)


def test_ui_borrow_same_book_twice_shows_error(logged_in_page, make_book,book_totals):
    book = make_book(total_copies=2)
    
    books = BooksPage(logged_in_page).goto()
    books.borrow_by_title(book["title"])
    expect(books.message).to_have_text("Book borrowed.")
    
    books.borrow(book['title'])
    expect(books.message).to_have_text("you already borrowed this book")

    # Assert what was stored: one copy on loan, one available
    assert book_totals(book["id"]) == (2, 1)

def test_ui_borrow_sixth_book_shows_limit(logged_in_page, make_book,token,borrow,book_totals):
    headers = {"Authorization": f"Bearer {token}"}
    for _ in range(5):
        borrow(make_book(total_copies=1)['id'],headers)
    
    sixth = make_book(total_copies=1)

    books = BooksPage(logged_in_page).goto()
    
    books.search(sixth["title"])
    books.borrow_by_title(sixth["title"])

    expect(books.message).to_have_text("loan limit reached")
    # The rejected request must not touch the stock of the sixth book
    assert book_totals(sixth["id"]) == (1, 1)


# ---------- Search (UI-18 to UI-21) ----------
def test_ui_book_search_by_title_partial(logged_in_page,make_book):
    book = make_book(total_copies=1)
    fragment = book["title"][-8:].upper()

    books = BooksPage(logged_in_page).goto()
    books.search(fragment)
    
    expect(books.row_for(book["title"])).to_have_count(1)


def test_ui_book_search_by_author(logged_in_page,make_book):
    book = make_book(total_copies=1)
    author = book["author"]
    books = BooksPage(logged_in_page).goto()
    books.search(author)
    
    expect(books.row_for(book["title"])).to_have_count(1)


def test_ui_search_with_no_match_shows_empty_state(logged_in_page):
    books = BooksPage(logged_in_page).goto()
    books.search("no-such-book-zzzz-9999")
    
    expect(logged_in_page.get_by_text("No books found")).to_be_visible()
    expect(books.row).to_have_count(0)

def test_ui_21_clearing_search_restores_full_list(logged_in_page, make_book):
    book = make_book(total_copies=1)

    books = BooksPage(logged_in_page).goto()
    books.search(book["title"])
    expect(books.row_for(book["title"])).to_have_count(1)

    books.search("")
    expect(books.row_for(book["title"])).to_have_count(1)

#---------Pagination----------
def test_ui_list_books_default_pagination_200(logged_in_page,seeded_books):
    books = BooksPage(logged_in_page).goto()
    expect(books.row).to_have_count(10)
    first_page_book_title = books.row.locator("td").first.all_inner_texts() # all book tiltles in 1 page
    
    second_page = books.go_to_page("Next")
    expect(logged_in_page.get_by_test_id("page-info")).to_have_text(re.compile(r"Page 2 of \d+"))
    second_page_book_title = books.row.locator("td").first.all_inner_texts() # all book tiltles in 2 page
    
    assert first_page_titles, "first page should not be empty"
    assert set(first_page_titles).isdisjoint(second_page_titles)

def test_ui_previous_disabled_on_first_page(logged_in_page):
    pass