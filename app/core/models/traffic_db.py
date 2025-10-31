import json
import os
from datetime import datetime, timedelta
from typing import List, Optional

from sqlmodel import Field, Session, SQLModel, create_engine, select

from app.core.config import settings
from app.core.models.settings_db import get_security_settings
from app.utils.logging import logger

# Use a separate database for logs
LOGS_DATABASE_URL = settings.LOGS_DATABASE_URL

# Conditionally create engine based on DB type
if LOGS_DATABASE_URL and 'sqlite' in LOGS_DATABASE_URL:
    logs_engine = create_engine(
        LOGS_DATABASE_URL,
        connect_args={'check_same_thread': False}
    )
else:
    logs_engine = create_engine(
        LOGS_DATABASE_URL,
    )


class TrafficLog(SQLModel, table=True):
    __tablename__ = 'traffic_logs'

    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    client_ip: str = Field(max_length=50)
    method: str = Field(max_length=10)
    path: str = Field(max_length=500)
    status_code: int
    duration_ms: float
    host: Optional[str] = Field(max_length=500, default=None)
    error: Optional[str] = Field(max_length=500, default=None)
    user_id: Optional[int] = Field(default=None)


class IPBan(SQLModel, table=True):
    __tablename__ = 'ip_bans'

    id: Optional[int] = Field(default=None, primary_key=True)
    ip_address: str = Field(max_length=50, unique=True, index=True)
    ban_reason: Optional[str] = Field(max_length=200, default=None)
    ban_count: int = Field(default=1)
    banned_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    expires_at: Optional[datetime] = Field(default=None)
    is_permanent: bool = Field(default=False)
    created_by: str = Field(max_length=50, default='system')


class Error404Tracker(SQLModel, table=True):
    __tablename__ = 'error_404_tracker'

    id: Optional[int] = Field(default=None, primary_key=True)
    ip_address: str = Field(max_length=50, index=True)
    error_count: int = Field(default=1)
    first_error_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    last_error_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    paths_attempted: Optional[str] = Field(default=None)


class InvalidAPIKeyTracker(SQLModel, table=True):
    __tablename__ = 'invalid_api_key_tracker'

    id: Optional[int] = Field(default=None, primary_key=True)
    ip_address: str = Field(max_length=50, index=True)
    attempt_count: int = Field(default=1)
    first_attempt_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    last_attempt_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    api_keys_tried: Optional[str] = Field(default=None)


def log_request(db: Session, client_ip: str, method: str, path: str, status_code: int, duration_ms: float, host: Optional[str] = None, error: Optional[str] = None, user_id: Optional[int] = None) -> bool:
    try:
        log = TrafficLog(client_ip=client_ip, method=method, path=path, status_code=status_code, duration_ms=duration_ms, host=host, error=error, user_id=user_id)
        db.add(log)
        db.commit()
        return True
    except Exception as e:
        logger.error(f"Error logging traffic: {str(e)}")
        db.rollback()
        return False


def get_recent_logs(db: Session, limit: int = 100) -> List[TrafficLog]:
    try:
        statement = select(TrafficLog).order_by(TrafficLog.timestamp.desc()).limit(limit)
        return db.exec(statement).all()
    except Exception as e:
        logger.error(f"Error getting recent logs: {str(e)}")
        return []


from sqlalchemy import func

def get_stats(db: Session) -> dict:
    try:
        total_requests = db.exec(select(func.count(TrafficLog.id))).one()
        error_requests = db.exec(select(func.count(TrafficLog.id)).where(TrafficLog.status_code >= 400)).one()
        avg_duration = db.exec(select(func.avg(TrafficLog.duration_ms))).one_or_none() or 0
        return {'total_requests': total_requests, 'error_requests': error_requests, 'avg_duration': round(float(avg_duration), 2)}
    except Exception as e:
        logger.error(f"Error getting traffic stats: {str(e)}")
        return {'total_requests': 0, 'error_requests': 0, 'avg_duration': 0}


