import os
import time
import uuid

import pytest

TOKEN_TTL = int(os.getenv("TOKEN_TTL_SECONDS", "3600"))

# ---------- Registration ----------
def test_register_return_201(api,new_user):
    resp = api.register(new_user["username"],new_user["password"])
    assert resp.status_code == 201
    assert resp.headers['Content-Type'].startswith("application/json")
    data = resp.json()
    assert data['username'] == new_user["username"]
    assert "password" not in data

def test_register_duplicate_return_409(api,registered_user):
    resp = api.register(registered_user["username"],registered_user["password"])
    assert resp.status_code == 409
    
    resp = api.login(registered_user["username"],registered_user["password"])
    assert resp.status_code == 200

@pytest.mark.parametrize("password",["1","12","1234567"])
def test_register_invalid_pass_return_422(api,new_user,password):
    resp = api.register(new_user["username"],password)
    assert resp.status_code == 422

    assert api.login(new_user["username"],password).status_code==401

#-----------login--------------------
def test_login_valid_data_return_200(api,registered_user):
    resp = api.login(registered_user["username"],registered_user["password"])
    assert resp.status_code == 200
    assert resp.headers['Content-Type'].startswith("application/json")
    data = resp.json()
    assert data['token_type'] == 'bearer'
    assert data["access_token"] # asscee-token exists
    assert isinstance(data["access_token"],str)

def test_login_invalid_pass_return_401(api,registered_user):
    resp = api.login(registered_user["username"],"wrongpass")
    assert resp.status_code == 401
    assert "access_token" not in resp.json()

def test_login_unknown_user_return_401(api,registered_user):
    unknown = api.login(f"unkw_{uuid.uuid4().hex[:8]}", registered_user["password"])
    wrong = api.login(registered_user["username"],"wrongpass")

    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json()==wrong.json()

#------------------endpint me--------------------------------
def test_endpoint_valid_token_return_200(api,registered_user,token):
    headers = {"Authorization": f"Bearer {token}"}
    resp = api.me(headers)
    assert resp.status_code == 200
    assert resp.json()["username"] == registered_user["username"]



def test_endpoint_without_token_return_401(api):
    resp = api.me()
    assert resp.status_code == 401

@pytest.mark.parametrize("auth_header",[
    "Bearer virtual-token", #wrong token
    "Bearer ",              #missed token
    "Basic dXNlcjpwYXNz",   #wrong schema
    "not-a-token"           #no Bearer
    ])
def test_endpoint_malformed_token_return_401(api,auth_header):
    resp = api.me(headers={"Authorization":auth_header})
    assert resp.status_code == 401

def test_tampered_real_token_returns_401(api, token):
    """A real token with its last character changed must be rejected."""
    tampered = token[:-1] + ("A" if token[-1] != "A" else "B")

    resp = api.me(headers={"Authorization": f"Bearer {tampered}"})

    assert resp.status_code == 401

#pytest.mark.skipif(TOKEN_TTL > 10, reason="run with TOKEN_TTL_SECONDS=2")
def test_endpoint_expired_token_return_401(api,token):
    headers = {"Authorization": f"Bearer {token}"}
    resp = api.me(headers)
    assert resp.status_code == 200

    time.sleep(TOKEN_TTL + 1)
    resp = api.me(headers)
    assert resp.status_code == 401




