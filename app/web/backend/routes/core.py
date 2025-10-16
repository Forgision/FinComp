import qrcode
import io
import base64

from fastapi import APIRouter, Depends, Request, Form, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.utils.logging import logger
from app.db.session import get_db
from app.db.user_db import add_user, find_user_by_username
from app.db.auth_db import upsert_api_key
from app.utils.session import check_session_validity_fastapi
from app.utils.web.flash import flash
from app.web.frontend import templates
from app.utils.web.security import generate_api_key # Assuming this path based on design principles


core_router = APIRouter()

@core_router.get('/')
async def home(request: Request, db: Session = Depends(get_db), _: bool = Depends(check_session_validity_fastapi)):
    return templates.TemplateResponse('index.html', {"request": request})

@core_router.get('/download')
async def download(request: Request, db: Session = Depends(get_db), _: bool = Depends(check_session_validity_fastapi)):
    return templates.TemplateResponse('download.html', {"request": request})

@core_router.get('/faq')
async def faq(request: Request, db: Session = Depends(get_db), _: bool = Depends(check_session_validity_fastapi)):
    return templates.TemplateResponse('faq.html', {"request": request})

@core_router.get('/setup')
async def get_setup(request: Request, db: Session = Depends(get_db)):
    if find_user_by_username(db) is not None:
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse('setup.html', {"request": request})

@core_router.post('/setup')
async def post_setup(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    if find_user_by_username(db) is not None:
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)

    # Add the new admin user
    user = add_user(db, username, email, password, is_admin=True)
    if user:
        logger.info(f"New admin user {username} created successfully")

        # Automatically generate and save API key
        api_key = generate_api_key()
        key_id = upsert_api_key(db, username, api_key)
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
        flash(request, 'Account created successfully! Please configure your SMTP credentials in Profile settings for password recovery.', 'success')
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)
    else:
        # If the user already exists or an error occurred, show an error message
        logger.error(f"Failed to create admin user {username}")
        flash(request, 'User already exists or an error occurred', 'error')
        return templates.TemplateResponse('setup.html', {"request": request, "error_message": "User already exists or an error occurred"})
