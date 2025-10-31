from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any

from sqlalchemy import (
    DECIMAL,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from sqlmodel import Field, SQLModel, select

from app.utils.logging import logger


class SandboxOrders(SQLModel, table=True):
    """Sandbox orders table - all virtual orders"""
    __tablename__ = 'sandbox_orders'

    id: Optional[int] = Field(default=None, primary_key=True)
    orderid: str = Field(max_length=50, unique=True, index=True)
    user_id: str = Field(max_length=50, index=True)
    strategy: Optional[str] = Field(default=None, max_length=100)
    symbol: str = Field(max_length=50, index=True)
    exchange: str = Field(max_length=20, index=True)
    action: str = Field(max_length=10)
    quantity: int
    price: Optional[Decimal] = Field(default=None, sa_column=Column(DECIMAL(10, 2)))
    trigger_price: Optional[Decimal] = Field(default=None, sa_column=Column(DECIMAL(10, 2)))
    price_type: str = Field(max_length=20)
    product: str = Field(max_length=20)
    order_status: str = Field(default='open', max_length=20, index=True)
    average_price: Optional[Decimal] = Field(default=None, sa_column=Column(DECIMAL(10, 2)))
    filled_quantity: int = Field(default=0)
    pending_quantity: int
    rejection_reason: Optional[str] = Field(default=None, sa_column=Column(Text))
    margin_blocked: Optional[Decimal] = Field(default=Decimal('0.00'), sa_column=Column(DECIMAL(10, 2)))
    order_timestamp: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"nullable": False, "server_default": func.now()})
    update_timestamp: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"nullable": False, "server_default": func.now(), "onupdate": func.now()})

    __table_args__ = (
        Index('idx_user_status', 'user_id', 'order_status'),
        Index('idx_symbol_exchange', 'symbol', 'exchange'),
        CheckConstraint("order_status IN ('open', 'complete', 'cancelled', 'rejected')", name='check_order_status'),
        CheckConstraint("action IN ('BUY', 'SELL')", name='check_action'),
        CheckConstraint("price_type IN ('MARKET', 'LIMIT', 'SL', 'SL-M')", name='check_price_type'),
        CheckConstraint("product IN ('CNC', 'NRML', 'MIS')", name='check_product'),
    )


class SandboxTrades(SQLModel, table=True):
    """Sandbox trades table - executed trades"""
    __tablename__ = 'sandbox_trades'

    id: Optional[int] = Field(default=None, primary_key=True)
    tradeid: str = Field(max_length=50, unique=True, index=True)
    orderid: str = Field(max_length=50, index=True)
    user_id: str = Field(max_length=50, index=True)
    symbol: str = Field(max_length=50, index=True)
    exchange: str = Field(max_length=20, index=True)
    action: str = Field(max_length=10)
    quantity: int
    price: Decimal = Field(sa_column=Column(DECIMAL(10, 2)))
    product: str = Field(max_length=20)
    strategy: Optional[str] = Field(default=None, max_length=100)
    trade_timestamp: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"nullable": False, "server_default": func.now()})

    __table_args__ = (
        Index('idx_user_symbol', 'user_id', 'symbol'),
        Index('idx_orderid', 'orderid'),
    )


class SandboxPositions(SQLModel, table=True):
    """Sandbox positions table - open positions"""
    __tablename__ = 'sandbox_positions'

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(max_length=50, index=True)
    symbol: str = Field(max_length=50, index=True)
    exchange: str = Field(max_length=20, index=True)
    product: str = Field(max_length=20)
    quantity: int
    average_price: Decimal = Field(sa_column=Column(DECIMAL(10, 2)))
    ltp: Optional[Decimal] = Field(default=None, sa_column=Column(DECIMAL(10, 2)))
    pnl: Decimal = Field(default=Decimal('0.00'), sa_column=Column(DECIMAL(10, 2)))
    pnl_percent: Decimal = Field(default=Decimal('0.0000'), sa_column=Column(DECIMAL(10, 4)))
    accumulated_realized_pnl: Decimal = Field(default=Decimal('0.00'), sa_column=Column(DECIMAL(10, 2)))
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"nullable": False, "server_default": func.now()})
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"nullable": False, "server_default": func.now(), "onupdate": func.now()})

    __table_args__ = (
        UniqueConstraint('user_id', 'symbol', 'exchange', 'product', name='unique_position'),
        Index('idx_user_product', 'user_id', 'product'),
    )


