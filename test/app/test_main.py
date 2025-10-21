import unittest
from fastapi.testclient import TestClient
from app.main import _app

class TestMainApp(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(_app)

    def test_read_main(self):
        response = self.client.get("/test")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"message": "Hello World"})

if __name__ == '__main__':
    unittest.main()
