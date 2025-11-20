import pytest
pytest.skip("Skipped by user request", allow_module_level=True)
import unittest
from unittest.mock import patch, MagicMock
from app.web.brokers.kotak.api.auth_api import authenticate_broker


class TestKotakAuthApi(unittest.TestCase):

    @patch('app.web.broker.broker.kotak.api.auth_api.http.client.HTTPSConnection')
    def test_authenticate_broker_success(self, mock_https_connection):
        mock_conn = MagicMock()
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"data": {"token": "test_token", "sid": "test_sid"}}'
        mock_conn.getresponse.return_value = mock_response
        mock_https_connection.return_value = mock_conn

        auth_string, error = authenticate_broker("123456", "token", "sid", "userid", "access_token", "hsServerId")
        self.assertEqual(auth_string, "test_token:::test_sid:::hsServerId:::access_token")
        self.assertIsNone(error)

    @patch('app.web.broker.broker.kotak.api.auth_api.http.client.HTTPSConnection')
    def test_authenticate_broker_failure(self, mock_https_connection):
        mock_conn = MagicMock()
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"error": "Invalid OTP"}'
        mock_conn.getresponse.return_value = mock_response
        mock_https_connection.return_value = mock_conn

        auth_string, error = authenticate_broker("wrong_otp", "token", "sid", "userid", "access_token", "hsServerId")
        self.assertIsNone(auth_string)
        self.assertIsNotNone(error)

if __name__ == '__main__':
    unittest.main()