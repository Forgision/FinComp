"""
Telegram Database Module using SQLAlchemy for secure database operations
"""

import base64
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from sqlalchemy import (
    Boolean,
    ForeignKey,
    Integer,
    String,
    Text,
    select,
    func,
    DateTime,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import settings
from app.core.schemas import Base, INIT_DB_REGISTRY, AsyncSessionLocal
from app.utils.logging import logger

# Database configuration
DATABASE_URL = settings.TELEGRAM_DATABASE_URL

if DATABASE_URL.startswith("sqlite:///") and ":memory:" not in DATABASE_URL:
    # Ensure the directory exists for file-based SQLite, but not for in-memory
    db_path = DATABASE_URL.replace("sqlite:///", "")
    if os.path.dirname(db_path):  # Only create if a directory is specified
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

# Encryption setup for API keys
TELEGRAM_KEY_SALT = settings.TELEGRAM_KEY_SALT.encode()


def get_encryption_key():
    """Generate a Fernet key for encrypting API keys"""
    pepper = settings.API_KEY_PEPPER
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=TELEGRAM_KEY_SALT,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(pepper.encode()))
    return Fernet(key)


# Initialize Fernet cipher for API key encryption
fernet = get_encryption_key()


class TelegramUser(Base):
    """Telegram users table"""

    __tablename__ = "telegram_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(
        Integer, unique=True, nullable=False, index=True
    )
    openalgo_username: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True
    )
    encrypted_api_key: Mapped[Optional[str]] = mapped_column(Text)
    host_url: Mapped[Optional[str]] = mapped_column(String(500))
    first_name: Mapped[Optional[str]] = mapped_column(String(255))
    last_name: Mapped[Optional[str]] = mapped_column(String(255))
    telegram_username: Mapped[Optional[str]] = mapped_column(String(255))
    broker: Mapped[str] = mapped_column(String(50), default="default")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now()
    )
    last_command_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Relationships
    command_logs: Mapped[List["CommandLog"]] = relationship(
        "CommandLog", back_populates="user", cascade="all, delete-orphan"
    )
    notifications: Mapped[List["NotificationQueue"]] = relationship(
        "NotificationQueue", back_populates="user", cascade="all, delete-orphan"
    )
    preferences: Mapped["UserPreference"] = relationship(
        "UserPreference",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )


class BotConfig(Base):
    """Bot configuration table"""

    __tablename__ = "bot_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    token: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    bot_username: Mapped[Optional[str]] = mapped_column(String(255))
    max_message_length: Mapped[int] = mapped_column(Integer, default=4096)
    rate_limit_per_minute: Mapped[int] = mapped_column(Integer, default=30)
    broadcast_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now()
    )


class CommandLog(Base):
    """Command logs table for analytics"""

    __tablename__ = "command_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("telegram_users.telegram_id"), nullable=False, index=True
    )
    command: Mapped[str] = mapped_column(String(100), nullable=False)
    chat_id: Mapped[Optional[int]] = mapped_column(Integer)
    parameters: Mapped[Optional[str]] = mapped_column(Text)
    executed_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    # Relationship
    user: Mapped["TelegramUser"] = relationship(
        "TelegramUser", back_populates="command_logs"
    )


class NotificationQueue(Base):
    """Notification queue table"""

    __tablename__ = "notification_queue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("telegram_users.telegram_id"), nullable=False
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=5)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    error_message: Mapped[Optional[str]] = mapped_column(Text)

    # Relationship
    user: Mapped["TelegramUser"] = relationship(
        "TelegramUser", back_populates="notifications"
    )


