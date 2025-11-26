# database/sandbox_db.py
from datetime import datetime, date
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    DECIMAL,
    CheckConstraint,
    Date,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    select,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.schemas import Base, AsyncSessionLocal
from app.utils.logging import logger


class SandboxOrders(Base):
    """Sandbox orders table - all virtual orders"""

    __tablename__ = "sandbox_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    orderid: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    strategy: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    symbol: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    exchange: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(10), nullable=False)  # BUY or SELL
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(10, 2), nullable=True
    )  # Null for market orders
    trigger_price: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(10, 2), nullable=True
    )  # For SL and SL-M orders
    price_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # MARKET, LIMIT, SL, SL-M
    product: Mapped[str] = mapped_column(String(20), nullable=False)  # CNC, NRML, MIS
    order_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="open", index=True
    )  # open, complete, cancelled, rejected
    average_price: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(10, 2), nullable=True
    )  # Filled price
    filled_quantity: Mapped[int] = mapped_column(
        Integer, default=0
    )  # Always 0 or quantity (no partial fills)
    pending_quantity: Mapped[int] = mapped_column(
        Integer, nullable=False
    )  # Remaining quantity
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    margin_blocked: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(10, 2), nullable=True, default=0.00
    )  # Margin blocked at order placement
    order_timestamp: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.now()
    )
    update_timestamp: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("idx_user_status", "user_id", "order_status"),
        Index("idx_symbol_exchange", "symbol", "exchange"),
        CheckConstraint(
            "order_status IN ('open', 'complete', 'cancelled', 'rejected')",
            name="check_order_status",
        ),
        CheckConstraint("action IN ('BUY', 'SELL')", name="check_action"),
        CheckConstraint(
            "price_type IN ('MARKET', 'LIMIT', 'SL', 'SL-M')", name="check_price_type"
        ),
        CheckConstraint("product IN ('CNC', 'NRML', 'MIS')", name="check_product"),
    )


class SandboxTrades(Base):
    """Sandbox trades table - executed trades"""

    __tablename__ = "sandbox_trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tradeid: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    orderid: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    exchange: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(10), nullable=False)  # BUY or SELL
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[Decimal] = mapped_column(
        DECIMAL(10, 2), nullable=False
    )  # Execution price
    product: Mapped[str] = mapped_column(String(20), nullable=False)  # CNC, NRML, MIS
    strategy: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    trade_timestamp: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.now()
    )

    __table_args__ = (
        Index("idx_user_symbol", "user_id", "symbol"),
        Index("idx_orderid", "orderid"),
    )


class SandboxPositions(Base):
    """Sandbox positions table - open positions"""

    __tablename__ = "sandbox_positions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    exchange: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    product: Mapped[str] = mapped_column(String(20), nullable=False)  # CNC, NRML, MIS
    quantity: Mapped[int] = mapped_column(
        Integer, nullable=False
    )  # Net quantity (can be negative for short)
    average_price: Mapped[Decimal] = mapped_column(
        DECIMAL(10, 2), nullable=False
    )  # Average entry price

    # MTM tracking
    ltp: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(10, 2), nullable=True
    )  # Last traded price
    pnl: Mapped[Decimal] = mapped_column(
        DECIMAL(10, 2), default=0.00
    )  # Current P&L (unrealized for open, realized for closed)
    pnl_percent: Mapped[Decimal] = mapped_column(
        DECIMAL(10, 4), default=0.00
    )  # P&L percentage
    accumulated_realized_pnl: Mapped[Decimal] = mapped_column(
        DECIMAL(10, 2), default=0.00
    )  # Accumulated realized P&L for the day

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id", "symbol", "exchange", "product", name="unique_position"
        ),
        Index("idx_user_product", "user_id", "product"),
    )


