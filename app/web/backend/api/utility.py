from fastapi import APIRouter, Depends, HTTPException, status
from app.web.models.api_schemas import AnalyzerSchema, AnalyzerToggleSchema, PingSchema
from app.web.services.analyzer_service import get_analyzer_status, toggle_analyzer_mode
from app.web.services.ping_service import get_ping
from app.utils.logging import get_logger

router = APIRouter(prefix="/utility", tags=["Utility"])
logger = get_logger(__name__)

@router.post("/analyzer", summary="Get analyzer mode status and statistics")
async def analyzer_status(analyzer_data: AnalyzerSchema):
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
    except Exception as e:
        logger.exception("An unexpected error occurred in Analyzer status endpoint.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred")

@router.post("/analyzer/toggle", summary="Toggle analyzer mode on/off")
async def analyzer_toggle(analyzer_data: AnalyzerToggleSchema):
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
    except Exception as e:
        logger.exception("An unexpected error occurred in Analyzer toggle endpoint.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred")

@router.post("/ping", summary="Check API connectivity and authentication")
async def ping(ping_data: PingSchema):
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