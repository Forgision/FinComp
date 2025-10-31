from datetime import datetime, timezone

from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlmodel import Field, SQLModel

def utcnow():
    """Returns the current time in UTC."""
    return datetime.now(timezone.utc)

class TimestampMixin(SQLModel):
    """A mixin to add created_at and updated_at timestamp fields to a model."""

    created_at: datetime = Field(
        default_factory=utcnow,
        nullable=False,
        sa_type=TIMESTAMP(timezone=True)
    )
    updated_at: datetime = Field(
        default_factory=utcnow,
        nullable=False,
        sa_column_kwargs={"onupdate": utcnow},
        sa_type=TIMESTAMP(timezone=True)
    )
