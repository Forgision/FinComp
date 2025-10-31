import base64
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from sqlalchemy import func
from sqlalchemy.orm import Session
from sqlmodel import Field, Relationship, SQLModel, select

from app.core.config import settings
from app.utils.logging import logger

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

fernet = get_encryption_key()


class CommandLog(SQLModel, table=True):
    __tablename__ = 'command_logs'
    id: Optional[int] = Field(default=None, primary_key=True)
    telegram_id: int = Field(foreign_key='telegram_users.telegram_id', index=True)
    command: str = Field(max_length=100)
    chat_id: Optional[int] = Field(default=None)
    parameters: Optional[str] = Field(default=None)
    executed_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"server_default": func.now()})
    user: "TelegramUser" = Relationship(back_populates="command_logs")


class NotificationQueue(SQLModel, table=True):
    __tablename__ = 'notification_queue'
    id: Optional[int] = Field(default=None, primary_key=True)
    telegram_id: int = Field(foreign_key='telegram_users.telegram_id')
    message: str
    priority: int = Field(default=5)
    status: str = Field(default='pending', index=True, max_length=20)
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"server_default": func.now()})
    sent_at: Optional[datetime] = Field(default=None)
    error_message: Optional[str] = Field(default=None)
    user: "TelegramUser" = Relationship(back_populates="notifications")


class UserPreference(SQLModel, table=True):
    __tablename__ = 'user_preferences'
    telegram_id: int = Field(foreign_key='telegram_users.telegram_id', primary_key=True)
    order_notifications: bool = Field(default=True)
    trade_notifications: bool = Field(default=True)
    pnl_notifications: bool = Field(default=True)
    daily_summary: bool = Field(default=True)
    summary_time: str = Field(default='18:00', max_length=10)
    language: str = Field(default='en', max_length=10)
    timezone: str = Field(default='Asia/Kolkata', max_length=50)
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"server_default": func.now()})
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"server_default": func.now(), "onupdate": func.now()})
    user: "TelegramUser" = Relationship(back_populates="preferences")


class TelegramUser(SQLModel, table=True):
    __tablename__ = 'telegram_users'
    id: Optional[int] = Field(default=None, primary_key=True)
    telegram_id: int = Field(unique=True, index=True)
    openalgo_username: str = Field(max_length=255, index=True)
    encrypted_api_key: Optional[str] = Field(default=None)
    host_url: Optional[str] = Field(default=None, max_length=500)
    first_name: Optional[str] = Field(default=None, max_length=255)
    last_name: Optional[str] = Field(default=None, max_length=255)
    telegram_username: Optional[str] = Field(default=None, max_length=255)
    broker: str = Field(default='default', max_length=50)
    is_active: bool = Field(default=True)
    notifications_enabled: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"server_default": func.now()})
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"server_default": func.now(), "onupdate": func.now()})
    last_command_at: Optional[datetime] = Field(default=None)
    command_logs: List["CommandLog"] = Relationship(back_populates="user", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    notifications: List["NotificationQueue"] = Relationship(back_populates="user", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    preferences: "UserPreference" = Relationship(back_populates="user", sa_relationship_kwargs={"uselist": False, "cascade": "all, delete-orphan"})


class BotConfig(SQLModel, table=True):
    __tablename__ = 'bot_config'
    id: Optional[int] = Field(default=1, primary_key=True)
    token: Optional[str] = Field(default=None)
    is_active: bool = Field(default=False)
    bot_username: Optional[str] = Field(default=None, max_length=255)
    max_message_length: int = Field(default=4096)
    rate_limit_per_minute: int = Field(default=30)
    broadcast_enabled: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"server_default": func.now()})
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"server_default": func.now(), "onupdate": func.now()})


def get_telegram_user(db: Session, telegram_id: int) -> Optional[Dict]:
    try:
        user = db.exec(select(TelegramUser).where(TelegramUser.telegram_id == telegram_id, TelegramUser.is_active == True)).first()
        if user:
            return user.dict()
        return None
    except Exception as e:
        logger.error(f"Failed to get telegram user: {str(e)}")
        return None


def get_telegram_user_by_username(db: Session, username: str) -> Optional[Dict]:
    try:
        user = db.exec(select(TelegramUser).where(TelegramUser.openalgo_username == username, TelegramUser.is_active == True)).first()
        if user:
            return user.dict()
        return None
    except Exception as e:
        logger.error(f"Failed to get telegram user by username: {str(e)}")
        return None