class SandboxHoldings(SQLModel, table=True):
    """Sandbox holdings table - T+1 settled CNC positions"""
    __tablename__ = 'sandbox_holdings'

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(max_length=50, index=True)
    symbol: str = Field(max_length=50, index=True)
    exchange: str = Field(max_length=20, index=True)
    quantity: int
    average_price: Decimal = Field(sa_column=Column(DECIMAL(10, 2)))
    ltp: Optional[Decimal] = Field(default=None, sa_column=Column(DECIMAL(10, 2)))
    pnl: Decimal = Field(default=Decimal('0.00'), sa_column=Column(DECIMAL(10, 2)))
    pnl_percent: Decimal = Field(default=Decimal('0.0000'), sa_column=Column(DECIMAL(10, 4)))
    settlement_date: date
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"nullable": False, "server_default": func.now()})
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"nullable": False, "server_default": func.now(), "onupdate": func.now()})

    __table_args__ = (
        UniqueConstraint('user_id', 'symbol', 'exchange', name='unique_holding'),
    )


class SandboxFunds(SQLModel, table=True):
    """Sandbox funds table - simulated capital and margin tracking"""
    __tablename__ = 'sandbox_funds'

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(max_length=50, unique=True, index=True)
    total_capital: Decimal = Field(default=Decimal('10000000.00'), sa_column=Column(DECIMAL(15, 2)))
    available_balance: Decimal = Field(default=Decimal('10000000.00'), sa_column=Column(DECIMAL(15, 2)))
    used_margin: Decimal = Field(default=Decimal('0.00'), sa_column=Column(DECIMAL(15, 2)))
    realized_pnl: Decimal = Field(default=Decimal('0.00'), sa_column=Column(DECIMAL(15, 2)))
    unrealized_pnl: Decimal = Field(default=Decimal('0.00'), sa_column=Column(DECIMAL(15, 2)))
    total_pnl: Decimal = Field(default=Decimal('0.00'), sa_column=Column(DECIMAL(15, 2)))
    last_reset_date: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"nullable": False, "server_default": func.now()})
    reset_count: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"nullable": False, "server_default": func.now()})
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"nullable": False, "server_default": func.now(), "onupdate": func.now()})


class SandboxConfig(SQLModel, table=True):
    """Sandbox configuration table - all configurable settings"""
    __tablename__ = 'sandbox_config'

    id: Optional[int] = Field(default=None, primary_key=True)
    config_key: str = Field(max_length=100, unique=True, index=True)
    config_value: str = Field(sa_column=Column(Text))
    description: Optional[str] = Field(default=None, sa_column=Column(Text))
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"nullable": False, "server_default": func.now(), "onupdate": func.now()})


