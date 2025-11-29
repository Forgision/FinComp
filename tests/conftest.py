import pytest
import random
from app.core.config import settings


@pytest.fixture(scope="session", autouse=True)
def mock_settings():
    """
    Global fixture to override settings for the entire test session.
    Using random ports to avoid conflicts with running services.
    """
    # Generate random ports in the range 20000-60000
    settings.ZMQ_PORT = random.randint(20000, 30000)
    settings.ZMQ_DATA_REQ_PORT = random.randint(30001, 40000)
    settings.ZMQ_DATA_ROUTER_PORT = random.randint(40001, 50000)

    # Ensure we are in a test environment
    settings.APP_ENV = "testing"

    yield
