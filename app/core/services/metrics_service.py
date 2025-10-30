from datetime import datetime
from typing import Any, Dict, Optional

from app.core.models.metrics_models import HealthCheckResponse, PerformanceMetric
from app.utils.logging import logger

async def collect_health_metrics() -> HealthCheckResponse:
    """Collects and returns overall application health metrics."""
    # Placeholder for actual health check logic
    # In a real application, this would check database connections, external services, etc.
    uptime = (datetime.now() - START_TIME).total_seconds() if 'START_TIME' in globals() else 0

    health_status = "healthy"
    dependencies_status: Dict[str, Any] = {
        "database": {"status": "ok", "details": "Connected"}, # Placeholder
        "external_api_x": {"status": "ok", "details": "Responsive"}, # Placeholder
    }

    # Example: if a dependency fails, set overall status to unhealthy
    if any(dep['status'] != 'ok' for dep in dependencies_status.values()):
        health_status = "unhealthy"

    return HealthCheckResponse(
        status=health_status,
        timestamp=datetime.now(),
        service="OpenAlgo_FastAPI",
        uptime_seconds=uptime,
        dependencies=dependencies_status,
        version="1.0.0", # Placeholder for actual version
    )

async def record_performance_metric(metric_name: str, value: float, unit: str = "", tags: Optional[Dict[str, Any]] = None):
    """Records a custom performance metric."""
    metric = PerformanceMetric(
        metric_name=metric_name,
        value=value,
        timestamp=datetime.now(),
        unit=unit,
        tags=tags or {}
    )
    logger.info(f"METRIC: {metric.metric_name}={metric.value}{metric.unit} (tags: {metric.tags})")
    # In a real system, this would push metrics to a monitoring system (e.g., Prometheus, Datadog)

# Global variable to store startup time for uptime calculation
START_TIME = datetime.now()
