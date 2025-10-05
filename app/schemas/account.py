from pydantic import BaseModel, Field
from typing import Literal

class APIKeySchema(BaseModel):
    apikey: str

class OrderStatusSchema(APIKeySchema):
    strategy: str
    orderid: str

class OpenPositionSchema(APIKeySchema):
    strategy: str
    symbol: str
    exchange: str
    product: Literal["MIS", "NRML", "CNC"]

class AnalyzerToggleSchema(APIKeySchema):
    mode: bool
    enabled: bool = Field(...)

class HoldingsSchema(APIKeySchema):
    pass

class OrderbookSchema(APIKeySchema):
    pass

class PositionbookSchema(APIKeySchema):
    pass

class FundsSchema(APIKeySchema):
    pass

class IntervalsSchema(APIKeySchema):
    pass

class AnalyzerSchema(APIKeySchema):
    pass


class PingSchema(APIKeySchema):
    pass
