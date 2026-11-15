import os

import pytest


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    # Relative URLs like page.goto("/ui/books") resolve against the API server.
    return {
        **browser_context_args,
        "base_url": os.getenv("BASE_URL", "http://127.0.0.1:8000"),
    }


@pytest.fixture
def logged_in_page(page, api, registered_user):
    """Start every test already logged in.

    Logging in through the UI is tested once, in test_login.py. Here the
    token is placed directly into sessionStorage so each test starts faster
    and fails only for its own reason.
    page is a fixture after installed playwright plugin
    """
    resp = api.login(registered_user["username"], registered_user["password"])
    token = resp.json()["access_token"]

    page.goto("/ui/login")  # sessionStorage is per origin, so set it on the real page
    page.evaluate("token => sessionStorage.setItem('bl_token', token)", token)
    return page