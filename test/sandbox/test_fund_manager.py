import unittest
from unittest.mock import patch, MagicMock
from decimal import Decimal
from datetime import datetime
import pytz

from app.sandbox.fund_manager import FundManager, is_option, is_future
from app.core.schemas.sandbox_db import SandboxFunds

class TestFundManager(unittest.TestCase):

    def setUp(self):
        self.user_id = "test_user"

        # --- Manual Patching for db_session ---
        self.db_session_patcher = patch('app.sandbox.fund_manager.db_session')
        self.mock_db_session = self.db_session_patcher.start()

        # Create a mock for the query object for better isolation
        self.mock_query = MagicMock()
        self.mock_db_session.query.return_value.filter_by.return_value = self.mock_query

        # --- Mock for get_config ---
        self.get_config_patcher = patch('app.sandbox.fund_manager.get_config', return_value='10000000.00')
        self.mock_get_config = self.get_config_patcher.start()

        # --- Mock 'funds' instance ---
        self.mock_funds_instance = MagicMock(spec=SandboxFunds)
        self.mock_funds_instance.user_id = self.user_id
        self.mock_funds_instance.available_balance = Decimal('100000.00')
        self.mock_funds_instance.used_margin = Decimal('0.00')
        self.mock_funds_instance.realized_pnl = Decimal('0.00')
        self.mock_funds_instance.unrealized_pnl = Decimal('0.00')
        self.mock_funds_instance.total_pnl = Decimal('0.00')
        self.mock_funds_instance.last_reset_date = datetime.now(pytz.timezone('Asia/Kolkata'))
        self.mock_funds_instance.reset_count = 0

    def tearDown(self):
        self.get_config_patcher.stop()
        self.db_session_patcher.stop()

    def test_is_option(self):
        self.assertTrue(is_option("NIFTY21JULFUT15500CE", "NFO"))
        self.assertTrue(is_option("NIFTY21JULFUT15500PE", "NFO"))
        self.assertFalse(is_option("NIFTY21JULFUT", "NFO"))
        self.assertFalse(is_option("RELIANCE", "NSE"))

    def test_is_future(self):
        self.assertTrue(is_future("NIFTY21JULFUT", "NFO"))
        self.assertFalse(is_future("NIFTY21JULFUT15500CE", "NFO"))
        self.assertFalse(is_future("RELIANCE", "NSE"))

    def test_initialize_funds_when_none_exist(self):
        self.mock_query.first.return_value = None
        fund_manager = FundManager(self.user_id)
        success, message = fund_manager.initialize_funds()
        self.assertTrue(success)
        self.assertEqual(message, "Funds initialized successfully")
        self.mock_db_session.add.assert_called_once()
        self.mock_db_session.commit.assert_called_once()

    @patch('app.sandbox.fund_manager.FundManager._check_and_reset_funds')
    def test_get_funds(self, mock_check_reset):
        self.mock_query.first.return_value = self.mock_funds_instance
        fund_manager = FundManager(self.user_id)
        funds = fund_manager.get_funds()
        self.assertIsNotNone(funds)
        self.assertEqual(funds['availablecash'], float(self.mock_funds_instance.available_balance))
        mock_check_reset.assert_called_once()

    def test_block_margin_success(self):
        self.mock_query.first.return_value = self.mock_funds_instance
        fund_manager = FundManager(self.user_id)
        success, message = fund_manager.block_margin(5000)
        self.assertTrue(success)
        self.assertEqual(self.mock_funds_instance.available_balance, Decimal('95000.00'))
        self.assertEqual(self.mock_funds_instance.used_margin, Decimal('5000.00'))
        self.mock_db_session.commit.assert_called_once()

    def test_release_margin_success(self):
        self.mock_funds_instance.used_margin = Decimal('5000.00')
        self.mock_funds_instance.available_balance = Decimal('95000.00')
        self.mock_query.first.return_value = self.mock_funds_instance
        fund_manager = FundManager(self.user_id)
        success, message = fund_manager.release_margin(5000, 100)
        self.assertTrue(success)
        self.assertEqual(self.mock_funds_instance.used_margin, Decimal('0.00'))
        self.assertEqual(self.mock_funds_instance.available_balance, Decimal('100100.00'))
        self.assertEqual(self.mock_funds_instance.realized_pnl, Decimal('100.00'))
        self.mock_db_session.commit.assert_called_once()

if __name__ == '__main__':
    unittest.main()
