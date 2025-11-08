from app.utils.session import check_session_validity_fastapi
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.schemas import get_db
from app.core.schemas.settings_db import get_analyze_mode, set_analyze_mode
from app.algo.sandbox.execution_thread import (
    start_execution_engine,
    stop_execution_engine,
)
from app.utils.logging import logger

settings_router = APIRouter(prefix="/settings", tags=["Settings"])


@settings_router.get("/analyze-mode")
async def get_mode(
    session_data: dict = Depends(check_session_validity_fastapi),
    db: AsyncSession = Depends(get_db),
):
    """Get current analyze mode setting"""
    try:
        analyze_mode = await get_analyze_mode(db)
        return JSONResponse(content={"analyze_mode": analyze_mode})
    except Exception as e:
        logger.error(f"Error getting analyze mode: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get analyze mode",
        )


@settings_router.post("/analyze-mode/{mode}")
async def set_mode(
    mode: int,
    session_data: dict = Depends(check_session_validity_fastapi),
    db: AsyncSession = Depends(get_db),
):
    """Set analyze mode setting and manage execution engine thread"""
    try:
        is_analyze_mode = bool(mode)
        await set_analyze_mode(db, is_analyze_mode)
        mode_name = "Analyze" if is_analyze_mode else "Live"

        # Start or stop execution engine based on mode
        if is_analyze_mode:
            # Starting Analyze mode - start execution engine
            success, message = await start_execution_engine()  # Assuming async
            if success:
                logger.info("Execution engine started for Analyze mode")
            else:
                logger.warning(f"Failed to start execution engine: {message}")
        else:
            # Switching to Live mode - stop execution engine
            success, message = await stop_execution_engine()  # Assuming async
            if success:
                logger.info("Execution engine stopped for Live mode")
            else:
                logger.warning(f"Failed to stop execution engine: {message}")

        return JSONResponse(
            content={
                "success": True,
                "analyze_mode": is_analyze_mode,
                "message": f"Switched to {mode_name} Mode",
            }
        )
    except Exception as e:
        logger.error(f"Error setting analyze mode: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to set analyze mode",
        )
