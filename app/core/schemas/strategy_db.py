from datetime import datetime
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.schemas import Base
from app.utils.logging import logger


class Strategy(Base):
    """Model for trading strategies"""

    __tablename__ = "strategies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    webhook_id: Mapped[str] = mapped_column(
        String(36), unique=True, nullable=False
    )  # UUID
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    platform: Mapped[str] = mapped_column(
        String(50), nullable=False, default="tradingview"
    )  # Platform type (tradingview, chartink, etc)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_intraday: Mapped[bool] = mapped_column(Boolean, default=True)
    trading_mode: Mapped[str] = mapped_column(
        String(10), nullable=False, default="LONG"
    )  # LONG, SHORT, or BOTH
    start_time: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)
    end_time: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)
    squareoff_time: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )

    # Relationships
    symbol_mappings: Mapped[List["StrategySymbolMapping"]] = relationship(
        "StrategySymbolMapping", back_populates="strategy", cascade="all, delete-orphan"
    )


class StrategySymbolMapping(Base):
    """Model for symbol mappings in strategies"""

    __tablename__ = "strategy_symbol_mappings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    strategy_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("strategies.id"), nullable=False
    )
    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    exchange: Mapped[str] = mapped_column(String(10), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    product_type: Mapped[str] = mapped_column(String(10), nullable=False)  # MIS/CNC
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )

    # Relationships
    strategy: Mapped["Strategy"] = relationship(
        "Strategy", back_populates="symbol_mappings"
    )


async def create_strategy(
    db: AsyncSession,
    name: str,
    webhook_id: str,
    user_id: str,
    is_intraday: bool = True,
    trading_mode: str = "LONG",
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    squareoff_time: Optional[str] = None,
    platform: str = "tradingview",
) -> Optional[Strategy]:
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
            platform=platform,
        )
        db.add(strategy)
        await db.commit()
        return strategy
    except Exception as e:
        logger.error(f"Error creating strategy: {str(e)}")
        await db.rollback()
        return None


async def get_strategy(db: AsyncSession, strategy_id: int) -> Optional[Strategy]:
    """Get strategy by ID"""
    try:
        return await db.get(Strategy, strategy_id)
    except Exception as e:
        logger.error(f"Error getting strategy {strategy_id}: {str(e)}")
        return None


async def get_strategy_by_webhook_id(
    db: AsyncSession, webhook_id: str
) -> Optional[Strategy]:
    """Get strategy by webhook ID"""
    try:
        result = await db.execute(select(Strategy).filter_by(webhook_id=webhook_id))
        return result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Error getting strategy by webhook ID {webhook_id}: {str(e)}")
        return None


async def get_all_strategies(db: AsyncSession) -> List[Strategy]:
    """Get all strategies"""
    try:
        result = await db.execute(select(Strategy))
        return list(result.scalars().all())
    except Exception as e:
        logger.error(f"Error getting all strategies: {str(e)}")
        return []


async def get_user_strategies(db: AsyncSession, user_id: str) -> List[Strategy]:
    """Get all strategies for a user"""
    try:
        logger.info(f"Fetching strategies for user: {user_id}")
        result = await db.execute(select(Strategy).filter_by(user_id=user_id))
        strategies = list(result.scalars().all())
        logger.info(f"Found {len(strategies)} strategies")
        return strategies
    except Exception as e:
        logger.error(f"Error getting user strategies for {user_id}: {str(e)}")
        return []


async def delete_strategy(db: AsyncSession, strategy_id: int) -> bool:
    """Delete strategy and its symbol mappings"""
    try:
        strategy = await get_strategy(db, strategy_id)
        if not strategy:
            return False

        await db.delete(strategy)
        await db.commit()
        return True
    except Exception as e:
        logger.error(f"Error deleting strategy {strategy_id}: {str(e)}")
        await db.rollback()
        return False


async def toggle_strategy(db: AsyncSession, strategy_id: int) -> Optional[Strategy]:
    """Toggle strategy active status"""
    try:
        strategy = await get_strategy(db, strategy_id)
        if not strategy:
            return None

        strategy.is_active = not strategy.is_active
        await db.commit()
        return strategy
    except Exception as e:
        logger.error(f"Error toggling strategy {strategy_id}: {str(e)}")
        await db.rollback()
        return None


async def update_strategy_times(
    db: AsyncSession,
    strategy_id: int,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    squareoff_time: Optional[str] = None,
) -> bool:
    """Update strategy trading times"""
    try:
        strategy = await db.get(Strategy, strategy_id)
        if strategy:
            if start_time is not None:
                strategy.start_time = start_time
            if end_time is not None:
                strategy.end_time = end_time
            if squareoff_time is not None:
                strategy.squareoff_time = squareoff_time
            await db.commit()
            return True
        return False
    except Exception as e:
        logger.error(f"Error updating strategy times {strategy_id}: {str(e)}")
        await db.rollback()
        return False


async def add_symbol_mapping(
    db: AsyncSession,
    strategy_id: int,
    symbol: str,
    exchange: str,
    quantity: int,
    product_type: str,
) -> Optional[StrategySymbolMapping]:
    """Add symbol mapping to strategy"""
    try:
        mapping = StrategySymbolMapping(
            strategy_id=strategy_id,
            symbol=symbol,
            exchange=exchange,
            quantity=quantity,
            product_type=product_type,
        )
        db.add(mapping)
        await db.commit()
        return mapping
    except Exception as e:
        logger.error(f"Error adding symbol mapping: {str(e)}")
        await db.rollback()
        return None


async def bulk_add_symbol_mappings(
    db: AsyncSession, strategy_id: int, mappings: List[dict]
) -> bool:
    """Add multiple symbol mappings at once"""
    try:
        for mapping_data in mappings:
            mapping = StrategySymbolMapping(strategy_id=strategy_id, **mapping_data)
            db.add(mapping)
        await db.commit()
        return True
    except Exception as e:
        logger.error(f"Error bulk adding symbol mappings: {str(e)}")
        await db.rollback()
        return False


async def get_symbol_mappings(
    db: AsyncSession, strategy_id: int
) -> List[StrategySymbolMapping]:
    """Get all symbol mappings for a strategy"""
    try:
        result = await db.execute(
            select(StrategySymbolMapping).filter_by(strategy_id=strategy_id)
        )
        return list(result.scalars().all())
    except Exception as e:
        logger.error(f"Error getting symbol mappings: {str(e)}")
        return []


async def delete_symbol_mapping(db: AsyncSession, mapping_id: int) -> bool:
    """Delete a symbol mapping"""
    try:
        mapping = await db.get(StrategySymbolMapping, mapping_id)
        if mapping:
            await db.delete(mapping)
            await db.commit()
            return True
        return False
    except Exception as e:
        logger.error(f"Error deleting symbol mapping {mapping_id}: {str(e)}")
        await db.rollback()
        return False
