from pydantic_settings import BaseSettings, SettingsConfigDict
import os

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_KEY: str = "super-secret-key"
    DATABASE_URL: str = "sqlite:///./sql_app.db"
    HOST_SERVER: str = "http://127.0.0.1:5000"
    USE_HTTPS: bool = False
    SESSION_COOKIE_NAME: str = "session"
    CSRF_ENABLED: bool = True
    CSRF_COOKIE_NAME: str = "csrf_token"
    CSRF_TIME_LIMIT: int | None = None
    FLASK_HOST_IP: str = "127.0.0.1"
    FLASK_PORT: int = 5000
    FLASK_DEBUG: bool = False
    NGROK_ALLOW: bool = False
    APP_MODE: str = "local" # or "standalone" for docker

    # Dynamic cookie security configuration based on HOST_SERVER
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.USE_HTTPS = self.HOST_SERVER.startswith('https://')
        if self.USE_HTTPS:
            self.SESSION_COOKIE_NAME = f'__Secure-{self.SESSION_COOKIE_NAME}'
            self.CSRF_COOKIE_NAME = f'__Secure-{self.CSRF_COOKIE_NAME}'

settings = Settings()