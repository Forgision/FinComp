import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from decimal import Decimal
from datetime import datetime
import pytz

from app.algo.sandbox.fund_manager import FundManager, is_option, is_future
from app.core.schemas.sandbox_db import SandboxFunds


class TestFundManager:
    @pytest.fixture
    async def setup_fund_manager(self):
        user_id = "test_user"

        # Mock AsyncSessionLocal to return an async context manager
        mock_session = AsyncMock()
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        # Setup query mock
        mock_result = MagicMock()
        mock_session.execute.return_value = mock_result
        mock_result.scalars.return_value.first.return_value = None
        mock_result.scalars.return_value.all.return_value = []

        # Mock SandboxFunds instance
        mock_funds_instance = MagicMock(spec=SandboxFunds)
        mock_funds_instance.user_id = user_id
        mock_funds_instance.available_balance = Decimal("100000.00")
        mock_funds_instance.used_margin = Decimal("0.00")
        mock_funds_instance.realized_pnl = Decimal("0.00")
        mock_funds_instance.unrealized_pnl = Decimal("0.00")
        mock_funds_instance.total_pnl = Decimal("0.00")
        mock_funds_instance.last_reset_date = datetime.now(
            pytz.timezone("Asia/Kolkata")
        )
        mock_funds_instance.reset_count = 0

        with (
            patch(
                "app.algo.sandbox.fund_manager.AsyncSessionLocal",
                return_value=mock_session,
            ),
            patch(
                "app.algo.sandbox.fund_manager.get_config", return_value="10000000.00"
            ),
        ):
            yield user_id, mock_session, mock_funds_instance

    def test_is_option(self):
        assert is_option("NIFTY21JULFUT15500CE", "NFO")
        assert is_option("NIFTY21JULFUT15500PE", "NFO")
        assert not is_option("NIFTY21JULFUT", "NFO")
        assert not is_option("RELIANCE", "NSE")

    def test_is_future(self):
        assert is_future("NIFTY21JULFUT", "NFO")
        assert not is_future("NIFTY21JULFUT15500CE", "NFO")
        assert not is_future("RELIANCE", "NSE")

    @pytest.mark.asyncio
    async def test_initialize_funds_when_none_exist(self, setup_fund_manager):
        user_id, mock_session, _ = setup_fund_manager
        # Configure mock to return None for the first query (check existence)
        mock_session.execute.return_value.scalars.return_value.first.return_value = None

        fund_manager = FundManager(user_id)
        success, message = await fund_manager.initialize_funds()

        assert success
        assert message == "Funds initialized successfully"
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.algo.sandbox.fund_manager.FundManager._check_and_reset_funds")
    async def test_get_funds(self, mock_check_reset, setup_fund_manager):
        user_id, mock_session, mock_funds_instance = setup_fund_manager
        # Configure mock to return funds instance
        mock_session.execute.return_value.scalars.return_value.first.return_value = (
            mock_funds_instance
        )

        fund_manager = FundManager(user_id)
        funds = await fund_manager.get_funds()

        assert funds is not None
        assert funds["availablecash"] == float(mock_funds_instance.available_balance)
        mock_check_reset.assert_called_once()

    @pytest.mark.asyncio
    async def test_block_margin_success(self, setup_fund_manager):
        user_id, mock_session, mock_funds_instance = setup_fund_manager
        mock_session.execute.return_value.scalars.return_value.first.return_value = (
            mock_funds_instance
        )

        fund_manager = FundManager(user_id)
        success, message = await fund_manager.block_margin(5000)

        assert success
        assert mock_funds_instance.available_balance == Decimal("95000.00")
        assert mock_funds_instance.used_margin == Decimal("5000.00")
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_release_margin_success(self, setup_fund_manager):
        user_id, mock_session, mock_funds_instance = setup_fund_manager
        mock_funds_instance.used_margin = Decimal("5000.00")
        mock_funds_instance.available_balance = Decimal("95000.00")
        mock_session.execute.return_value.scalars.return_value.first.return_value = (
            mock_funds_instance
        )

        fund_manager = FundManager(user_id)
        success, message = await fund_manager.release_margin(5000, 100)

        assert success
        assert mock_funds_instance.used_margin == Decimal("0.00")
        assert mock_funds_instance.available_balance == Decimal("100100.00")
        assert mock_funds_instance.realized_pnl == Decimal("100.00")
        mock_session.commit.assert_called_once()
