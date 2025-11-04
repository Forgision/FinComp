from pydantic import BaseModel, Field, validator
from enum import Enum
from typing import List, Optional

# --- Enums for Validation ---
class Action(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

class PriceType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    SL = "SL"
    SL_M = "SL-M"

class ProductType(str, Enum):
    MIS = "MIS"
    NRML = "NRML"
    CNC = "CNC"

# --- Account Schemas ---
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
    product: ProductType

class AnalyzerSchema(BaseModel):
    apikey: str

class AnalyzerToggleSchema(BaseModel):
    apikey: str
    mode: bool

class PingSchema(BaseModel):
    apikey: str

# --- Order Schemas ---
class PlaceOrderPayload(BaseModel):
    strategy: str
    exchange: str
    symbol: str
    action: Action
    quantity: int = Field(..., gt=0)
    pricetype: PriceType = PriceType.MARKET
    product: ProductType = ProductType.MIS
    price: float = Field(0.0, ge=0)
    trigger_price: float = Field(0.0, ge=0)
    disclosed_quantity: int = Field(0, ge=0)

    @validator('action', pre=True, allow_reuse=True)
    def action_to_uppercase(cls, v):
        return v.upper()

    @validator('trigger_price')
    def trigger_price_required_for_sl(cls, v, values):
        if 'pricetype' in values and values['pricetype'] in (PriceType.SL, PriceType.SL_M) and v <= 0:
            raise ValueError("A trigger_price > 0 is required for SL and SL-M orders.")
        return v

class PlaceOrderSchema(BaseModel):
    apikey: str
    strategy: str
    exchange: str
    symbol: str
    action: Action
    quantity: int = Field(..., gt=0)
    pricetype: PriceType = PriceType.MARKET
    product: ProductType = ProductType.MIS
    price: float = Field(0.0, ge=0)
    trigger_price: float = Field(0.0, ge=0)
    disclosed_quantity: int = Field(0, ge=0)

    @validator('action', pre=True, allow_reuse=True)
    def action_to_uppercase(cls, v):
        return v.upper()

    @validator('trigger_price')
    def trigger_price_required_for_sl(cls, v, values):
        if 'pricetype' in values and values['pricetype'] in (PriceType.SL, PriceType.SL_M) and v <= 0:
            raise ValueError("A trigger_price > 0 is required for SL and SL-M orders.")
        return v

class SmartOrderSchema(PlaceOrderSchema):
    position_size: int

class ModifyOrderSchema(BaseModel):
    apikey: str
    strategy: str
    exchange: str
    symbol: str
    orderid: str
    action: Action
    product: ProductType
    pricetype: PriceType
    price: float = Field(..., ge=0)
    quantity: int = Field(..., gt=0)
    disclosed_quantity: int = Field(..., ge=0)
    trigger_price: float = Field(..., ge=0)

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
    action: Action
    quantity: int = Field(..., gt=0)
    pricetype: PriceType = PriceType.MARKET
    product: ProductType = ProductType.MIS
    price: float = Field(0.0, ge=0)
    trigger_price: float = Field(0.0, ge=0)
    disclosed_quantity: int = Field(0, ge=0)

class BasketOrderSchema(BaseModel):
    apikey: str
    strategy: str
    orders: List[BasketOrderItemSchema]

class SplitOrderSchema(PlaceOrderSchema):
    splitsize: int = Field(..., gt=0)

class OptionsOrderSchema(BaseModel):
    apikey: str
    strategy: str
    underlying: str
    exchange: str
    expiry_date: Optional[str] = None
    strike_int: int = Field(..., gt=0)
    offset: str
    option_type: str
    action: Action
    quantity: int = Field(..., gt=0)
    pricetype: PriceType = PriceType.MARKET
    product: ProductType
    price: float = Field(0.0, ge=0)
    trigger_price: float = Field(0.0, ge=0)
    disclosed_quantity: int = Field(0, ge=0)

    @validator('option_type', pre=True, allow_reuse=True)
    def option_type_to_uppercase(cls, v):
        if v.upper() not in ["CE", "PE"]:
            raise ValueError("option_type must be 'CE' or 'PE'")
        return v.upper()

# - - - Order Schemas - - -
from marshmallow import Schema, fields, validate
class OrderSchema(Schema):
    apikey = fields.Str(required=True)
    strategy = fields.Str(required=True)
    exchange = fields.Str(required=True)
    symbol = fields.Str(required=True)
    action = fields.Str(required=True, validate=validate.OneOf(["BUY", "SELL", "buy", "sell"]))
    quantity = fields.Int(required=True, validate=validate.Range(min=1, error="Quantity must be a positive integer."))
    pricetype = fields.Str(missing='MARKET', validate=validate.OneOf(["MARKET", "LIMIT", "SL", "SL-M"]))
    product = fields.Str(missing='MIS', validate=validate.OneOf(["MIS", "NRML", "CNC"]))
    price = fields.Float(missing=0.0, validate=validate.Range(min=0, error="Price must be a non-negative number."))
    trigger_price = fields.Float(missing=0.0, validate=validate.Range(min=0, error="Trigger price must be a non-negative number."))
    disclosed_quantity = fields.Int(missing=0, validate=validate.Range(min=0, error="Disclosed quantity must be a non-negative integer."))

# --- Order Schemas ---
class PlaceOrderSchema(BaseModel):
    apikey: str
    strategy: str
    exchange: str
    symbol: str
    action: Action
    quantity: int = Field(..., gt=0)
    pricetype: PriceType = PriceType.MARKET
    product: ProductType = ProductType.MIS
    price: float = Field(0.0, ge=0)
    trigger_price: float = Field(0.0, ge=0)
    disclosed_quantity: int = Field(0, ge=0)

    @validator('action', pre=True, allow_reuse=True)
    def action_to_uppercase(cls, v):
        return v.upper()

    @validator('trigger_price')
    def trigger_price_required_for_sl(cls, v, values):
        if 'pricetype' in values and values['pricetype'] in (PriceType.SL, PriceType.SL_M) and v <= 0:
            raise ValueError("A trigger_price > 0 is required for SL and SL-M orders.")
        return v

class SmartOrderSchema(PlaceOrderSchema):
    position_size: int

class ModifyOrderSchema(BaseModel):
    apikey: str
    strategy: str
    exchange: str
    symbol: str
    orderid: str
    action: Action
    product: ProductType
    pricetype: PriceType
    price: float = Field(..., ge=0)
    quantity: int = Field(..., gt=0)
    disclosed_quantity: int = Field(..., ge=0)
    trigger_price: float = Field(..., ge=0)

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
    action: Action
    quantity: int = Field(..., gt=0)
    pricetype: PriceType = PriceType.MARKET
    product: ProductType = ProductType.MIS
    price: float = Field(0.0, ge=0)
    trigger_price: float = Field(0.0, ge=0)
    disclosed_quantity: int = Field(0, ge=0)

class BasketOrderSchema(BaseModel):
    apikey: str
    strategy: str
    orders: List[BasketOrderItemSchema]

class SplitOrderSchema(PlaceOrderSchema):
    splitsize: int = Field(..., gt=0)

class OptionsOrderSchema(BaseModel):
    apikey: str
    strategy: str
    underlying: str
    exchange: str
    expiry_date: Optional[str] = None
    strike_int: int = Field(..., gt=0)
    offset: str
    option_type: str
    action: Action
    quantity: int = Field(..., gt=0)
    pricetype: PriceType = PriceType.MARKET
    product: ProductType
    price: float = Field(0.0, ge=0)
    trigger_price: float = Field(0.0, ge=0)
    disclosed_quantity: int = Field(0, ge=0)

    @validator('option_type', pre=True, allow_reuse=True)
    def option_type_to_uppercase(cls, v):
        if v.upper() not in ["CE", "PE"]:
            raise ValueError("option_type must be 'CE' or 'PE'")
        return v.upper()

# - - - Order Schemas - - -
from marshmallow import Schema, fields, validate
class OrderSchema(Schema):
    apikey = fields.Str(required=True)
    strategy = fields.Str(required=True)
    exchange = fields.Str(required=True)
    symbol = fields.Str(required=True)
    action = fields.Str(required=True, validate=validate.OneOf(["BUY", "SELL", "buy", "sell"]))
    quantity = fields.Int(required=True, validate=validate.Range(min=1, error="Quantity must be a positive integer."))
    pricetype = fields.Str(missing='MARKET', validate=validate.OneOf(["MARKET", "LIMIT", "SL", "SL-M"]))
    product = fields.Str(missing='MIS', validate=validate.OneOf(["MIS", "NRML", "CNC"]))
    price = fields.Float(missing=0.0, validate=validate.Range(min=0, error="Price must be a non-negative number."))
    trigger_price = fields.Float(missing=0.0, validate=validate.Range(min=0, error="Trigger price must be a non-negative number."))
    disclosed_quantity = fields.Int(missing=0, validate=validate.Range(min=0, error="Disclosed quantity must be a non-negative integer."))
