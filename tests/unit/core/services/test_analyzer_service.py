import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from app.core.services import analyzer_service

@pytest.mark.asyncio
async def test_get_recent_requests():
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_result

    requests = await analyzer_service.get_recent_requests(mock_db)

    assert requests == []
    mock_db.execute.assert_called_once()

@pytest.mark.asyncio
async def test_get_filtered_requests():
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_result

    requests = await analyzer_service.get_filtered_requests(mock_db, start_date="2023-01-01")

    assert requests == []
    mock_db.execute.assert_called_once()

@pytest.mark.asyncio
async def test_clear_analyzer_logs():
    mock_db = AsyncMock()

    success, message = await analyzer_service.clear_analyzer_logs(mock_db)

    assert success is True
    assert message == "Analyzer logs cleared successfully"
    mock_db.execute.assert_called_once()
    mock_db.commit.assert_called_once()
