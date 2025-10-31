import logging
from typing import List, Optional
from datetime import datetime

from sqlalchemy.orm import Session
from sqlmodel import Field, Relationship, SQLModel, select


logger = logging.getLogger(__name__)

class ChartinkStrategy(SQLModel, table=True):
    """Model for Chartink strategies"""
    __tablename__ = 'chartink_strategies'

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=255)
    webhook_id: str = Field(max_length=36, unique=True)  # UUID
    user_id: str = Field(max_length=255)
    is_active: bool = Field(default=True)
    is_intraday: bool = Field(default=True)
    start_time: Optional[str] = Field(default=None, max_length=5)  # HH:MM format
    end_time: Optional[str] = Field(default=None, max_length=5)  # HH:MM format
    squareoff_time: Optional[str] = Field(default=None, max_length=5)  # HH:MM format
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow, sa_column_kwargs={"onupdate": datetime.utcnow})

    # Relationships
    symbol_mappings: List["ChartinkSymbolMapping"] = Relationship(back_populates="strategy", sa_relationship_kwargs={"cascade": "all, delete-orphan"})


class ChartinkSymbolMapping(SQLModel, table=True):
    """Model for symbol mappings in Chartink strategies"""
    __tablename__ = 'chartink_symbol_mappings'

    id: Optional[int] = Field(default=None, primary_key=True)
    strategy_id: int = Field(foreign_key='chartink_strategies.id')
    chartink_symbol: str = Field(max_length=50)
    exchange: str = Field(max_length=10)
    quantity: int
    product_type: str = Field(max_length=10)  # MIS/CNC
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow, sa_column_kwargs={"onupdate": datetime.utcnow})

    # Relationships
    strategy: "ChartinkStrategy" = Relationship(back_populates="symbol_mappings")


def create_strategy(db: Session, name: str, webhook_id: str, user_id: str, is_intraday: bool = True, start_time: str = None, end_time: str = None, squareoff_time: str = None):
    """Create a new strategy"""
    try:
        strategy = ChartinkStrategy(
            name=name,
            webhook_id=webhook_id,
            user_id=user_id,
            is_intraday=is_intraday,
            start_time=start_time,
            end_time=end_time,
            squareoff_time=squareoff_time
        )
        db.add(strategy)
        db.commit()
        db.refresh(strategy)
        return strategy
    except Exception as e:
        logger.error(f"Error creating strategy: {str(e)}")
        db.rollback()
        return None

def get_strategy(db: Session, strategy_id: int):
    """Get strategy by ID"""
    try:
        return db.get(ChartinkStrategy, strategy_id)
    except Exception as e:
        logger.error(f"Error getting strategy {strategy_id}: {str(e)}")
        return None

def get_strategy_by_webhook_id(db: Session, webhook_id: str):
    """Get strategy by webhook ID"""
    try:
        statement = select(ChartinkStrategy).where(ChartinkStrategy.webhook_id == webhook_id)
        return db.exec(statement).first()
    except Exception as e:
        logger.error(f"Error getting strategy by webhook ID {webhook_id}: {str(e)}")
        return None

def get_all_strategies(db: Session):
    """Get all strategies"""
    try:
        statement = select(ChartinkStrategy)
        return db.exec(statement).all()
    except Exception as e:
        logger.error(f"Error getting all strategies: {str(e)}")
        return []

def get_user_strategies(db: Session, user_id: str):
    """Get all strategies for a user"""
    try:
        statement = select(ChartinkStrategy).where(ChartinkStrategy.user_id == user_id)
        return db.exec(statement).all()
    except Exception as e:
        logger.error(f"Error getting strategies for user {user_id}: {str(e)}")
        return []

def delete_strategy(db: Session, strategy_id: int):
    """Delete a strategy"""
    try:
        strategy = db.get(ChartinkStrategy, strategy_id)
        if strategy:
            db.delete(strategy)
            db.commit()
            return True
        return False
    except Exception as e:
        logger.error(f"Error deleting strategy {strategy_id}: {str(e)}")
        db.rollback()
        return False

def toggle_strategy(db: Session, strategy_id: int):
    """Toggle strategy active status"""
    try:
        strategy = db.get(ChartinkStrategy, strategy_id)
        if strategy:
            strategy.is_active = not strategy.is_active
            db.add(strategy)
            db.commit()
            db.refresh(strategy)
            return strategy
        return None
    except Exception as e:
        logger.error(f"Error toggling strategy {strategy_id}: {str(e)}")
        db.rollback()
        return None

def update_strategy_times(db: Session, strategy_id: int, start_time: str = None, end_time: str = None, squareoff_time: str = None):
    """Update strategy trading times"""
    try:
        strategy = db.get(ChartinkStrategy, strategy_id)
        if strategy:
            if start_time is not None:
                strategy.start_time = start_time
            if end_time is not None:
                strategy.end_time = end_time
            if squareoff_time is not None:
                strategy.squareoff_time = squareoff_time
            db.add(strategy)
            db.commit()
            db.refresh(strategy)
            return strategy
        return None
    except Exception as e:
        logger.error(f"Error updating strategy times {strategy_id}: {str(e)}")
        db.rollback()
        return None

def add_symbol_mapping(db: Session, strategy_id: int, chartink_symbol: str, exchange: str, quantity: int, product_type: str):
    """Add symbol mapping to strategy"""
    try:
        mapping = ChartinkSymbolMapping(
            strategy_id=strategy_id,
            chartink_symbol=chartink_symbol,
            exchange=exchange,
            quantity=quantity,
            product_type=product_type
        )
        db.add(mapping)
        db.commit()
        db.refresh(mapping)
        return mapping
    except Exception as e:
        logger.error(f"Error adding symbol mapping: {str(e)}")
        db.rollback()
        return None

def bulk_add_symbol_mappings(db: Session, strategy_id: int, mappings: List[dict]):
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
            db.add(mapping)
        db.commit()
        return True
    except Exception as e:
        logger.error(f"Error bulk adding symbol mappings: {str(e)}")
        db.rollback()
        return False

def get_symbol_mappings(db: Session, strategy_id: int):
    """Get all symbol mappings for a strategy"""
    try:
        statement = select(ChartinkSymbolMapping).where(ChartinkSymbolMapping.strategy_id == strategy_id)
        return db.exec(statement).all()
    except Exception as e:
        logger.error(f"Error getting symbol mappings for strategy {strategy_id}: {str(e)}")
        return []

def delete_symbol_mapping(db: Session, mapping_id: int):
    """Delete a symbol mapping"""
    try:
        mapping = db.get(ChartinkSymbolMapping, mapping_id)
        if mapping:
            db.delete(mapping)
            db.commit()
            return True
        return False
    except Exception as e:
        logger.error(f"Error deleting symbol mapping {mapping_id}: {str(e)}")
        db.rollback()
        return False
