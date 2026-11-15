from tests.ui.pages.base_page import BasePage
from playwright.sync_api import expect


class LoansPage(BasePage):
    path = "/ui/loans"

    def __init__(self,page):
        super().__init__(page)
        self.status_filter = page.get_by_test_id("status-filter")
        self.row = page.get_by_test_id("loan-row")
    
    def row_for(self, title: str):
        # Filter by title so the test targets one book, not the first row.
        return self.page.get_by_test_id("loan-row").filter(has_text=title)
    
    def return_book(self,title):
        self.row_for(title).get_by_test_id("return-button").click()
    
    def status_of(self, title: str):
        return self.row_for(title).locator("td").nth(3)

    def filter_by(self, status: str):
        # "" means All. select_option picks the option by its value.
        self.status_filter.select_option(status)
    
    def wait_for_loans(self, count: int):
        expect(self.row).to_have_count(count)