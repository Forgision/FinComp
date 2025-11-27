# api/funds.py
import http.client
import json
import urllib.parse

from app.utils.logging import logger


def get_margin_data(auth_token):
    """Fetch margin data from the broker's API using the provided auth token."""
    access_token_parts = auth_token.split(":::")
    token = access_token_parts[0]
    sid = access_token_parts[1]
    hsServerId = access_token_parts[2]
    access_token = access_token_parts[3]

    conn = http.client.HTTPSConnection("gw-napi.kotaksecurities.com")
    payload = "jData=%7B%22seg%22%3A%22ALL%22%2C%22exch%22%3A%22ALL%22%2C%22prod%22%3A%22ALL%22%7D"
    query_params = {"sId": hsServerId}
    headers = {
        "accept": "application/json",
        "Sid": sid,
        "Auth": token,
        "neo-fin-key": "neotradeapi",
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Bearer {access_token}",
    }
    conn.request(
        "POST",
        "/Orders/2.0/quick/user/limits?" + urllib.parse.urlencode(query_params),
        payload,
        headers,
    )
    try:
        res = conn.getresponse()
        data = res.read()
        logger.info(f"{data.decode('utf-8')}")
        margin_data = json.loads(data.decode("utf-8"))

        # logger.info(f"Margin Data {margin_data}")

        # Process and return the 'data' key from margin_data if it exists and is not None

        # Sum up realized and unrealized PnL from all segments
        unrealized_pnl = (
            float(margin_data.get("CurUnRlsMtomPrsnt", 0))
            + float(margin_data.get("ComUnRlsMtomPrsnt", 0))
            + float(margin_data.get("FoUnRlsMtomPrsnt", 0))
            + float(margin_data.get("CashUnRlsMtomPrsnt", 0))
        )
        realized_pnl = (
            float(margin_data.get("CurRlsMtomPrsnt", 0))
            + float(margin_data.get("ComRlsMtomPrsnt", 0))
            + float(margin_data.get("FoRlsMtomPrsnt", 0))
            + float(margin_data.get("CashRlsMtomPrsnt", 0))
        )

        processed_margin_data = {
            "availablecash": f"{float(margin_data.get('Net', 0)):.2f}",
            "collateral": f"{float(margin_data.get('Collateral', 0)):.2f}",
            "m2munrealized": f"{unrealized_pnl:.2f}",
            "m2mrealized": f"{realized_pnl:.2f}",
            "utiliseddebits": f"{round(((float(margin_data.get('CurRlsMtomPrsnt', 0)) + float(margin_data.get('ComRlsMtomPrsnt', 0)) + float(margin_data.get('FoRlsMtomPrsnt', 0)) + float(margin_data.get('CashRlsMtomPrsnt', 0))) * -1) - (float(margin_data.get('MarginUsed', 0)) * -1) - (float(margin_data.get('RealizedMtomPrsnt', 0)) * -1), 2)}",
        }
        return processed_margin_data
    except Exception as e:
        logger.error(f"Error fetching margin data: {e}")
        return {}
