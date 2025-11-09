from pydantic import BaseModel, Field, StrictStr


class TradingViewRequest(BaseModel):
    """Represents a request for TradingView data."""

    symbol: StrictStr = Field(
        ..., min_length=1, max_length=50, description="Trading symbol, e.g., 'AAPL'."
    )
    exchange: StrictStr = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Exchange where the symbol is traded, e.g., 'NASDAQ'.",
    )
    product: StrictStr = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Product type, e.g., 'equity', 'futures'.",
    )

    class Config:
        schema_extra = {
            "example": {
                "symbol": "GOOGL",
                "exchange": "NASDAQ",
                "product": "equity",
            }
        }