class SandboxHoldings(Base):
    """Sandbox holdings table - T+1 settled CNC positions"""

    __tablename__ = "sandbox_holdings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    exchange: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    quantity: Mapped[int] = mapped_column(
        Integer, nullable=False
    )  # Total holdings quantity
    average_price: Mapped[Decimal] = mapped_column(
        DECIMAL(10, 2), nullable=False
    )  # Average buy price

    # MTM tracking
    ltp: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(10, 2), nullable=True
    )  # Last traded price
    pnl: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), default=0.00)  # Unrealized P&L
    pnl_percent: Mapped[Decimal] = mapped_column(
        DECIMAL(10, 4), default=0.00
    )  # P&L percentage

    # Settlement tracking
    settlement_date: Mapped[date] = mapped_column(
        Date, nullable=False
    )  # Date when position was settled to holdings

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("user_id", "symbol", "exchange", name="unique_holding"),
    )


class SandboxFunds(Base):
    """Sandbox funds table - simulated capital and margin tracking"""

    __tablename__ = "sandbox_funds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )

    # Fund balances
    total_capital: Mapped[Decimal] = mapped_column(
        DECIMAL(15, 2), default=10000000.00
    )  # ₹1 Crore starting capital
    available_balance: Mapped[Decimal] = mapped_column(
        DECIMAL(15, 2), default=10000000.00
    )  # Available for trading
    used_margin: Mapped[Decimal] = mapped_column(
        DECIMAL(15, 2), default=0.00
    )  # Margin blocked in positions

    # P&L tracking
    realized_pnl: Mapped[Decimal] = mapped_column(
        DECIMAL(15, 2), default=0.00
    )  # Realized profit/loss from closed positions
    unrealized_pnl: Mapped[Decimal] = mapped_column(
        DECIMAL(15, 2), default=0.00
    )  # Unrealized P&L from open positions
    total_pnl: Mapped[Decimal] = mapped_column(
        DECIMAL(15, 2), default=0.00
    )  # Total P&L (realized + unrealized)

    # Reset tracking
    last_reset_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.now()
    )
    reset_count: Mapped[int] = mapped_column(
        Integer, default=0
    )  # Number of times reset has occurred

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.now(), onupdate=func.now()
    )


class SandboxConfig(Base):
    """Sandbox configuration table - all configurable settings"""

    __tablename__ = "sandbox_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    config_key: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    config_value: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.now(), onupdate=func.now()
    )


