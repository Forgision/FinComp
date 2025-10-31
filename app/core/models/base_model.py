from typing import Optional

from sqlmodel import Field, SQLModel
from .mixins import TimestampMixin

class BaseModel(SQLModel):
    """A base model with an ID field."""
    id: Optional[int] = Field(default=None, primary_key=True, index=True)

class TimestampedBaseModel(BaseModel, TimestampMixin):
    """A base model with ID, created_at, and updated_at fields."""
    pass
