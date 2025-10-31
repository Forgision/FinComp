import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, create_engine, Session

from app.core.models.auth_db import delete_api_key_by_username, upsert_api_key
from app.core.models.user import add_user, delete_user_by_username
from app.main import _app as app_fastapi
from app.db.session import get_db

# Use an in-memory SQLite database for testing, configured to allow multi-threaded access
DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(DATABASE_URL, echo=True, connect_args={"check_same_thread": False})

def get_test_db():
    """Dependency override for test database session."""
    with Session(engine) as session:
        yield session

app_fastapi.dependency_overrides[get_db] = get_test_db

@pytest.fixture(scope="module")
def client():
    """Provides a test client for the FastAPI application, handling startup and shutdown events."""
    with TestClient(app_fastapi) as c:
        yield c

@pytest.fixture(scope="function")
def test_user():
    """Creates a test user and API key, and cleans them up after tests."""
    username = "testuser"
    email = "test@example.com"
    password = "testpassword"
    api_key = "testapikey"

    with Session(engine) as session:
        add_user(session, username, email, password, True)
        upsert_api_key(session, username, api_key)

    yield {"username": username, "password": password, "api_key": api_key}

    with Session(engine) as session:
        try:
            delete_api_key_by_username(session, user_id=username)
            delete_user_by_username(session, username)
        except Exception as e:
            session.rollback()
            raise e

def test_read_main(client):
    """Tests that the root URL redirects to the login page."""
    response = client.get("/")
    assert response.status_code == 302
    assert response.headers['location'] == '/auth/login'

def test_login_page_access(client):
    """Tests that the login page is accessible and contains the correct elements."""
    response = client.get("/auth/login")
    assert response.status_code == 200
    assert "Login" in response.text
    assert "Username" in response.text
    assert "Password" in response.text

def test_successful_login(client, test_user):
    """Tests that a user can successfully log in with correct credentials."""
    response = client.post(
        "/auth/login",
        data={"username": test_user["username"], "password": test_user["password"]},
    )
    assert response.status_code == 200
    assert response.json() == {"status": "success"}