async def init_default_config():
    """Initialize default sandbox configuration"""
    from sqlalchemy.exc import IntegrityError

    default_configs = [
        {
            "config_key": "starting_capital",
            "config_value": "10000000.00",
            "description": "Starting sandbox capital in INR (₹1 Crore) - Min: ₹1000",
        },
        {
            "config_key": "reset_day",
            "config_value": "Sunday",
            "description": "Day of week for automatic fund reset",
        },
        {
            "config_key": "reset_time",
            "config_value": "00:00",
            "description": "Time for automatic fund reset (IST)",
        },
        {
            "config_key": "order_check_interval",
            "config_value": "5",
            "description": "Interval in seconds to check pending orders - Range: 1-30 seconds",
        },
        {
            "config_key": "mtm_update_interval",
            "config_value": "5",
            "description": "Interval in seconds to update MTM - Range: 0-60 seconds (0 = manual only)",
        },
        {
            "config_key": "nse_bse_square_off_time",
            "config_value": "15:15",
            "description": "Square-off time for NSE/BSE MIS positions (IST)",
        },
        {
            "config_key": "cds_bcd_square_off_time",
            "config_value": "16:45",
            "description": "Square-off time for CDS/BCD MIS positions (IST)",
        },
        {
            "config_key": "mcx_square_off_time",
            "config_value": "23:30",
            "description": "Square-off time for MCX MIS positions (IST)",
        },
        {
            "config_key": "ncdex_square_off_time",
            "config_value": "17:00",
            "description": "Square-off time for NCDEX MIS positions (IST)",
        },
        {
            "config_key": "equity_mis_leverage",
            "config_value": "5",
            "description": "Leverage multiplier for equity MIS (NSE/BSE) - Range: 1-50x",
        },
        {
            "config_key": "equity_cnc_leverage",
            "config_value": "1",
            "description": "Leverage multiplier for equity CNC (NSE/BSE) - Range: 1-50x",
        },
        {
            "config_key": "futures_leverage",
            "config_value": "10",
            "description": "Leverage multiplier for all futures (NFO/BFO/CDS/BCD/MCX/NCDEX) - Range: 1-50x",
        },
        {
            "config_key": "option_buy_leverage",
            "config_value": "1",
            "description": "Leverage for buying options (full premium) - Range: 1-50x",
        },
        {
            "config_key": "option_sell_leverage",
            "config_value": "1",
            "description": "Leverage for selling options (same as buying - full premium) - Range: 1-50x",
        },
        {
            "config_key": "order_rate_limit",
            "config_value": "10",
            "description": "Maximum orders per second - Range: 1-100 orders/sec (for future use)",
        },
        {
            "config_key": "api_rate_limit",
            "config_value": "50",
            "description": "Maximum API calls per second - Range: 1-1000 calls/sec (for future use)",
        },
        {
            "config_key": "smart_order_rate_limit",
            "config_value": "2",
            "description": "Maximum smart orders per second - Range: 1-50 orders/sec (for future use)",
        },
        {
            "config_key": "smart_order_delay",
            "config_value": "0.5",
            "description": "Delay between multi-leg smart orders - Range: 0.1-10 seconds (for future use)",
        },
    ]
    async with AsyncSessionLocal() as db_session:
        for config in default_configs:
            try:
                existing = (
                    await db_session.execute(
                        select(SandboxConfig).filter_by(config_key=config["config_key"])
                    )
                ).scalar_one_or_none()
                if not existing:
                    config_obj = SandboxConfig(**config)
                    db_session.add(config_obj)
                    await db_session.commit()
                    logger.info(f"Added default config: {config['config_key']}")
            except IntegrityError:
                await db_session.rollback()
                logger.debug(f"Config already exists: {config['config_key']}")
            except Exception as e:
                await db_session.rollback()
                logger.error(f"Error adding config {config['config_key']}: {e}")


async def get_config(config_key, default=None):
    """Get configuration value by key"""
    async with AsyncSessionLocal() as db_session:
        try:
            config = (
                await db_session.execute(
                    select(SandboxConfig).filter_by(config_key=config_key)
                )
            ).scalar_one_or_none()
            if config:
                return config.config_value
            return default
        except Exception as e:
            logger.error(f"Error fetching config {config_key}: {e}")
            return default


async def set_config(config_key, config_value, description=None):
    """Set configuration value"""
    async with AsyncSessionLocal() as db_session:
        try:
            config = (
                await db_session.execute(
                    select(SandboxConfig).filter_by(config_key=config_key)
                )
            ).scalar_one_or_none()
            if config:
                config.config_value = str(config_value)
                if description:
                    config.description = description
            else:
                config = SandboxConfig(
                    config_key=config_key,
                    config_value=str(config_value),
                    description=description,
                )
                db_session.add(config)
            await db_session.commit()
            logger.info(f"Updated config: {config_key} = {config_value}")
            return True
        except Exception as e:
            await db_session.rollback()
            logger.error(f"Error setting config {config_key}: {e}")
            return False


async def get_all_configs():
    """Get all configuration values"""
    async with AsyncSessionLocal() as db_session:
        try:
            result = await db_session.execute(select(SandboxConfig))
            configs = result.scalars().all()
            return {
                config.config_key: {
                    "value": config.config_value,
                    "description": config.description,
                }
                for config in configs
            }
        except Exception as e:
            logger.error(f"Error fetching all configs: {e}")
            return {}
