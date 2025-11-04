from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi.concurrency import run_in_threadpool
import traceback

from fastapi_app.api.v1.schemas import PlaceOrderPayload
from services.place_order_service import place_order
from fastapi_app.core.logging import get_logger
from fastapi_app.api.v1.dependencies import get_auth_broker, AuthBroker

# Initialize logger
logger = get_logger(__name__)

# Create a new router for order-related endpoints
router = APIRouter()

@router.post("/placeorder", tags=["Orders"])
async def place_new_order(payload: PlaceOrderPayload, auth: AuthBroker = Depends(get_auth_broker)):
    """
    Place a new order using API Key authentication.
    """
    try:
        # The service expects a dictionary, so we convert the Pydantic model
        order_data = payload.model_dump()

        # Run the synchronous place_order function in a separate thread
        success, response_data, status_code = await run_in_threadpool(
            place_order,
            order_data=order_data,
            auth_token=auth.token,
            broker=auth.broker,
            api_key=auth.api_key
        )

        # Return the response from the service
        return JSONResponse(content=response_data, status_code=status_code)

    except Exception as e:
        logger.error(f"Unexpected error in placeorder endpoint: {e}")
        logger.error(traceback.format_exc())

        # Raise a generic 500 internal server error
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": "An unexpected error occurred on the server."
            }
        )
