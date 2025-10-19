import json

from app.utils.httpx_client import get_httpx_client

from app.core.config import settings
from app.utils.logging import logger


def get_margin_data(auth_token):
    """
    Fetch margin data from Finvasia's API using the provided auth token.
    
    NOTE: This is a placeholder implementation. The actual API endpoints,
    payload, and response handling will need to be updated based on the
    official Finvasia API documentation.
    """
    userid = settings.BROKER_API_KEY
    actid = userid

    data = {
        "uid": userid,
        "actid": actid
    }

    payload_str = "jData=" + json.dumps(data) + "&jKey=" + auth_token

    client = get_httpx_client()

    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    url = "https://api.finvasia.com/NorenWClientTP/Limits" # Placeholder URL

    response = client.post(url, content=payload_str, headers=headers)

    margin_data = json.loads(response.text)

    logger.info(f"Funds Details: {margin_data}")

    if margin_data.get('stat') != 'Ok':
        logger.info(f"Error fetching margin data: {margin_data.get('emsg')}")
        return {}

    try:
        total_available_margin = float(margin_data.get('cash',0)) + float(margin_data.get('payin',0)) - float(margin_data.get('marginused',0))
        total_collateral = float(margin_data.get('brkcollamt',0))
        total_used_margin = float(margin_data.get('marginused',0))
        total_realised = -float(margin_data.get('rpnl',0))
        total_unrealised = float(margin_data.get('urmtom',0))

        processed_margin_data = {
            "availablecash": "{:.2f}".format(total_available_margin),
            "collateral": "{:.2f}".format(total_collateral),
            "m2munrealized": "{:.2f}".format(total_unrealised),
            "m2mrealized": "{:.2f}".format(total_realised),
            "utiliseddebits": "{:.2f}".format(total_used_margin),
        }
        return processed_margin_data
    except KeyError as e:
        logger.error(f"Error processing margin data: {e}")
        return {}