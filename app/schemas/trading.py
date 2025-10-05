from pydantic import BaseModel, Field
from typing import List, Literal, Optional

class OrderBase(BaseModel):
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

class OrderSchema(OrderBase):
    pass

class SmartOrderSchema(OrderBase):
    position_size: int

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
    quantity: int = Field(..., gt=0, description="Total quantity must be a positive integer.")
    splitsize: int = Field(..., gt=0, description="Split size must be a positive integer.")
    pricetype: Literal["MARKET", "LIMIT", "SL", "SL-M"] = "MARKET"
    product: Literal["MIS", "NRML", "CNC"] = "MIS"
    price: float = Field(0.0, ge=0, description="Price must be a non-negative number.")
    trigger_price: float = Field(0.0, ge=0, description="Trigger price must be a non-negative number.")
    disclosed_quantity: int = Field(0, ge=0, description="Disclosed quantity must be a non-negative integer.")

class DepthSchema(BaseModel):
    apikey: str
    symbol: str
    exchange: str
    class Config:
        json_schema_extra = {
            "example": {
                "apikey": "your_api_key",
                "symbol": "NIFTY",
                "exchange": "NSE"
            }
        }

class QuotesSchema(BaseModel):
    apikey: str
    symbol: str
    exchange: str
    class Config:
        json_schema_extra = {
            "example": {
                "apikey": "your_api_key",
                "symbol": "NIFTY",
                "exchange": "NSE"
            }
        }

class HistorySchema(BaseModel):
    apikey: str
    symbol: str
    exchange: str
    interval: str
    start_date: str
    end_date: str
    class Config:
        json_schema_extra = {
            "example": {
                "apikey": "your_api_key",
                "symbol": "NIFTY",
                "exchange": "NSE",
                "interval": "5minute",
                "start_date": "2023-01-01",
                "end_date": "2023-01-02"
            }
        }

class SymbolSchema(BaseModel):
    apikey: str
    symbol: str
    exchange: str
    class Config:
        json_schema_extra = {
            "example": {
                "apikey": "your_api_key",
                "symbol": "NIFTY",
                "exchange": "NSE"
            }
        }

class SearchSchema(BaseModel):
    apikey: str
    query: str
    exchange: Optional[str] = None
    class Config:
        json_schema_extra = {
            "example": {
                "apikey": "your_api_key",
                "query": "NIFTY",
                "exchange": "NSE"
            }
        }