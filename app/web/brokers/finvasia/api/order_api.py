import json

from app.web.brokers.finvasia.mapping.transform_data import (
    map_product_type,
    reverse_map_product_type,
    transform_data,
    transform_modify_order_data,
)
from app.core.schemas.token_db import get_br_symbol, get_symbol, get_token
from app.utils.httpx_client import get_httpx_client

from app.core.config import settings
from app.utils.logging import logger


def get_api_response(endpoint, auth, method="GET", payload=""):
    """
    NOTE: This is a placeholder implementation. The actual API endpoints,
    payload, and response handling will need to be updated based on the
    official Finvasia API documentation.
    """
    AUTH_TOKEN = auth
    api_key = settings.BROKER_API_KEY

    data = f'{{"uid": "{api_key}", "actid": "{api_key}"}}'

    if endpoint == "/v1/holdings":
        data = f'{{"uid": "{api_key}", "actid": "{api_key}", "prd": "C"}}'

    payload_str = "jData=" + data + "&jKey=" + AUTH_TOKEN

    client = get_httpx_client()

    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    url = f"https://api.finvasia.com{endpoint}"

    response = client.request(method, url, content=payload_str, headers=headers)
    data = response.text

    try:
        return json.loads(data)
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON: {e}")
        logger.info(f"Response data: {data}")
        raise


def get_order_book(auth):
    response = get_api_response("/v1/orderBook", auth, method="POST")
    if isinstance(response, dict) and response.get("stat") == "Not_Ok":
        return []
    return response


def get_trade_book(auth):
    return get_api_response("/v1/tradeBook", auth, method="POST")


def get_positions(auth):
    return get_api_response("/v1/positionBook", auth, method="POST")


def get_holdings(auth):
    return get_api_response("/v1/holdings", auth, method="POST")


def get_open_position(tradingsymbol, exchange, producttype, auth):
    tradingsymbol = get_br_symbol(tradingsymbol, exchange)
    positions_data = get_positions(auth)
    logger.info(f"{positions_data}")
    net_qty = "0"
    if positions_data is None or (
        isinstance(positions_data, dict) and (positions_data.get("stat") == "Not_Ok")
    ):
        logger.info("No data available.")
        net_qty = "0"
    if positions_data and isinstance(positions_data, list):
        for position in positions_data:
            if (
                position.get("tsym") == tradingsymbol
                and position.get("exch") == exchange
                and position.get("prd") == producttype
            ):
                net_qty = position.get("netqty", "0")
                break
    return net_qty


def place_order_api(data, auth):
    AUTH_TOKEN = auth
    BROKER_API_KEY = settings.BROKER_API_KEY
    data["apikey"] = BROKER_API_KEY
    token = get_token(data["symbol"], data["exchange"])
    newdata = transform_data(data, token)
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    payload_str = "jData=" + json.dumps(newdata) + "&jKey=" + AUTH_TOKEN
    logger.info(f"{payload_str}")
    client = get_httpx_client()
    url = "https://api.finvasia.com/v1/placeOrder"
    response = client.post(url, content=payload_str, headers=headers)
    response_data = json.loads(response.text)
    response.status = response.status_code
    if response_data.get("stat") == "Ok":
        orderid = response_data.get("norenordno")
    else:
        orderid = None
    return response, response_data, orderid


def place_smartorder_api(data, auth):
    AUTH_TOKEN = auth
    res = None
    symbol = data.get("symbol")
    exchange = data.get("exchange")
    product = data.get("product")
    position_size = int(data.get("position_size", "0"))
    current_position = int(
        get_open_position(symbol, exchange, map_product_type(product), AUTH_TOKEN)
    )
    logger.info(f"position_size : {position_size}")
    logger.info(f"Open Position : {current_position}")
    action = None
    quantity = 0
    if (
        position_size == 0
        and current_position == 0
        and int(data.get("quantity", 0)) != 0
    ):
        action = data["action"]
        quantity = data["quantity"]
        res, response, orderid = place_order_api(data, AUTH_TOKEN)
        return res, response, orderid
    elif position_size == current_position:
        if int(data.get("quantity", 0)) == 0:
            response = {
                "status": "success",
                "message": "No OpenPosition Found. Not placing Exit order.",
            }
        else:
            response = {
                "status": "success",
                "message": "No action needed. Position size matches current position",
            }
        orderid = None
        return res, response, orderid
    if position_size == 0 and current_position > 0:
        action = "SELL"
        quantity = abs(current_position)
    elif position_size == 0 and current_position < 0:
        action = "BUY"
        quantity = abs(current_position)
    elif current_position == 0:
        action = "BUY" if position_size > 0 else "SELL"
        quantity = abs(position_size)
    else:
        if position_size > current_position:
            action = "BUY"
            quantity = position_size - current_position
        elif position_size < current_position:
            action = "SELL"
            quantity = current_position - position_size
    if action:
        order_data = data.copy()
        order_data["action"] = action
        order_data["quantity"] = str(quantity)
        res, response, orderid = place_order_api(order_data, auth)
        logger.info(f"{response}")
        logger.info(f"{orderid}")
        return res, response, orderid


