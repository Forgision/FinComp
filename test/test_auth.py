import unittest
from app.db.schemas.session import get_db
from fastapi.testclient import TestClient

from app.db.schemas.auth_db import delete_api_key_by_username, upsert_api_key
from app.db.schemas.user_db import add_user, delete_user_by_username
from app.main import _app as app_fastapi  # Import the underlying FastAPI app


class TestAuth(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app_fastapi, follow_redirects=True)
        self.username = "testuser"
        self.email = "test@example.com"
        self.password = "testpassword"
        self.api_key = "testapikey"

        # Create a test user and API key
        db = next(get_db())
        add_user(self.username, self.email, self.password, True)
        upsert_api_key(self.username, self.api_key)
        db.close()

    def tearDown(self):
        # Clean up the test user and API key
        db = next(get_db())
        delete_api_key_by_username(db, user_id=self.username)
        delete_user_by_username(self.username)
        db.close()

    def test_read_main(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Login", response.text)

    def test_login_page_access(self):
        response = self.client.get("/auth/login")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Login", response.text)
        self.assertIn("Username", response.text)
        self.assertIn("Password", response.text)

    def test_successful_login(self):
        response = self.client.post(
            "/auth/login",
            data={"username": self.username, "password": self.password},
            follow_redirects=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "success"})


if __name__ == '__main__':
    unittest.main()