from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.schemas.master_contract_status_db import check_if_ready, get_status
from app.core.schemas import get_db
from app.utils.logging import logger
from app.utils.session import check_session_validity_fastapi


master_contract_status_router = APIRouter(prefix="/api/master-contract", tags=["Master Contract"])

@master_contract_status_router.get("/status")
async def get_master_contract_status(request: Request, db: Session = Depends(get_db), user: dict = Depends(check_session_validity_fastapi)):
    """
    Get the status of the master contract download for the current broker.

    Args:
        request: The incoming request object.
        db: The database session.
        user: The current authenticated user.

    Returns:
        A JSON response with the master contract status.
    """
    try:
        broker = request.session.get("broker")
        if not broker:
            return JSONResponse({"status": "error", "message": "No broker session found"}, status_code=401)

        status_data = get_status(db, broker)
        return JSONResponse(status_data)
    except Exception as e:
        logger.error(f"Error getting master contract status: {e}")
        return JSONResponse({"status": "error", "message": "Failed to get master contract status"}, status_code=500)

@master_contract_status_router.get("/ready")
async def check_master_contract_ready(request: Request, db: Session = Depends(get_db), user: dict = Depends(check_session_validity_fastapi)):
    """
    Check if the master contract for the current broker is ready.

    Args:
        request: The incoming request object.
        db: The database session.
        user: The current authenticated user.

    Returns:
        A JSON response indicating whether the master contract is ready.
    """
    try:
        broker = request.session.get("broker")
        if not broker:
            return JSONResponse({"ready": False, "message": "No broker session found"}, status_code=401)

        is_ready = check_if_ready(db, broker)
        return JSONResponse({"ready": is_ready, "message": "Master contracts are ready" if is_ready else "Master contracts not ready"})
    except Exception as e:
        logger.error(f"Error checking master contract readiness: {e}")
        return JSONResponse({"ready": False, "message": "Failed to check master contract readiness"}, status_code=500)

# ... other cache-related routes can be refactored similarly
