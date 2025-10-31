from sqlmodel import Session, select

from app.core.models.user import User, add_user


def get_user_by_username(db: Session, username: str) -> User | None:
    statement = select(User).where(User.username == username)
    return db.exec(statement).first()


def get_total_users_count(db: Session) -> int:
    """
    Returns the total number of users in the database.
    """
    return db.query(User).count()


def create_admin_user(db: Session, username: str, email: str, password: str) -> User | None:
    """
    Creates the initial admin user.
    """
    if get_total_users_count(db) > 0:
        return None  # Admin user already exists

    return add_user(db, username, email, password, is_admin=True)
