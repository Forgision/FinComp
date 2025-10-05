from pydantic_settings import BaseSettings, SettingsConfigDict
import os

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    # Broker Configuration
    BROKER_API_KEY: str = "YOUR_BROKER_API_KEY"
    BROKER_API_SECRET: str = "YOUR_BROKER_API_SECRET"
    BROKER_API_KEY_MARKET: str = "YOUR_BROKER_MARKET_API_KEY"
    BROKER_API_SECRET_MARKET: str = "YOUR_BROKER_MARKET_API_SECRET"
    REDIRECT_URL: str = "http://127.0.0.1:5000/<broker>/callback"
    VALID_BROKERS: str = "fivepaisa,fivepaisaxts,aliceblue,angel,compositedge,dhan,dhan_sandbox,definedge,firstock,flattrade,fyers,groww,ibulls,iifl,indmoney,kotak,paytm,pocketful,shoonya,tradejini,upstox,wisdom,zebu,zerodha"

    # Security Configuration
    APP_KEY: str = "3daa0403ce2501ee7432b75bf100048e3cf510d63d2754f952e93d88bf07ea84"
    API_KEY_PEPPER: str = "a25d94718479b170c16278e321ea6c989358bf499a658fd20c90033cef8ce772"

    # Database Configuration
    DATABASE_URL: str = "sqlite:///db/openalgo.db"
    LATENCY_DATABASE_URL: str = "sqlite:///db/latency.db"
    LOGS_DATABASE_URL: str = "sqlite:///db/logs.db"
    SANDBOX_DATABASE_URL: str = "sqlite:///db/sandbox.db"

    # Ngrok Configuration
    NGROK_ALLOW: str = "FALSE"
    HOST_SERVER: str = "http://127.0.0.1:5000"

    # Flask/FastAPI Host and Port Configuration
    APP_HOST_IP: str = "127.0.0.1"
    APP_PORT: int = 5000
    APP_DEBUG: bool = False
    APP_ENV: str = "development"

    # WebSocket Configuration
    WEBSOCKET_HOST: str = "127.0.0.1"
    WEBSOCKET_PORT: int = 8765
    WEBSOCKET_URL: str = "ws://127.0.0.1:8765"

    # ZeroMQ Configuration
    ZMQ_HOST: str = "127.0.0.1"
    ZMQ_PORT: int = 5555

    # Logging configuration
    LOG_TO_FILE: bool = False
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "log"
    LOG_FORMAT: str = "[%(asctime)s] %(levelname)s in %(module)s: %(message)s"
    LOG_RETENTION: str = "14"
    LOG_COLORS: bool = True
    FORCE_COLOR: int = 1

    # Rate Limit Settings
    LOGIN_RATE_LIMIT_MIN: str = "5 per minute"
    LOGIN_RATE_LIMIT_HOUR: str = "25 per hour"
    RESET_RATE_LIMIT: str = "15 per hour"
    API_RATE_LIMIT: str = "50 per second"
    ORDER_RATE_LIMIT: str = "10 per second"
    SMART_ORDER_RATE_LIMIT: str = "2 per second"
    WEBHOOK_RATE_LIMIT: str = "100 per minute"
    STRATEGY_RATE_LIMIT: str = "200 per minute"

    # API Configuration
    SMART_ORDER_DELAY: float = 0.5
    SESSION_EXPIRY_TIME: str = "03:00"

    # CORS Configuration
    CORS_ENABLED: bool = True
    CORS_ALLOWED_ORIGINS: str = "http://127.0.0.1:5000"
    CORS_ALLOWED_METHODS: str = "GET,POST,DELETE,PUT,PATCH"
    CORS_ALLOWED_HEADERS: str = "Content-Type,Authorization,X-Requested-With"
    CORS_EXPOSED_HEADERS: str = ""
    CORS_ALLOW_CREDENTIALS: bool = False
    CORS_MAX_AGE: int = 86400

    # CSP Configuration
    CSP_ENABLED: bool = True
    CSP_REPORT_ONLY: bool = False
    CSP_DEFAULT_SRC: str = "'self'"
    CSP_SCRIPT_SRC: str = "'self' 'unsafe-inline' https://cdn.socket.io https://static.cloudflareinsights.com"
    CSP_STYLE_SRC: str = "'self' 'unsafe-inline'"
    CSP_IMG_SRC: str = "'self' data:"
    CSP_CONNECT_SRC: str = "'self' wss: ws: https://cdn.socket.io"
    CSP_FONT_SRC: str = "'self'"
    CSP_OBJECT_SRC: str = "'none'"
    CSP_MEDIA_SRC: str = "'self' data: https://*.amazonaws.com https://*.cloudfront.net"
    CSP_FRAME_SRC: str = "'self'"
    CSP_FORM_ACTION: str = "'self'"
    CSP_FRAME_ANCESTORS: str = "'self'"
    CSP_BASE_URI: str = "'self'"
    CSP_UPGRADE_INSECURE_REQUESTS: bool = False
    CSP_REPORT_URI: str = ""

    # CSRF Configuration
    CSRF_ENABLED: bool = True
    CSRF_TIME_LIMIT: int = 3600 # Example: 1 hour, or None for no limit
    SESSION_COOKIE_NAME: str = "session"
    CSRF_COOKIE_NAME: str = "csrf_token"


settings = Settings()

