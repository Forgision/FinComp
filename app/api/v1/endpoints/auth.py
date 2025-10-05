from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session
from app.schemas.auth import UserLogin, NewPassword, TOTPVerification, PasswordResetRequest, ChangePassword, SMTPSettings, TestEmail
from app.db.session import get_db
from database.user_db import authenticate_user, find_user_by_username, find_user_by_email, User, db_session
from database.settings_db import get_smtp_settings, set_smtp_settings
from utils.email_utils import send_test_email, send_password_reset_email
from utils.email_debug import debug_smtp_connection
from utils.logging import get_logger
from app.core.config import settings
import secrets
import re
import os

router = APIRouter()
logger = get_logger(__name__)

@router.post("/login")
async def login(user_login: UserLogin, request: Request, db: Session = Depends(get_db)):
    # This is a placeholder. In a real FastAPI app, you'd handle sessions/tokens differently.
    # For now, we'll mimic the Flask behavior as much as possible for migration.
    
    # Check if a user exists, if not, redirect to setup (mimicking Flask's behavior)
    if find_user_by_username() is None:
        return RedirectResponse(url="/setup", status_code=status.HTTP_302_FOUND)

    # If already logged in (based on session), redirect to broker login
    if request.session.get('user'):
        return RedirectResponse(url="/auth/broker", status_code=status.HTTP_302_FOUND)

    if authenticate_user(user_login.username, user_login.password):
        request.session['user'] = user_login.username
        logger.info(f"Login success for user: {user_login.username}")
        return JSONResponse(content={"status": "success"}, status_code=status.HTTP_200_OK)
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

# Placeholder for other auth routes
# @router.post("/reset-password")
# @router.get("/reset-password-email/{token}")
# @router.post("/change")
# @router.post("/smtp-config")
# @router.post("/test-smtp")
# @router.post("/debug-smtp")
# @router.get("/logout")