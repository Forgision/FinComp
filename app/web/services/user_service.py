from sqlalchemy.orm import Session
from ..models.user import User
from ...utils.logging import get_logger
from ...utils.web.security import hash_password
import pyotp
import secrets

logger = get_logger(__name__)

def get_user_by_username(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()

def create_user(db: Session, username: str, email: str, password: str, is_admin: bool = False):
    password_hash = hash_password(password)
    db_user = User(username=username, email=email, password_hash=password_hash, is_admin=is_admin)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_total_users_count(db: Session) -> int:
    """
    Returns the total number of users in the database.
    """
    return db.query(User).count()

def generate_api_key():
    """Generates a secure, random API key."""
    return secrets.token_urlsafe(32)

def create_admin_user(db: Session, username: str, email: str, password: str):
    """
    Creates the initial admin user, hashes the password, and generates a TOTP secret.
    """
    if get_total_users_count(db) > 0:
        return None  # Admin user already exists

    password_hash = hash_password(password)
    
    # Generate TOTP secret
    totp_secret = pyotp.random_base32()

    user = User(
        username=username,
        email=email,
        password_hash=password_hash,
        is_admin=True,
        totp_secret=totp_secret
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # In a real app, you would also create and store the API key here
    # and associate it with the user.

    return user

def get_totp_uri(user: User) -> str:
    """
    Returns the TOTP provisioning URI for the user.
    """
    return pyotp.totp.TOTP(user.totp_secret).provisioning_uri(
        name=user.username, issuer_name="OpenAlgo"
    )
