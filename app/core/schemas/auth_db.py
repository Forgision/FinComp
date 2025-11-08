# app/db/auth_db.py

import base64
from typing import Optional

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from cachetools import TTLCache
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from sqlalchemy import Boolean, DateTime, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.schemas import Base
from app.utils.logging import logger

# Initialize Argon2 hasher
ph = PasswordHasher()

PEPPER = settings.API_KEY_PEPPER


# Setup Fernet encryption for auth tokens
def get_encryption_key():
    """Generate a Fernet key from the pepper"""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"openalgo_static_salt",
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(PEPPER.encode()))
    return Fernet(key)


# Initialize Fernet cipher
fernet = get_encryption_key()


# Calculate cache TTL based on session expiry time to minimize DB hits
def get_session_based_cache_ttl():
    """Calculate cache TTL based on daily session expiry time in .env"""
    try:
        from datetime import datetime
        import pytz

        expiry_time = settings.SESSION_EXPIRY_TIME
        hour, minute = map(int, expiry_time.split(":"))
        now_utc = datetime.now(pytz.timezone("UTC"))
        now_ist = now_utc.astimezone(pytz.timezone("Asia/Kolkata"))
        today_expiry = now_ist.replace(
            hour=hour, minute=minute, second=0, microsecond=0
        )

        if now_ist >= today_expiry:
            from datetime import timedelta

            today_expiry += timedelta(days=1)

        time_until_expiry = (today_expiry - now_ist).total_seconds()
        ttl_seconds = max(300, min(time_until_expiry, 24 * 3600))
        logger.debug(
            f"Auth cache TTL set to {ttl_seconds} seconds until session expiry at {today_expiry.strftime('%H:%M IST')}"
        )
        return int(ttl_seconds)

    except Exception as e:
        logger.warning(
            f"Could not calculate session-based cache TTL, using 5-minute default: {e}"
        )
        return 300


auth_cache: TTLCache = TTLCache(maxsize=1024, ttl=get_session_based_cache_ttl())
feed_token_cache: TTLCache = TTLCache(maxsize=1024, ttl=get_session_based_cache_ttl())
broker_cache: TTLCache = TTLCache(maxsize=1024, ttl=3000)


class Auth(Base):
    __tablename__ = "auth"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    auth: Mapped[str] = mapped_column(Text, nullable=False)
    feed_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    broker: Mapped[str] = mapped_column(String(20), nullable=False)
    user_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False)


class ApiKeys(Base):
    __tablename__ = "api_keys"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    api_key_hash: Mapped[str] = mapped_column(Text, nullable=False)
    api_key_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), default=func.now()
    )


def encrypt_token(token: str) -> str:
    if not token:
        return ""
    return fernet.encrypt(token.encode()).decode()


def decrypt_token(encrypted_token: str) -> Optional[str]:
    if not encrypted_token:
        return ""
    try:
        return fernet.decrypt(encrypted_token.encode()).decode()
    except Exception as e:
        logger.error(f"Error decrypting token: {e}")
        return None


async def upsert_auth(
    db: AsyncSession,
    name: str,
    auth_token: str,
    broker: str,
    feed_token: Optional[str] = None,
    user_id: Optional[str] = None,
    revoke: bool = False,
) -> int:
    encrypted_token = encrypt_token(auth_token)
    encrypted_feed_token = encrypt_token(feed_token) if feed_token else None

    stmt = select(Auth).where(Auth.name == name)
    auth_obj = (await db.execute(stmt)).scalar_one_or_none()

    if auth_obj:
        auth_obj.auth = encrypted_token
        auth_obj.feed_token = encrypted_feed_token
        auth_obj.broker = broker
        auth_obj.user_id = user_id
        auth_obj.is_revoked = revoke
        if revoke:
            cache_key_auth = f"auth-{name}"
            cache_key_feed = f"feed-{name}"
            if cache_key_auth in auth_cache:
                del auth_cache[cache_key_auth]
            if cache_key_feed in feed_token_cache:
                del feed_token_cache[cache_key_feed]
            logger.info(f"Cleared cache entries for revoked tokens of user: {name}")
    else:
        auth_obj = Auth(
            name=name,
            auth=encrypted_token,
            feed_token=encrypted_feed_token,
            broker=broker,
            user_id=user_id,
            is_revoked=revoke,
        )
        db.add(auth_obj)
    await db.commit()
    return auth_obj.id


