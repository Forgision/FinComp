import hashlib
import json

from app.core.brokers.base import AuthConfig, BaseBrokerAuth
from app.core.config import settings
from app.utils.httpx_client import get_httpx_client
from app.utils.logging import logger


class FyersAuth(BaseBrokerAuth):
    """
    Fyers Broker Authentication Implementation.
    """

    async def authenticate(self, config: AuthConfig) -> str:
        """
        Authenticate with Fyers using authorization code.
        Returns the access token.
        """
        request_token = config.auth_code
        if not request_token:
            raise ValueError("auth_code is required for Fyers authentication")

        broker_api_key = settings.BROKER_API_KEY
        broker_api_secret = settings.BROKER_API_SECRET

        if not broker_api_key or not broker_api_secret:
            raise ValueError("Missing BROKER_API_KEY or BROKER_API_SECRET")

        url = "https://api-t1.fyers.in/api/v3/validate-authcode"

        checksum_input = f"{broker_api_key}:{broker_api_secret}"
        app_id_hash = hashlib.sha256(checksum_input.encode("utf-8")).hexdigest()

        payload = {
            "grant_type": "authorization_code",
            "appIdHash": app_id_hash,
            "code": request_token,
        }

        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        client = get_httpx_client()

        logger.debug(
            f"Authenticating with FYERS API. Request: {json.dumps(payload, indent=2)}"
        )

        try:
            response = await client.post(
                url,
                headers=headers,
                json=payload,
                timeout=30.0,
            )
            response.raise_for_status()
            auth_data = response.json()

            if auth_data.get("s") == "ok":
                access_token = auth_data.get("access_token")
                if not access_token:
                    raise Exception(
                        "Authentication succeeded but no access token returned"
                    )
                return access_token
            else:
                error_msg = auth_data.get("message", "Authentication failed")
                raise Exception(f"API error: {error_msg}")

        except Exception as e:
            logger.exception("Fyers Authentication failed")
            raise e
