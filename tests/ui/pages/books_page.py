from playwright.sync_api import expect
from tests.ui.pages.base_page import BasePage

class BooksPage(BasePage):
    path = "/ui/books"
    
    def __init__(self,page):
        super().__init__(page)
        self.search_input = page.get_by_test_id("search-input")
        self.search_button = page.get_by_test_id("search-button")
        self.row = page.get_by_test_id("book-row")
    
    def search(self,txt:str):
        self.search_input.fill(txt)
        self.search_button.click()
    
    def row_for(self, title: str):
        # Filter by title so the test targets one book, not the first row.
        return self.page.get_by_test_id("book-row").filter(has_text=title)

    def borrow(self,title:str):
        self.row_for(title).get_by_test_id("borrow-button").click()
    
    def borrow_by_title(self, title: str):
        self.search(title)
        # Wait until the filtered list shows this book before clicking.
        expect(self.row_for(title)).to_have_count(1)
        self.borrow(title)
    
    def go_to_page(self, direction: str):
        # direction: "next" or "previous"
        self.page.get_by_test_id(f"{direction}-page").click()

    def page_info(self):
        return self.page.get_by_test_id("page-info")

    def add_book(self, title: str, author: str, isbn: str, copies: int):
        self.page.get_by_test_id("add-book-panel").locator("summary").click()
        self.page.get_by_test_id("new-title-input").fill(title)
        self.page.get_by_test_id("new-author-input").fill(author)
        self.page.get_by_test_id("new-isbn-input").fill(isbn)
        self.page.get_by_test_id("new-copies-input").fill(str(copies))
        self.page.get_by_test_id("add-book-button").click()

    def book_row_cells(self, title: str):
        return self.row_for(title).locator("td")
