import base64
from typing import Optional

from cryptography.fernet import Fernet
from sqlalchemy.orm import Session
from sqlmodel import Field, SQLModel, select

from app.core.config import settings
from app.utils.logging import logger


class Settings(SQLModel, table=True):
    __tablename__ = 'settings'

    id: Optional[int] = Field(default=None, primary_key=True)
    analyze_mode: bool = Field(default=False)

    # SMTP Configuration
    smtp_server: Optional[str] = Field(default=None, max_length=255)
    smtp_port: Optional[int] = Field(default=None)
    smtp_username: Optional[str] = Field(default=None, max_length=255)
    smtp_password_encrypted: Optional[str] = Field(default=None)
    smtp_use_tls: bool = Field(default=True)
    smtp_from_email: Optional[str] = Field(default=None, max_length=255)
    smtp_helo_hostname: Optional[str] = Field(default=None, max_length=255)

    # Security Settings
    security_404_threshold: int = Field(default=20)
    security_404_ban_duration: int = Field(default=24)
    security_api_threshold: int = Field(default=10)
    security_api_ban_duration: int = Field(default=48)
    security_repeat_offender_limit: int = Field(default=3)

    @property
    def smtp_password(self) -> Optional[str]:
        if self.smtp_password_encrypted:
            return _decrypt_password(self.smtp_password_encrypted)
        return None


def get_settings(db: Session) -> Settings:
    """Get settings from the database"""
    settings_instance = db.exec(select(Settings)).first()
    if not settings_instance:
        settings_instance = Settings()
        db.add(settings_instance)
        db.commit()
        db.refresh(settings_instance)
    return settings_instance


def get_analyze_mode(db: Session) -> bool:
    """Get current analyze mode setting"""
    return get_settings(db).analyze_mode


def set_analyze_mode(db: Session, mode: bool):
    """Set analyze mode setting"""
    settings_instance = get_settings(db)
    settings_instance.analyze_mode = mode
    db.add(settings_instance)
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


def get_smtp_settings(db: Session) -> dict:
    """Get SMTP configuration"""
    s = get_settings(db)
    return {
        'smtp_server': s.smtp_server,
        'smtp_port': s.smtp_port,
        'smtp_username': s.smtp_username,
        'smtp_password': s.smtp_password,
        'smtp_use_tls': s.smtp_use_tls,
        'smtp_from_email': s.smtp_from_email,
        'smtp_helo_hostname': s.smtp_helo_hostname
    }


def set_smtp_settings(
    db: Session,
    smtp_server: Optional[str] = None,
    smtp_port: Optional[int] = None,
    smtp_username: Optional[str] = None,
    smtp_password: Optional[str] = None,
    smtp_use_tls: Optional[bool] = None,
    smtp_from_email: Optional[str] = None,
    smtp_helo_hostname: Optional[str] = None
):
    """Set SMTP configuration"""
    settings_instance = get_settings(db)
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
    db.add(settings_instance)
    db.commit()
    logger.info("SMTP settings updated successfully")


def get_security_settings(db: Session) -> dict:
    """Get security configuration"""
    s = get_settings(db)
    return {
        '404_threshold': s.security_404_threshold,
        '404_ban_duration': s.security_404_ban_duration,
        'api_threshold': s.security_api_threshold,
        'api_ban_duration': s.security_api_ban_duration,
        'repeat_offender_limit': s.security_repeat_offender_limit
    }


def set_security_settings(
    db: Session,
    threshold_404: Optional[int] = None,
    ban_duration_404: Optional[int] = None,
    threshold_api: Optional[int] = None,
    ban_duration_api: Optional[int] = None,
    repeat_offender_limit: Optional[int] = None
):
    """Set security configuration"""
    s = get_settings(db)
    if threshold_404 is not None:
        s.security_404_threshold = threshold_404
    if ban_duration_404 is not None:
        s.security_404_ban_duration = ban_duration_404
    if threshold_api is not None:
        s.security_api_threshold = threshold_api
    if ban_duration_api is not None:
        s.security_api_ban_duration = ban_duration_api
    if repeat_offender_limit is not None:
        s.security_repeat_offender_limit = repeat_offender_limit
    db.add(s)
    db.commit()
    logger.info("Security settings updated successfully")
