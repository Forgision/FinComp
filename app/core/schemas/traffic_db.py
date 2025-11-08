import json
import os
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    select,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from app.core.schemas import INIT_DB_REGISTRY, make_db_connection, DBConnectionConfig
from app.core.config import settings
from app.core.schemas.settings_db import get_security_settings
from app.utils.logging import logger


LOGS_DATABASE_URL = settings.LOGS_DATABASE_URL


logs_db_config = DBConnectionConfig(
    database_url=LOGS_DATABASE_URL,
    echo=False,
)


logs_engine, LogSessionLocal, get_logs_db = make_db_connection(logs_db_config)


class LogBase(DeclarativeBase):
    pass


async def init_log_db():
    db_path = LOGS_DATABASE_URL.replace('sqlite+aiosqlite:///', '')
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    logger.info(f"Initializing Traffic Logs DB at: {LOGS_DATABASE_URL}")
    
    async with logs_engine.begin() as conn:
        await conn.run_sync(LogBase.metadata.create_all)
    

INIT_DB_REGISTRY['logs_db'] = init_log_db


class TrafficLog(LogBase):
    __tablename__ = 'traffic_logs'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    client_ip: Mapped[str] = mapped_column(String(50), nullable=False)
    method: Mapped[str] = mapped_column(String(10), nullable=False)
    path: Mapped[str] = mapped_column(String(500), nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_ms: Mapped[float] = mapped_column(Float, nullable=False)
    host: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    error: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

class IPBan(LogBase):
    __tablename__ = 'ip_bans'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ip_address: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    ban_reason: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    ban_count: Mapped[int] = mapped_column(Integer, default=1)
    banned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_permanent: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by: Mapped[str] = mapped_column(String(50), default='system')

class Error404Tracker(LogBase):
    __tablename__ = 'error_404_tracker'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ip_address: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    error_count: Mapped[int] = mapped_column(Integer, default=1)
    first_error_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_error_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    paths_attempted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

class InvalidAPIKeyTracker(LogBase):
    __tablename__ = 'invalid_api_key_tracker'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ip_address: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=1)
    first_attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    api_keys_tried: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

async def log_request(db: AsyncSession, client_ip: str, method: str, path: str, status_code: int, duration_ms: float, host: Optional[str] = None, error: Optional[str] = None, user_id: Optional[int] = None) -> bool:
    try:
        log = TrafficLog(client_ip=client_ip, method=method, path=path, status_code=status_code, duration_ms=duration_ms, host=host, error=error, user_id=user_id)
        db.add(log)
        await db.commit()
        return True
    except Exception as e:
        logger.error(f"Error logging traffic: {str(e)}")
        await db.rollback()
        return False

async def get_recent_logs(db: AsyncSession, limit: int = 100) -> List[TrafficLog]:
    try:
        stmt = select(TrafficLog).order_by(TrafficLog.timestamp.desc()).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())
    except Exception as e:
        logger.error(f"Error getting recent logs: {str(e)}")
        return []

async def get_stats(db: AsyncSession) -> dict:
    try:
        total_requests = (await db.execute(select(func.count(TrafficLog.id)))).scalar_one_or_none() or 0
        error_requests = (await db.execute(select(func.count(TrafficLog.id)).filter(TrafficLog.status_code >= 400))).scalar_one_or_none() or 0
        avg_duration = (await db.execute(select(func.avg(TrafficLog.duration_ms)))).scalar_one_or_none() or 0
        return {'total_requests': total_requests, 'error_requests': error_requests, 'avg_duration': round(float(avg_duration), 2)}
    except Exception as e:
        logger.error(f"Error getting traffic stats: {str(e)}")
        return {'total_requests': 0, 'error_requests': 0, 'avg_duration': 0}

async def is_ip_banned(db: AsyncSession, ip_address: str) -> bool:
    try:
        stmt = select(IPBan).filter_by(ip_address=ip_address)
        result = await db.execute(stmt)
        ban = result.scalars().first()
        if not ban:
            return False
        if ban.is_permanent:
            return True
        if ban.expires_at and datetime.utcnow() < ban.expires_at:
            return True
        if ban.expires_at and datetime.utcnow() >= ban.expires_at:
            await db.delete(ban)
            await db.commit()
        return False
    except Exception as e:
        logger.error(f"Error checking IP ban status: {e}")
        await db.rollback()
        return False

async def ban_ip(db: AsyncSession, ip_address: str, reason: str, duration_hours: int = 24, permanent: bool = False, created_by: str = 'system') -> bool:
    try:
        if ip_address in ['127.0.0.1', '::1', 'localhost']:
            logger.warning(f"Attempted to ban localhost IP {ip_address} - ignoring")
            return False

        security_settings = await get_security_settings(db)
        repeat_limit = security_settings['repeat_offender_limit']

        stmt = select(IPBan).filter_by(ip_address=ip_address)
        result = await db.execute(stmt)
        existing_ban = result.scalars().first()

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
        else:
            ban = IPBan(ip_address=ip_address, ban_reason=reason, is_permanent=permanent, expires_at=None if permanent else datetime.utcnow() + timedelta(hours=duration_hours), created_by=created_by)
            db.add(ban)

        await db.commit()
        logger.info(f"IP {ip_address} banned: {reason}")
        return True
    except Exception as e:
        logger.error(f"Error banning IP {ip_address}: {e}")
        await db.rollback()
        return False

