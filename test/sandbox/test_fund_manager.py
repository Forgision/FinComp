import unittest
from unittest.mock import patch, MagicMock
from decimal import Decimal
from datetime import datetime
import pytz

from app.sandbox.fund_manager import FundManager, is_option, is_future

class TestFundManager(unittest.TestCase):

    def setUp(self):
        self.user_id = "test_user"
        self.fund_manager = FundManager(self.user_id)

    def test_is_option(self):
        self.assertTrue(is_option("NIFTY21JULFUT15500CE", "NFO"))
        self.assertTrue(is_option("NIFTY21JULFUT15500PE", "NFO"))
        self.assertFalse(is_option("NIFTY21JULFUT", "NFO"))
        self.assertFalse(is_option("RELIANCE", "NSE"))

    def test_is_future(self):
        self.assertTrue(is_future("NIFTY21JULFUT", "NFO"))
        self.assertFalse(is_future("NIFTY21JULFUT15500CE", "NFO"))
        self.assertFalse(is_future("RELIANCE", "NSE"))

    @patch('app.sandbox.fund_manager.db_session')
    @patch('app.sandbox.fund_manager.SandboxFunds')
    def test_initialize_funds(self, mock_sandbox_funds, mock_db_session):
        mock_sandbox_funds.query.filter_by.return_value.first.return_value = None
        success, message = self.fund_manager.initialize_funds()
        self.assertTrue(success)
        self.assertEqual(message, "Funds initialized successfully")
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()

    @patch('app.sandbox.fund_manager.SandboxFunds')
    def test_get_funds(self, mock_sandbox_funds):
        mock_funds = MagicMock()
        mock_funds.available_balance = Decimal('10000000.00')
        mock_funds.unrealized_pnl = Decimal('0.00')
        mock_funds.realized_pnl = Decimal('0.00')
        mock_funds.used_margin = Decimal('0.00')
        mock_funds.total_pnl = Decimal('0.00')
        mock_funds.last_reset_date = datetime.now(pytz.timezone('Asia/Kolkata'))
        mock_funds.reset_count = 0
        mock_sandbox_funds.query.filter_by.return_value.first.return_value = mock_funds
        
        funds = self.fund_manager.get_funds()
        self.assertIsNotNone(funds)
        self.assertEqual(funds['availablecash'], 10000000.00)

    @patch('app.sandbox.fund_manager.db_session')
    @patch('app.sandbox.fund_manager.SandboxFunds')
    def test_block_margin(self, mock_sandbox_funds, mock_db_session):
        mock_funds = MagicMock()
        mock_funds.available_balance = Decimal('100000.00')
        mock_sandbox_funds.query.filter_by.return_value.first.return_value = mock_funds
        
        success, message = self.fund_manager.block_margin(5000)
        self.assertTrue(success)
        self.assertEqual(mock_funds.available_balance, Decimal('95000.00'))
        self.assertEqual(mock_funds.used_margin, Decimal('5000.00'))
        mock_db_session.commit.assert_called_once()

    @patch('app.sandbox.fund_manager.db_session')
    @patch('app.sandbox.fund_manager.SandboxFunds')
    def test_release_margin(self, mock_sandbox_funds, mock_db_session):
        mock_funds = MagicMock()
        mock_funds.used_margin = Decimal('5000.00')
        mock_funds.available_balance = Decimal('95000.00')
        mock_funds.realized_pnl = Decimal('0.00')
        mock_funds.unrealized_pnl = Decimal('0.00')
        mock_sandbox_funds.query.filter_by.return_value.first.return_value = mock_funds

        success, message = self.fund_manager.release_margin(5000, 100)
        self.assertTrue(success)
        self.assertEqual(mock_funds.used_margin, Decimal('0.00'))
        self.assertEqual(mock_funds.available_balance, Decimal('100100.00'))
        self.assertEqual(mock_funds.realized_pnl, Decimal('100.00'))
        mock_db_session.commit.assert_called_once()

if __name__ == '__main__':
    unittest.main()