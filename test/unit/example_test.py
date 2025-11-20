import pytest
from unittest.mock import MagicMock


@pytest.fixture
def mock_settings():
    settings = MagicMock()
    settings.DEBUG = True
    settings.TESTING = True
    return settings


def test_example_unit_test():
    """A basic example unit test."""
    assert 1 + 1 == 2


def test_another_example_unit_test(mock_settings):
    """Another example unit test using the mock_settings fixture."""
    assert mock_settings.DEBUG is True
    assert mock_settings.TESTING is True
