import hashlib
import json

from app.core.config import settings
from app.utils.httpx_client import get_httpx_client


def sha256_hash(text):
    """Generate SHA256 hash."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def authenticate_broker(userid, password, totp_code):
    """
    Authenticate with Finvasia and return the auth token.

    NOTE: This is a placeholder implementation. The actual API endpoints,
    payload, and response handling will need to be updated based on the
    official Finvasia API documentation.
    """
    # Get the Finvasia API key and other credentials from environment variables
    api_secretkey = settings.BROKER_API_SECRET
    vendor_code = settings.BROKER_API_KEY
    imei = "abc1234"  # Default IMEI if not provided

    try:
        # Placeholder for Finvasia API login URL
        url = "https://api.finvasia.com/some-auth-endpoint"

        # Placeholder for login payload
        payload = {
            "uid": userid,
            "pwd": sha256_hash(password),
            "factor2": totp_code,
            "apkversion": "1.0.0",
            "appkey": sha256_hash(f"{userid}|{api_secretkey}"),
            "imei": imei,
            "vc": vendor_code,
            "source": "API",
        }

        # Convert payload to string with 'jData=' prefix
        payload_str = "jData=" + json.dumps(payload)

        # Set headers for the API request
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        # Get the shared httpx client and send the POST request
        client = get_httpx_client()
        response = client.post(url, data=payload_str, headers=headers)

        # Handle the response
        if response.status_code == 200:
            data = response.json()
            # Placeholder for success condition
            if data.get("stat") == "Ok":
                # Placeholder for token extraction
                return data.get("susertoken"), None
            else:
                return None, data.get("emsg", "Authentication failed.")
        else:
            return None, f"Error: {response.status_code}, {response.text}"

    except Exception as e:
        return None, str(e)
