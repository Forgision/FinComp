from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi.concurrency import run_in_threadpool
import traceback

from services.funds_service import get_funds
from services.orderbook_service import get_orderbook
from fastapi_app.core.logging import get_logger
from fastapi_app.api.v1.dependencies import get_auth_broker, AuthBroker

# Initialize logger
logger = get_logger(__name__)

# Create a new router for account-related endpoints
router = APIRouter()

@router.get("/funds", tags=["Account"])
async def get_account_funds(auth: AuthBroker = Depends(get_auth_broker)):
    """
    Get account funds and margin details using API Key authentication.
    """
    try:
        # Use the auth_token and broker provided by the dependency
        success, response_data, status_code = await run_in_threadpool(
            get_funds, auth_token=auth.token, broker=auth.broker
        )
        return JSONResponse(content=response_data, status_code=status_code)
    except Exception as e:
        logger.error(f"Unexpected error in funds endpoint: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": "An unexpected error occurred on the server."
            }
        )

@router.get("/orderbook", tags=["Account"])
async def get_account_orderbook(auth: AuthBroker = Depends(get_auth_broker)):
    """
    Get order book details using API Key authentication.
    """
    try:
        # Use the auth_token and broker provided by the dependency
        success, response_data, status_code = await run_in_threadpool(
            get_orderbook, auth_token=auth.token, broker=auth.broker
        )
        return JSONResponse(content=response_data, status_code=status_code)
    except Exception as e:
        logger.error(f"Unexpected error in orderbook endpoint: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": "An unexpected error occurred on the server."
            }
        )
