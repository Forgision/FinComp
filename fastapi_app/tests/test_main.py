import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_root_endpoint(async_client: AsyncClient):
    """
    Test the root endpoint to ensure it returns a successful response.
    """
    response = await async_client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "message": "Welcome to OpenAlgo on FastAPI!"}
