import re
import pytest
import uuid
from playwright.sync_api import expect

from tests.ui.pages.login_page import LoginPage

BOOKS_URL = re.compile(r".*/ui/books$")
LOGIN_URL = re.compile(r".*/ui/login$")


def test_ui_01_register_new_user_lands_on_books(page, new_user):
    """UI-01: registering from the login page logs the new user in."""
    login = LoginPage(page).goto()
    login.register(new_user["username"], new_user["password"])

    expect(page).to_have_url(BOOKS_URL)
    expect(page.get_by_test_id("logout-button")).to_be_visible()

def test_ui_02_register_registered_user_fail(page, registered_user):
    """UI-02: registering the registered user failed."""
    login = LoginPage(page).goto()
    login.register(registered_user["username"], registered_user["password"])
    
    expect(login.message).to_have_text("username already exists")
    
@pytest.mark.parametrize("password",["1","12","1234567"])
def test_ui_03_register_invalid_pass__fail(page, new_user,password):
    login = LoginPage(page).goto()
    login.register(new_user["username"], password)

    expect(login.message).to_have_text("password must be at least 8 characters")


#---------------login---------------------
def test_ui_01_login_registered_user_lands_on_books(page, registered_user):
    login = LoginPage(page).goto()
    login.log_in(registered_user["username"], registered_user["password"])

    expect(page).to_have_url(BOOKS_URL)
    expect(page.get_by_test_id("logout-button")).to_be_visible()


def test_ui_02_wrong_pass(page, registered_user):
    login = LoginPage(page).goto()
    login.log_in(registered_user["username"], "wrongpass")

    expect(login.message).to_have_text("invalid username or password")


def test_ui_03_wrong_user(page, registered_user):
    login = LoginPage(page).goto()
    login.log_in(f"unkw_{uuid.uuid4().hex[:8]}", registered_user["password"])

    expect(login.message).to_have_text("invalid username or password")