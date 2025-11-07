from datetime import datetime, timedelta
from typing import Optional

import pyotp
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.schemas.user_db import User
from app.utils.web.security import verify_password

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


async def authenticate_user(username: str, password: str, db: AsyncSession) -> Optional[User]:
    stmt = select(User).where(User.username == username)
    user = await db.execute(stmt).scalar_one_or_none()
    if not user or not verify_password(password, user.password_hash):
        return None
    return user


async def get_current_user(token: str, db: AsyncSession) -> Optional[User]:
    try:
        payload = jwt.decode(token, settings.APP_KEY, algorithms=[ALGORITHM])
        username: Optional[str] = payload.get("sub")
        if username is None:
            return None
    except JWTError:
        return None

    stmt = select(User).where(User.username == username)
    user = await db.execute(stmt).scalar_one_or_none()
    return user


async def register_user(username: str, email: str, password: str, db: AsyncSession) -> User:
    totp_secret = pyotp.random_base32()
    new_user = User(username=username, email=email, totp_secret=totp_secret)
    new_user.set_password(password)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user
