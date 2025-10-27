import logging
from typing import List

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, select
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from .base import Base
from .session import db_session, engine

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

def init_db():
    """Initialize the database"""
    logger.info("Initializing Chartink DB")
    Base.metadata.create_all(bind=engine)

def create_strategy(name, webhook_id, user_id, is_intraday=True, start_time=None, end_time=None, squareoff_time=None):
    """Create a new strategy"""
    try:
        strategy = ChartinkStrategy(
            name=name,
            webhook_id=webhook_id,
            user_id=user_id,  # Added user_id
            is_intraday=is_intraday,
            start_time=start_time,
            end_time=end_time,
            squareoff_time=squareoff_time
        )
        db_session.add(strategy)
        db_session.commit()
        return strategy
    except Exception as e:
        logger.error(f"Error creating strategy: {str(e)}")
        db_session.rollback()
        return None

def get_strategy(strategy_id):
    """Get strategy by ID"""
    try:
        return db_session.get(ChartinkStrategy, strategy_id)
    except Exception as e:
        logger.error(f"Error getting strategy {strategy_id}: {str(e)}")
        return None

def get_strategy_by_webhook_id(webhook_id):
    """Get strategy by webhook ID"""
    try:
        stmt = select(ChartinkStrategy).filter_by(webhook_id=webhook_id)
        return db_session.execute(stmt).scalars().first()
    except Exception as e:
        logger.error(f"Error getting strategy by webhook ID {webhook_id}: {str(e)}")
        return None

def get_all_strategies():
    """Get all strategies"""
    try:
        stmt = select(ChartinkStrategy)
        return db_session.execute(stmt).scalars().all()
    except Exception as e:
        logger.error(f"Error getting all strategies: {str(e)}")
        return []

def get_user_strategies(user_id):
    """Get all strategies for a user"""
    try:
        stmt = select(ChartinkStrategy).filter_by(user_id=user_id)
        return db_session.execute(stmt).scalars().all()
    except Exception as e:
        logger.error(f"Error getting strategies for user {user_id}: {str(e)}")
        return []

def delete_strategy(strategy_id):
    """Delete a strategy"""
    try:
        strategy = db_session.get(ChartinkStrategy, strategy_id)
        if strategy:
            db_session.delete(strategy)
            db_session.commit()
            return True
        return False
    except Exception as e:
        logger.error(f"Error deleting strategy {strategy_id}: {str(e)}")
        db_session.rollback()
        return False

def toggle_strategy(strategy_id):
    """Toggle strategy active status"""
    try:
        strategy = db_session.get(ChartinkStrategy, strategy_id)
        if strategy:
            strategy.is_active = not strategy.is_active
            db_session.commit()
            return strategy
        return None
    except Exception as e:
        logger.error(f"Error toggling strategy {strategy_id}: {str(e)}")
        db_session.rollback()
        return None

def update_strategy_times(strategy_id, start_time=None, end_time=None, squareoff_time=None):
    """Update strategy trading times"""
    try:
        strategy = db_session.get(ChartinkStrategy, strategy_id)
        if strategy:
            if start_time is not None:
                strategy.start_time = start_time
            if end_time is not None:
                strategy.end_time = end_time
            if squareoff_time is not None:
                strategy.squareoff_time = squareoff_time
            db_session.commit()
            return strategy
        return None
    except Exception as e:
        logger.error(f"Error updating strategy times {strategy_id}: {str(e)}")
        db_session.rollback()
        return None

def add_symbol_mapping(strategy_id, chartink_symbol, exchange, quantity, product_type):
    """Add symbol mapping to strategy"""
    try:
        mapping = ChartinkSymbolMapping(
            strategy_id=strategy_id,
            chartink_symbol=chartink_symbol,
            exchange=exchange,
            quantity=quantity,
            product_type=product_type
        )
        db_session.add(mapping)
        db_session.commit()
        return mapping
    except Exception as e:
        logger.error(f"Error adding symbol mapping: {str(e)}")
        db_session.rollback()
        return None

def bulk_add_symbol_mappings(strategy_id, mappings):
    """Add multiple symbol mappings at once"""
    try:
        for mapping_data in mappings:
            mapping = ChartinkSymbolMapping(
                strategy_id=strategy_id,
                chartink_symbol=mapping_data['chartink_symbol'],
                exchange=mapping_data['exchange'],
                quantity=mapping_data['quantity'],
                product_type=mapping_data['product_type']
            )
            db_session.add(mapping)
        db_session.commit()
        return True
    except Exception as e:
        logger.error(f"Error bulk adding symbol mappings: {str(e)}")
        db_session.rollback()
        return False

def get_symbol_mappings(strategy_id):
    """Get all symbol mappings for a strategy"""
    try:
        stmt = select(ChartinkSymbolMapping).filter_by(strategy_id=strategy_id)
        return db_session.execute(stmt).scalars().all()
    except Exception as e:
        logger.error(f"Error getting symbol mappings for strategy {strategy_id}: {str(e)}")
        return []

def delete_symbol_mapping(mapping_id):
    """Delete a symbol mapping"""
    try:
        mapping = db_session.get(ChartinkSymbolMapping, mapping_id)
        if mapping:
            db_session.delete(mapping)
            db_session.commit()
            return True
        return False
    except Exception as e:
        logger.error(f"Error deleting symbol mapping {mapping_id}: {str(e)}")
        db_session.rollback()
        return False
