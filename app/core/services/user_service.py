import pyotp
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.schemas.user_db import User


async def get_user_by_username(db: AsyncSession, username: str):
    result = await db.execute(select(User).filter(User.username == username))
    return result.scalars().first()


async def create_user(
    db: AsyncSession, username: str, email: str, password: str, is_admin: bool = False
):
    db_user = User(username=username, email=email, is_admin=is_admin)
    db_user.set_password(password)
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user


async def get_total_users_count(db: AsyncSession) -> int:
    """
    Returns the total number of users in the database.
    """
    result = await db.execute(select(func.count()).select_from(User))
    return result.scalar_one()


async def create_admin_user(db: AsyncSession, username: str, email: str, password: str):
    """
    Creates the initial admin user, hashes the password, and generates a TOTP secret.
    """
    if await get_total_users_count(db) > 0:
        return None  # Admin user already exists

    # Generate TOTP secret
    totp_secret = pyotp.random_base32()

    user = User(username=username, email=email, is_admin=True, totp_secret=totp_secret)
    user.set_password(password)
    db.add(user)
    await db.commit()
    await db.refresh(user)

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
