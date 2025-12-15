from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic import BaseModel


class AuthConfig(BaseModel):
    """
    Base configuration for broker authentication.
    Brokers can extend this or use optional fields.
    """

    userid: Optional[str] = None
    password: Optional[str] = None
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    totp: Optional[str] = None
    vendor_code: Optional[str] = None
    imei: Optional[str] = None
    auth_code: Optional[str] = None

    class Config:
        extra = "allow"


class BaseBrokerAuth(ABC):
    """
    Abstract base class for Broker Authentication.
    Consumer: Web Server Service
    """

    @abstractmethod
    async def authenticate(self, config: AuthConfig) -> str:
        """
        Authenticate with the broker and return an auth token (or session id).
        """
        pass


class BaseBrokerAccount(ABC):
    """
    Abstract base class for Broker Account operations (Orders, Positions, Holdings).
    Consumer: Execution Engine Service
    """

    @abstractmethod
    async def place_order(
        self, order_data: Dict[str, Any], auth_token: str
    ) -> Dict[str, Any]:
        """Place an order."""
        pass

    @abstractmethod
    async def cancel_order(self, order_id: str, auth_token: str) -> Dict[str, Any]:
        """Cancel an order."""
        pass

    @abstractmethod
    async def modify_order(
        self, order_id: str, new_data: Dict[str, Any], auth_token: str
    ) -> Dict[str, Any]:
        """Modify an order."""
        pass

    @abstractmethod
    async def get_order_book(self, auth_token: str) -> Dict[str, Any]:
        """Get order book."""
        pass

    @abstractmethod
    async def get_trade_book(self, auth_token: str) -> Dict[str, Any]:
        """Get trade book."""
        pass

    @abstractmethod
    async def get_positions(self, auth_token: str) -> Dict[str, Any]:
        """Get positions."""
        pass

    @abstractmethod
    async def get_holdings(self, auth_token: str) -> Dict[str, Any]:
        """Get holdings."""
        pass

    @abstractmethod
    async def get_funds(self, auth_token: str) -> Dict[str, Any]:
        """Get funds and margin details."""
        pass


class BaseBrokerData(ABC):
    """
    Abstract base class for Broker Data operations (Quotes, History, Depth).
    Consumer: Data Engine Service
    """

    def __init__(self, auth_token: str):
        self.auth_token = auth_token

    @abstractmethod
    async def get_quotes(self, symbol: str, exchange: str) -> Dict[str, Any]:
        """Get real-time quotes."""
        pass

    @abstractmethod
    async def get_history(
        self, symbol: str, exchange: str, interval: str, start_date: str, end_date: str
    ) -> Any:
        """Get historical data (Pandas DataFrame usually)."""
        pass

    @abstractmethod
    async def get_depth(self, symbol: str, exchange: str) -> Dict[str, Any]:
        """Get market depth."""
        pass
