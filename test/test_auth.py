import pytest
from fastapi.testclient import TestClient
from app.web.main import _app as app  # Import the underlying FastAPI app
from app.db.session import get_db
from app.db.user_db import add_user, delete_user_by_username
from app.db.auth_db import upsert_api_key, delete_api_key_by_username

client = TestClient(app, follow_redirects=True)

def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert "Login" in response.text


@pytest.fixture(name="test_user")
def test_user_fixture():
    username = "testuser"
    email = "test@example.com"
    password = "testpassword"
    api_key = "testapikey"

    # Create a test user and API key
    db = next(get_db())
    add_user(db, username, email, password, True)
    upsert_api_key(username, api_key)
    db.close()

    yield {
        "username": username,
        "email": email,
        "password": password,
        "api_key": api_key
    }

    # Clean up the test user and API key
    db = next(get_db())
    delete_api_key_by_username(db, username)
    delete_user_by_username(db, username)
    db.close()

def test_login_page_access():
    response = client.get("/auth/login")
    assert response.status_code == 200
    assert "Login" in response.text
    assert "Username" in response.text
    assert "Password" in response.text

def test_successful_login(test_user):
    response = client.post(
        "/auth/login",
        data={"username": test_user["username"], "password": test_user["password"]},
        follow_redirects=True
    )
    assert response.status_code == 200
    assert response.json() == {"status": "success"}