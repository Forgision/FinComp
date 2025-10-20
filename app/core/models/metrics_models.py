from pydantic import BaseModel, Field
from datetime import datetime

class HealthCheckResponse(BaseModel):
    status: str = Field(..., description="Overall health status of the application.")
    timestamp: datetime = Field(..., description="Timestamp of when the health check was performed.")
    service: str = Field(..., description="Name of the service being checked.")
    version: str | None = Field(None, description="Version of the service.")
    dependencies: dict | None = Field(None, description="Status of key dependencies (e.g., database, external APIs).")
    uptime_seconds: float | None = Field(None, description="Uptime of the service in seconds.")

class PerformanceMetric(BaseModel):
    metric_name: str = Field(..., description="Name of the performance metric.")
    value: float = Field(..., description="Value of the metric.")
    timestamp: datetime = Field(..., description="Timestamp of the metric collection.")
    unit: str | None = Field(None, description="Unit of the metric (e.g., 'ms', 'req/s').")
    tags: dict | None = Field(None, description="Optional tags for filtering/grouping metrics.")
