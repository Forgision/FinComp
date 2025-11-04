from pydantic_settings import BaseSettings
from pydantic import Field, validator, AnyHttpUrl
from typing import List, Optional
import re

class Settings(BaseSettings):
    # Core App Settings
    APP_KEY: str
    DATABASE_URL: str
    API_KEY_PEPPER: str
    ENV_CONFIG_VERSION: str
    FLASK_ENV: str = Field("production", alias="FLASK_ENV")

    # Server Settings
    HOST_SERVER: str = "http://127.0.0.1:5000"
    FLASK_HOST_IP: str = Field("127.0.0.1", alias="FLASK_HOST_IP")
    FLASK_PORT: int = Field(5000, alias="FLASK_PORT")
    FLASK_DEBUG: bool = Field(False, alias="FLASK_DEBUG")

    # Broker Settings
    BROKER_API_KEY: str
    BROKER_API_SECRET: str
    VALID_BROKERS: str
    REDIRECT_URL: str

    # Rate Limiting
    LOGIN_RATE_LIMIT_MIN: str = "5 per minute"
    LOGIN_RATE_LIMIT_HOUR: str = "25 per hour"
    API_RATE_LIMIT: str = "10 per second"
    ORDER_RATE_LIMIT: str = "10 per second"
    SMART_ORDER_RATE_LIMIT: str = "10 per second"
    WEBHOOK_RATE_LIMIT: str = "10 per second"
    STRATEGY_RATE_LIMIT: str = "10 per second"

    # Trading Settings
    SMART_ORDER_DELAY: float = 0.5

    # Session and Security
    SESSION_EXPIRY_TIME: str = "03:30"
    SESSION_COOKIE_NAME: str = "session"
    CSRF_ENABLED: bool = True
    CSRF_COOKIE_NAME: str = "csrf_token"
    CSRF_TIME_LIMIT: Optional[int] = None

    # WebSocket Settings
    WEBSOCKET_HOST: str = "127.0.0.1"
    WEBSOCKET_PORT: int = 8765
    WEBSOCKET_URL: str = "ws://localhost:8765"

    # Logging Settings
    LOG_TO_FILE: bool = False
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "log"
    LOG_FORMAT: str = "[%(asctime)s] %(levelname)s in %(module)s: %(message)s"
    LOG_RETENTION: int = 14

    # Development tools
    NGROK_ALLOW: bool = False

    @validator('FLASK_ENV')
    def validate_flask_env(cls, v):
        if v.lower() not in ['development', 'production']:
            raise ValueError("FLASK_ENV must be 'development' or 'production'")
        return v

    @validator('REDIRECT_URL')
    def validate_redirect_url(cls, v, values):
        if '<broker>' in v:
            raise ValueError("REDIRECT_URL must not contain '<broker>'")

        valid_brokers_str = values.get('VALID_BROKERS', '')
        valid_brokers = set(b.strip().lower() for b in valid_brokers_str.split(','))

        match = re.search(r'/([^/]+)/callback$', v)
        if not match:
            raise ValueError("Invalid REDIRECT_URL format. Must end in '/<broker>/callback'")

        broker_name = match.group(1).lower()
        if broker_name not in valid_brokers:
            raise ValueError(f"Broker '{broker_name}' in REDIRECT_URL is not in VALID_BROKERS")

        return v

    @validator('LOGIN_RATE_LIMIT_MIN', 'LOGIN_RATE_LIMIT_HOUR', 'API_RATE_LIMIT', 'ORDER_RATE_LIMIT', 'SMART_ORDER_RATE_LIMIT', 'WEBHOOK_RATE_LIMIT', 'STRATEGY_RATE_LIMIT')
    def validate_rate_limit_format(cls, v):
        if not re.match(r'^\d+\s+per\s+(second|minute|hour|day)$', v):
            raise ValueError("Rate limit format must be 'number per timeunit'")
        return v

    @validator('SESSION_EXPIRY_TIME')
    def validate_session_expiry_time(cls, v):
        if not re.match(r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$', v):
            raise ValueError("SESSION_EXPIRY_TIME format must be HH:MM")
        return v

    @validator('WEBSOCKET_URL')
    def validate_websocket_url(cls, v):
        if not v.startswith(('ws://', 'wss://')):
            raise ValueError("WEBSOCKET_URL must start with 'ws://' or 'wss://'")
        return v

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'

# Create a single settings instance to be used throughout the application
settings = Settings()
