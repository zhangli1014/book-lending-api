from tests.ui.pages.base_page import BasePage

class LoginPage(BasePage):
    path = "/ui/login"

    def __init__(self,page):
        super().__init__(page)
        self.username = page.get_by_test_id("username-input")
        self.password = page.get_by_test_id("password-input")
        self.login_button = page.get_by_test_id("login-button")
        self.registered_button = page.get_by_test_id("register-button")

    def log_in(self,username:str,password:str):
        self.username.fill(username)
        self.password.fill(password)
        self.login_button.click()

    def register(self,username:str,password:str):
        self.username.fill(username)
        self.password.fill(password)
        self.registered_button.click()

