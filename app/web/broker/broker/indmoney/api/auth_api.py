from app.core.config import settings


def authenticate_broker(code):
    try:
        BROKER_API_SECRET = settings.BROKER_API_SECRET

        # For IndMoney, the access token is directly provided in BROKER_API_SECRET
        # No OAuth flow needed - just return the access token
        if BROKER_API_SECRET:
            return BROKER_API_SECRET, None
        else:
            return None, "No access token found in BROKER_API_SECRET environment variable"

    except Exception as e:
        return None, f"An exception occurred: {str(e)}"