def close_all_positions(current_api_key, auth):
    AUTH_TOKEN = auth
    positions_response = get_positions(AUTH_TOKEN)
    if positions_response is None or (
        positions_response and positions_response[0].get("stat") == "Not_Ok"
    ):
        return {"message": "No Open Positions Found"}, 200
    if positions_response:
        for position in positions_response:
            if int(position.get("netqty", 0)) == 0:
                continue
            action = "SELL" if int(position.get("netqty")) > 0 else "BUY"
            quantity = abs(int(position.get("netqty")))
            symbol = get_symbol(position["token"], position["exch"])
            logger.info(f"The Symbol is {symbol}")
            place_order_payload = {
                "apikey": current_api_key,
                "strategy": "Squareoff",
                "symbol": symbol,
                "action": action,
                "exchange": position["exch"],
                "pricetype": "MARKET",
                "product": reverse_map_product_type(position["prd"]),
                "quantity": str(quantity),
            }
            logger.info(f"{place_order_payload}")
            res, response, orderid = place_order_api(place_order_payload, auth)
    return {"status": "success", "message": "All Open Positions SquaredOff"}, 200


def cancel_order(orderid, auth):
    AUTH_TOKEN = auth
    api_key = settings.BROKER_API_KEY
    data = {"uid": api_key, "norenordno": orderid}
    payload_str = "jData=" + json.dumps(data) + "&jKey=" + AUTH_TOKEN
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    client = get_httpx_client()
    url = "https://api.finvasia.com/v1/cancelOrder"
    response = client.post(url, content=payload_str, headers=headers)
    data = json.loads(response.text)
    logger.info(f"{data}")
    response.status = response.status_code
    if data.get("stat") == "Ok":
        return {"status": "success", "orderid": orderid}, 200
    else:
        return {
            "status": "error",
            "message": data.get("message", "Failed to cancel order"),
        }, response.status


def modify_order(data, auth):
    AUTH_TOKEN = auth
    api_key = settings.BROKER_API_KEY
    token = get_token(data["symbol"], data["exchange"])
    data["symbol"] = get_br_symbol(data["symbol"], data["exchange"])
    data["apikey"] = api_key
    transformed_data = transform_modify_order_data(data, token)
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    payload_str = "jData=" + json.dumps(transformed_data) + "&jKey=" + AUTH_TOKEN
    client = get_httpx_client()
    url = "https://api.finvasia.com/v1/modifyOrder"
    response = client.post(url, content=payload_str, headers=headers)
    response_data = json.loads(response.text)
    response.status = response.status_code
    if response_data.get("stat") == "Ok":
        return {"status": "success", "orderid": data["orderid"]}, 200
    else:
        return {
            "status": "error",
            "message": response_data.get("emsg", "Failed to modify order"),
        }, response.status


def cancel_all_orders_api(data, auth):
    AUTH_TOKEN = auth
    order_book_response = get_order_book(AUTH_TOKEN)
    if order_book_response is None:
        return [], []
    orders_to_cancel = [
        order
        for order in order_book_response
        if order.get("status") in ["OPEN", "TRIGGER PENDING"]
    ]
    canceled_orders = []
    failed_cancellations = []
    for order in orders_to_cancel:
        orderid = order.get("norenordno")
        cancel_response, status_code = cancel_order(orderid, auth)
        if status_code == 200:
            canceled_orders.append(orderid)
        else:
            failed_cancellations.append(orderid)
    return canceled_orders, failed_cancellations
