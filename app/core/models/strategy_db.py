import logging
from datetime import datetime
from typing import List, Optional

from sqlmodel import Field, Relationship, Session, SQLModel, select

logger = logging.getLogger(__name__)


class Strategy(SQLModel, table=True):
    """Model for trading strategies"""
    __tablename__ = 'strategies'

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=255)
    webhook_id: str = Field(max_length=36, unique=True)
    user_id: str = Field(max_length=255)
    platform: str = Field(max_length=50, default='tradingview')
    is_active: bool = Field(default=True)
    is_intraday: bool = Field(default=True)
    trading_mode: str = Field(max_length=10, default='LONG')
    start_time: Optional[str] = Field(max_length=5, default=None)
    end_time: Optional[str] = Field(max_length=5, default=None)
    squareoff_time: Optional[str] = Field(max_length=5, default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: Optional[datetime] = Field(default=None, sa_column_kwargs={"onupdate": datetime.utcnow})

    # Relationships
    symbol_mappings: List["StrategySymbolMapping"] = Relationship(back_populates="strategy", sa_relationship_kwargs={"cascade": "all, delete-orphan"})


class StrategySymbolMapping(SQLModel, table=True):
    """Model for symbol mappings in strategies"""
    __tablename__ = 'strategy_symbol_mappings'

    id: Optional[int] = Field(default=None, primary_key=True)
    strategy_id: int = Field(foreign_key='strategies.id')
    symbol: str = Field(max_length=50)
    exchange: str = Field(max_length=10)
    quantity: int
    product_type: str = Field(max_length=10)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: Optional[datetime] = Field(default=None, sa_column_kwargs={"onupdate": datetime.utcnow})

    # Relationships
    strategy: Optional["Strategy"] = Relationship(back_populates="symbol_mappings")


def create_strategy(db: Session, name: str, webhook_id: str, user_id: str, is_intraday: bool = True, trading_mode: str = 'LONG', start_time: Optional[str] = None, end_time: Optional[str] = None, squareoff_time: Optional[str] = None, platform: str = 'tradingview') -> Optional[Strategy]:
    """Create a new strategy"""
    try:
        strategy = Strategy(
            name=name,
            webhook_id=webhook_id,
            user_id=user_id,
            is_intraday=is_intraday,
            trading_mode=trading_mode,
            start_time=start_time,
            end_time=end_time,
            squareoff_time=squareoff_time,
            platform=platform
        )
        db.add(strategy)
        db.commit()
        db.refresh(strategy)
        return strategy
    except Exception as e:
        logger.error(f"Error creating strategy: {str(e)}")
        db.rollback()
        return None


def get_strategy(db: Session, strategy_id: int) -> Optional[Strategy]:
    """Get strategy by ID"""
    try:
        return db.get(Strategy, strategy_id)
    except Exception as e:
        logger.error(f"Error getting strategy {strategy_id}: {str(e)}")
        return None


def get_strategy_by_webhook_id(db: Session, webhook_id: str) -> Optional[Strategy]:
    """Get strategy by webhook ID"""
    try:
        statement = select(Strategy).where(Strategy.webhook_id == webhook_id)
        return db.exec(statement).first()
    except Exception as e:
        logger.error(f"Error getting strategy by webhook ID {webhook_id}: {str(e)}")
        return None


def get_all_strategies(db: Session) -> List[Strategy]:
    """Get all strategies"""
    try:
        statement = select(Strategy)
        return db.exec(statement).all()
    except Exception as e:
        logger.error(f"Error getting all strategies: {str(e)}")
        return []


def get_user_strategies(db: Session, user_id: str) -> List[Strategy]:
    """Get all strategies for a user"""
    try:
        logger.info(f"Fetching strategies for user: {user_id}")
        statement = select(Strategy).where(Strategy.user_id == user_id)
        strategies = db.exec(statement).all()
        logger.info(f"Found {len(strategies)} strategies")
        return strategies
    except Exception as e:
        logger.error(f"Error getting user strategies for {user_id}: {str(e)}")
        return []


def delete_strategy(db: Session, strategy_id: int) -> bool:
    """Delete strategy and its symbol mappings"""
    try:
        strategy = get_strategy(db, strategy_id)
        if not strategy:
            return False

        db.delete(strategy)
        db.commit()
        return True
    except Exception as e:
        logger.error(f"Error deleting strategy {strategy_id}: {str(e)}")
        db.rollback()
        return False


def toggle_strategy(db: Session, strategy_id: int) -> Optional[Strategy]:
    """Toggle strategy active status"""
    try:
        strategy = get_strategy(db, strategy_id)
        if not strategy:
            return None

        strategy.is_active = not strategy.is_active
        db.add(strategy)
        db.commit()
        db.refresh(strategy)
        return strategy
    except Exception as e:
        logger.error(f"Error toggling strategy {strategy_id}: {str(e)}")
        db.rollback()
        return None


def update_strategy_times(db: Session, strategy_id: int, start_time: Optional[str] = None, end_time: Optional[str] = None, squareoff_time: Optional[str] = None) -> bool:
    """Update strategy trading times"""
    try:
        strategy = db.get(Strategy, strategy_id)
        if strategy:
            if start_time is not None:
                strategy.start_time = start_time
            if end_time is not None:
                strategy.end_time = end_time
            if squareoff_time is not None:
                strategy.squareoff_time = squareoff_time
            db.add(strategy)
            db.commit()
            return True
        return False
    except Exception as e:
        logger.error(f"Error updating strategy times {strategy_id}: {str(e)}")
        db.rollback()
        return False


def add_symbol_mapping(db: Session, strategy_id: int, symbol: str, exchange: str, quantity: int, product_type: str) -> Optional[StrategySymbolMapping]:
    """Add symbol mapping to strategy"""
    try:
        mapping = StrategySymbolMapping(
            strategy_id=strategy_id,
            symbol=symbol,
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


def bulk_add_symbol_mappings(db: Session, strategy_id: int, mappings: List[dict]) -> bool:
    """Add multiple symbol mappings at once"""
    try:
        for mapping_data in mappings:
            mapping = StrategySymbolMapping(
                strategy_id=strategy_id,
                **mapping_data
            )
            db.add(mapping)
        db.commit()
        return True
    except Exception as e:
        logger.error(f"Error bulk adding symbol mappings: {str(e)}")
        db.rollback()
        return False


def get_symbol_mappings(db: Session, strategy_id: int) -> List[StrategySymbolMapping]:
    """Get all symbol mappings for a strategy"""
    try:
        statement = select(StrategySymbolMapping).where(StrategySymbolMapping.strategy_id == strategy_id)
        return db.exec(statement).all()
    except Exception as e:
        logger.error(f"Error getting symbol mappings: {str(e)}")
        return []


def delete_symbol_mapping(db: Session, mapping_id: int) -> bool:
    """Delete a symbol mapping"""
    try:
        mapping = db.get(StrategySymbolMapping, mapping_id)
        if mapping:
            db.delete(mapping)
            db.commit()
            return True
        return False
    except Exception as e:
        logger.error(f"Error deleting symbol mapping {mapping_id}: {str(e)}")
        db.rollback()
        return False
