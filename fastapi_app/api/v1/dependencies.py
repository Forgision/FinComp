from fastapi import Security, HTTPException, status, Request
from fastapi.security import APIKeyHeader
from typing import Optional
from fastapi.templating import Jinja2Templates

from database.auth_db import verify_api_key, get_auth_token_broker
from fastapi_app.core.logging import get_logger

# Initialize logger
logger = get_logger(__name__)

# Define the API key header
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)

async def get_valid_api_key(api_key: str = Security(api_key_header)) -> str:
    """
    Dependency to verify the API key.
    """
    user_id = await verify_api_key(provided_api_key=api_key)
    if user_id is None:
        logger.warning(f"Invalid API key received.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing API Key"
        )
    return user_id

class AuthBroker:
    """Data class to hold authentication details."""
    def __init__(self, token: str, broker: str, api_key: str):
        self.token = token
        self.broker = broker
        self.api_key = api_key

async def get_auth_broker(api_key: str = Security(api_key_header)) -> AuthBroker:
    """
    Dependency to get auth token, broker, and the original API key.
    """
    auth_token, broker_name = await get_auth_token_broker(provided_api_key=api_key)

    if not auth_token or not broker_name:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not retrieve broker details for the provided API key."
        )

    return AuthBroker(token=auth_token, broker=broker_name, api_key=api_key)

def get_templates(request: Request) -> Jinja2Templates:
    """
    Dependency to get the Jinja2Templates instance from the application state.
    """
    templates = request.app.state.templates
    if not templates:
        # This will help in debugging if templates are not loaded
        logger.error("Jinja2Templates instance not found in application state.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Templates are not configured on the application."
        )
    return templates

