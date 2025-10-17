from pydantic import BaseModel, Field, ValidationError, field_validator
from typing import List, Literal, Optional, Union
import re
from datetime import date

# Custom validator for date or timestamp string
def validate_date_or_timestamp_str(data: str) -> str:
    """
    Validates that the input string is either in 'YYYY-MM-DD' format or a numeric timestamp.
    """
    date_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}$')
    timestamp_pattern = re.compile(r'^\d{10,13}$') # Allows for seconds or milliseconds
    if not (isinstance(data, str) and (date_pattern.match(data) or timestamp_pattern.match(data))):
        raise ValueError("Field must be a string in 'YYYY-MM-DD' format or a numeric timestamp.")
    return data

# From .garbage/restx_api/schemas.py
class OrderSchema(BaseModel):
    apikey: str
    strategy: str
    exchange: str
    symbol: str
    action: Literal["BUY", "SELL", "buy", "sell"]
    quantity: int = Field(..., gt=0, description="Quantity must be a positive integer.")
    pricetype: Literal["MARKET", "LIMIT", "SL", "SL-M"] = "MARKET"
    product: Literal["MIS", "NRML", "CNC"] = "MIS"
    price: float = Field(0.0, ge=0, description="Price must be a non-negative number.")
    trigger_price: float = Field(0.0, ge=0, description="Trigger price must be a non-negative number.")
    disclosed_quantity: int = Field(0, ge=0, description="Disclosed quantity must be a non-negative integer.")

class SmartOrderSchema(BaseModel):
    apikey: str
    strategy: str
    exchange: str
    symbol: str
    action: Literal["BUY", "SELL", "buy", "sell"]
    quantity: int = Field(..., ge=0, description="Quantity must be a non-negative integer.")
    position_size: int
    pricetype: Literal["MARKET", "LIMIT", "SL", "SL-M"] = "MARKET"
    product: Literal["MIS", "NRML", "CNC"] = "MIS"
    price: float = Field(0.0, ge=0, description="Price must be a non-negative number.")
    trigger_price: float = Field(0.0, ge=0, description="Trigger price must be a non-negative number.")
    disclosed_quantity: int = Field(0, ge=0, description="Disclosed quantity must be a non-negative integer.")

class ModifyOrderSchema(BaseModel):
    apikey: str
    strategy: str
    exchange: str
    symbol: str
    orderid: str
    action: Literal["BUY", "SELL", "buy", "sell"]
    product: Literal["MIS", "NRML", "CNC"]
    pricetype: Literal["MARKET", "LIMIT", "SL", "SL-M"]
    price: float = Field(..., ge=0, description="Price must be a non-negative number.")
    quantity: int = Field(..., gt=0, description="Quantity must be a positive integer.")
    disclosed_quantity: int = Field(..., ge=0, description="Disclosed quantity must be a non-negative integer.")
    trigger_price: float = Field(..., ge=0, description="Trigger price must be a non-negative number.")

class CancelOrderSchema(BaseModel):
    apikey: str
    strategy: str
    orderid: str

class ClosePositionSchema(BaseModel):
    apikey: str
    strategy: str

class CancelAllOrderSchema(BaseModel):
    apikey: str
    strategy: str

class BasketOrderItemSchema(BaseModel):
    exchange: str
    symbol: str
    action: Literal["BUY", "SELL", "buy", "sell"]
    quantity: int = Field(..., gt=0, description="Quantity must be a positive integer.")
    pricetype: Literal["MARKET", "LIMIT", "SL", "SL-M"] = "MARKET"
    product: Literal["MIS", "NRML", "CNC"] = "MIS"
    price: float = Field(0.0, ge=0, description="Price must be a non-negative number.")
    trigger_price: float = Field(0.0, ge=0, description="Trigger price must be a non-negative number.")
    disclosed_quantity: int = Field(0, ge=0, description="Disclosed quantity must be a non-negative integer.")

class BasketOrderSchema(BaseModel):
    apikey: str
    strategy: str
    orders: List[BasketOrderItemSchema]

class SplitOrderSchema(BaseModel):
    apikey: str
    strategy: str
    exchange: str
    symbol: str
    action: Literal["BUY", "SELL", "buy", "sell"]
    quantity: int = Field(..., gt=0, description="Total quantity to split must be a positive integer.")
    splitsize: int = Field(..., gt=0, description="Split size must be a positive integer.")
    pricetype: Literal["MARKET", "LIMIT", "SL", "SL-M"] = "MARKET"
    product: Literal["MIS", "NRML", "CNC"] = "MIS"
    price: float = Field(0.0, ge=0, description="Price must be a non-negative number.")
    trigger_price: float = Field(0.0, ge=0, description="Trigger price must be a non-negative number.")
    disclosed_quantity: int = Field(0, ge=0, description="Disclosed quantity must be a non-negative integer.")


# From .garbage/restx_api/account_schema.py
class FundsSchema(BaseModel):
    apikey: str

class OrderbookSchema(BaseModel):
    apikey: str

class TradebookSchema(BaseModel):
    apikey: str

class PositionbookSchema(BaseModel):
    apikey: str

class HoldingsSchema(BaseModel):
    apikey: str

class OrderStatusSchema(BaseModel):
    apikey: str
    strategy: str
    orderid: str

class OpenPositionSchema(BaseModel):
    apikey: str
    strategy: str
    symbol: str
    exchange: str
    product: Literal["MIS", "NRML", "CNC"]

class AnalyzerSchema(BaseModel):
    apikey: str

class AnalyzerToggleSchema(BaseModel):
    apikey: str
    mode: bool

class PingSchema(BaseModel):
    apikey: str

# From .garbage/restx_api/data_schemas.py
class QuotesSchema(BaseModel):
    apikey: str
    symbol: str
    exchange: str

class HistorySchema(BaseModel):
    apikey: str
    symbol: str
    exchange: str
    interval: Literal["1m", "5m", "15m", "30m", "1h", "D"]
    start_date: date
    end_date: date

class DepthSchema(BaseModel):
    apikey: str
    symbol: str
    exchange: str

class IntervalsSchema(BaseModel):
    apikey: str

class SymbolSchema(BaseModel):
    apikey: str
    symbol: str
    exchange: str

class TickerSchema(BaseModel):
    apikey: str
    symbol: str
    interval: Literal["1m", "5m", "15m", "30m", "1h", "4h", "D", "W", "M"]
    from_: str = Field(..., alias="from") # Use alias for 'from' keyword
    to: str
    adjusted: Optional[bool] = True
    sort: Literal["asc", "desc"] = "asc"

    @field_validator('from_', 'to')
    @classmethod
    def validate_date_or_timestamp_fields(cls, v: str) -> str:
        return validate_date_or_timestamp_str(v)

class SearchSchema(BaseModel):
    apikey: str
    query: str
    exchange: Optional[str] = None

class ExpirySchema(BaseModel):
    apikey: str
    symbol: str
    exchange: Literal["NFO", "BFO", "MCX", "CDS"]
    instrumenttype: Literal["futures", "options"]