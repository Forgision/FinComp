from typing import List
from pydantic import BaseModel


class OrderData(BaseModel):
    symbol: str = ""
    exchange: str = ""
    action: str = ""
    quantity: float = 0.0
    price: float = 0.0
    trigger_price: float = 0.0
    pricetype: str = ""
    product: str = ""
    orderid: str = ""
    order_status: str = ""
    timestamp: str = ""


class OrderStatistics(BaseModel):
    total_orders: int = 0
    completed_orders: int = 0
    open_orders: int = 0
    rejected_orders: int = 0
    total_buy_value: float = 0.0
    total_sell_value: float = 0.0
    net_value: float = 0.0


class OrderbookResponse(BaseModel):
    order_data: List[OrderData]
    order_stats: OrderStatistics
