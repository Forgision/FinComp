from typing import Any, Dict
import json

from app.core.brokers.base import BaseBrokerAccount
from app.core.config import settings
from app.utils.httpx_client import get_httpx_client
from app.utils.logging import logger
from app.core.brokers.fyers.mapping.transform_data import (
    transform_data,
    transform_modify_order_data,
)


class FyersAccount(BaseBrokerAccount):
    """
    Fyers Broker Account Implementation.
    """

    async def get_order_book(self, auth_token: str) -> Dict[str, Any]:
        return await self._get_api_response("/api/v3/orders", auth_token)

    async def get_trade_book(self, auth_token: str) -> Dict[str, Any]:
        return await self._get_api_response("/api/v3/tradebook", auth_token)

    async def get_positions(self, auth_token: str) -> Dict[str, Any]:
        return await self._get_api_response("/api/v3/positions", auth_token)

    async def get_holdings(self, auth_token: str) -> Dict[str, Any]:
        return await self._get_api_response("/api/v3/holdings", auth_token)

    async def place_order(
        self, order_data: Dict[str, Any], auth_token: str
    ) -> Dict[str, Any]:
        """
        Place a new order using the Fyers API.
        """
        try:
            client = get_httpx_client()
            broker_api_key = settings.BROKER_API_KEY
            order_data["apikey"] = broker_api_key

            url = "https://api-t1.fyers.in/api/v3/orders/sync"
            headers = {
                "Authorization": f"{broker_api_key}:{auth_token}",
                "Content-Type": "application/json",
            }

            # Transform order data
            fyers_data = await transform_data(order_data)
            logger.debug(f"Placing Fyers Order: {fyers_data}")

            response = await client.post(url, headers=headers, json=fyers_data)
            response_data = response.json()

            # Compatibility with existing service expectations (status attr on response object isn't returned here, just dict)
            # The BaseBrokerAccount returns Dict[str, Any], so we just return response_data

            return response_data

        except Exception as e:
            logger.exception("Error during order placement")
            return {"s": "error", "message": f"General error: {e}"}

    async def cancel_order(self, order_id: str, auth_token: str) -> Dict[str, Any]:
        try:
            client = get_httpx_client()
            broker_api_key = settings.BROKER_API_KEY

            url = "https://api-t1.fyers.in/api/v3/orders/sync"
            headers = {
                "Authorization": f"{broker_api_key}:{auth_token}",
                "Content-Type": "application/json",
            }

            payload = {"id": order_id}
            response = await client.request(
                "DELETE", url, headers=headers, json=payload
            )
            return response.json()

        except Exception as e:
            logger.exception("Error during order cancellation")
            return {"s": "error", "message": f"General error: {e}"}

    async def modify_order(
        self, order_id: str, new_data: Dict[str, Any], auth_token: str
    ) -> Dict[str, Any]:
        try:
            client = get_httpx_client()
            broker_api_key = settings.BROKER_API_KEY

            url = "https://api-t1.fyers.in/api/v3/orders/sync"
            headers = {
                "Authorization": f"{broker_api_key}:{auth_token}",
                "Content-Type": "application/json",
            }

            # Ensure ID is in data or passed correctly to transform
            new_data["orderid"] = (
                order_id  # Assuming transform_modify_order_data uses it or we need to merge
            )
            # Actually transform_modify_order_data usually expects 'orderid' key

            payload = transform_modify_order_data(new_data)
            response = await client.patch(url, headers=headers, json=payload)
            return response.json()

        except Exception as e:
            logger.exception("Error during order modification")
            return {"s": "error", "message": f"General error: {e}"}

    async def _get_api_response(
        self, endpoint: str, auth_token: str, method: str = "GET", payload: Any = ""
    ) -> Dict[str, Any]:
        try:
            client = get_httpx_client()
            broker_api_key = settings.BROKER_API_KEY

            url = f"https://api-t1.fyers.in{endpoint}"
            headers = {
                "Authorization": f"{broker_api_key}:{auth_token}",
                "Content-Type": "application/json",
            }

            logger.debug(f"Making {method} request to Fyers API: {url}")

            if method == "GET":
                response = await client.get(url, headers=headers)
            elif method == "POST":
                response = await client.post(
                    url,
                    headers=headers,
                    json=payload if isinstance(payload, dict) else json.loads(payload),
                )
            else:
                response = await client.request(
                    method,
                    url,
                    headers=headers,
                    json=payload if isinstance(payload, dict) else json.loads(payload),
                )

            response.raise_for_status()
            return response.json()

        except Exception as e:
            logger.error(f"HTTP error during API request: {e}")
            return {"s": "error", "message": str(e)}

    async def get_funds(self, auth_token: str) -> Dict[str, Any]:
        """
        Fetch and process margin/funds data from Fyers' API.
        """
        # Default response
        default_response = {
            "availablecash": "0.00",
            "collateral": "0.00",
            "m2munrealized": "0.00",
            "m2mrealized": "0.00",
            "utiliseddebits": "0.00",
        }

        try:
            client = get_httpx_client()
            broker_api_key = settings.BROKER_API_KEY

            headers = {
                "Authorization": f"{broker_api_key}:{auth_token}",
                "Content-Type": "application/json",
            }

            url = "https://api-t1.fyers.in/api/v3/funds"
            response = await client.get(url, headers=headers, timeout=30.0)

            # Handle 4xx/5xx explicitly or json parse check
            if response.status_code != 200:
                logger.error(f"Error in Fyers funds API: {response.text}")
                return default_response

            funds_data = response.json()
            if funds_data.get("code") != 200:
                logger.error(f"Error in Fyers funds API: {funds_data}")
                return default_response

            # Process logic copied from api/funds.py
            processed_funds = {}
            for fund in funds_data.get("fund_limit", []):
                try:
                    key = fund["title"].lower().replace(" ", "_")
                    processed_funds[key] = {
                        "equity_amount": float(fund.get("equityAmount", 0)),
                        "commodity_amount": float(fund.get("commodityAmount", 0)),
                    }
                except (KeyError, ValueError):
                    continue

            # Calculate totals
            try:
                balance = processed_funds.get("available_balance", {})
                total_balance = float(balance.get("equity_amount", 0)) + float(
                    balance.get("commodity_amount", 0)
                )

                collateral = processed_funds.get("collaterals", {})
                total_collateral = float(collateral.get("equity_amount", 0)) + float(
                    collateral.get("commodity_amount", 0)
                )

                pnl = processed_funds.get("realized_profit_and_loss", {})
                total_real_pnl = float(pnl.get("equity_amount", 0)) + float(
                    pnl.get("commodity_amount", 0)
                )

                utilized = processed_funds.get("utilized_amount", {})
                total_utilized = float(utilized.get("equity_amount", 0)) + float(
                    utilized.get("commodity_amount", 0)
                )

                return {
                    "availablecash": "{:.2f}".format(total_balance),
                    "collateral": "{:.2f}".format(total_collateral),
                    "m2munrealized": "{:.2f}".format(total_collateral),
                    "m2mrealized": "{:.2f}".format(total_real_pnl),
                    "utiliseddebits": "{:.2f}".format(total_utilized),
                }
            except Exception as e:
                logger.error(f"Error calculation funds: {e}")
                return default_response

        except Exception:
            logger.exception("Error fetching Fyers funds")
            return default_response
