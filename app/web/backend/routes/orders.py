from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any

from importlib import import_module
import csv
import io
import os

from app.db.auth_db import get_auth_token, get_api_key_for_tradingview
from app.db.settings_db import get_analyze_mode
from app.db.session import get_db
from app.utils.session import check_session_validity_fastapi
from app.web.services.place_smart_order_service import place_smart_order
from app.web.services.close_position_service import close_position
from app.web.services.orderbook_service import get_orderbook
from app.web.services.tradebook_service import get_tradebook
from app.web.services.positionbook_service import get_positionbook
from app.web.services.holdings_service import get_holdings
from app.web.services.cancel_all_order_service import cancel_all_orders
from app.utils.web import limiter
from app.utils.logging import logger
from app.core.config import settings
from app.web.frontend import templates

# Use existing rate limits from .env
API_RATE_LIMIT = settings.API_RATE_LIMIT

orders_router = APIRouter(
    prefix="/orders",
    tags=["Orders"],
    dependencies=[Depends(check_session_validity_fastapi), Depends(limiter.limit(API_RATE_LIMIT))]
)


def dynamic_import(broker: str, module_name: str, function_names: list[str]) -> Optional[Dict[str, Any]]:
    module_functions = {}
    try:
        # Import the module based on the broker name
        module = import_module(f'app.web.broker.{broker}.{module_name}')
        for name in function_names:
            module_functions[name] = getattr(module, name)
        return module_functions
    except (ImportError, AttributeError) as e:
        logger.error(f"Error importing functions {function_names} from {module_name} for broker {broker}: {e}")
        return None

def generate_orderbook_csv(order_data: list[dict]) -> str:
    """Generate CSV file from orderbook data"""
    output = io.StringIO()
    writer = csv.writer(output)
    headers = ['Trading Symbol', 'Exchange', 'Transaction Type', 'Quantity', 'Price', 
               'Trigger Price', 'Order Type', 'Product Type', 'Order ID', 'Status', 'Time']
    writer.writerow(headers)
    for order in order_data:
        row = [
            order.get('symbol', ''), order.get('exchange', ''), order.get('action', ''),
            order.get('quantity', ''), order.get('price', ''), order.get('trigger_price', ''),
            order.get('pricetype', ''), order.get('product', ''), order.get('orderid', ''),
            order.get('order_status', ''), order.get('timestamp', '')
        ]
        writer.writerow(row)
    return output.getvalue()

def generate_tradebook_csv(trade_data: list[dict]) -> str:
    """Generate CSV file from tradebook data"""
    output = io.StringIO()
    writer = csv.writer(output)
    headers = ['Trading Symbol', 'Exchange', 'Product Type', 'Transaction Type', 'Fill Size', 
               'Fill Price', 'Trade Value', 'Order ID', 'Fill Time']
    writer.writerow(headers)
    for trade in trade_data:
        row = [
            trade.get('symbol', ''), trade.get('exchange', ''), trade.get('product', ''),
            trade.get('action', ''), trade.get('quantity', ''), trade.get('average_price', ''),
            trade.get('trade_value', ''), trade.get('orderid', ''), trade.get('timestamp', '')
        ]
        writer.writerow(row)
    return output.getvalue()

def generate_positions_csv(positions_data: list[dict]) -> str:
    """Generate CSV file from positions data"""
    output = io.StringIO()
    writer = csv.writer(output)
    headers = ['Symbol', 'Exchange', 'Product Type', 'Net Qty', 'Avg Price', 'LTP', 'P&L']
    writer.writerow(headers)
    for position in positions_data:
        row = [
            position.get('symbol', ''), position.get('exchange', ''), position.get('product', ''),
            position.get('quantity', ''), position.get('average_price', ''),
            position.get('ltp', ''), position.get('pnl', '')
        ]
        writer.writerow(row)
    return output.getvalue()

@orders_router.get("/orderbook")
async def orderbook(request: Request, db: Session = Depends(get_db)):
    login_username = request.session.get('user')
    auth_token = get_auth_token(login_username)

    if auth_token is None:
        logger.warning(f"No auth token found for user {login_username}")
        return RedirectResponse(url=request.url_for("auth_router.logout"), status_code=status.HTTP_302_FOUND)

    broker = request.session.get('broker')
    if not broker:
        logger.error("Broker not set in session")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Broker not set in session")

    if get_analyze_mode():
        api_key = get_api_key_for_tradingview(login_username)
        if api_key:
            success, response, status_code_service = await get_orderbook(api_key=api_key)
        else:
            logger.error("No API key found for analyze mode")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="API key required for analyze mode")
    else:
        success, response, status_code_service = await get_orderbook(auth_token=auth_token, broker=broker)

    if not success:
        logger.error(f"Failed to get orderbook data: {response.get('message', 'Unknown error')}")
        if status_code_service == 404:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to import broker module")
        return RedirectResponse(url=request.url_for("auth_router.logout"), status_code=status.HTTP_302_FOUND)

    data = response.get('data', {})
    order_data = data.get('orders', [])
    order_stats = data.get('statistics', {})

    return templates.TemplateResponse("orderbook.html", {"request": request, "order_data": order_data, "order_stats": order_stats})

@orders_router.get("/tradebook")
async def tradebook(request: Request, db: Session = Depends(get_db)):
    login_username = request.session.get('user')
    auth_token = get_auth_token(login_username)

    if auth_token is None:
        logger.warning(f"No auth token found for user {login_username}")
        return RedirectResponse(url=request.url_for("auth_router.logout"), status_code=status.HTTP_302_FOUND)

    broker = request.session.get('broker')
    if not broker:
        logger.error("Broker not set in session")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Broker not set in session")

    if get_analyze_mode():
        api_key = get_api_key_for_tradingview(login_username)
        if api_key:
            success, response, status_code_service = await get_tradebook(api_key=api_key)
        else:
            logger.error("No API key found for analyze mode")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="API key required for analyze mode")
    else:
        success, response, status_code_service = await get_tradebook(auth_token=auth_token, broker=broker)

    if not success:
        logger.error(f"Failed to get tradebook data: {response.get('message', 'Unknown error')}")
        if status_code_service == 404:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to import broker module")
        return RedirectResponse(url=request.url_for("auth_router.logout"), status_code=status.HTTP_302_FOUND)

    tradebook_data = response.get('data', [])

    return templates.TemplateResponse("tradebook.html", {"request": request, "tradebook_data": tradebook_data})

@orders_router.get("/positions")
async def positions(request: Request, db: Session = Depends(get_db)):
    login_username = request.session.get('user')
    auth_token = get_auth_token(login_username)

    if auth_token is None:
        logger.warning(f"No auth token found for user {login_username}")
        return RedirectResponse(url=request.url_for("auth_router.logout"), status_code=status.HTTP_302_FOUND)

    broker = request.session.get('broker')
    if not broker:
        logger.error("Broker not set in session")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Broker not set in session")

    if get_analyze_mode():
        api_key = get_api_key_for_tradingview(login_username)
        if api_key:
            success, response, status_code_service = await get_positionbook(api_key=api_key)
        else:
            logger.error("No API key found for analyze mode")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="API key required for analyze mode")
    else:
        success, response, status_code_service = await get_positionbook(auth_token=auth_token, broker=broker)

    if not success:
        logger.error(f"Failed to get positions data: {response.get('message', 'Unknown error')}")
        if status_code_service == 404:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to import broker module")
        return RedirectResponse(url=request.url_for("auth_router.logout"), status_code=status.HTTP_302_FOUND)

    positions_data = response.get('data', [])

    return templates.TemplateResponse("positions.html", {"request": request, "positions_data": positions_data})

@orders_router.get("/holdings", name="orders.holdings")
async def holdings(request: Request, db: Session = Depends(get_db)):
    login_username = request.session.get('user')
    auth_token = get_auth_token(login_username)

    if auth_token is None:
        logger.warning(f"No auth token found for user {login_username}")
        return RedirectResponse(url=request.url_for("auth_router.logout"), status_code=status.HTTP_302_FOUND)

    broker = request.session.get('broker')
    if not broker:
        logger.error("Broker not set in session")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Broker not set in session")

    if get_analyze_mode():
        api_key = get_api_key_for_tradingview(login_username)
        if api_key:
            success, response, status_code_service = await get_holdings(api_key=api_key)
        else:
            logger.error("No API key found for analyze mode")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="API key required for analyze mode")
    else:
        success, response, status_code_service = await get_holdings(auth_token=auth_token, broker=broker)

    if not success:
        logger.error(f"Failed to get holdings data: {response.get('message', 'Unknown error')}")
        if status_code_service == 404:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to import broker module")
        return RedirectResponse(url=request.url_for("auth_router.logout"), status_code=status.HTTP_302_FOUND)

    data = response.get('data', {})
    holdings_data = data.get('holdings', [])
    portfolio_stats = data.get('statistics', {})

    return templates.TemplateResponse("holdings.html", {"request": request, "holdings_data": holdings_data, "portfolio_stats": portfolio_stats})

@orders_router.get("/orderbook/export")
async def export_orderbook(request: Request, db: Session = Depends(get_db)):
    try:
        broker = request.session.get('broker')
        if not broker:
            logger.error("Broker not set in session")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Broker not set in session")

        api_funcs = dynamic_import(broker, 'api.order_api', ['get_order_book'])
        mapping_funcs = dynamic_import(broker, 'mapping.order_data', ['map_order_data', 'transform_order_data'])

        if not api_funcs or not mapping_funcs:
            logger.error(f"Error loading broker-specific modules for {broker}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error loading broker-specific modules")

        login_username = request.session.get('user')
        auth_token = get_auth_token(login_username)

        if auth_token is None:
            logger.warning(f"No auth token found for user {login_username}")
            return RedirectResponse(url=request.url_for("auth_router.logout"), status_code=status.HTTP_302_FOUND)

        order_data = await api_funcs['get_order_book'](auth_token)
        if 'status' in order_data and order_data['status'] == 'error':
            logger.error("Error in order data response")
            return RedirectResponse(url=request.url_for("auth_router.logout"), status_code=status.HTTP_302_FOUND)

        order_data = mapping_funcs['map_order_data'](order_data=order_data)
        order_data = mapping_funcs['transform_order_data'](order_data)

        csv_data = generate_orderbook_csv(order_data)
        return StreamingResponse(
            io.BytesIO(csv_data.encode('utf-8')),
            media_type='text/csv',
            headers={'Content-Disposition': 'attachment; filename=orderbook.csv'}
        )
    except Exception as e:
        logger.error(f"Error exporting orderbook: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error exporting orderbook: {str(e)}")

@orders_router.get("/tradebook/export")
async def export_tradebook(request: Request, db: Session = Depends(get_db)):
    try:
        broker = request.session.get('broker')
        if not broker:
            logger.error("Broker not set in session")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Broker not set in session")

        api_funcs = dynamic_import(broker, 'api.order_api', ['get_trade_book'])
        mapping_funcs = dynamic_import(broker, 'mapping.order_data', ['map_trade_data', 'transform_tradebook_data'])

        if not api_funcs or not mapping_funcs:
            logger.error(f"Error loading broker-specific modules for {broker}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error loading broker-specific modules")

        login_username = request.session.get('user')
        auth_token = get_auth_token(login_username)

        if auth_token is None:
            logger.warning(f"No auth token found for user {login_username}")
            return RedirectResponse(url=request.url_for("auth_router.logout"), status_code=status.HTTP_302_FOUND)

        tradebook_data = await api_funcs['get_trade_book'](auth_token)
        if 'status' in tradebook_data and tradebook_data['status'] == 'error':
            logger.error("Error in tradebook data response")
            return RedirectResponse(url=request.url_for("auth_router.logout"), status_code=status.HTTP_302_FOUND)

        tradebook_data = mapping_funcs['map_trade_data'](tradebook_data)
        tradebook_data = mapping_funcs['transform_tradebook_data'](tradebook_data)

        csv_data = generate_tradebook_csv(tradebook_data)
        return StreamingResponse(
            io.BytesIO(csv_data.encode('utf-8')),
            media_type='text/csv',
            headers={'Content-Disposition': 'attachment; filename=tradebook.csv'}
        )
    except Exception as e:
        logger.error(f"Error exporting tradebook: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error exporting tradebook: {str(e)}")

