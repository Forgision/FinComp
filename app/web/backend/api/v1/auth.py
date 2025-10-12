from typing import Annotated
from fastapi import APIRouter, Request, Depends, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.core.config import settings
from .....db.session import get_db
from .....db.user_db import add_user, find_user_by_username
from .....db.auth_db import upsert_api_key
from sqlalchemy.orm import Session
from ....frontend import templates
from ....models.user import User
from ....models.auth import Auth
from app.utils.logging import get_logger
from app.utils.web.security import verify_password
from ....frontend import templates
from ....services import user_service
from .....utils.web.flash import flash
from .....utils.web.security import generate_api_key
import qrcode
import io
import base64

logger = get_logger(__name__)

auth_router = APIRouter(prefix="/auth", tags=["auth"])

# Rate limiting will be handled as a dependency or middleware later
# For now, we'll implement the basic login logic

@auth_router.get("/login", name="auth.login")
async def login_get(request: Request):
    if user_service.get_total_users_count(get_db()) == 0:
        return RedirectResponse(url=auth_router.url_path_for('setup'), status_code=status.HTTP_302_FOUND)

    if request.session.get('logged_in'): # Check if already logged in
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    
    return templates.TemplateResponse("login.html", {"request": request})

@auth_router.post("/login", name="auth.login")
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

@auth_router.post("/logout", name="auth.logout")
async def logout(request: Request):
    request.session.clear()
    flash(request, "You have been logged out.", "success")
    return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)

@auth_router.route('/setup', methods=['GET', 'POST'], name="setup")
async def setup(request: Request, db: Session = Depends(get_db)):
    if user_service.get_total_users_count(db) > 0:
        flash(request, "Setup has already been completed.", "warning")
        return RedirectResponse(url=auth_router.url_path_for('auth.login'))

    if request.method == 'POST':
        form = await request.form()
        username = form.get("username")
        email = form.get("email")
        password = form.get("password")
        
        # Add the new admin user
        user = add_user(db, username, email, password, is_admin=True)
        if user:
            logger.info(f"New admin user {username} created successfully")
            
            # Automatically generate and save API key
            api_key = generate_api_key()
            key_id = upsert_api_key(username, api_key)
            if not key_id:
                logger.error(f"Failed to create API key for user {username}")
            else:
                logger.info(f"API key created successfully for user {username}")
            
            # Generate QR code
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(user.get_totp_uri())
            qr.make(fit=True)
            
            # Create QR code image
            img_buffer = io.BytesIO()
            qr.make_image(fill_color="black", back_color="white").save(img_buffer, format='PNG')
            qr_code = base64.b64encode(img_buffer.getvalue()).decode()
            
            # Store TOTP setup in session temporarily for later access if needed
            request.session['totp_setup'] = True
            request.session['username'] = username
            request.session['qr_code'] = qr_code
            request.session['totp_secret'] = user.totp_secret
            
            # Flash message with SMTP setup info and redirect to login
            flash('Account created successfully! Please configure your SMTP credentials in Profile settings for password recovery.', 'success')
            return RedirectResponse(auth_router.url_path_for('auth.login'))
        else:
            # If the user already exists or an error occurred, show an error message
            logger.error(f"Failed to create admin user {username}")
            flash('User already exists or an error occurred', 'error')
            return RedirectResponse(auth_router.url_path_for('setup'))
            
    return templates.TemplateResponse("setup.html", {"request": request})