async def get_auth_token(db: AsyncSession, name: str) -> Optional[str]:
    if not name:
        logger.debug("get_auth_token called with empty/None name, returning None")
        return None

    cache_key = f"auth-{name}"
    cached_obj = auth_cache.get(cache_key)
    if isinstance(cached_obj, Auth) and not cached_obj.is_revoked:
        return decrypt_token(cached_obj.auth)

    auth_obj = await get_auth_token_dbquery(db, name)
    if isinstance(auth_obj, Auth) and not auth_obj.is_revoked:
        auth_cache[cache_key] = auth_obj
        return decrypt_token(auth_obj.auth)
    return None


async def get_auth_token_dbquery(db: AsyncSession, name: str) -> Optional[Auth]:
    if not name:
        logger.debug("get_auth_token_dbquery called with empty/None name")
        return None

    stmt = select(Auth).where(Auth.name == name)
    auth_obj = (await db.execute(stmt)).scalar_one_or_none()

    if auth_obj and not auth_obj.is_revoked:
        return auth_obj
    else:
        if name:
            logger.warning(f"No valid auth token found for name '{name}'.")
    return None


async def get_feed_token(db: AsyncSession, name: str) -> Optional[str]:
    if not name:
        logger.debug("get_feed_token called with empty/None name, returning None")
        return None

    cache_key = f"feed-{name}"
    cached_obj = feed_token_cache.get(cache_key)
    if isinstance(cached_obj, Auth) and not cached_obj.is_revoked:
        return decrypt_token(cached_obj.feed_token) if cached_obj.feed_token else None

    auth_obj = await get_feed_token_dbquery(db, name)
    if isinstance(auth_obj, Auth) and not auth_obj.is_revoked:
        feed_token_cache[cache_key] = auth_obj
        return decrypt_token(auth_obj.feed_token) if auth_obj.feed_token else None
    return None


async def get_feed_token_dbquery(db: AsyncSession, name: str) -> Optional[Auth]:
    if not name:
        logger.debug("get_feed_token_dbquery called with empty/None name")
        return None

    stmt = select(Auth).where(Auth.name == name)
    auth_obj = (await db.execute(stmt)).scalar_one_or_none()

    if auth_obj and not auth_obj.is_revoked:
        return auth_obj
    else:
        if name:
            logger.warning(f"No valid feed token found for name '{name}'.")
        return None


async def get_user_id(db: AsyncSession, name: str) -> Optional[str]:
    if not name:
        logger.debug("get_user_id called with empty/None name")
        return None

    stmt = select(Auth).where(Auth.name == name)
    auth_obj = (await db.execute(stmt)).scalar_one_or_none()

    if auth_obj and not auth_obj.is_revoked:
        return auth_obj.user_id
    else:
        if name:
            logger.warning(f"No valid user_id found for name '{name}'.")
        return None


async def upsert_api_key(db: AsyncSession, user_id: str, api_key: str):
    peppered_key = api_key + PEPPER
    hashed_key = ph.hash(peppered_key)
    encrypted_key = encrypt_token(api_key)

    stmt = select(ApiKeys).where(ApiKeys.user_id == user_id)
    api_key_obj = (await db.execute(stmt)).scalar_one_or_none()

    if api_key_obj:
        api_key_obj.api_key_hash = hashed_key
        api_key_obj.api_key_encrypted = encrypted_key
    else:
        api_key_obj = ApiKeys(
            user_id=user_id, api_key_hash=hashed_key, api_key_encrypted=encrypted_key
        )
        db.add(api_key_obj)
    await db.commit()
    return api_key_obj.id


