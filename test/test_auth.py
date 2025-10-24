import unittest
from app.core.schemas.session import get_db
from fastapi.testclient import TestClient

from app.core.schemas.auth_db import delete_api_key_by_username, upsert_api_key
from app.core.schemas.user_db import (
    add_user,
    authenticate_user,
    delete_user_by_username,
    find_user_by_username,
    username_cache,
)
from app.main import _app as app_fastapi  # Import the underlying FastAPI app


class TestAuth(unittest.TestCase):
    def setUp(self):
        self.username = "testuser"
        self.email = "test@example.com"
        self.password = "testpassword"
        self.api_key = "testapikey"

        # Create a test user and API key
        self.db = next(get_db())
        delete_user_by_username("admin")
        add_user(self.username, self.email, self.password, True)
        upsert_api_key(self.username, self.api_key)
        self.db.commit()

    def tearDown(self):
        # Clean up the test user and API key
        try:
            delete_api_key_by_username(self.db, user_id=self.username)
            delete_user_by_username(self.username)
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            raise e
        finally:
            self.db.close()

    def test_read_main(self):
        client = TestClient(app_fastapi, follow_redirects=False)
        response = client.get("/")
        self.assertEqual(response.status_code, 302) # Expect redirect to login
        self.assertEqual(response.headers['location'], '/auth/login')

    def test_login_page_access(self):
        client = TestClient(app_fastapi, follow_redirects=False)
        response = client.get("/auth/login")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Login", response.text)
        self.assertIn("Username", response.text)
        self.assertIn("Password", response.text)

    def test_successful_login(self):
        client = TestClient(app_fastapi, follow_redirects=False)
        response = client.post(
            "/auth/login",
            data={"username": self.username, "password": self.password},
            follow_redirects=False
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "success"})

    def test_authenticate_user_caches_none(self):
        # Clear the cache to ensure a clean test
        username_cache.clear()

        # Try to authenticate a non-existent user
        authenticate_user("nonexistentuser", "password")

        # Check that the cache now contains a None value for the non-existent user
        self.assertIn("user-nonexistentuser", username_cache)
        self.assertIsNone(username_cache["user-nonexistentuser"])


if __name__ == '__main__':
    unittest.main()