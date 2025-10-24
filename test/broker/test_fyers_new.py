import pytest
from app.broker.broker.fyers.api.auth_api import authenticate_broker

def test_import():
    assert authenticate_broker is not None
