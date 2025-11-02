# app/core/schemas/settings_db.py

import base64
from typing import Optional

from cryptography.fernet import Fernet
from sqlalchemy import Boolean, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column, Session

from app.core.config import settings
from app.core.schemas import Base, SessionLocal, ENSURE_TABLE_REGISTRY
from app.utils.logging import logger


class Settings(Base):
    __tablename__ = 'settings'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    analyze_mode: Mapped[bool] = mapped_column(Boolean, default=False)

    # SMTP Configuration
    smtp_server: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    smtp_port: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    smtp_username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    smtp_password_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    smtp_use_tls: Mapped[bool] = mapped_column(Boolean, default=True)
    smtp_from_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    smtp_helo_hostname: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Security Settings
    security_404_threshold: Mapped[int] = mapped_column(Integer, default=20)
    security_404_ban_duration: Mapped[int] = mapped_column(Integer, default=24)
    security_api_threshold: Mapped[int] = mapped_column(Integer, default=10)
    security_api_ban_duration: Mapped[int] = mapped_column(Integer, default=48)
    security_repeat_offender_limit: Mapped[int] = mapped_column(Integer, default=3)

    def __init__(self, analyze_mode: bool = False,
                 smtp_server: Optional[str] = None, smtp_port: Optional[int] = None,
                 smtp_username: Optional[str] = None, smtp_password_encrypted: Optional[str] = None,
                 smtp_use_tls: bool = True, smtp_from_email: Optional[str] = None,
                 smtp_helo_hostname: Optional[str] = None,
                 security_404_threshold: int = 20,
                 security_404_ban_duration: int = 24,
                 security_api_threshold: int = 10,
                 security_api_ban_duration: int = 48,
                 security_repeat_offender_limit: int = 3):
        self.analyze_mode = analyze_mode
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.smtp_username = smtp_username
        self.smtp_password_encrypted = smtp_password_encrypted
        self.smtp_use_tls = smtp_use_tls
        self.smtp_from_email = smtp_from_email
        self.smtp_helo_hostname = smtp_helo_hostname
        self.security_404_threshold = security_404_threshold
        self.security_404_ban_duration = security_404_ban_duration
        self.security_api_threshold = security_api_threshold
        self.security_api_ban_duration = security_api_ban_duration
        self.security_repeat_offender_limit = security_repeat_offender_limit

    @property
    def smtp_password(self) -> Optional[str]:
        if self.smtp_password_encrypted:
            return _decrypt_password(self.smtp_password_encrypted)
        return None


def ensure_table():
    with SessionLocal() as db_session:
        # Create default settings if not exists
        if not db_session.query(Settings).first():
            logger.info("Creating default settings (Live Mode)")
            default_settings = Settings(analyze_mode=False)
            db_session.add(default_settings)
            db_session.commit()

            
ENSURE_TABLE_REGISTRY['settings_db'] = ensure_table


def get_settings() -> Settings:
    """Get settings from the database"""
    with SessionLocal() as db:    
        settings_instance = db.execute(select(Settings)).scalar_one_or_none()
        if not settings_instance:
            settings_instance = Settings()
            db.add(settings_instance)
            db.commit()
        return settings_instance


def get_analyze_mode() -> bool:
    """Get current analyze mode setting"""
    return get_settings().analyze_mode


def set_analyze_mode(mode: bool):
    """Set analyze mode setting"""
    with SessionLocal() as db:
        settings_instance = get_settings()
        settings_instance.analyze_mode = mode
        db.commit()


def _get_encryption_key() -> bytes:
    """Get or create encryption key for SMTP password"""
    pepper = settings.API_KEY_PEPPER
    key = base64.urlsafe_b64encode(pepper.ljust(32)[:32].encode())
    return key


def _encrypt_password(password: str) -> Optional[str]:
    """Encrypt SMTP password"""
    if not password:
        return None
    key = _get_encryption_key()
    f = Fernet(key)
    encrypted = f.encrypt(password.encode())
    return encrypted.decode()


def _decrypt_password(encrypted_password: str) -> Optional[str]:
    """Decrypt SMTP password"""
    if not encrypted_password:
        return None
    key = _get_encryption_key()
    f = Fernet(key)
    try:
        decrypted = f.decrypt(encrypted_password.encode())
        return decrypted.decode()
    except Exception:
        return None


def get_smtp_settings() -> dict:
    """Get SMTP configuration"""
    settings_instance = get_settings()

    return {
        'smtp_server': settings_instance.smtp_server,
        'smtp_port': settings_instance.smtp_port,
        'smtp_username': settings_instance.smtp_username,
        'smtp_password': settings_instance.smtp_password,
        'smtp_use_tls': settings_instance.smtp_use_tls,
        'smtp_from_email': settings_instance.smtp_from_email,
        'smtp_helo_hostname': settings_instance.smtp_helo_hostname
    }


def set_smtp_settings(smtp_server: Optional[str] = None, smtp_port: Optional[int] = None,
                     smtp_username: Optional[str] = None, smtp_password: Optional[str] = None,
                     smtp_use_tls: Optional[bool] = None, smtp_from_email: Optional[str] = None,
                     smtp_helo_hostname: Optional[str] = None):
    """Set SMTP configuration"""
    with SessionLocal() as db:
        settings_instance = get_settings()

        if smtp_server is not None:
            settings_instance.smtp_server = smtp_server
        if smtp_port is not None:
            settings_instance.smtp_port = smtp_port
        if smtp_username is not None:
            settings_instance.smtp_username = smtp_username
        if smtp_password is not None:
            settings_instance.smtp_password_encrypted = _encrypt_password(smtp_password)
        if smtp_use_tls is not None:
            settings_instance.smtp_use_tls = smtp_use_tls
        if smtp_from_email is not None:
            settings_instance.smtp_from_email = smtp_from_email
        if smtp_helo_hostname is not None:
            settings_instance.smtp_helo_hostname = smtp_helo_hostname

        db.commit()
        logger.info("SMTP settings updated successfully")


def get_security_settings() -> dict:
    """Get security configuration"""
    s = get_settings()

    return {
        '404_threshold': s.security_404_threshold,
        '404_ban_duration': s.security_404_ban_duration,
        'api_threshold': s.security_api_threshold,
        'api_ban_duration': s.security_api_ban_duration,
        'repeat_offender_limit': s.security_repeat_offender_limit
    }


def set_security_settings(threshold_404: Optional[int] = None, ban_duration_404: Optional[int] = None,
                         threshold_api: Optional[int] = None, ban_duration_api: Optional[int] = None,
                         repeat_offender_limit: Optional[int] = None):
    """Set security configuration"""
    with SessionLocal() as db:
        settings_instance = get_settings()

        if threshold_404 is not None:
            settings_instance.security_404_threshold = threshold_404
        if ban_duration_404 is not None:
            settings_instance.security_404_ban_duration = ban_duration_404
        if threshold_api is not None:
            settings_instance.security_api_threshold = threshold_api
        if ban_duration_api is not None:
            settings_instance.security_api_ban_duration = ban_duration_api
        if repeat_offender_limit is not None:
            settings_instance.security_repeat_offender_limit = repeat_offender_limit

        db.commit()
        logger.info("Security settings updated successfully")
