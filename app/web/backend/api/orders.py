from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

# Import FastAPI schemas for request body validation
from app.core.models.api_schemas import (
    BasketOrderSchema,
    CancelAllOrderSchema,
    CancelOrderSchema,
    ClosePositionSchema,
    ModifyOrderSchema,
    OrderStatusSchema,
    PlaceOrderSchema,
    PlaceSmartOrderSchema,
    SplitOrderSchema,
)
from app.core.models.error_models import BaseErrorResponse
from app.core.services.basket_order_service import place_basket_order
from app.core.services.cancel_all_order_service import cancel_all_orders
from app.core.services.cancel_order_service import cancel_order
from app.core.services.close_position_service import close_position
from app.core.services.modify_order_service import modify_order
from app.core.services.orderstatus_service import get_order_status

# Import service functions
from app.core.services.place_order_service import place_order
from app.core.services.place_smart_order_service import place_smart_order
from app.core.services.split_order_service import split_order
from app.utils.session import check_session_validity_fastapi

# Import authentication dependency (assuming it exists)
# from app.web.backend.dependencies import get_current_user # Placeholder for authentication

orders_router = APIRouter()


@orders_router.post("/placeorder", summary="Place an order with the broker", responses={status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": BaseErrorResponse}})
async def place_order_endpoint(
    order_data: PlaceOrderSchema,
    api_key: Optional[str] = None, # Assuming API key can be passed as a header or part of the body
    current_user: dict = Depends(check_session_validity_fastapi) # Example of dependency injection for authentication
):
    """
    Place an order with the broker.

    Args:
        order_data: The order data.
        api_key: The user's API key.
        current_user: The current authenticated user.

    Returns:
        A JSON response with the order placement result.

    Raises:
        HTTPException: If an error occurs while placing the order.
    """
    # The Flask-RestX version extracts api_key from the body and pops it.
    # FastAPI handles validation and allows direct access.
    # If api_key is expected in the body, it should be part of PlaceOrderSchema.
    # For demonstration, assuming it can be passed as an optional query/header param for now.

    # Call the service function to place the order
    success, response_data, status_code = await place_order(
        order_data=order_data.model_dump(), # Use .model_dump() to convert Pydantic model to dict
        api_key=api_key
    )

    if not success:
        raise HTTPException(status_code=status_code, detail=BaseErrorResponse(message=response_data.get("message", "An error occurred")).model_dump())

    return response_data

@orders_router.post("/placesmartorder", summary="Place a smart order", responses={status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": BaseErrorResponse}})
async def place_smart_order_endpoint(
    order_data: PlaceSmartOrderSchema,
    api_key: Optional[str] = None,
    current_user: dict = Depends(check_session_validity_fastapi)
):
    """
    Place a smart order with the broker.

    Args:
        order_data: The smart order data.
        api_key: The user's API key.
        current_user: The current authenticated user.

    Returns:
        A JSON response with the smart order placement result.

    Raises:
        HTTPException: If an error occurs while placing the smart order.
    """
    success, response_data, status_code = await place_smart_order(
        order_data=order_data.model_dump(),
        api_key=api_key
    )

    if not success:
        raise HTTPException(status_code=status_code, detail=BaseErrorResponse(message=response_data.get("message", "An error occurred")).model_dump())

    return response_data

@orders_router.post("/modifyorder", summary="Modify an existing order", responses={status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": BaseErrorResponse}})
async def modify_order_endpoint(
    order_data: ModifyOrderSchema,
    api_key: Optional[str] = None,
    current_user: dict = Depends(check_session_validity_fastapi)
):
    """
    Modify an existing order.

    Args:
        order_data: The modification order data.
        api_key: The user's API key.
        current_user: The current authenticated user.

    Returns:
        A JSON response with the order modification result.

    Raises:
        HTTPException: If an error occurs while modifying the order.
    """
    success, response_data, status_code = await modify_order(
        order_data=order_data.model_dump(),
        api_key=api_key
    )

    if not success:
        raise HTTPException(status_code=status_code, detail=BaseErrorResponse(message=response_data.get("message", "An error occurred")).model_dump())

    return response_data

@orders_router.post("/cancelorder", summary="Cancel an existing order", responses={status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": BaseErrorResponse}})
async def cancel_order_endpoint(
    order_data: CancelOrderSchema,
    api_key: Optional[str] = None,
    current_user: dict = Depends(check_session_validity_fastapi)
):
    """
    Cancel an existing order.

    Args:
        order_data: The cancellation order data, including the order ID.
        api_key: The user's API key.
        current_user: The current authenticated user.

    Returns:
        A JSON response with the order cancellation result.

    Raises:
        HTTPException: If an error occurs while canceling the order.
    """
    success, response_data, status_code = await cancel_order(
        orderid=order_data.orderid, # Assuming orderid is directly available in the schema
        api_key=api_key
    )

    if not success:
        raise HTTPException(status_code=status_code, detail=BaseErrorResponse(message=response_data.get("message", "An error occurred")).model_dump())

    return response_data

@orders_router.post("/closeposition", summary="Close all open positions", responses={status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": BaseErrorResponse}})
async def close_position_endpoint(
    position_data: ClosePositionSchema,
    api_key: Optional[str] = None,
    current_user: dict = Depends(check_session_validity_fastapi)
):
    """
    Close all open positions.

    Args:
        position_data: The data for closing positions.
        api_key: The user's API key.
        current_user: The current authenticated user.

    Returns:
        A JSON response with the result of closing positions.

    Raises:
        HTTPException: If an error occurs while closing positions.
    """
    success, response_data, status_code = await close_position(
        position_data=position_data.model_dump(),
        api_key=api_key
    )

    if not success:
        raise HTTPException(status_code=status_code, detail=BaseErrorResponse(message=response_data.get("message", "An error occurred")).model_dump())

    return response_data

@orders_router.post("/cancelallorder", summary="Cancel all open orders", responses={status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": BaseErrorResponse}})
async def cancel_all_order_endpoint(
    order_data: CancelAllOrderSchema,
    api_key: Optional[str] = None,
    current_user: dict = Depends(check_session_validity_fastapi)
):
    """
    Cancel all open orders.

    Args:
        order_data: The data for canceling all orders.
        api_key: The user's API key.
        current_user: The current authenticated user.

    Returns:
        A JSON response with the result of canceling all orders.

    Raises:
        HTTPException: If an error occurs while canceling all orders.
    """
    success, response_data, status_code = await cancel_all_orders(
        order_data=order_data.model_dump(),
        api_key=api_key
    )

    if not success:
        raise HTTPException(status_code=status_code, detail=BaseErrorResponse(message=response_data.get("message", "An error occurred")).model_dump())

    return response_data

@orders_router.post("/basketorder", summary="Place multiple orders in a basket", responses={status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": BaseErrorResponse}})
async def basket_order_endpoint(
    basket_data: BasketOrderSchema,
    api_key: Optional[str] = None,
    current_user: dict = Depends(check_session_validity_fastapi)
):
    """
    Place multiple orders in a basket.

    Args:
        basket_data: The basket order data.
        api_key: The user's API key.
        current_user: The current authenticated user.

    Returns:
        A JSON response with the basket order placement result.

    Raises:
        HTTPException: If an error occurs while placing the basket order.
    """
    success, response_data, status_code = await place_basket_order(
        basket_data=basket_data.model_dump(),
        api_key=api_key
    )

    if not success:
        raise HTTPException(status_code=status_code, detail=BaseErrorResponse(message=response_data.get("message", "An error occurred")).model_dump())

    return response_data

@orders_router.post("/splitorder", summary="Split a large order into multiple orders of specified size", responses={status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": BaseErrorResponse}})
async def split_order_endpoint(
    split_data: SplitOrderSchema,
    api_key: Optional[str] = None,
    current_user: dict = Depends(check_session_validity_fastapi)
):
    """
    Split a large order into multiple orders of specified size.

    Args:
        split_data: The split order data.
        api_key: The user's API key.
        current_user: The current authenticated user.

    Returns:
        A JSON response with the split order result.

    Raises:
        HTTPException: If an error occurs while splitting the order.
    """
    success, response_data, status_code = await split_order(
        split_data=split_data.model_dump(),
        api_key=api_key
    )

    if not success:
        raise HTTPException(status_code=status_code, detail=BaseErrorResponse(message=response_data.get("message", "An error occurred")).model_dump())

    return response_data

@orders_router.post("/orderstatus", summary="Get status of a specific order", responses={status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": BaseErrorResponse}})
async def order_status_endpoint(
    status_data: OrderStatusSchema,
    api_key: Optional[str] = None,
    current_user: dict = Depends(check_session_validity_fastapi)
):
    """
    Get the status of a specific order.

    Args:
        status_data: The order status data.
        api_key: The user's API key.
        current_user: The current authenticated user.

    Returns:
        A JSON response with the order status result.

    Raises:
        HTTPException: If an error occurs while fetching the order status.
    """
    success, response_data, status_code = await get_order_status(
        status_data=status_data.model_dump(),
        api_key=api_key
    )

    if not success:
        raise HTTPException(status_code=status_code, detail=BaseErrorResponse(message=response_data.get("message", "An error occurred")).model_dump())

    return response_data