def is_ip_banned(db: Session, ip_address: str) -> bool:
    try:
        statement = select(IPBan).where(IPBan.ip_address == ip_address)
        ban = db.exec(statement).first()
        if not ban:
            return False
        if ban.is_permanent:
            return True
        if ban.expires_at and datetime.utcnow() < ban.expires_at:
            return True
        if ban.expires_at and datetime.utcnow() >= ban.expires_at:
            db.delete(ban)
            db.commit()
        return False
    except Exception as e:
        logger.error(f"Error checking IP ban status: {e}")
        db.rollback()
        return False


def ban_ip(db: Session, ip_address: str, reason: str, duration_hours: int = 24, permanent: bool = False, created_by: str = 'system') -> bool:
    try:
        if ip_address in ['127.0.0.1', '::1', 'localhost']:
            logger.warning(f"Attempted to ban localhost IP {ip_address} - ignoring")
            return False

        security_settings = get_security_settings(db)
        repeat_limit = security_settings['repeat_offender_limit']

        statement = select(IPBan).where(IPBan.ip_address == ip_address)
        existing_ban = db.exec(statement).first()

        if existing_ban:
            existing_ban.ban_count += 1
            existing_ban.ban_reason = reason
            existing_ban.banned_at = datetime.utcnow()
            if existing_ban.ban_count >= repeat_limit:
                existing_ban.is_permanent = True
                existing_ban.expires_at = None
                logger.warning(f"IP {ip_address} permanently banned after {existing_ban.ban_count} offenses")
            else:
                existing_ban.is_permanent = permanent
                existing_ban.expires_at = None if permanent else datetime.utcnow() + timedelta(hours=duration_hours)
            db.add(existing_ban)
        else:
            ban = IPBan(ip_address=ip_address, ban_reason=reason, is_permanent=permanent, expires_at=None if permanent else datetime.utcnow() + timedelta(hours=duration_hours), created_by=created_by)
            db.add(ban)

        db.commit()
        logger.info(f"IP {ip_address} banned: {reason}")
        return True
    except Exception as e:
        logger.error(f"Error banning IP {ip_address}: {e}")
        db.rollback()
        return False


def unban_ip(db: Session, ip_address: str) -> bool:
    try:
        statement = select(IPBan).where(IPBan.ip_address == ip_address)
        ban = db.exec(statement).first()
        if ban:
            db.delete(ban)
            db.commit()
            logger.info(f"IP {ip_address} unbanned")
            return True
        return False
    except Exception as e:
        logger.error(f"Error unbanning IP: {e}")
        db.rollback()
        return False


def get_all_bans(db: Session) -> List[IPBan]:
    try:
        statement = select(IPBan).where(IPBan.is_permanent == False, IPBan.expires_at < datetime.utcnow())
        expired = db.exec(statement).all()
        for ban in expired:
            db.delete(ban)
        db.commit()
        statement = select(IPBan)
        return db.exec(statement).all()
    except Exception as e:
        logger.error(f"Error getting IP bans: {e}")
        return []


def track_404(db: Session, ip_address: str, path: str) -> bool:
    try:
        if is_ip_banned(db, ip_address):
            return False

        security_settings = get_security_settings(db)
        threshold_404 = security_settings['404_threshold']
        ban_duration_404 = security_settings['404_ban_duration']
        now = datetime.utcnow()

        statement = select(Error404Tracker).where(Error404Tracker.ip_address == ip_address)
        tracker = db.exec(statement).first()

        if tracker:
            if (now - tracker.first_error_at).days >= 1:
                tracker.error_count = 1
                tracker.first_error_at = now
                tracker.paths_attempted = json.dumps([path])
            else:
                tracker.error_count += 1
                paths = json.loads(tracker.paths_attempted or '[]')
                if path not in paths:
                    paths.append(path)
                    tracker.paths_attempted = json.dumps(paths[-50:])
            tracker.last_error_at = now
            if tracker.error_count >= threshold_404:
                if ip_address not in ['127.0.0.1', '::1', 'localhost']:
                    ban_ip(db, ip_address=ip_address, reason=f"Exceeded 404 threshold: {tracker.error_count} errors in 24 hours", duration_hours=ban_duration_404, created_by='404_detector')
                    db.delete(tracker)
            else:
                db.add(tracker)
        else:
            tracker = Error404Tracker(ip_address=ip_address, error_count=1, paths_attempted=json.dumps([path]))
            db.add(tracker)

        db.commit()
        return True
    except Exception as e:
        logger.error(f"Error tracking 404: {e}")
        db.rollback()
        return False


