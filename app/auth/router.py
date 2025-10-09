from fastapi import APIRouter, Request, Depends, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.core.config import settings
from app.db.session import get_db
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.auth import Auth
from app.utils.logging import get_logger
from app.utils.web.security import verify_password
from app.services import user_service
import os
import re

logger = get_logger(__name__)

# Initialize Jinja2Templates
templates = Jinja2Templates(directory="templates")

auth_router = APIRouter()

# Rate limiting will be handled as a dependency or middleware later
# For now, we'll implement the basic login logic

@auth_router.get("/login", response_class=HTMLResponse)
async def login_get(request: Request, db: Session = Depends(get_db)):
    if user_service.get_total_users_count(db) == 0:
        return RedirectResponse(url="/setup", status_code=status.HTTP_302_FOUND)

    if request.session.get('logged_in'): # Check if already logged in
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    
    return templates.TemplateResponse("login.html", {"request": request})

@auth_router.post("/login")
async def login_post(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = user_service.get_user_by_username(db, username)
    if user and verify_password(password, user.password_hash):
        request.session['user'] = username
        request.session['logged_in'] = True  # Set session as logged in
        logger.info(f"Login success for user: {username}")
        # This will eventually redirect to a broker login or dashboard
        return RedirectResponse(url="/auth/broker", status_code=status.HTTP_302_FOUND)
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )