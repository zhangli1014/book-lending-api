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
    books = BooksPage(logged_in_page).goto()

    expect(logged_in_page.get_by_test_id("prev-page")).to_be_disabled()

def test_ui_24_next_disabled_on_last_page(logged_in_page, make_book):
    book = make_book(total_copies=1)

    books = BooksPage(logged_in_page).goto()
    books.search(book["title"])  # a search narrows the list to one page
    expect(logged_in_page.get_by_test_id("next-page")).to_be_disabled()

def test_ui_25_shows_available_and_total_copies(logged_in_page, make_book, borrow, make_headers):
    book = make_book(total_copies=3)
    borrow(book["id"], make_headers())

    books = BooksPage(logged_in_page).goto()
    books.search(book["title"])

    cells = books.book_row_cells(book["title"])
    expect(cells.nth(2)).to_have_text("2")  # available
    expect(cells.nth(3)).to_have_text("3")  # total


# ---------- Add book (UI-26 to UI-28) ----------

def test_ui_26_add_book_appears_in_list(logged_in_page, make_book):
    books = BooksPage(logged_in_page).goto()
    title = f"ui_added_{make_book.__name__}"  # unique enough for a search
    isbn = "ui-add-isbn-001"

    books.add_book(title, "UI Author", isbn, 2)

    expect(books.message).to_have_text("Book added.")
    books.search(title)
    expect(books.row_for(title)).to_have_count(1)


def test_ui_27_duplicate_isbn_shows_error(logged_in_page, make_book):
    existing = make_book(total_copies=1)

    books = BooksPage(logged_in_page).goto()
    books.add_book("Another title", "Another author", existing["isbn"], 1)

    expect(books.message).to_have_text("isbn already exists")


def test_ui_28_negative_copies_is_rejected_by_server(logged_in_page):
    books = BooksPage(logged_in_page).goto()
    books.add_book("Negative title", "Some author", "ui-neg-isbn-001", -1)

    # The browser's min="0" check may block the submit before any request.
    # If it does, the message stays empty and the server is never called.
    expect(books.message).to_have_text(re.compile(r"^(?!\s*$).+"))