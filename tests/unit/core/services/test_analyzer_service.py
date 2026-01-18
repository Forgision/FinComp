import pytest
from datetime import datetime, timedelta
import pytz
import json
from unittest.mock import MagicMock, AsyncMock, patch

from app.core.services import analyzer_service
from app.core.schemas.analyzer_db import AnalyzerLog

@pytest.fixture
def mock_analyzer_log():
    return AnalyzerLog(
        id=1,
        api_type="placeorder",
        request_data=json.dumps({"symbol": "TEST", "quantity": 10, "strategy": "TestStrategy"}),
        response_data=json.dumps({"status": "success", "message": "Order placed"}),
        created_at=datetime.now(pytz.UTC)
    )

@pytest.mark.asyncio
async def test_get_recent_requests_success(mock_analyzer_log):
    # Mock the database session
    mock_db = AsyncMock()

    # Mock the result of db.execute
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_analyzer_log]
    mock_db.execute.return_value = mock_result

    # Call the function
    requests = await analyzer_service.get_recent_requests(mock_db)

    # Assertions
    assert len(requests) == 1
    assert requests[0]["api_type"] == "placeorder"
    assert requests[0]["source"] == "TestStrategy"

    # Verify db execution
    mock_db.execute.assert_called_once()

@pytest.mark.asyncio
async def test_get_filtered_requests_success(mock_analyzer_log):
    # Mock the database session
    mock_db = AsyncMock()

    # Mock the result of db.execute
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_analyzer_log]
    mock_db.execute.return_value = mock_result

    # Call the function with dates
    requests = await analyzer_service.get_filtered_requests(
        mock_db,
        start_date="2024-01-01",
        end_date="2024-01-02"
    )

    # Assertions
    assert len(requests) == 1

    # Verify db execution
    mock_db.execute.assert_called_once()

@pytest.mark.asyncio
async def test_clear_analyzer_logs_success():
    # Mock the database session
    mock_db = AsyncMock()

    # Call the function
    success, message = await analyzer_service.clear_analyzer_logs(mock_db)

    # Assertions
    assert success is True
    assert "successfully" in message

    # Verify db execution and commit
    mock_db.execute.assert_called_once()
    mock_db.commit.assert_called_once()
