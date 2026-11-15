from playwright.sync_api import Page


class BasePage:
    path = "/"

    def __init__(self, page: Page):
        self.page = page
        self.message = page.get_by_test_id("message")

    def goto(self):
        self.page.goto(self.path)
        return self