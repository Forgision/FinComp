# db/user_db.py
# This file manages the user database using SQLAlchemy and Argon2 for password hashing.
from typing import Optional
import pyotp
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from cachetools import (
    TTLCache,
)
from sqlalchemy import Boolean, Integer, String, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import settings
from app.core.schemas import Base
from app.core.schemas.session import db_session
from app.utils.logging import logger

# Initialize Argon2 hasher
ph = PasswordHasher()

# Database connection details
PASSWORD_PEPPER = settings.API_KEY_PEPPER  # We'll use the same pepper for consistency

# Define a cache for the usernames with a max size and a 30-second TTL
username_cache: TTLCache = TTLCache(maxsize=1024, ttl=30)

class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    totp_secret: Mapped[str] = mapped_column(String(32), nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)

    def __init__(self, username: str, email: str, totp_secret: str, is_admin: bool = False):
        self.username = username
        self.email = email
        self.totp_secret = totp_secret
        self.is_admin = is_admin
        self.password_hash = ""  # Initialize with an empty string

    def set_password(self, password: str):
        """Hash password using Argon2 with pepper"""
        peppered_password = password + PASSWORD_PEPPER
        self.password_hash = ph.hash(peppered_password)

    def check_password(self, password: str) -> bool:
        """Verify password using Argon2 with pepper"""
        peppered_password = password + PASSWORD_PEPPER
        try:
            ph.verify(self.password_hash, peppered_password)
            # Check if the hash needs to be updated
            if ph.check_needs_rehash(self.password_hash):
                self.set_password(password)
                db_session.commit()
            return True
        except VerifyMismatchError:
            return False

    def get_totp_uri(self) -> str:
        """Get the TOTP URI for QR code generation"""
        return pyotp.totp.TOTP(self.totp_secret).provisioning_uri(
            name=self.email,
            issuer_name="OpenAlgo"
        )

    def verify_totp(self, token: str) -> bool:
        """Verify TOTP token"""
        totp = pyotp.TOTP(self.totp_secret)
        return totp.verify(token)

def init_db():
    from app.core.schemas.session import engine
    logger.info("Initializing User DB")
    Base.metadata.create_all(bind=engine)

def add_user(username: str, email: str, password: str, is_admin: bool = False) -> Optional[User]:
    try:
        # Generate TOTP secret for the user
        totp_secret = pyotp.random_base32()
        user = User(
            username=username,
            email=email,
            totp_secret=totp_secret,
            is_admin=is_admin
        )
        user.set_password(password)
        db_session.add(user)
        db_session.commit()
        return user  # Return the user object instead of True
    except IntegrityError:
        db_session.rollback()
        return None  # Return None instead of False

def authenticate_user(username: str, password: str) -> bool:
    """Authenticate user with Argon2 hashed password"""
    cache_key = f"user-{username}"
    cached_user = username_cache.get(cache_key)

    if cached_user and isinstance(cached_user, User):
        if cached_user.check_password(password):
            return True
        else:
            # Invalid password, remove from cache
            del username_cache[cache_key]
            return False

    stmt = select(User).filter_by(username=username)
    user = db_session.execute(stmt).scalars().first()

    if user and user.check_password(password):
        username_cache[cache_key] = user  # Cache the User object
        return True

    username_cache[cache_key] = None  # Cache the None value to prevent repeated lookups
    return False

def find_user_by_email(email: str) -> Optional[User]:
    """Find user by email for password reset"""
    stmt = select(User).filter_by(email=email)
    return db_session.execute(stmt).scalars().first()

def find_admin_user() -> Optional[User]:
    """Find admin user"""
    stmt = select(User).filter_by(is_admin=True)
    return db_session.execute(stmt).scalars().first()

def rehash_all_passwords():
    """
    Utility function to rehash all existing passwords with Argon2.
    This should be called once when upgrading from the old hashing method.
    Requires knowing the original passwords or having users reset them.
    """
    stmt = select(User)
    users = db_session.execute(stmt).scalars().all()
    for user in users:
        if user.password_hash.startswith('pbkdf2:sha256'):  # Old Werkzeug format
            # At this point, you would either:
            # 1. Have users reset their passwords
            # 2. Or if you have access to original passwords (during migration):
            #    user.set_password(original_password)
            pass
    db_session.commit()

def delete_user_by_username(username: str) -> bool:
    """Delete a user by username."""
    stmt = select(User).filter_by(username=username)
    user = db_session.execute(stmt).scalars().first()
    if user:
        db_session.delete(user)
        db_session.commit()
        if f"user-{username}" in username_cache:
            del username_cache[f"user-{username}"]
        return True
    return False
