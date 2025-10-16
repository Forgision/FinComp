from pydantic import BaseModel

class TradingViewRequest(BaseModel):
    symbol: str
    exchange: str
    product: str