def create_or_update_telegram_user(db: Session, telegram_id: int, username: str, api_key: Optional[str] = None, host_url: Optional[str] = None, first_name: str = '', last_name: str = '', telegram_username: str = '', broker: str = 'default') -> bool:
    try:
        user = db.exec(select(TelegramUser).where(TelegramUser.telegram_id == telegram_id)).first()
        encrypted_key = fernet.encrypt(api_key.encode()).decode() if api_key else None
        if user:
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
        else:
            user = TelegramUser(telegram_id=telegram_id, openalgo_username=username, encrypted_api_key=encrypted_key, host_url=host_url, first_name=first_name, last_name=last_name, telegram_username=telegram_username, broker=broker)
            db.add(user)
            preferences = UserPreference(telegram_id=telegram_id)
            db.add(preferences)
        db.commit()
        db.refresh(user)
        logger.debug(f"Telegram user {telegram_id} linked successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to create/update telegram user: {str(e)}")
        db.rollback()
        return False


def delete_telegram_user(db: Session, telegram_id: int) -> bool:
    try:
        user = db.exec(select(TelegramUser).where(TelegramUser.telegram_id == telegram_id)).first()
        if user:
            user.is_active = False
            db.add(user)
            db.commit()
            logger.debug(f"Telegram user {telegram_id} unlinked")
            return True
        return False
    except Exception as e:
        logger.error(f"Failed to delete telegram user: {str(e)}")
        db.rollback()
        return False


def get_all_telegram_users(db: Session, filters: Optional[Dict] = None) -> List[Dict]:
    try:
        statement = select(TelegramUser).where(TelegramUser.is_active == True)
        if filters:
            if 'broker' in filters:
                statement = statement.where(TelegramUser.broker == filters['broker'])
            if 'notifications_enabled' in filters:
                statement = statement.where(TelegramUser.notifications_enabled == filters['notifications_enabled'])
        users = db.exec(statement).all()
        return [user.dict() for user in users]
    except Exception as e:
        logger.error(f"Failed to get all telegram users: {str(e)}")
        return []


def get_bot_config(db: Session) -> Dict:
    try:
        config = db.exec(select(BotConfig).where(BotConfig.id == 1)).first()
        if config:
            config_dict = config.dict()
            config_dict['bot_token'] = config.token
            return config_dict
        return {'bot_token': None, 'token': None, 'is_active': False, 'bot_username': None, 'max_message_length': 4096, 'rate_limit_per_minute': 30, 'broadcast_enabled': True}
    except Exception as e:
        logger.error(f"Failed to get bot config: {str(e)}")
        return {}


def update_bot_config(db: Session, config: Dict) -> bool:
    try:
        bot_config = db.exec(select(BotConfig).where(BotConfig.id == 1)).first()
        if not bot_config:
            bot_config = BotConfig(id=1)
            db.add(bot_config)
        for key, value in config.items():
            if key == 'bot_token':
                setattr(bot_config, 'token', value)
            elif hasattr(bot_config, key) and key not in ['id', 'created_at']:
                setattr(bot_config, key, value)
        db.add(bot_config)
        db.commit()
        logger.debug("Bot configuration updated")
        return True
    except Exception as e:
        logger.error(f"Failed to update bot config: {str(e)}")
        db.rollback()
        return False


def log_command(db: Session, telegram_id: int, command: str, chat_id: Optional[int] = None, parameters: Optional[Dict] = None):
    try:
        params_json = json.dumps(parameters) if parameters else None
        command_log = CommandLog(telegram_id=telegram_id, command=command, chat_id=chat_id, parameters=params_json)
        db.add(command_log)
        user = db.exec(select(TelegramUser).where(TelegramUser.telegram_id == telegram_id)).first()
        if user:
            user.last_command_at = datetime.utcnow()
            db.add(user)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to log command: {str(e)}")
        db.rollback()