@orders_router.get("/positions/export")
async def export_positions(request: Request, db: Session = Depends(get_db)):
    try:
        broker = request.session.get('broker')
        if not broker:
            logger.error("Broker not set in session")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Broker not set in session")

        api_funcs = dynamic_import(broker, 'api.order_api', ['get_positions'])
        mapping_funcs = dynamic_import(broker, 'mapping.order_data', [
            'map_position_data', 'transform_positions_data'
        ])

        if not api_funcs or not mapping_funcs:
            logger.error(f"Error loading broker-specific modules for {broker}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error loading broker-specific modules")

        login_username = request.session.get('user')
        auth_token = get_auth_token(login_username)

        if auth_token is None:
            logger.warning(f"No auth token found for user {login_username}")
            return RedirectResponse(url=request.url_for("auth_router.logout"), status_code=status.HTTP_302_FOUND)

        positions_data = await api_funcs['get_positions'](auth_token)
        if 'status' in positions_data and positions_data['status'] == 'error':
            logger.error("Error in positions data response")
            return RedirectResponse(url=request.url_for("auth_router.logout"), status_code=status.HTTP_302_FOUND)

        positions_data = mapping_funcs['map_position_data'](positions_data)
        positions_data = mapping_funcs['transform_positions_data'](positions_data)

        csv_data = generate_positions_csv(positions_data)
        return StreamingResponse(
            io.BytesIO(csv_data.encode('utf-8')),
            media_type='text/csv',
            headers={'Content-Disposition': 'attachment; filename=positions.csv'}
        )
    except Exception as e:
        logger.error(f"Error exporting positions: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error exporting positions: {str(e)}")

@orders_router.post("/close_position")
async def close_position_route(request: Request, db: Session = Depends(get_db)):
    """Close a specific position - uses broker API in live mode, placesmartorder service in analyze mode"""
    try:
        data = await request.json()
        symbol = data.get('symbol')
        exchange = data.get('exchange')
        product = data.get('product')

        if not all([symbol, exchange, product]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Missing required parameters (symbol, exchange, product)'
            )

        login_username = request.session.get('user')
        auth_token = get_auth_token(login_username)
        broker_name = request.session.get('broker')

        if get_analyze_mode():
            api_key = get_api_key_for_tradingview(login_username)

            if not api_key:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail='API key not found for analyze mode'
                )

            order_data = {
                "strategy": "UI Exit Position",
                "exchange": exchange,
                "symbol": symbol,
                "action": "BUY",
                "product_type": product,
                "pricetype": "MARKET",
                "quantity": "0",
                "price": "0",
                "trigger_price": "0",
                "disclosed_quantity": "0",
                "position_size": "0"
            }

            success, response_data, status_code_service = await place_smart_order(
                order_data=order_data,
                api_key=api_key
            )
            return JSONResponse(content=response_data, status_code=status_code_service)

        if not auth_token or not broker_name:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Authentication error'
            )

        api_funcs = dynamic_import(broker_name, 'api.order_api', ['place_smartorder_api', 'get_open_position'])

        if not api_funcs:
            logger.error(f"Error loading broker-specific modules for {broker_name}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Error loading broker modules'
            )

        place_smartorder_api = api_funcs['place_smartorder_api']

        order_data = {
            "strategy": "UI Exit Position",
            "exchange": exchange,
            "symbol": symbol,
            "action": "BUY",
            "product": product,
            "pricetype": "MARKET",
            "quantity": "0",
            "price": "0",
            "trigger_price": "0",
            "disclosed_quantity": "0",
            "position_size": "0"
        }

        res, response, orderid = await place_smartorder_api(order_data, auth_token)
        
        if orderid:
            response_data = {
                'status': 'success',
                'message': response.get('message') if response and 'message' in response else 'Position close order placed successfully.',
                'orderid': orderid
            }
            status_code_response = status.HTTP_200_OK
        else:
            response_data = {
                'status': 'error',
                'message': response.get('message') if response and 'message' in response else 'Failed to close position (broker did not return order ID).'
            }
            if res and hasattr(res, 'status') and isinstance(res.status, int) and res.status >= 400:
                status_code_response = res.status
            else:
                status_code_response = status.HTTP_400_BAD_REQUEST
        
        return JSONResponse(content=response_data, status_code=status_code_response)
        
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Error in close_position endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'An error occurred: {str(e)}'
        )

