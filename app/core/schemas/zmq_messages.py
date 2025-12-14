from typing import Any, Dict, Literal, Optional, Union
from pydantic import BaseModel, Field
import time


class MessageEnvelope(BaseModel):
    type: str  # e.g., md.update, orders.signal, orders.exec_report
    schema_version: int = 1
    correlation_id: str
    topic: str
    seq: int
    ts: float = Field(default_factory=time.time)
    source: str
    payload: Dict[str, Any]


class Signal(BaseModel):
    strategy_id: str
    symbol: str
    entry_price: float
    stop_loss: float
    target_price: float
    timestamp: int
    signal_type: Literal["BUY", "SELL"]


class OrderRequest(Signal):
    quantity: int
    estimated_pnl: float
    validity: Literal["DAY", "IOC"]
    order_type: Literal["MARKET", "LIMIT"]


class ControlMessage(BaseModel):
    request_id: str
    command: str
    payload: Dict[str, Any]


class ExecutionReport(BaseModel):
    order_id: str
    strategy_id: Optional[str] = None
    symbol: str
    side: Literal["BUY", "SELL"]
    status: Literal["PLACED", "PARTIAL", "FILLED", "CANCELLED", "REJECTED"]
    filled_qty: int
    avg_fill_price: Optional[float] = None
    reason: Optional[str] = None
    ts: float = Field(default_factory=time.time)


class MarketData(BaseModel):
    symbol: str
    exchange: str
    ltp: float
    change: float
    percent_change: float
    open: float
    high: float
    low: float
    close: float
    volume: int
    timestamp: float
