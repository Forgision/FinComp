from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.responses import JSONResponse
from app.core.models.metrics_models import HealthCheckResponse
from app.core.services.metrics_service import collect_health_metrics
from app.utils.session import check_session_validity_fastapi
from app.utils.logging import logger
from app.core.models.error_models import BaseErrorResponse

monitoring_router = APIRouter(prefix="/monitoring", tags=["Monitoring"])

@monitoring_router.get("/health", response_model=HealthCheckResponse, responses={status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": BaseErrorResponse}})
async def health_check_endpoint(current_user: dict = Depends(check_session_validity_fastapi)):
    """Returns the current health status of the application."""
    try:
        health_status = await collect_health_metrics()
        return JSONResponse(content=health_status.model_dump(), status_code=status.HTTP_200_OK)
    except Exception as e:
        logger.exception(f"Health check failed: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=BaseErrorResponse(message="Internal Server Error during health check").model_dump())

@monitoring_router.get("/metrics", responses={status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": BaseErrorResponse}})
async def get_metrics_endpoint(current_user: dict = Depends(check_session_validity_fastapi)):
    """Returns application performance metrics (placeholder for actual metrics system)."""
    try:
        # Placeholder for actual metrics collection logic
        # In a real system, this would expose metrics in a format suitable for Prometheus or similar.
        current_metrics = {
            "cpu_usage_percent": 25.5,
            "memory_usage_mb": 512,
            "api_requests_total": 12345,
            "api_errors_total": 12
        }
        return JSONResponse(content=current_metrics, status_code=status.HTTP_200_OK)
    except Exception as e:
        logger.exception(f"Metrics collection failed: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=BaseErrorResponse(message="Internal Server Error during metrics collection").model_dump())