class UserPreference(Base):
    """User preferences table"""

    __tablename__ = "user_preferences"

    telegram_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("telegram_users.telegram_id"), primary_key=True
    )
    order_notifications: Mapped[bool] = mapped_column(Boolean, default=True)
    trade_notifications: Mapped[bool] = mapped_column(Boolean, default=True)
    pnl_notifications: Mapped[bool] = mapped_column(Boolean, default=True)
    daily_summary: Mapped[bool] = mapped_column(Boolean, default=True)
    summary_time: Mapped[str] = mapped_column(String(10), default="18:00")
    language: Mapped[str] = mapped_column(String(10), default="en")
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Kolkata")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now()
    )

    # Relationship
    user: Mapped["TelegramUser"] = relationship(
        "TelegramUser", back_populates="preferences"
    )


async def ensure_table():
    """Initialize the database with required tables"""
    try:
        # Create default bot config if not exists
        async with AsyncSessionLocal() as session:
            stmt = select(BotConfig).filter_by(id=1)
            result = await session.execute(stmt)
            config = result.scalars().first()
            if not config:
                default_config = BotConfig(id=1)
                session.add(default_config)
                await session.commit()

        logger.info("Telegram database initialized successfully")
    except Exception as e:
        logger.exception(f"Failed to initialize database: {str(e)}")


# Add to registry to ensure table exist before app start
INIT_DB_REGISTRY["telegram_db"] = ensure_table


async def get_telegram_user(db: AsyncSession, telegram_id: int) -> Optional[Dict]:
    """Get telegram user by telegram_id"""
    try:
        stmt = select(TelegramUser).filter_by(telegram_id=telegram_id, is_active=True)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if user:
            return {
                "id": user.id,
                "telegram_id": user.telegram_id,
                "openalgo_username": user.openalgo_username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "telegram_username": user.telegram_username,
                "broker": user.broker,
                "is_active": user.is_active,
                "notifications_enabled": user.notifications_enabled,
                "created_at": user.created_at,
                "updated_at": user.updated_at,
                "last_command_at": user.last_command_at,
            }
        return None
    except Exception as e:
        logger.error(f"Failed to get telegram user: {str(e)}")
        return None


async def get_telegram_user_by_username(
    db: AsyncSession, username: str
) -> Optional[Dict]:
    """Get telegram user by OpenAlgo username"""
    try:
        stmt = select(TelegramUser).filter_by(
            openalgo_username=username, is_active=True
        )
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if user:
            return {
                "id": user.id,
                "telegram_id": user.telegram_id,
                "openalgo_username": user.openalgo_username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "telegram_username": user.telegram_username,
                "broker": user.broker,
                "is_active": user.is_active,
                "notifications_enabled": user.notifications_enabled,
                "created_at": user.created_at,
                "updated_at": user.updated_at,
                "last_command_at": user.last_command_at,
            }
        return None
    except Exception as e:
        logger.error(f"Failed to get telegram user by username: {str(e)}")
        return None


