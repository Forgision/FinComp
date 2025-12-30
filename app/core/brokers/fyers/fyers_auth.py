import hashlib
import json

from app.core.brokers.base import AuthConfig, AuthResponse, BaseBrokerAuth

from app.utils.httpx_client import get_httpx_client
from app.utils.logging import logger


class FyersAuth(BaseBrokerAuth):
    """
    Fyers Broker Authentication Implementation.
    """

    async def authenticate(self, config: AuthConfig) -> AuthResponse:
        """
        Authenticate with Fyers using authorization code.
        Returns the AuthResponse containing access token and other details.
        """

        request_token = config.auth_code
        if not request_token:
            logger.error("No request token provided for Fyers authentication")
            raise ValueError("auth_code is required for Fyers authentication")

        # Prefer config credentials, fall back to settings if not provided (or remove fallback if strict)
        # Based on user request "Instead of using from settings, I want to use AuthConfig", I will prioritize config.
        broker_api_key = config.api_key
        broker_api_secret = config.api_secret

        if not broker_api_key or not broker_api_secret:
            logger.error("Missing api_key or api_secret in AuthConfig")
            raise ValueError("api_key and api_secret are required in AuthConfig")

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
            logger.debug(f"FYERS auth API response: {json.dumps(auth_data, indent=2)}")

            if auth_data.get("s") == "ok":
                access_token = auth_data.get("access_token")
                if not access_token:
                    error_msg = (
                        "Authentication succeeded but no access token was returned"
                    )
                    logger.error(error_msg)
                    raise Exception(error_msg)

                logger.debug("Successfully authenticated with FYERS API")
                return AuthResponse(
                    access_token=access_token,
                    refresh_token=auth_data.get("refresh_token"),
                    expires_in=auth_data.get("expires_in"),
                    message="Authentication successful",
                    status="success",
                )
            else:
                error_msg = auth_data.get("message", "Authentication failed")
                logger.error(f"FYERS API error: {error_msg}")
                raise Exception(f"API error: {error_msg}")

        except Exception as e:
            logger.exception("Fyers Authentication failed")
            raise e