async def get_api_key(db: AsyncSession, user_id: str) -> bool:
    stmt = select(ApiKeys).where(ApiKeys.user_id == user_id)
    api_key_obj = (await db.execute(stmt)).scalar_one_or_none()
    return api_key_obj is not None


async def get_api_key_for_tradingview(db: AsyncSession, user_id: str) -> Optional[str]:
    stmt = select(ApiKeys).where(ApiKeys.user_id == user_id)
    api_key_obj = (await db.execute(stmt)).scalar_one_or_none()
    if api_key_obj and api_key_obj.api_key_encrypted:
        return decrypt_token(api_key_obj.api_key_encrypted)
    return None


async def verify_api_key(db: AsyncSession, provided_api_key: str) -> Optional[str]:
    import hashlib
    from flask import has_request_context
    from app.core.schemas.traffic_db import track_invalid_api_key
    from app.utils.ip_helper import get_real_ip

    peppered_key = provided_api_key + PEPPER

    stmt = select(ApiKeys)
    api_keys = (await db.execute(stmt)).scalars().all()

    for api_key_obj in api_keys:
        try:
            ph.verify(api_key_obj.api_key_hash, peppered_key)
            return api_key_obj.user_id
        except VerifyMismatchError:
            continue

    try:
        client_ip = get_real_ip() if has_request_context() else "127.0.0.1"
        if client_ip is None:
            client_ip = "127.0.0.1"
        api_key_hash = hashlib.sha256(provided_api_key.encode()).hexdigest()[:16]
        await track_invalid_api_key(db, client_ip, api_key_hash)
    except Exception as track_error:
        logger.warning(f"Could not track invalid API key attempt: {track_error}")

    return None


async def get_username_by_apikey(
    db: AsyncSession, provided_api_key: str
) -> Optional[str]:
    return await verify_api_key(db, provided_api_key)


async def get_broker_name(db: AsyncSession, provided_api_key: str) -> Optional[str]:
    if provided_api_key in broker_cache:
        return broker_cache[provided_api_key]

    user_id = await verify_api_key(db, provided_api_key)

    if user_id:
        stmt = select(Auth).where(Auth.name == user_id)
        auth_obj = (await db.execute(stmt)).scalar_one_or_none()
        if auth_obj and not auth_obj.is_revoked:
            broker_cache[provided_api_key] = auth_obj.broker
            return auth_obj.broker
        else:
            logger.warning(f"No valid broker found for user_id '{user_id}'.")
            return None
    return None


async def get_auth_token_broker(
    db: AsyncSession, provided_api_key: str, include_feed_token: bool = False
):
    user_id = await verify_api_key(db, provided_api_key)

    if user_id:
        try:
            stmt = select(Auth).where(Auth.name == user_id)
            auth_obj = (await db.execute(stmt)).scalar_one_or_none()
            if auth_obj and not auth_obj.is_revoked:
                decrypted_token = decrypt_token(auth_obj.auth)
                if include_feed_token:
                    decrypted_feed_token = (
                        decrypt_token(auth_obj.feed_token)
                        if auth_obj.feed_token
                        else None
                    )
                    return decrypted_token, decrypted_feed_token, auth_obj.broker
                return decrypted_token, auth_obj.broker
            else:
                logger.warning(
                    f"No valid auth token or broker found for user_id '{user_id}'."
                )
                return (None, None, None) if include_feed_token else (None, None)
        except Exception as e:
            logger.error(
                f"Error while querying the database for auth token and broker: {e}"
            )
            return (None, None, None) if include_feed_token else (None, None)
    else:
        return (None, None, None) if include_feed_token else (None, None)


async def delete_api_key_by_username(db: AsyncSession, user_id: str) -> bool:
    stmt = select(ApiKeys).where(ApiKeys.user_id == user_id)
    api_key_obj = (await db.execute(stmt)).scalar_one_or_none()
    if api_key_obj:
        await db.delete(api_key_obj)
        await db.commit()
        return True
    return False
