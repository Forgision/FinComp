import unittest
from unittest.mock import patch, MagicMock
import json
import hashlib

from app.broker.finvasia.api.auth_api import sha256_hash, authenticate_broker

class TestAuthAPI(unittest.TestCase):

    def test_sha256_hash(self):
        self.assertEqual(sha256_hash("test"), hashlib.sha256("test".encode('utf-8')).hexdigest())
        self.assertEqual(sha256_hash("password123"), hashlib.sha256("password123".encode('utf-8')).hexdigest())

    @patch('app.broker.finvasia.api.auth_api.settings')
    @patch('app.broker.finvasia.api.auth_api.get_httpx_client')
    def test_authenticate_broker_success(self, mock_get_httpx_client, mock_settings):
        # Mock settings
        mock_settings.BROKER_API_SECRET = "test_secret"
        mock_settings.BROKER_API_KEY = "test_vendor_code"

        # Mock httpx client and response
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_get_httpx_client.return_value = mock_client
        mock_client.post.return_value = mock_response

        mock_response.status_code = 200
        mock_response.json.return_value = {"stat": "Ok", "susertoken": "mock_token"}

        userid = "testuser"
        password = "testpassword"
        totp_code = "123456"

        token, error = authenticate_broker(userid, password, totp_code)

        self.assertEqual(token, "mock_token")
        self.assertIsNone(error)

        # Verify post call arguments
        expected_url = "https://api.finvasia.com/some-auth-endpoint"
        expected_payload = {
            "uid": userid,
            "pwd": sha256_hash(password),
            "factor2": totp_code,
            "apkversion": "1.0.0",
            "appkey": sha256_hash(f"{userid}|{mock_settings.BROKER_API_SECRET}"),
            "imei": "abc1234",
            "vc": mock_settings.BROKER_API_KEY,
            "source": "API"
        }
        expected_payload_str = "jData=" + json.dumps(expected_payload)
        expected_headers = {'Content-Type': 'application/x-www-form-urlencoded'}

        mock_client.post.assert_called_once_with(expected_url, data=expected_payload_str, headers=expected_headers)

    @patch('app.broker.finvasia.api.auth_api.settings')
    @patch('app.broker.finvasia.api.auth_api.get_httpx_client')
    def test_authenticate_broker_failure_api_error(self, mock_get_httpx_client, mock_settings):
        # Mock settings
        mock_settings.BROKER_API_SECRET = "test_secret"
        mock_settings.BROKER_API_KEY = "test_vendor_code"

        # Mock httpx client and response
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_get_httpx_client.return_value = mock_client
        mock_client.post.return_value = mock_response

        mock_response.status_code = 200
        mock_response.json.return_value = {"stat": "Not_Ok", "emsg": "Invalid credentials"}

        userid = "testuser"
        password = "wrongpassword"
        totp_code = "123456"

        token, error = authenticate_broker(userid, password, totp_code)

        self.assertIsNone(token)
        self.assertEqual(error, "Invalid credentials")

    @patch('app.broker.finvasia.api.auth_api.settings')
    @patch('app.broker.finvasia.api.auth_api.get_httpx_client')
    def test_authenticate_broker_failure_http_error(self, mock_get_httpx_client, mock_settings):
        # Mock settings
        mock_settings.BROKER_API_SECRET = "test_secret"
        mock_settings.BROKER_API_KEY = "test_vendor_code"

        # Mock httpx client and response
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_get_httpx_client.return_value = mock_client
        mock_client.post.return_value = mock_response

        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        userid = "testuser"
        password = "testpassword"
        totp_code = "123456"

        token, error = authenticate_broker(userid, password, totp_code)

        self.assertIsNone(token)
        self.assertEqual(error, "Error: 401, Unauthorized")

    @patch('app.broker.finvasia.api.auth_api.settings')
    @patch('app.broker.finvasia.api.auth_api.get_httpx_client')
    def test_authenticate_broker_exception_handling(self, mock_get_httpx_client, mock_settings):
        # Mock settings
        mock_settings.BROKER_API_SECRET = "test_secret"
        mock_settings.BROKER_API_KEY = "test_vendor_code"

        # Mock httpx client to raise an exception
        mock_client = MagicMock()
        mock_get_httpx_client.return_value = mock_client
        mock_client.post.side_effect = Exception("Network error")

        userid = "testuser"
        password = "testpassword"
        totp_code = "123456"

        token, error = authenticate_broker(userid, password, totp_code)

        self.assertIsNone(token)
        self.assertEqual(error, "Network error")

if __name__ == '__main__':
    unittest.main()