async def create_or_update_telegram_user(
    db: AsyncSession,
    telegram_id: int,
    username: str,
    api_key: Optional[str] = None,
    host_url: Optional[str] = None,
    first_name: str = "",
    last_name: str = "",
    telegram_username: str = "",
    broker: str = "default",
) -> bool:
    """Create or update telegram user with encrypted API key"""
    try:
        stmt = select(TelegramUser).filter_by(telegram_id=telegram_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        # Encrypt API key if provided
        encrypted_key = None
        if api_key:
            encrypted_key = fernet.encrypt(api_key.encode()).decode()

        if user:
            # Update existing user
            user.openalgo_username = username
            if encrypted_key:
                user.encrypted_api_key = encrypted_key
            if host_url:
                user.host_url = host_url
            user.first_name = first_name
            user.last_name = last_name
            user.telegram_username = telegram_username
            user.broker = broker
            user.is_active = True
            user.updated_at = func.now()
        else:
            # Create new user
            user = TelegramUser(
                telegram_id=telegram_id,
                openalgo_username=username,
                encrypted_api_key=encrypted_key,
                host_url=host_url,
                first_name=first_name,
                last_name=last_name,
                telegram_username=telegram_username,
                broker=broker,
            )
            db.add(user)

            # Also create default preferences
            preferences = UserPreference(telegram_id=telegram_id)
            db.add(preferences)

        await db.commit()
        logger.debug(f"Telegram user {telegram_id} linked successfully")
        return True

    except Exception as e:
        logger.error(f"Failed to create/update telegram user: {str(e)}")
        await db.rollback()
        return False


async def delete_telegram_user(db: AsyncSession, telegram_id: int) -> bool:
    """Delete telegram user (soft delete by marking inactive)"""
    try:
        stmt = select(TelegramUser).filter_by(telegram_id=telegram_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if user:
            user.is_active = False
            user.updated_at = func.now()
            await db.commit()
            logger.debug(f"Telegram user {telegram_id} unlinked")
            return True

        return False

    except Exception as e:
        logger.error(f"Failed to delete telegram user: {str(e)}")
        await db.rollback()
        return False


async def get_all_telegram_users(
    db: AsyncSession, filters: Optional[Dict] = None
) -> List[Dict]:
    """Get all active telegram users with optional filters"""
    try:
        stmt = select(TelegramUser).filter_by(is_active=True)

        if filters:
            if "broker" in filters:
                stmt = stmt.filter_by(broker=filters["broker"])
            if "notifications_enabled" in filters:
                stmt = stmt.filter_by(
                    notifications_enabled=filters["notifications_enabled"]
                )

        result = await db.execute(stmt)
        users = result.scalars().all()

        return [
            {
                "id": user.id,
                "telegram_id": user.telegram_id,
                "openalgo_username": user.openalgo_username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "telegram_username": user.telegram_username,
                "broker": user.broker,
                "notifications_enabled": user.notifications_enabled,
                "created_at": user.created_at,
                "last_command_at": user.last_command_at,
            }
            for user in users
        ]

    except Exception as e:
        logger.error(f"Failed to get all telegram users: {str(e)}")
        return []


# Bot Configuration Functions


async def get_bot_config(db: AsyncSession) -> Dict:
    """Get bot configuration"""
    try:
        stmt = select(BotConfig).filter_by(id=1)
        result = await db.execute(stmt)
        config = result.scalar_one_or_none()

        if config:
            return {
                "bot_token": config.token,
                "token": config.token,  # Alias for backward compatibility
                "is_active": config.is_active,
                "bot_username": config.bot_username,
                "max_message_length": config.max_message_length,
                "rate_limit_per_minute": config.rate_limit_per_minute,
                "broadcast_enabled": config.broadcast_enabled,
                "created_at": config.created_at,
                "updated_at": config.updated_at,
            }

        # Return default config if not exists
        return {
            "bot_token": None,
            "token": None,
            "is_active": False,
            "bot_username": None,
            "max_message_length": 4096,
            "rate_limit_per_minute": 30,
            "broadcast_enabled": True,
        }

    except Exception as e:
        logger.error(f"Failed to get bot config: {str(e)}")
        return {}


async def update_bot_config(db: AsyncSession, config: Dict) -> bool:
    """Update bot configuration"""
    try:
        stmt = select(BotConfig).filter_by(id=1)
        result = await db.execute(stmt)
        bot_config = result.scalar_one_or_none()

        if not bot_config:
            bot_config = BotConfig(id=1)
            db.add(bot_config)

        # Update fields (map bot_token to token for database)
        for key, value in config.items():
            # Handle the bot_token -> token mapping
            if key == "bot_token":
                setattr(bot_config, "token", value)
            elif hasattr(bot_config, key) and key not in ["id", "created_at"]:
                setattr(bot_config, key, value)

        await db.commit()
        logger.debug("Bot configuration updated")
        return True

    except Exception as e:
        logger.error(f"Failed to update bot config: {str(e)}")
        await db.rollback()
        return False


# Command Logging Functions


async def log_command(
    db: AsyncSession,
    telegram_id: int,
    command: str,
    chat_id: Optional[int] = None,
    parameters: Optional[Dict] = None,
):
    """Log command execution for analytics"""
    try:
        params_json = json.dumps(parameters) if parameters else None

        # Create command log
        command_log = CommandLog(
            telegram_id=telegram_id,
            command=command,
            chat_id=chat_id,
            parameters=params_json,
        )
        db.add(command_log)

        # Update last_command_at in telegram_users
        stmt = select(TelegramUser).filter_by(telegram_id=telegram_id)
        user = await db.execute(stmt).scalars().first()
        if user:
            user.last_command_at = func.now()

        db.commit()

    except Exception as e:
        logger.error(f"Failed to log command: {str(e)}")
        db.rollback()


async def get_command_stats(db: AsyncSession, days: int = 7) -> Dict:
    """Get command statistics for the last N days"""
    try:
        since_date = datetime.now() - timedelta(days=days)

        # Total commands
        stmt_total = select(func.count(CommandLog.id)).filter(
            CommandLog.executed_at >= since_date
        )
        total_commands = (await db.execute(stmt_total)).scalar_one()

        # Commands by type
        stmt_counts = (
            select(CommandLog.command, func.count(CommandLog.id).label("count"))
            .filter(CommandLog.executed_at >= since_date)
            .group_by(CommandLog.command)
            .order_by(func.count(CommandLog.id).desc())
        )
        command_counts = (await db.execute(stmt_counts)).all()

        commands_by_type = {cmd: count for cmd, count in command_counts}

        # Active users
        stmt_active = select(func.count(func.distinct(CommandLog.telegram_id))).filter(
            CommandLog.executed_at >= since_date
        )
        active_users = (await db.execute(stmt_active)).scalar_one()

        # Most active users
        stmt_top = (
            select(
                TelegramUser.telegram_username,
                func.count(CommandLog.id).label("command_count"),
            )
            .join(CommandLog, CommandLog.telegram_id == TelegramUser.telegram_id)
            .filter(CommandLog.executed_at >= since_date)
            .group_by(TelegramUser.telegram_username)
            .order_by(func.count(CommandLog.id).desc())
            .limit(10)
        )
        top_users = (await db.execute(stmt_top)).all()

        return {
            "total_commands": total_commands,
            "commands_by_type": commands_by_type,
            "active_users": active_users or 0,
            "top_users": [(username, count) for username, count in top_users],
            "period_days": days,
        }

    except Exception as e:
        logger.error(f"Failed to get command stats: {str(e)}")
        return {
            "total_commands": 0,
            "commands_by_type": {},
            "active_users": 0,
            "top_users": [],
            "period_days": days,
        }


# User Preferences Functions


async def get_user_preferences(db: AsyncSession, telegram_id: int) -> Dict:
    """Get user preferences"""
    try:
        stmt = select(UserPreference).filter_by(telegram_id=telegram_id)
        pref = (await db.execute(stmt)).scalars().first()

        if pref:
            return {
                "order_notifications": pref.order_notifications,
                "trade_notifications": pref.trade_notifications,
                "pnl_notifications": pref.pnl_notifications,
                "daily_summary": pref.daily_summary,
                "summary_time": pref.summary_time,
                "language": pref.language,
                "timezone": pref.timezone,
            }

        # Return default preferences
        return {
            "order_notifications": True,
            "trade_notifications": True,
            "pnl_notifications": True,
            "daily_summary": True,
            "summary_time": "18:00",
            "language": "en",
            "timezone": "Asia/Kolkata",
        }

    except Exception as e:
        logger.error(f"Failed to get user preferences: {str(e)}")
        return {}


async def update_user_preferences(
    db: AsyncSession, telegram_id: int, preferences: Dict
) -> bool:
    """Update user preferences"""
    try:
        stmt = select(UserPreference).filter_by(telegram_id=telegram_id)
        pref = (await db.execute(stmt)).scalars().first()

        if not pref:
            pref = UserPreference(telegram_id=telegram_id)
            db.add(pref)

        # Update fields
        for key, value in preferences.items():
            if hasattr(pref, key) and key not in ["telegram_id", "created_at"]:
                setattr(pref, key, value)

        await db.commit()
        logger.debug(f"User preferences updated for telegram_id: {telegram_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to update user preferences: {str(e)}")
        await db.rollback()
        return False


# Notification Queue Functions


async def add_notification(
    db: AsyncSession, telegram_id: int, message: str, priority: int = 5
) -> bool:
    """Add notification to queue"""
    try:
        notification = NotificationQueue(
            telegram_id=telegram_id, message=message, priority=priority
        )
        db.add(notification)
        await db.commit()
        return True

    except Exception as e:
        logger.error(f"Failed to add notification: {str(e)}")
        await db.rollback()
        return False


async def get_pending_notifications(db: AsyncSession, limit: int = 100) -> List[Dict]:
    """Get pending notifications from queue"""
    try:
        stmt = (
            select(NotificationQueue)
            .filter_by(status="pending")
            .order_by(
                NotificationQueue.priority.desc(), NotificationQueue.created_at.asc()
            )
            .limit(limit)
        )
        notifications = await db.execute(stmt).scalars().all()

        return [
            {
                "id": n.id,
                "telegram_id": n.telegram_id,
                "message": n.message,
                "priority": n.priority,
                "status": n.status,
                "created_at": n.created_at,
            }
            for n in notifications
        ]

    except Exception as e:
        logger.error(f"Failed to get pending notifications: {str(e)}")
        return []


async def mark_notification_sent(
    db: AsyncSession,
    notification_id: int,
    success: bool = True,
    error_message: Optional[str] = None,
):
    """Mark notification as sent or failed"""
    try:
        stmt = select(NotificationQueue).filter_by(id=notification_id)
        notification = await db.execute(stmt).scalars().first()

        if notification:
            notification.status = "sent" if success else "failed"
            notification.sent_at = func.now()
            notification.error_message = error_message
            await db.commit()

    except Exception as e:
        logger.error(f"Failed to update notification status: {str(e)}")
        await db.rollback()


# Helper functions for API key management
async def get_decrypted_api_key(db: AsyncSession, telegram_id: int) -> Optional[str]:
    """Get and decrypt API key for a telegram user"""
    try:
        stmt = select(TelegramUser).filter_by(telegram_id=telegram_id, is_active=True)
        user = db.execute(stmt).scalars().first()

        if user and user.encrypted_api_key:
            decrypted_key = fernet.decrypt(user.encrypted_api_key.encode()).decode()
            return decrypted_key
        return None
    except Exception as e:
        logger.error(f"Failed to decrypt API key: {str(e)}")
        return None


async def get_user_credentials(db: AsyncSession, telegram_id: int) -> Optional[Dict]:
    """Get user's API credentials and host URL"""
    try:
        stmt = select(TelegramUser).filter_by(telegram_id=telegram_id, is_active=True)
        user = await db.execute(stmt).scalars().first()

        if user:
            api_key = None
            if user.encrypted_api_key:
                try:
                    api_key = fernet.decrypt(user.encrypted_api_key.encode()).decode()
                except Exception as e:
                    logger.error(f"Failed to decrypt API key: {str(e)}")

            return {
                "username": user.openalgo_username,
                "api_key": api_key,
                "host_url": user.host_url or settings.HOST_SERVER,
                "broker": user.broker,
            }
        return None
    except Exception as e:
        logger.error(f"Failed to get user credentials: {str(e)}")
        return None


# Helper function to get auth token
async def get_auth_token_by_username(db: AsyncSession, username: str):
    """Helper function to get auth token - imports here to avoid circular imports"""
    from app.core.schemas.auth_db import get_auth_token

    return await get_auth_token(db, name=username)


# Cleanup function
async def cleanup_db(db: AsyncSession):
    """Cleanup database connections"""
    db.close()


# Initialize database on module load
