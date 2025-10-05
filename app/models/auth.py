from sqlalchemy import Column, Integer, String, Text, Boolean
from app.models.base import Base

class Auth(Base):
    __tablename__ = "auth"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    auth = Column(Text, nullable=False)
    feed_token = Column(Text, nullable=True)
    broker = Column(String, nullable=False)
    user_id = Column(String, nullable=True)
    is_revoked = Column(Boolean, default=False)