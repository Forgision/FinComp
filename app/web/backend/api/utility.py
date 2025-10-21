from fastapi import APIRouter, HTTPException, status

from app.core.models.api_schemas import AnalyzerSchema, AnalyzerToggleSchema, PingSchema
from app.core.services.analyzer_service import get_analyzer_status, toggle_analyzer_mode
from app.core.services.ping_service import get_ping
from app.utils.logging import logger

utility_router = APIRouter(prefix="/utility", tags=["Utility"])

@utility_router.post("/analyzer", summary="Get analyzer mode status and statistics")
async def analyzer_status(analyzer_data: AnalyzerSchema):
    """
    Get analyzer mode status and statistics.

    Args:
        analyzer_data: The analyzer data.

    Returns:
        A dictionary with the analyzer status and statistics.

    Raises:
        HTTPException: If an error occurs while fetching the status.
    """
    try:
        api_key = analyzer_data.apikey
        success, response_data, status_code = await get_analyzer_status(
            analyzer_data=analyzer_data.model_dump(),
            api_key=api_key
        )
        if not success:
            raise HTTPException(status_code=status_code, detail=response_data.get("message", "An error occurred"))
        return response_data
    except HTTPException as e:
        raise e
    except Exception:
        logger.exception("An unexpected error occurred in Analyzer status endpoint.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred")

@utility_router.post("/analyzer/toggle", summary="Toggle analyzer mode on/off")
async def analyzer_toggle(analyzer_data: AnalyzerToggleSchema):
    """
    Toggle analyzer mode on/off.

    Args:
        analyzer_data: The analyzer toggle data.

    Returns:
        A dictionary with the result of the toggle operation.

    Raises:
        HTTPException: If an error occurs during the toggle operation.
    """
    try:
        api_key = analyzer_data.apikey
        success, response_data, status_code = await toggle_analyzer_mode(
            analyzer_data=analyzer_data.model_dump(),
            api_key=api_key
        )
        if not success:
            raise HTTPException(status_code=status_code, detail=response_data.get("message", "An error occurred"))
        return response_data
    except HTTPException as e:
        raise e
    except Exception:
        logger.exception("An unexpected error occurred in Analyzer toggle endpoint.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred")

@utility_router.post("/ping", summary="Check API connectivity and authentication")
async def ping(ping_data: PingSchema):
    """
    Check API connectivity and authentication.

    Args:
        ping_data: The ping data.

    Returns:
        A dictionary with the result of the ping.

    Raises:
        HTTPException: If an error occurs during the ping.
    """
    try:
        api_key = ping_data.apikey
        success, response_data, status_code = await get_ping(api_key=api_key)
        if not success:
            raise HTTPException(status_code=status_code, detail=response_data.get("message", "An error occurred"))
        return response_data
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unexpected error in ping endpoint: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred")
