import pytest
from unittest.mock import patch, MagicMock
from decimal import Decimal
from datetime import datetime
import pytz

from app.sandbox.fund_manager import FundManager, is_option, is_future
from app.core.schemas.sandbox_db import SandboxFunds

class TestFundManager:

    @pytest.fixture
    def setup_fund_manager(self):
        user_id = "test_user"

        with patch('app.sandbox.fund_manager.db_session') as mock_db_session,\
             patch('app.sandbox.fund_manager.get_config', return_value='10000000.00') as mock_get_config:

            mock_query = MagicMock()
            mock_db_session.query.return_value.filter_by.return_value = mock_query

            mock_funds_instance = MagicMock(spec=SandboxFunds)
            mock_funds_instance.user_id = user_id
            mock_funds_instance.available_balance = Decimal('100000.00')
            mock_funds_instance.used_margin = Decimal('0.00')
            mock_funds_instance.realized_pnl = Decimal('0.00')
            mock_funds_instance.unrealized_pnl = Decimal('0.00')
            mock_funds_instance.total_pnl = Decimal('0.00')
            mock_funds_instance.last_reset_date = datetime.now(pytz.timezone('Asia/Kolkata'))
            mock_funds_instance.reset_count = 0

            yield user_id, mock_db_session, mock_query, mock_funds_instance

    def test_is_option(self):
        assert is_option("NIFTY21JULFUT15500CE", "NFO")
        assert is_option("NIFTY21JULFUT15500PE", "NFO")
        assert not is_option("NIFTY21JULFUT", "NFO")
        assert not is_option("RELIANCE", "NSE")

    def test_is_future(self):
        assert is_future("NIFTY21JULFUT", "NFO")
        assert not is_future("NIFTY21JULFUT15500CE", "NFO")
        assert not is_future("RELIANCE", "NSE")

    def test_initialize_funds_when_none_exist(self, setup_fund_manager):
        user_id, mock_db_session, mock_query, _ = setup_fund_manager
        mock_query.first.return_value = None
        fund_manager = FundManager(user_id)
        success, message = fund_manager.initialize_funds()
        assert success
        assert message == "Funds initialized successfully"
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()

    @patch('app.sandbox.fund_manager.FundManager._check_and_reset_funds')
    def test_get_funds(self, mock_check_reset, setup_fund_manager):
        user_id, _, mock_query, mock_funds_instance = setup_fund_manager
        mock_query.first.return_value = mock_funds_instance
        fund_manager = FundManager(user_id)
        funds = fund_manager.get_funds()
        assert funds is not None
        assert funds['availablecash'] == float(mock_funds_instance.available_balance)
        mock_check_reset.assert_called_once()

    def test_block_margin_success(self, setup_fund_manager):
        user_id, mock_db_session, mock_query, mock_funds_instance = setup_fund_manager
        mock_query.first.return_value = mock_funds_instance
        fund_manager = FundManager(user_id)
        success, message = fund_manager.block_margin(5000)
        assert success
        assert mock_funds_instance.available_balance == Decimal('95000.00')
        assert mock_funds_instance.used_margin == Decimal('5000.00')
        mock_db_session.commit.assert_called_once()

    def test_release_margin_success(self, setup_fund_manager):
        user_id, mock_db_session, mock_query, mock_funds_instance = setup_fund_manager
        mock_funds_instance.used_margin = Decimal('5000.00')
        mock_funds_instance.available_balance = Decimal('95000.00')
        mock_query.first.return_value = mock_funds_instance
        fund_manager = FundManager(user_id)
        success, message = fund_manager.release_margin(5000, 100)
        assert success
        assert mock_funds_instance.used_margin == Decimal('0.00')
        assert mock_funds_instance.available_balance == Decimal('100100.00')
        assert mock_funds_instance.realized_pnl == Decimal('100.00')
        mock_db_session.commit.assert_called_once()
