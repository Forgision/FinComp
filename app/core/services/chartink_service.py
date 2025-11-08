from app.core.schemas import AsyncSessionLocal
from app.core.schemas.chartink_db import ChartinkStrategy, ChartinkSymbolMapping
from app.utils.logging import logger
from sqlalchemy import select


async def create_strategy(
    name,
    webhook_id,
    user_id,
    is_intraday=True,
    start_time=None,
    end_time=None,
    squareoff_time=None,
):
    """Create a new strategy"""
    async with AsyncSessionLocal() as db_session:
        try:
            strategy = ChartinkStrategy(
                name=name,
                webhook_id=webhook_id,
                user_id=user_id,  # Added user_id
                is_intraday=is_intraday,
                start_time=start_time,
                end_time=end_time,
                squareoff_time=squareoff_time,
            )
            db_session.add(strategy)
            await db_session.commit()
            return strategy
        except Exception as e:
            logger.error(f"Error creating strategy: {str(e)}")
            await db_session.rollback()

    return None


async def get_strategy(strategy_id):
    """Get strategy by ID"""
    async with AsyncSessionLocal() as db_session:
        try:
            q = select(ChartinkStrategy).filter_by(id=strategy_id)
            result = await db_session.execute(q)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error getting strategy {strategy_id}: {str(e)}")

    return None


async def get_strategy_by_webhook_id(webhook_id):
    """Get strategy by webhook ID"""
    async with AsyncSessionLocal() as db_session:
        try:
            stmt = select(ChartinkStrategy).filter_by(webhook_id=webhook_id)
            result = await db_session.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error getting strategy by webhook ID {webhook_id}: {str(e)}")

    return None


async def get_all_strategies():
    """Get all strategies"""
    async with AsyncSessionLocal() as db_session:
        try:
            stmt = select(ChartinkStrategy)
            result = await db_session.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error getting all strategies: {str(e)}")

    return []


async def get_user_strategies(user_id):
    """Get all strategies for a user"""
    async with AsyncSessionLocal() as db_session:
        try:
            stmt = select(ChartinkStrategy).filter_by(user_id=user_id)
            result = await db_session.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error getting strategies for user {user_id}: {str(e)}")

    return []


async def delete_strategy(strategy_id):
    """Delete a strategy"""
    async with AsyncSessionLocal() as db_session:
        try:
            q = select(ChartinkStrategy).filter_by(id=strategy_id)
            result = await db_session.execute(q)
            strategy = result.scalars().first()
            if strategy:
                await db_session.delete(strategy)
                await db_session.commit()
                return True
        except Exception as e:
            logger.error(f"Error deleting strategy {strategy_id}: {str(e)}")
            await db_session.rollback()

    return False


async def toggle_strategy(strategy_id):
    """Toggle strategy active status"""
    async with AsyncSessionLocal() as db_session:
        try:
            strategy = await db_session.get(ChartinkStrategy, strategy_id)
            if strategy:
                strategy.is_active = not strategy.is_active
                await db_session.commit()
                return strategy
            return None
        except Exception as e:
            logger.error(f"Error toggling strategy {strategy_id}: {str(e)}")
            await db_session.rollback()
    return None


async def update_strategy_times(
    strategy_id, start_time=None, end_time=None, squareoff_time=None
):
    """Update strategy trading times"""
    async with AsyncSessionLocal() as db_session:
        try:
            strategy = await db_session.get(ChartinkStrategy, strategy_id)
            if strategy:
                if start_time is not None:
                    strategy.start_time = start_time
                if end_time is not None:
                    strategy.end_time = end_time
                if squareoff_time is not None:
                    strategy.squareoff_time = squareoff_time
                await db_session.commit()
                return strategy
            return None
        except Exception as e:
            logger.error(f"Error updating strategy times {strategy_id}: {str(e)}")
            await db_session.rollback()
    return None


async def add_symbol_mapping(
    strategy_id, chartink_symbol, exchange, quantity, product_type
):
    """Add symbol mapping to strategy"""
    async with AsyncSessionLocal() as db_session:
        try:
            mapping = ChartinkSymbolMapping(
                strategy_id=strategy_id,
                chartink_symbol=chartink_symbol,
                exchange=exchange,
                quantity=quantity,
                product_type=product_type,
            )
            db_session.add(mapping)
            await db_session.commit()
            return mapping
        except Exception as e:
            logger.error(f"Error adding symbol mapping: {str(e)}")
            await db_session.rollback()
    return None


async def bulk_add_symbol_mappings(strategy_id, mappings):
    """Add multiple symbol mappings at once"""
    async with AsyncSessionLocal() as db_session:
        try:
            for mapping_data in mappings:
                mapping = ChartinkSymbolMapping(
                    strategy_id=strategy_id,
                    chartink_symbol=mapping_data["chartink_symbol"],
                    exchange=mapping_data["exchange"],
                    quantity=mapping_data["quantity"],
                    product_type=mapping_data["product_type"],
                )
                db_session.add(mapping)
            await db_session.commit()
            return True
        except Exception as e:
            logger.error(f"Error bulk adding symbol mappings: {str(e)}")
            await db_session.rollback()
    return False


async def get_symbol_mappings(strategy_id):
    """Get all symbol mappings for a strategy"""
    async with AsyncSessionLocal() as db_session:
        try:
            stmt = select(ChartinkSymbolMapping).filter_by(strategy_id=strategy_id)
            result = await db_session.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            logger.error(
                f"Error getting symbol mappings for strategy {strategy_id}: {str(e)}"
            )
    return []


async def delete_symbol_mapping(mapping_id):
    """Delete a symbol mapping"""
    async with AsyncSessionLocal() as db_session:
        try:
            mapping = await db_session.get(ChartinkSymbolMapping, mapping_id)
            if mapping:
                await db_session.delete(mapping)
                await db_session.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting symbol mapping {mapping_id}: {str(e)}")
            await db_session.rollback()
    return False