def get_command_stats(db: Session, days: int = 7) -> Dict:
    try:
        since_date = datetime.now() - timedelta(days=days)
        total_commands = db.scalar(select(func.count(CommandLog.id)).where(CommandLog.executed_at >= since_date))
        command_counts = db.exec(select(CommandLog.command, func.count(CommandLog.id)).where(CommandLog.executed_at >= since_date).group_by(CommandLog.command).order_by(func.count(CommandLog.id).desc())).all()
        commands_by_type = {cmd: count for cmd, count in command_counts}
        active_users = db.scalar(select(func.count(func.distinct(CommandLog.telegram_id))).where(CommandLog.executed_at >= since_date))
        top_users_query = select(TelegramUser.telegram_username, func.count(CommandLog.id).label('command_count')).join(CommandLog, CommandLog.telegram_id == TelegramUser.telegram_id).where(CommandLog.executed_at >= since_date).group_by(TelegramUser.telegram_username).order_by(func.count(CommandLog.id).desc()).limit(10)
        top_users = db.exec(top_users_query).all()
        return {'total_commands': total_commands, 'commands_by_type': commands_by_type, 'active_users': active_users or 0, 'top_users': [(username, count) for username, count in top_users], 'period_days': days}
    except Exception as e:
        logger.error(f"Failed to get command stats: {str(e)}")
        return {'total_commands': 0, 'commands_by_type': {}, 'active_users': 0, 'top_users': [], 'period_days': days}


def get_user_preferences(db: Session, telegram_id: int) -> Dict:
    try:
        pref = db.exec(select(UserPreference).where(UserPreference.telegram_id == telegram_id)).first()
        if pref:
            return pref.dict()
        return {'order_notifications': True, 'trade_notifications': True, 'pnl_notifications': True, 'daily_summary': True, 'summary_time': '18:00', 'language': 'en', 'timezone': 'Asia/Kolkata'}
    except Exception as e:
        logger.error(f"Failed to get user preferences: {str(e)}")
        return {}


def update_user_preferences(db: Session, telegram_id: int, preferences: Dict) -> bool:
    try:
        pref = db.exec(select(UserPreference).where(UserPreference.telegram_id == telegram_id)).first()
        if not pref:
            pref = UserPreference(telegram_id=telegram_id)
            db.add(pref)
        for key, value in preferences.items():
            if hasattr(pref, key) and key not in ['telegram_id', 'created_at']:
                setattr(pref, key, value)
        db.add(pref)
        db.commit()
        logger.debug(f"User preferences updated for telegram_id: {telegram_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to update user preferences: {str(e)}")
        db.rollback()
        return False


def add_notification(db: Session, telegram_id: int, message: str, priority: int = 5) -> bool:
    try:
        notification = NotificationQueue(telegram_id=telegram_id, message=message, priority=priority)
        db.add(notification)
        db.commit()
        return True
    except Exception as e:
        logger.error(f"Failed to add notification: {str(e)}")
        db.rollback()
        return False


def get_pending_notifications(db: Session, limit: int = 100) -> List[Dict]:
    try:
        notifications = db.exec(select(NotificationQueue).where(NotificationQueue.status == 'pending').order_by(NotificationQueue.priority.desc(), NotificationQueue.created_at.asc()).limit(limit)).all()
        return [n.dict() for n in notifications]
    except Exception as e:
        logger.error(f"Failed to get pending notifications: {str(e)}")
        return []


def mark_notification_sent(db: Session, notification_id: int, success: bool = True, error_message: Optional[str] = None):
    try:
        notification = db.get(NotificationQueue, notification_id)
        if notification:
            notification.status = 'sent' if success else 'failed'
            notification.sent_at = datetime.utcnow()
            notification.error_message = error_message
            db.add(notification)
            db.commit()
    except Exception as e:
        logger.error(f"Failed to update notification status: {str(e)}")
        db.rollback()


def get_decrypted_api_key(db: Session, telegram_id: int) -> Optional[str]:
    try:
        user = db.exec(select(TelegramUser).where(TelegramUser.telegram_id == telegram_id, TelegramUser.is_active == True)).first()
        if user and user.encrypted_api_key:
            return fernet.decrypt(user.encrypted_api_key.encode()).decode()
        return None
    except Exception as e:
        logger.error(f"Failed to decrypt API key: {str(e)}")
        return None


def get_user_credentials(db: Session, telegram_id: int) -> Optional[Dict]:
    try:
        user = db.exec(select(TelegramUser).where(TelegramUser.telegram_id == telegram_id, TelegramUser.is_active == True)).first()
        if user:
            api_key = get_decrypted_api_key(db, telegram_id)
            return {'username': user.openalgo_username, 'api_key': api_key, 'host_url': user.host_url or settings.HOST_SERVER, 'broker': user.broker}
        return None
    except Exception as e:
        logger.error(f"Failed to get user credentials: {str(e)}")
        return None


def get_auth_token_by_username(db: Session, username: str):
    from app.core.models.auth_db import get_auth_token
    return get_auth_token(db, name=username)