@orders_router.post("/close_all_positions")
async def close_all_positions_route(request: Request, db: Session = Depends(get_db)):
    """Close all open positions using the broker API"""
    try:
        login_username = request.session.get('user')
        auth_token = get_auth_token(login_username)
        broker_name = request.session.get('broker')

        if not auth_token or not broker_name:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Authentication error'
            )

        api_key = None
        if get_analyze_mode():
            api_key = get_api_key_for_tradingview(login_username)

        success, response_data, status_code_service = await close_position(
            position_data={},
            api_key=api_key,
            auth_token=auth_token,
            broker=broker_name
        )

        if success and status_code_service == 200:
            return JSONResponse(content={
                'status': 'success',
                'message': response_data.get('message', 'All Open Positions Squared Off')
            }, status_code=status.HTTP_200_OK)
        else:
            return JSONResponse(content=response_data, status_code=status_code_service)
        
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Error in close_all_positions endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'An error occurred: {str(e)}'
        )

@orders_router.post("/cancel_all_orders")
async def cancel_all_orders_ui(request: Request, db: Session = Depends(get_db)):
    """Cancel all open orders using the broker API from UI"""
    try:
        login_username = request.session.get('user')
        auth_token = get_auth_token(login_username)
        broker_name = request.session.get('broker')

        if not auth_token or not broker_name:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Authentication error'
            )

        api_key = None
        if get_analyze_mode():
            api_key = get_api_key_for_tradingview(login_username)

        success, response_data, status_code_service = await cancel_all_orders(
            order_data={},
            api_key=api_key,
            auth_token=auth_token,
            broker=broker_name
        )
        
        if success and status_code_service == 200:
            canceled_count = len(response_data.get('canceled_orders', []))
            failed_count = len(response_data.get('failed_cancellations', []))
            
            if canceled_count > 0 or failed_count == 0:
                message = f'Successfully canceled {canceled_count} orders'
                if failed_count > 0:
                    message += f' (Failed to cancel {failed_count} orders)'
                return JSONResponse(content={
                    'status': 'success',
                    'message': message,
                    'canceled_orders': response_data.get('canceled_orders', []),
                    'failed_cancellations': response_data.get('failed_cancellations', [])
                }, status_code=status.HTTP_200_OK)
            else:
                return JSONResponse(content={
                    'status': 'info',
                    'message': 'No open orders to cancel'
                }, status_code=status.HTTP_200_OK)
        else:
            return JSONResponse(content=response_data, status_code=status_code_service)
        
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Error in cancel_all_orders_ui endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'An error occurred: {str(e)}'
        )