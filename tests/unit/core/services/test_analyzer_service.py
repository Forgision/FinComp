import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.core.services import analyzer_service

@pytest.mark.asyncio
async def test_get_recent_requests_async():
    # Mock DB session
    mock_db = AsyncMock()

    # Mock execute result
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_result

    # Call the function
    requests = await analyzer_service.get_recent_requests(mock_db)

    # Verify it was awaited and execute was called
    mock_db.execute.assert_called_once()
    assert isinstance(requests, list)

@pytest.mark.asyncio
async def test_get_filtered_requests_async():
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_result

    requests = await analyzer_service.get_filtered_requests(mock_db)

    mock_db.execute.assert_called_once()
    assert isinstance(requests, list)

@pytest.mark.asyncio
async def test_clear_analyzer_logs_async():
    mock_db = AsyncMock()

    success, msg = await analyzer_service.clear_analyzer_logs(mock_db)

    mock_db.execute.assert_called_once()
    mock_db.commit.assert_awaited_once()
    assert success is True

@pytest.mark.asyncio
async def test_toggle_analyzer_mode_async():
    mock_db = AsyncMock()

    # We need to mock get_analyze_mode and set_analyze_mode imports in analyzer_service
    with patch('app.core.services.analyzer_service.get_analyze_mode', new_callable=AsyncMock) as mock_get, \
         patch('app.core.services.analyzer_service.set_analyze_mode', new_callable=AsyncMock) as mock_set:

        mock_get.return_value = False

        success, data, code = await analyzer_service.toggle_analyzer_mode(mock_db, {}, "")

        assert success is True
        mock_get.assert_awaited_once_with(mock_db)
        mock_set.assert_awaited_once_with(mock_db, True)

@pytest.mark.asyncio
async def test_get_analyzer_status_async():
    mock_db = AsyncMock()

    with patch('app.core.services.analyzer_service.get_analyze_mode', new_callable=AsyncMock) as mock_get, \
         patch('app.core.services.analyzer_service.get_analyzer_stats', new_callable=AsyncMock) as mock_stats:

        mock_get.return_value = True
        mock_stats.return_value = {}

        success, data, code = await analyzer_service.get_analyzer_status(mock_db, {}, "")

        assert success is True
        mock_get.assert_awaited_once_with(mock_db)
        mock_stats.assert_awaited_once_with(mock_db)
