from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

class APIKeySchema(BaseModel):
    apikey: str

class BotConfigSchema(APIKeySchema):
    token: Optional[str] = None
    webhook_url: Optional[str] = None
    polling_mode: Optional[bool] = None
    broadcast_enabled: Optional[bool] = None
    rate_limit_per_minute: Optional[int] = None

class StartStopBotSchema(APIKeySchema):
    pass

class BroadcastSchema(APIKeySchema):
    message: str
    filters: Optional[Dict[str, Any]] = {}

class NotificationSchema(APIKeySchema):
    username: str
    message: str
    priority: int = Field(5, ge=1, le=10)

class PreferencesSchema(APIKeySchema):
    telegram_id: int
    order_notifications: Optional[bool] = None
    trade_notifications: Optional[bool] = None
    pnl_notifications: Optional[bool] = None
    daily_summary: Optional[bool] = None
    summary_time: Optional[str] = None
    language: Optional[str] = None
    timezone: Optional[str] = None

class UserLinkSchema(APIKeySchema):
    telegram_id: int
    username: str

class StatsSchema(APIKeySchema):
    days: int = Field(7, gt=0)