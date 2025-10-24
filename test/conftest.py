import pytest
from unittest.mock import MagicMock

class MockSettings:
    """
    A mock settings class for testing purposes.
    This class can be extended to include specific settings
    needed for different test environments.
    """
    DEBUG: bool = True
    TESTING: bool = True
    DATABASE_URL: str = "sqlite:///./test.db"
    SECRET_KEY: str = "super-secret-test-key"
    # Add other settings as needed for your application

@pytest.fixture(scope="session")
def mock_settings():
    """
    Provides a mock settings object for tests.
    """
    return MockSettings()

# Example of how to use pytest_addoption for environment differentiation
# This can be expanded later if dynamic environment switching is required.
def pytest_addoption(parser):
    parser.addoption(
        "--env", action="store", default="test", help="Environment to run tests against: test, dev, prod"
    )

@pytest.fixture(scope="session")
def env(request):
    return request.config.getoption("--env")

# You can then create fixtures that depend on 'env' to provide different settings
# For example:
# @pytest.fixture(scope="session")
# def app_settings(env):
#     if env == "dev":
#         # Return dev settings
#         pass
#     elif env == "prod":
#         # Return prod settings
#         pass
#     else: # default to test
#         return MockSettings()
