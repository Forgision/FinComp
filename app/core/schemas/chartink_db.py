import logging
from typing import List

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from . import Base

logger = logging.getLogger(__name__)

class ChartinkStrategy(Base):
    """Model for Chartink strategies"""
    __tablename__ = 'chartink_strategies'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    webhook_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)  # UUID
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)  # Added user_id field
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_intraday: Mapped[bool] = mapped_column(Boolean, default=True)
    start_time: Mapped[str] = mapped_column(String(5))  # HH:MM format
    end_time: Mapped[str] = mapped_column(String(5))  # HH:MM format
    squareoff_time: Mapped[str] = mapped_column(String(5))  # HH:MM format
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    symbol_mappings: Mapped[List["ChartinkSymbolMapping"]] = relationship("ChartinkSymbolMapping", back_populates="strategy", cascade="all, delete-orphan")

    def as_dict(self):
       return {c.name: getattr(self, c.name) for c in self.__table__.columns}

class ChartinkSymbolMapping(Base):
    """Model for symbol mappings in Chartink strategies"""
    __tablename__ = 'chartink_symbol_mappings'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    strategy_id: Mapped[int] = mapped_column(Integer, ForeignKey('chartink_strategies.id'), nullable=False)
    chartink_symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    exchange: Mapped[str] = mapped_column(String(10), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    product_type: Mapped[str] = mapped_column(String(10), nullable=False)  # MIS/CNC
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    strategy: Mapped["ChartinkStrategy"] = relationship("ChartinkStrategy", back_populates="symbol_mappings")

    def as_dict(self):
       return {c.name: getattr(self, c.name) for c in self.__table__.columns}
