from sqlalchemy.orm import Session
from app.models.user import User
from app.utils.logging import get_logger

logger = get_logger(__name__)

def get_user_by_username(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()

def create_user(db: Session, username: str, email: str, password_hash: str, is_admin: bool = False):
    db_user = User(username=username, email=email, password_hash=password_hash, totp_secret="", is_admin=is_admin)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_total_users_count(db: Session) -> int:
    """
    Returns the total number of users in the database.
    """
    return db.query(User).count()
