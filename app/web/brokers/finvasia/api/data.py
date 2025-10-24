import json
from datetime import datetime

import pandas as pd
from app.core.schemas.token_db import get_br_symbol, get_token
from app.utils.httpx_client import get_httpx_client

from app.core.config import settings
from app.utils.logging import logger


def get_api_response(endpoint, auth, method="POST", payload=None):
    """
    Common function to make API calls to Finvasia using httpx with connection pooling.
    
    NOTE: This is a placeholder implementation. The actual API endpoints,
    payload, and response handling will need to be updated based on the
    official Finvasia API documentation.
    """
    AUTH_TOKEN = auth
    api_key = settings.BROKER_API_KEY
    
    if payload is None:
        data = {
            "uid": api_key,
            "actid": api_key
        }
    else:
        data = payload
        data["uid"] = api_key

    payload_str = "jData=" + json.dumps(data) + "&jKey=" + AUTH_TOKEN

    client = get_httpx_client()

    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    url = f"https://api.finvasia.com{endpoint}"

    response = client.request(method, url, content=payload_str, headers=headers)
    data = response.text

    logger.debug(f"Raw Response: {data}")

    try:
        return json.loads(data)
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON: {e}")
        logger.debug(f"Response data: {data}")
        raise


class BrokerData:
    def __init__(self, auth_token):
        """Initialize Finvasia data handler with authentication token"""
        self.auth_token = auth_token
        self.timeframe_map = {
            '1m': '1',
            '3m': '3',
            '5m': '5',
            '10m': '10',
            '15m': '15',
            '30m': '30',
            '1h': '60',
            'D': 'D'
        }

    def get_quotes(self, symbol: str, exchange: str) -> dict:
        """
        Get real-time quotes for a given symbol.
        NOTE: Placeholder implementation.
        """
        try:
            get_br_symbol(symbol, exchange)
            token = get_token(symbol, exchange)
            payload = {"exch": exchange, "token": token}
            response = get_api_response("/v1/quotes", self.auth_token, payload=payload)

            if response.get('stat') != 'Ok':
                raise Exception(f"Error from Finvasia API: {response.get('emsg', 'Unknown error')}")

            return {
                'bid': float(response.get('bid', 0)),
                'ask': float(response.get('ask', 0)),
                'open': float(response.get('open', 0)),
                'high': float(response.get('high', 0)),
                'low': float(response.get('low', 0)),
                'ltp': float(response.get('ltp', 0)),
                'prev_close': float(response.get('prev_close', 0)),
                'volume': int(response.get('volume', 0)),
                'oi': int(response.get('oi', 0))
            }
        except Exception as e:
            raise Exception(f"Error fetching quotes: {str(e)}")

    def get_depth(self, symbol: str, exchange: str) -> dict:
        """
        Get market depth for a given symbol.
        NOTE: Placeholder implementation.
        """
        try:
            get_br_symbol(symbol, exchange)
            token = get_token(symbol, exchange)
            payload = {"exch": exchange, "token": token}
            response = get_api_response("/v1/depth", self.auth_token, payload=payload)

            if response.get('stat') != 'Ok':
                raise Exception(f"Error from Finvasia API: {response.get('emsg', 'Unknown error')}")
            
            bids = response.get('bids', [])
            asks = response.get('asks', [])

            return {
                'bids': bids,
                'asks': asks,
                'totalbuyqty': sum(bid.get('quantity', 0) for bid in bids),
                'totalsellqty': sum(ask.get('quantity', 0) for ask in asks),
                'high': float(response.get('high', 0)),
                'low': float(response.get('low', 0)),
                'ltp': float(response.get('ltp', 0)),
                'ltq': int(response.get('ltq', 0)),
                'open': float(response.get('open', 0)),
                'prev_close': float(response.get('prev_close', 0)),
                'volume': int(response.get('volume', 0)),
                'oi': int(response.get('oi', 0))
            }
        except Exception as e:
            raise Exception(f"Error fetching market depth: {str(e)}")

    def get_history(self, symbol: str, exchange: str, interval: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Get historical data for a given symbol.
        NOTE: Placeholder implementation.
        """
        try:
            if interval not in self.timeframe_map:
                supported = list(self.timeframe_map.keys())
                raise Exception(f"Unsupported interval '{interval}'. Supported intervals are: {', '.join(supported)}")

            get_br_symbol(symbol, exchange)
            token = get_token(symbol, exchange)

            start_ts = int(datetime.strptime(str(start_date), '%Y-%m-%d').timestamp())
            end_ts = int(datetime.strptime(str(end_date), '%Y-%m-%d').timestamp())

            payload = {
                "exch": exchange,
                "token": token,
                "st": str(start_ts),
                "et": str(end_ts),
                "intrv": self.timeframe_map[interval]
            }
            response = get_api_response("/v1/history", self.auth_token, payload=payload)

            df = pd.DataFrame(response)
            if df.empty:
                return pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'oi'])
            
            # Placeholder for data transformation
            df = df.rename(columns={
                't': 'timestamp',
                'o': 'open',
                'h': 'high',
                'l': 'low',
                'c': 'close',
                'v': 'volume',
            })
            df['oi'] = 0 # Add oi column if not present
            
            df = df.sort_values('timestamp')
            return df
        except Exception as e:
            logger.error(f"Error in get_history: {e}")
            raise Exception(f"Error fetching historical data: {str(e)}")