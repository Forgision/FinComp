from datetime import datetime, timedelta
import pytz
from functools import wraps
from typing import Dict, Any, Optional

from fastapi import Request, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from .logging import logger

# Placeholder for get_db and Session. Will be properly imported in main.py
# from app.db.connection import get_db


def get_session_expiry_time():
    """Get session expiry time set to 3 AM IST next day"""
    now_utc = datetime.now(pytz.timezone('UTC'))
    now_ist = now_utc.astimezone(pytz.timezone('Asia/Kolkata'))
    
    # Get configured expiry time or default to 3 AM
    from app.core.config import settings
    expiry_time = settings.SESSION_EXPIRY_TIME
    hour, minute = map(int, expiry_time.split(':'))
    
    target_time_ist = now_ist.replace(hour=hour, minute=minute, second=0, microsecond=0)
    
    # If current time is past target time, set expiry to next day
    if now_ist > target_time_ist:
        target_time_ist += timedelta(days=1)
    
    remaining_time = target_time_ist - now_ist
    logger.debug(f"Session expiry time set to: {target_time_ist}")
    return remaining_time

def set_session_login_time(request: Request):
    """Set the session login time in IST for FastAPI"""
    now_utc = datetime.now(pytz.timezone('UTC'))
    now_ist = now_utc.astimezone(pytz.timezone('Asia/Kolkata'))
    request.session['login_time'] = now_ist.isoformat()
    logger.info(f"Session login time set to: {now_ist}")

async def is_session_valid_fastapi(request: Request) -> bool:
    """Check if the current session is valid for FastAPI"""
    if not request.session.get('logged_in'):
        logger.debug("Session invalid: 'logged_in' flag not set")
        return False
    
    if 'user' not in request.session:
        logger.debug("Session invalid: 'user' not in session")
        return False

    # If no login time is set, consider session invalid
    if 'login_time' not in request.session:
        logger.debug("Session invalid: 'login_time' not in session")
        return False
        
    now_utc = datetime.now(pytz.timezone('UTC'))
    now_ist = now_utc.astimezone(pytz.timezone('Asia/Kolkata'))
    
    # Parse login time
    login_time = datetime.fromisoformat(request.session['login_time'])
    
    # Get configured expiry time
    expiry_time = settings.SESSION_EXPIRY_TIME
    hour, minute = map(int, expiry_time.split(':'))
    
    # Get today's expiry time
    daily_expiry = now_ist.replace(hour=hour, minute=minute, second=0, microsecond=0)
    
    # If current time is past expiry time and login was before expiry time
    if now_ist > daily_expiry and login_time < daily_expiry:
        logger.info(f"Session expired at {daily_expiry} IST")
        return False
    
    logger.debug(f"Session valid. Current time: {now_ist}, Login time: {login_time}, Daily expiry: {daily_expiry}")
    return True

async def revoke_user_tokens_fastapi(request: Request, db: Session):
    """Revoke auth tokens for the current user when session expires for FastAPI"""
    if 'user' in request.session:
        username = request.session.get('user')
        try:
            # Local import to avoid circular dependencies
            from app.db.auth_db import upsert_auth, auth_cache, feed_token_cache
            from app.db.master_contract_cache_hook import clear_cache_on_logout
            
            # Clear cache entries first to prevent stale data access
            cache_key_auth = f"auth-{username}"
            cache_key_feed = f"feed-{username}"
            if cache_key_auth in auth_cache:
                del auth_cache[cache_key_auth]
            if cache_key_feed in feed_token_cache:
                del feed_token_cache[cache_key_feed]
            
            # Clear symbol cache on logout/session expiry
            try:
                clear_cache_on_logout()
            except Exception as cache_error:
                logger.error(f"Error clearing symbol cache: {cache_error}")
            
            # Revoke the auth token in database
            inserted_id = upsert_auth(db, username, "", "", revoke=True)
            if inserted_id is not None:
                logger.info(f"Auto-expiry: Revoked auth tokens for user: {username}")
            else:
                logger.error(f"Auto-expiry: Failed to revoke auth tokens for user: {username}")
        except Exception as e:
            logger.error(f"Error revoking tokens during auto-expiry for user {username}: {e}")

async def check_session_validity_fastapi(request: Request, db: Session = Depends(None)) -> Dict[str, Any]:
    """
    FastAPI dependency to check session validity.
    Raises HTTPException if session is invalid, otherwise returns user data.
    """
    # NOTE: db: Session = Depends(None) is a placeholder.
    # get_db will be injected by FastAPI in the actual route.
    # This is to avoid circular dependency here.
    from app.db.session import get_db
    if db is None:
        db = next(get_db())

    if not await is_session_valid_fastapi(request):
        logger.info("Invalid session detected - revoking tokens and clearing session")
        await revoke_user_tokens_fastapi(request, db)
        request.session.clear()
        
        # For API endpoints, raise HTTPException
        if request.url.path.startswith("/api"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session expired or invalid. Please log in again."
            )
        # For web UI, redirect
        else:
            # This redirect won't work directly as a dependency that raises.
            # Routes calling this dependency would need to handle the RedirectResponse.
            # However, for API routes, HTTPException is appropriate.
            logger.warning("Attempted to redirect from FastAPI dependency, this might not work as expected for non-API routes.")
            raise HTTPException(
                status_code=status.HTTP_307_TEMPORARY_REDIRECT,
                detail="Redirecting to login",
                headers={"Location": "/login"}  # Assuming /login is your login page
            )
    
    user_data = request.session.get('user')
    logger.debug("Session validated successfully for FastAPI.")
    return user_data

async def invalidate_session_if_invalid_fastapi(request: Request, db: Session = Depends(None)):
    """
    FastAPI dependency to invalidate session if invalid without raising HTTPException.
    """
    from app.db.session import get_db
    if db is None:
        db = next(get_db())

    if not await is_session_valid_fastapi(request):
        logger.info("Invalid session detected - clearing session (FastAPI)")
        await revoke_user_tokens_fastapi(request, db)
        request.session.clear()
