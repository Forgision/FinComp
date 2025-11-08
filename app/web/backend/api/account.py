import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.schemas import get_db
from fastapi import APIRouter, Depends, HTTPException, status
from app.core.models.error_models import BaseErrorResponse
from app.core.models.api_schemas import (
    APIKeySchema,
    FundsResponse,
    HoldingsResponse,
    OpenPositionRequest,
    OpenPositionResponse,
    OrderbookResponse,
    PositionbookResponse,
    TradebookResponse,
)
from app.core.services.funds_service import get_funds
from app.core.services.holdings_service import get_holdings
from app.core.services.openposition_service import (
    emit_analyzer_error,
    get_open_position,
)
from app.core.services.orderbook_service import get_orderbook
from app.core.services.positionbook_service import get_positionbook
from app.core.services.tradebook_service import get_tradebook
from app.core.schemas.apilog_db import async_log_order
from app.core.schemas.settings_db import get_analyze_mode
from app.utils.logging import logger

account_router = APIRouter()


# Placeholder for get_current_user dependency - assume it exists and handles authentication
async def get_current_user():
    # In a real application, this would validate a token and return a user object.
    # For this migration, we assume it's available and handles authentication.
    pass


@account_router.post(
    "/funds",
    response_model=FundsResponse,
    responses={status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": BaseErrorResponse}},
)
async def funds_endpoint(
    api_key_data: APIKeySchema,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Retrieves the user's account funds and margin details.

    Args:
        api_key_data: The API key data.
        current_user: The current authenticated user.

    Returns:
        The funds and margin details.

    Raises:
        HTTPException: If an error occurs while fetching the funds.
    """
    try:
        success, response_data, status_code = await get_funds(
            db, api_key=api_key_data.api_key
        )
        if not success:
            raise HTTPException(
                status_code=status_code,
                detail=BaseErrorResponse(
                    message=response_data.get("message", "An error occurred"),
                    code=str(status_code),
                    details=response_data,
                ).model_dump(),
            )
        return FundsResponse(**response_data)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.exception(f"Unexpected error in funds endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=BaseErrorResponse(
                message="An unexpected error occurred",
                code=str(status.HTTP_500_INTERNAL_SERVER_ERROR),
                details={"error": str(e)},
            ).model_dump(),
        )


@account_router.post(
    "/orderbook",
    response_model=OrderbookResponse,
    responses={status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": BaseErrorResponse}},
)
async def orderbook_endpoint(
    api_key_data: APIKeySchema,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Retrieves the user's order book details.

    Args:
        api_key_data: The API key data.
        current_user: The current authenticated user.

    Returns:
        The order book details.

    Raises:
        HTTPException: If an error occurs while fetching the order book.
    """
    try:
        success, response_data, status_code = await get_orderbook(
            db, api_key=api_key_data.api_key
        )
        if not success:
            raise HTTPException(
                status_code=status_code,
                detail=BaseErrorResponse(
                    message=response_data.get("message", "An error occurred"),
                    code=str(status_code),
                    details=response_data,
                ).model_dump(),
            )
        return OrderbookResponse(**response_data)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.exception(f"Unexpected error in orderbook endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=BaseErrorResponse(
                message="An unexpected error occurred",
                code=str(status.HTTP_500_INTERNAL_SERVER_ERROR),
                details={"error": str(e)},
            ).model_dump(),
        )


@account_router.post(
    "/tradebook",
    response_model=TradebookResponse,
    responses={status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": BaseErrorResponse}},
)
async def tradebook_endpoint(
    api_key_data: APIKeySchema,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Retrieves the user's trade book details.

    Args:
        api_key_data: The API key data.
        current_user: The current authenticated user.

    Returns:
        The trade book details.

    Raises:
        HTTPException: If an error occurs while fetching the trade book.
    """
    try:
        success, response_data, status_code = await get_tradebook(
            db, api_key=api_key_data.api_key
        )
        if not success:
            raise HTTPException(
                status_code=status_code,
                detail=BaseErrorResponse(
                    message=response_data.get("message", "An error occurred"),
                    code=str(status_code),
                    details=response_data,
                ).model_dump(),
            )
        return TradebookResponse(**response_data)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.exception(f"Unexpected error in tradebook endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=BaseErrorResponse(
                message="An unexpected error occurred",
                code=str(status.HTTP_500_INTERNAL_SERVER_ERROR),
                details={"error": str(e)},
            ).model_dump(),
        )


@account_router.post(
    "/positionbook",
    response_model=PositionbookResponse,
    responses={status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": BaseErrorResponse}},
)
async def positionbook_endpoint(
    api_key_data: APIKeySchema,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Retrieves the user's position book details.

    Args:
        api_key_data: The API key data.
        current_user: The current authenticated user.

    Returns:
        The position book details.

    Raises:
        HTTPException: If an error occurs while fetching the position book.
    """
    try:
        success, response_data, status_code = await get_positionbook(
            db, api_key=api_key_data.api_key
        )
        if not success:
            raise HTTPException(
                status_code=status_code,
                detail=BaseErrorResponse(
                    message=response_data.get("message", "An error occurred"),
                    code=str(status_code),
                    details=response_data,
                ).model_dump(),
            )
        return PositionbookResponse(**response_data)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.exception(f"Unexpected error in positionbook endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=BaseErrorResponse(
                message="An unexpected error occurred",
                code=str(status.HTTP_500_INTERNAL_SERVER_ERROR),
                details={"error": str(e)},
            ).model_dump(),
        )


@account_router.post(
    "/holdings",
    response_model=HoldingsResponse,
    responses={status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": BaseErrorResponse}},
)
async def holdings_endpoint(
    api_key_data: APIKeySchema,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Retrieves the user's holdings details.

    Args:
        api_key_data: The API key data.
        current_user: The current authenticated user.

    Returns:
        The holdings details.

    Raises:
        HTTPException: If an error occurs while fetching the holdings.
    """
    try:
        success, response_data, status_code = await get_holdings(
            db, api_key=api_key_data.api_key
        )
        if not success:
            raise HTTPException(
                status_code=status_code,
                detail=BaseErrorResponse(
                    message=response_data.get("message", "An error occurred"),
                    code=str(status_code),
                    details=response_data,
                ).model_dump(),
            )
        return HoldingsResponse(**response_data)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.exception(f"Unexpected error in holdings endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=BaseErrorResponse(
                message="An unexpected error occurred",
                code=str(status.HTTP_500_INTERNAL_SERVER_ERROR),
                details={"error": str(e)},
            ).model_dump(),
        )


@account_router.post(
    "/openposition",
    response_model=OpenPositionResponse,
    responses={status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": BaseErrorResponse}},
)
async def openposition_endpoint(
    open_position_request: OpenPositionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Retrieves the quantity of an open position.

    This endpoint fetches the current quantity for a specified open position.
    It also includes logic to handle analytics and logging based on the application's mode.

    Args:
        open_position_request: The request model containing API key and position details.
        current_user: The current authenticated user.

    Returns:
        The open position details, including the quantity.

    Raises:
        HTTPException: If an error occurs while fetching the position, or if an
                     unexpected server error occurs.
    """
    try:
        api_key = open_position_request.apikey
        position_data = open_position_request.model_dump(
            exclude_unset=True, exclude={"apikey"}
        )

        success, response_data, status_code = await get_open_position(
            db, position_data=position_data, api_key=api_key
        )
        if not success:
            if await get_analyze_mode(db):
                # Assuming emit_analyzer_error is synchronous or handled differently in FastAPI context
                # and returns a dict compatible with HTTPException detail
                error_detail = await emit_analyzer_error(
                    db,
                    open_position_request.model_dump(),
                    response_data.get("message", "An error occurred"),
                )
                raise HTTPException(
                    status_code=status_code,
                    detail=BaseErrorResponse(
                        message=error_detail,
                        code=str(status_code),
                        details=response_data,
                    ).model_dump(),
                )

            asyncio.create_task(
                async_log_order(
                    "openposition", open_position_request.model_dump(), response_data
                )
            )
            raise HTTPException(
                status_code=status_code,
                detail=BaseErrorResponse(
                    message=response_data.get("message", "An error occurred"),
                    code=str(status_code),
                    details=response_data,
                ).model_dump(),
            )

        return OpenPositionResponse(**response_data)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.exception("An unexpected error occurred in OpenPosition endpoint.")
        error_message = "An unexpected error occurred"
        if await get_analyze_mode(db):
            # Assuming emit_analyzer_error is synchronous or handled differently in FastAPI context
            error_detail = await emit_analyzer_error(
                db, open_position_request.model_dump(), error_message
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=BaseErrorResponse(
                    message=error_detail,
                    code=str(status.HTTP_500_INTERNAL_SERVER_ERROR),
                    details={"error": str(e)},
                ).model_dump(),
            )

        asyncio.create_task(
            async_log_order(
                "openposition",
                open_position_request.model_dump(),
                {"status": "error", "message": error_message},
            )
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=BaseErrorResponse(
                message=error_message,
                code=str(status.HTTP_500_INTERNAL_SERVER_ERROR),
                details={"error": str(e)},
            ).model_dump(),
        )
