from pydantic import BaseModel, Field

class BaseErrorResponse(BaseModel):
    message: str = Field(..., description="A human-readable message describing the error.")
    code: str | None = Field(None, description="An optional, unique error code for programmatic identification.")
    details: dict | None = Field(None, description="Optional, additional details about the error, e.g., validation errors.")