async def unban_ip(db: AsyncSession, ip_address: str) -> bool:
    try:
        stmt = select(IPBan).filter_by(ip_address=ip_address)
        result = await db.execute(stmt)
        ban = result.scalars().first()
        if ban:
            await db.delete(ban)
            await db.commit()
            logger.info(f"IP {ip_address} unbanned")
            return True
        return False
    except Exception as e:
        logger.error(f"Error unbanning IP: {e}")
        await db.rollback()
        return False

async def get_all_bans(db: AsyncSession) -> List[IPBan]:
    try:
        stmt_delete = select(IPBan).filter(IPBan.is_permanent.is_(False), IPBan.expires_at < datetime.utcnow())
        result_delete = await db.execute(stmt_delete)
        expired = result_delete.scalars().all()
        for ban in expired:
            await db.delete(ban)
        await db.commit()
        result_select = await db.execute(select(IPBan))
        return list(result_select.scalars().all())
    except Exception as e:
        logger.error(f"Error getting IP bans: {e}")
        return []

async def track_404(db: AsyncSession, ip_address: str, path: str) -> bool:
    try:
        if await is_ip_banned(db, ip_address):
            return False

        security_settings = await get_security_settings(db)
        threshold_404 = security_settings['404_threshold']
        ban_duration_404 = security_settings['404_ban_duration']
        now = datetime.utcnow()

        stmt = select(Error404Tracker).filter_by(ip_address=ip_address)
        result = await db.execute(stmt)
        tracker = result.scalars().first()

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
                    await ban_ip(db, ip_address=ip_address, reason=f"Exceeded 404 threshold: {tracker.error_count} errors in 24 hours", duration_hours=ban_duration_404, created_by='404_detector')
                    await db.delete(tracker)
        else:
            tracker = Error404Tracker(ip_address=ip_address, error_count=1, paths_attempted=json.dumps([path]))
            db.add(tracker)

        await db.commit()
        return True
    except Exception as e:
        logger.error(f"Error tracking 404: {e}")
        await db.rollback()
        return False

async def get_suspicious_ips(db: AsyncSession, min_errors: int = 5) -> List[Error404Tracker]:
    try:
        cutoff = datetime.utcnow() - timedelta(days=1)
        stmt_delete = select(Error404Tracker).filter(Error404Tracker.first_error_at < cutoff)
        result_delete = await db.execute(stmt_delete)
        old_entries = result_delete.scalars().all()
        for entry in old_entries:
            await db.delete(entry)
        await db.commit()

        stmt_select = select(Error404Tracker).filter(Error404Tracker.error_count >= min_errors).order_by(Error404Tracker.error_count.desc())
        result_select = await db.execute(stmt_select)
        return list(result_select.scalars().all())
    except Exception as e:
        logger.error(f"Error getting suspicious IPs: {e}")
        return []

async def track_invalid_api_key(db: AsyncSession, ip_address: str, api_key_hash: Optional[str] = None) -> bool:
    try:
        if await is_ip_banned(db, ip_address):
            return False

        security_settings = await get_security_settings(db)
        threshold_api = security_settings['api_threshold']
        ban_duration_api = security_settings['api_ban_duration']
        now = datetime.utcnow()

        stmt = select(InvalidAPIKeyTracker).filter_by(ip_address=ip_address)
        result = await db.execute(stmt)
        tracker = result.scalars().first()

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
                    if await ban_ip(db, ip_address=ip_address, reason=f"Exceeded invalid API key threshold: {tracker.attempt_count} attempts in 24 hours", duration_hours=ban_duration_api, created_by='api_key_detector'):
                        await db.delete(tracker)
        else:
            tracker = InvalidAPIKeyTracker(ip_address=ip_address, attempt_count=1, api_keys_tried=json.dumps([api_key_hash] if api_key_hash else []))
            db.add(tracker)

        await db.commit()
        return True
    except Exception as e:
        logger.error(f"Error tracking invalid API key: {e}")
        await db.rollback()
        return False

async def get_suspicious_api_users(db: AsyncSession, min_attempts: int = 3) -> List[InvalidAPIKeyTracker]:
    try:
        cutoff = datetime.utcnow() - timedelta(days=1)
        stmt_delete = select(InvalidAPIKeyTracker).filter(InvalidAPIKeyTracker.first_attempt_at < cutoff)
        result_delete = await db.execute(stmt_delete)
        old_entries = result_delete.scalars().all()
        for entry in old_entries:
            await db.delete(entry)
        await db.commit()

        stmt_select = select(InvalidAPIKeyTracker).filter(InvalidAPIKeyTracker.attempt_count >= min_attempts).order_by(InvalidAPIKeyTracker.attempt_count.desc())
        result_select = await db.execute(stmt_select)
        return list(result_select.scalars().all())
    except Exception as e:
        logger.error(f"Error getting suspicious API users: {e}")
        return []