def init_default_config(db: Session):
    """Initialize default sandbox configuration"""
    from sqlalchemy.exc import IntegrityError

    default_configs = [
        {'config_key': 'starting_capital', 'config_value': '10000000.00', 'description': 'Starting sandbox capital in INR (₹1 Crore) - Min: ₹1000'},
        {'config_key': 'reset_day', 'config_value': 'Sunday', 'description': 'Day of week for automatic fund reset'},
        {'config_key': 'reset_time', 'config_value': '00:00', 'description': 'Time for automatic fund reset (IST)'},
        {'config_key': 'order_check_interval', 'config_value': '5', 'description': 'Interval in seconds to check pending orders - Range: 1-30 seconds'},
        {'config_key': 'mtm_update_interval', 'config_value': '5', 'description': 'Interval in seconds to update MTM - Range: 0-60 seconds (0 = manual only)'},
        {'config_key': 'nse_bse_square_off_time', 'config_value': '15:15', 'description': 'Square-off time for NSE/BSE MIS positions (IST)'},
        {'config_key': 'cds_bcd_square_off_time', 'config_value': '16:45', 'description': 'Square-off time for CDS/BCD MIS positions (IST)'},
        {'config_key': 'mcx_square_off_time', 'config_value': '23:30', 'description': 'Square-off time for MCX MIS positions (IST)'},
        {'config_key': 'ncdex_square_off_time', 'config_value': '17:00', 'description': 'Square-off time for NCDEX MIS positions (IST)'},
        {'config_key': 'equity_mis_leverage', 'config_value': '5', 'description': 'Leverage multiplier for equity MIS (NSE/BSE) - Range: 1-50x'},
        {'config_key': 'equity_cnc_leverage', 'config_value': '1', 'description': 'Leverage multiplier for equity CNC (NSE/BSE) - Range: 1-50x'},
        {'config_key': 'futures_leverage', 'config_value': '10', 'description': 'Leverage multiplier for all futures (NFO/BFO/CDS/BCD/MCX/NCDEX) - Range: 1-50x'},
        {'config_key': 'option_buy_leverage', 'config_value': '1', 'description': 'Leverage for buying options (full premium) - Range: 1-50x'},
        {'config_key': 'option_sell_leverage', 'config_value': '1', 'description': 'Leverage for selling options (same as buying - full premium) - Range: 1-50x'},
        {'config_key': 'order_rate_limit', 'config_value': '10', 'description': 'Maximum orders per second - Range: 1-100 orders/sec (for future use)'},
        {'config_key': 'api_rate_limit', 'config_value': '50', 'description': 'Maximum API calls per second - Range: 1-1000 calls/sec (for future use)'},
        {'config_key': 'smart_order_rate_limit', 'config_value': '2', 'description': 'Maximum smart orders per second - Range: 1-50 orders/sec (for future use)'},
        {'config_key': 'smart_order_delay', 'config_value': '0.5', 'description': 'Delay between multi-leg smart orders - Range: 0.1-10 seconds (for future use)'}
    ]

    for config in default_configs:
        try:
            existing = db.exec(select(SandboxConfig).where(SandboxConfig.config_key == config['config_key'])).first()
            if not existing:
                config_obj = SandboxConfig(**config)
                db.add(config_obj)
                db.commit()
                logger.info(f"Added default config: {config['config_key']}")
        except IntegrityError:
            db.rollback()
            logger.debug(f"Config already exists: {config['config_key']}")
        except Exception as e:
            db.rollback()
            logger.error(f"Error adding config {config['config_key']}: {e}")


def get_config(db: Session, config_key: str, default: Optional[Any] = None) -> Optional[str]:
    """Get configuration value by key"""
    try:
        config = db.exec(select(SandboxConfig).where(SandboxConfig.config_key == config_key)).first()
        if config:
            return config.config_value
        return default
    except Exception as e:
        logger.error(f"Error fetching config {config_key}: {e}")
        return default


def set_config(db: Session, config_key: str, config_value: str, description: Optional[str] = None) -> bool:
    """Set configuration value"""
    try:
        config = db.exec(select(SandboxConfig).where(SandboxConfig.config_key == config_key)).first()
        if config:
            config.config_value = str(config_value)
            if description:
                config.description = description
            db.add(config)
        else:
            config = SandboxConfig(
                config_key=config_key,
                config_value=str(config_value),
                description=description
            )
            db.add(config)
        db.commit()
        db.refresh(config)
        logger.info(f"Updated config: {config_key} = {config_value}")
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"Error setting config {config_key}: {e}")
        return False


def get_all_configs(db: Session) -> Dict[str, Dict[str, str]]:
    """Get all configuration values"""
    try:
        configs = db.exec(select(SandboxConfig)).all()
        return {config.config_key: {
            'value': config.config_value,
            'description': config.description
        } for config in configs}
    except Exception as e:
        logger.error(f"Error fetching all configs: {e}")
        return {}