def get_suspicious_ips(db: Session, min_errors: int = 5) -> List[Error404Tracker]:
    try:
        cutoff = datetime.utcnow() - timedelta(days=1)
        statement = select(Error404Tracker).where(Error404Tracker.first_error_at < cutoff)
        old_entries = db.exec(statement).all()
        for entry in old_entries:
            db.delete(entry)
        db.commit()

        statement = select(Error404Tracker).where(Error404Tracker.error_count >= min_errors).order_by(Error404Tracker.error_count.desc())
        return db.exec(statement).all()
    except Exception as e:
        logger.error(f"Error getting suspicious IPs: {e}")
        return []


def track_invalid_api_key(db: Session, ip_address: str, api_key_hash: Optional[str] = None) -> bool:
    try:
        if is_ip_banned(db, ip_address):
            return False

        security_settings = get_security_settings(db)
        threshold_api = security_settings['api_threshold']
        ban_duration_api = security_settings['api_ban_duration']
        now = datetime.utcnow()

        statement = select(InvalidAPIKeyTracker).where(InvalidAPIKeyTracker.ip_address == ip_address)
        tracker = db.exec(statement).first()

        if tracker:
            if (now - tracker.first_attempt_at).days >= 1:
                tracker.attempt_count = 1
                tracker.first_attempt_at = now
                tracker.api_keys_tried = json.dumps([api_key_hash] if api_key_hash else [])
            else:
                tracker.attempt_count += 1
                if api_key_hash:
                    keys_tried = json.loads(tracker.api_keys_tried or '[]')
                    if api_key_hash not in keys_tried:
                        keys_tried.append(api_key_hash)
                        tracker.api_keys_tried = json.dumps(keys_tried[-20:])
            tracker.last_attempt_at = now
            if tracker.attempt_count >= threshold_api:
                if ip_address not in ['127.0.0.1', '::1', 'localhost']:
                    if ban_ip(db, ip_address=ip_address, reason=f"Exceeded invalid API key threshold: {tracker.attempt_count} attempts in 24 hours", duration_hours=ban_duration_api, created_by='api_key_detector'):
                        db.delete(tracker)
                else:
                    db.add(tracker)
            else:
                db.add(tracker)
        else:
            tracker = InvalidAPIKeyTracker(ip_address=ip_address, attempt_count=1, api_keys_tried=json.dumps([api_key_hash] if api_key_hash else []))
            db.add(tracker)

        db.commit()
        return True
    except Exception as e:
        logger.error(f"Error tracking invalid API key: {e}")
        db.rollback()
        return False


def get_suspicious_api_users(db: Session, min_attempts: int = 3) -> List[InvalidAPIKeyTracker]:
    try:
        cutoff = datetime.utcnow() - timedelta(days=1)
        statement = select(InvalidAPIKeyTracker).where(InvalidAPIKeyTracker.first_attempt_at < cutoff)
        old_entries = db.exec(statement).all()
        for entry in old_entries:
            db.delete(entry)
        db.commit()

        statement = select(InvalidAPIKeyTracker).where(InvalidAPIKeyTracker.attempt_count >= min_attempts).order_by(InvalidAPIKeyTracker.attempt_count.desc())
        return db.exec(statement).all()
    except Exception as e:
        logger.error(f"Error getting suspicious API users: {e}")
        return []


def init_logs_db():
    db_path = LOGS_DATABASE_URL.replace('sqlite:///', '')
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    logger.info(f"Initializing Traffic Logs DB at: {LOGS_DATABASE_URL}")
    SQLModel.metadata.create_all(logs_engine)
