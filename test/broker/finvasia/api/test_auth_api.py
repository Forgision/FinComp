import unittest
from unittest.mock import patch, MagicMock
from app.broker.finvasia.api.auth_api import authenticate_broker, sha256_hash

class TestFinvasiaAuthApi(unittest.TestCase):

    def test_sha256_hash(self):
        self.assertEqual(sha256_hash("password"), "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8")

    @patch('app.broker.finvasia.api.auth_api.get_httpx_client')
    def test_authenticate_broker_success(self, mock_get_httpx_client):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"stat": "Ok", "susertoken": "test_token"}
        mock_client.post.return_value = mock_response
        mock_get_httpx_client.return_value = mock_client

        token, error = authenticate_broker("testuser", "password", "123456")
        self.assertEqual(token, "test_token")
        self.assertIsNone(error)

    @patch('app.broker.finvasia.api.auth_api.get_httpx_client')
    def test_authenticate_broker_failure(self, mock_get_httpx_client):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"stat": "Not_Ok", "emsg": "Invalid credentials"}
        mock_client.post.return_value = mock_response
        mock_get_httpx_client.return_value = mock_client

        token, error = authenticate_broker("testuser", "wrong_password", "123456")
        self.assertIsNone(token)
        self.assertEqual(error, "Invalid credentials")

    @patch('app.broker.finvasia.api.auth_api.get_httpx_client')
    def test_authenticate_broker_http_error(self, mock_get_httpx_client):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_client.post.return_value = mock_response
        mock_get_httpx_client.return_value = mock_client

        token, error = authenticate_broker("testuser", "password", "123456")
        self.assertIsNone(token)
        self.assertEqual(error, "Error: 404, Not Found")

if __name__ == '__main__':
    unittest.main()