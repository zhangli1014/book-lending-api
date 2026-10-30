import os
import uuid

import pytest
import requests


class ApiClient:
    #API Wrapper,Thin wrapper around the auth endpoints.
    def __init__(self, base_url: str, timeout: float):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout 

    def register(self, username: str, password: str)-> requests.Response:
        return requests.post(
            f"{self.base_url}/auth/register",
            json={"username":username, "password":password},
            timeout=self.timeout,
        )
        
    def login(self, username: str, password: str)-> requests.Response:
        return requests.post(
            f"{self.base_url}/auth/login",
            json = {"username":username, "password":password},
            timeout = self.timeout,
        )
        
    def me(self, headers:dict|None=None)->requests.Response:
        return requests.get(
            f"{self.base_url}/auth/me",
            headers = headers,
            timeout = self.timeout
        )

@pytest.fixture(scope="session")
def api()->ApiClient:
    return ApiClient(        
        base_url=os.getenv("BASE_URL", "http://127.0.0.1:8000"),
        timeout=float(os.getenv("REQUEST_TIMEOUT", "5")),
    )

@pytest.fixture
def new_user()->dict:
    # create a new user 
    return{
        "username": f"user_{uuid.uuid4().hex[:8]}",
        "password": "abcd1234"
    }

@pytest.fixture
def registered_user(api,new_user)->dict:

    resp = api.register(new_user["username"], new_user["password"])
    assert resp.status_code == 201, f"setup failed: {resp.status_code} {resp.text}"
    return new_user

@pytest.fixture
def token(api,registered_user)->dict:
    resp = api.login(registered_user["username"], registered_user["password"])
    assert resp.status_code == 200, f"setup failed: {resp.status_code} {resp.text}"
    return resp.json()["access_token"]

