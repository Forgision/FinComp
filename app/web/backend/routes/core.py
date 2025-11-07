import base64
import io

import qrcode
from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.schemas.auth_db import upsert_api_key
from app.core.schemas import get_db
from app.core.schemas.user_db import add_user, find_user_by_username
from app.utils.logging import logger
from app.utils.web.security import (
    generate_api_key,  # Assuming this path based on design principles
)

core_router = APIRouter()

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
        # flash(request, 'Account created successfully! Please configure your SMTP credentials in Profile settings for password recovery.', 'success')
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)
    else:
        # If the user already exists or an error occurred, show an error message
        logger.error(f"Failed to create admin user {username}")
        # flash(request, 'User already exists or an error occurred', 'error')
        return JSONResponse(content={"error_message": "User already exists or an error occurred"}, status_code=400)
