# database/settings_db.py

import base64
from typing import Optional

from cryptography.fernet import Fernet
from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, Session

from app.core.config import settings
from app.core.schemas.base import Base
from app.core.schemas.session import db_session, engine
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
                 security_404_threshold: int = 20,
                 security_404_ban_duration: int = 24,
                 security_api_threshold: int = 10,
                 security_api_ban_duration: int = 48,
                 security_repeat_offender_limit: int = 3):
        self.analyze_mode = analyze_mode
        self.security_404_threshold = security_404_threshold
        self.security_404_ban_duration = security_404_ban_duration
        self.security_api_threshold = security_api_threshold
        self.security_api_ban_duration = security_api_ban_duration
        self.security_repeat_offender_limit = security_repeat_offender_limit


def init_db():
    """Initialize the settings database"""
    logger.info("Initializing Settings DB")

    Base.metadata.create_all(bind=engine)

    if not db_session.query(Settings).first():
        logger.info("Creating default settings (Live Mode)")
        default_settings = Settings(analyze_mode=False)
        db_session.add(default_settings)
        db_session.commit()


def get_analyze_mode(db: Session):
    """Get current analyze mode setting"""
    settings = db.query(Settings).first()
    if not settings:
        settings = Settings(analyze_mode=False)
        db.add(settings)
        db.commit()
    return settings.analyze_mode


def set_analyze_mode(mode: bool):
    """Set analyze mode setting"""
    settings_instance = db_session.query(Settings).first()
    if not settings_instance:
        settings_instance = Settings(analyze_mode=mode)
        db_session.add(settings_instance)
    else:
        settings_instance.analyze_mode = mode
    db_session.commit()


def _get_encryption_key():
    """Get or create encryption key for SMTP password"""
    pepper = settings.API_KEY_PEPPER
    key = base64.urlsafe_b64encode(pepper.ljust(32)[:32].encode())
    return key


def _encrypt_password(password: str) -> str | None:
    """Encrypt SMTP password"""
    if not password:
        return None
    key = _get_encryption_key()
    f = Fernet(key)
    encrypted = f.encrypt(password.encode())
    return encrypted.decode()


def _decrypt_password(encrypted_password: str) -> str | None:
    """Decrypt SMTP password"""
    if not encrypted_password:
        return None
    key = _get_encryption_key()
    f = Fernet(key)
    decrypted = f.decrypt(encrypted_password.encode())
    return decrypted.decode()


def get_smtp_settings(db: Session) -> dict | None:
    """Get SMTP configuration"""
    settings_instance = db.query(Settings).first()
    if not settings_instance:
        return None

    decrypted_password = None
    if settings_instance.smtp_password_encrypted:
        decrypted_password = _decrypt_password(settings_instance.smtp_password_encrypted)

    return {
        'smtp_server': settings_instance.smtp_server,
        'smtp_port': settings_instance.smtp_port,
        'smtp_username': settings_instance.smtp_username,
        'smtp_password': decrypted_password,
        'smtp_use_tls': settings_instance.smtp_use_tls,
        'smtp_from_email': settings_instance.smtp_from_email,
        'smtp_helo_hostname': settings_instance.smtp_helo_hostname
    }


def set_smtp_settings(db: Session, smtp_server=None, smtp_port=None, smtp_username=None,
                     smtp_password=None, smtp_use_tls=True, smtp_from_email=None, smtp_helo_hostname=None):
    """Set SMTP configuration"""
    settings_instance = db.query(Settings).first()
    if not settings_instance:
        settings_instance = Settings(analyze_mode=False)
        db.add(settings_instance)

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


def get_security_settings():
    """Get security configuration"""
    settings = db_session.query(Settings).first()
    if not settings:
        settings = Settings(
            analyze_mode=False,
            security_404_threshold=20,
            security_404_ban_duration=24,
            security_api_threshold=10,
            security_api_ban_duration=48,
            security_repeat_offender_limit=3
        )
        db_session.add(settings)
        db_session.commit()

    return {
        '404_threshold': settings.security_404_threshold or 20,
        '404_ban_duration': settings.security_404_ban_duration or 24,
        'api_threshold': settings.security_api_threshold or 10,
        'api_ban_duration': settings.security_api_ban_duration or 48,
        'repeat_offender_limit': settings.security_repeat_offender_limit or 3
    }


def set_security_settings(threshold_404=None, ban_duration_404=None,
                         threshold_api=None, ban_duration_api=None,
                         repeat_offender_limit=None):
    """Set security configuration"""
    settings = db_session.query(Settings).first()
    if not settings:
        settings = Settings(analyze_mode=False)
        db_session.add(settings)

    if threshold_404 is not None:
        settings.security_404_threshold = threshold_404
    if ban_duration_404 is not None:
        settings.security_404_ban_duration = ban_duration_404
    if threshold_api is not None:
        settings.security_api_threshold = threshold_api
    if ban_duration_api is not None:
        settings.security_api_ban_duration = ban_duration_api
    if repeat_offender_limit is not None:
        settings.security_repeat_offender_limit = repeat_offender_limit

    db_session.commit()
    logger.info("Security settings updated successfully")
