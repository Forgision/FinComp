# app/core/models/user.py
from typing import Optional
import pyotp
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from cachetools import TTLCache
from sqlalchemy.exc import IntegrityError
from sqlmodel import Field, Session, SQLModel, select

from app.core.config import settings
from app.db.session import engine  # Import engine for init_db
from app.utils.logging import logger

# Initialize Argon2 hasher
ph = PasswordHasher()

# Database connection details
PASSWORD_PEPPER = settings.API_KEY_PEPPER

# Define a cache for the usernames with a max size and a 30-second TTL
username_cache: TTLCache = TTLCache(maxsize=1024, ttl=30)

class User(SQLModel, table=True):
    __tablename__ = 'users'
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, max_length=80, sa_column_kwargs={"unique": True, "nullable": False})
    email: str = Field(index=True, max_length=120, sa_column_kwargs={"unique": True, "nullable": False})
    password_hash: str = Field(max_length=255, nullable=False)
    totp_secret: str = Field(max_length=32, nullable=False)
    is_admin: bool = Field(default=False)

    def set_password(self, password: str):
        """Hash password using Argon2 with pepper"""
        peppered_password = password + PASSWORD_PEPPER
        self.password_hash = ph.hash(peppered_password)

    def check_password(self, password: str, db: Optional[Session] = None) -> bool:
        """Verify password using Argon2 with pepper"""
        peppered_password = password + PASSWORD_PEPPER
        try:
            ph.verify(self.password_hash, peppered_password)
            if db and ph.check_needs_rehash(self.password_hash):
                self.set_password(password)
                db.add(self)
                db.commit()
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
    logger.info("Initializing User DB")
    SQLModel.metadata.create_all(bind=engine)

def add_user(db: Session, username: str, email: str, password: str, is_admin: bool = False) -> Optional[User]:
    try:
        totp_secret = pyotp.random_base32()
        user = User(
            username=username,
            email=email,
            totp_secret=totp_secret,
            is_admin=is_admin,
            password_hash="" # Initialize
        )
        user.set_password(password)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    except IntegrityError:
        db.rollback()
        return None

def authenticate_user(db: Session, username: str, password: str) -> bool:
    """Authenticate user with Argon2 hashed password"""
    cache_key = f"user-{username}"
    cached_user = username_cache.get(cache_key)

    if cached_user and isinstance(cached_user, User):
        if cached_user.check_password(password, db=db):
            return True
        else:
            if cache_key in username_cache:
                 del username_cache[cache_key]
            return False

    statement = select(User).where(User.username == username)
    user = db.exec(statement).first()

    if user and user.check_password(password, db=db):
        username_cache[cache_key] = user
        return True

    username_cache[cache_key] = None
    return False

def find_user_by_email(db: Session, email: str) -> Optional[User]:
    """Find user by email for password reset"""
    statement = select(User).where(User.email == email)
    return db.exec(statement).first()

def find_admin_user(db: Session) -> Optional[User]:
    """Find admin user"""
    statement = select(User).where(User.is_admin == True)
    return db.exec(statement).first()

def rehash_all_passwords(db: Session):
    """
    Utility function to rehash all existing passwords with Argon2.
    """
    users = db.exec(select(User)).all()
    for user in users:
        if user.password_hash.startswith('pbkdf2:sha256'):
            # This part requires a strategy for getting original passwords,
            # which is outside the scope of this migration.
            # For now, we just demonstrate the rehashing would be triggered.
            pass
    db.commit()

def delete_user_by_username(db: Session, username: str) -> bool:
    """Delete a user by username."""
    statement = select(User).where(User.username == username)
    user = db.exec(statement).first()
    if user:
        db.delete(user)
        db.commit()
        cache_key = f"user-{username}"
        if cache_key in username_cache:
            del username_cache[cache_key]
        return True
    return False
