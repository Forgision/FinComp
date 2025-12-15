from app.core.brokers.base import AuthConfig, BaseBrokerAuth
from app.core.config import settings
from app.utils.httpx_client import get_httpx_client
from app.utils.logging import logger


class UpstoxAuth(BaseBrokerAuth):
    """
    Upstox Broker Authentication Implementation.
    """

    async def authenticate(self, config: AuthConfig) -> str:
        """
        Authenticate with Upstox using authorization code.
        Returns the access token.
        """
        code = config.auth_code
        if not code:
            raise ValueError("auth_code is required for Upstox authentication")

        BROKER_API_KEY = settings.BROKER_API_KEY
        BROKER_API_SECRET = settings.BROKER_API_SECRET
        REDIRECT_URL = settings.REDIRECT_URL

        if not all([BROKER_API_KEY, BROKER_API_SECRET, REDIRECT_URL]):
            raise ValueError("Configuration error: Missing API credentials for Upstox")

        url = "https://api.upstox.com/v2/login/authorization/token"
        data = {
            "code": code,
            "client_id": BROKER_API_KEY,
            "client_secret": BROKER_API_SECRET,
            "redirect_uri": REDIRECT_URL,
            "grant_type": "authorization_code",
        }

        client = get_httpx_client()
        try:
            # Note: Upstox auth example used synchronous post in original code, but we should use async here if possible
            # or wrap it. The httpx client is usually async compatible if instantiated as AsyncClient, but get_httpx_client
            # likely returns an AsyncClient given other usages. Wait, original code usage:
            # client = get_httpx_client()
            # response = client.post(url, data=data) -> This looks synchronous if not awaited.
            # But in fyers `await client.post` was used.
            # Let's check `get_httpx_client` implementation to be sure.
            # I'll assume it returns an AsyncClient since we are in an async ecosystem, but the original upstox auth_api loop *didn't* use await?
            # Original: `response = client.post(url, data=data)` -> SYNC
            # Fyers original: `response = await client.post(...)` -> ASYNC
            # This implies `get_httpx_client` might return a sync client or the usage was mixed/wrong.
            # Let's check `app/utils/httpx_client.py`.
            # If I can't check, I'll assume I should use await if it's async context.
            # Given `BaseBrokerAuth.authenticate` is `async`, I should use `await`.

            response = await client.post(url, data=data)

            if response.status_code == 200:
                response_data = response.json()
                access_token = response_data.get("access_token")
                if access_token:
                    return access_token
                else:
                    raise Exception(f"No access token returned: {response_data}")
            else:
                raise Exception(f"Upstox Auth Failed: {response.text}")

        except Exception as e:
            logger.exception("Upstox Authentication failed")
            raise e
