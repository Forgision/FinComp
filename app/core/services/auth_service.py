from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from sqlmodel import Session, select

from app.core.config import settings
from app.core.models.user import User, add_user as register_user, authenticate_user as db_authenticate_user


ALGORITHM = "HS256"


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.APP_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    if db_authenticate_user(db, username, password):
        statement = select(User).where(User.username == username)
        return db.exec(statement).first()
    return None


def get_current_user(db: Session, token: str) -> Optional[User]:
    try:
        payload = jwt.decode(token, settings.APP_KEY, algorithms=[ALGORITHM])
        username: Optional[str] = payload.get("sub")
        if username is None:
            return None
    except JWTError:
        return None

    statement = select(User).where(User.username == username)
    return db.exec(statement).first()
