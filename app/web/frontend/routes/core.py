import base64
import io

import qrcode
from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import RedirectResponse
from app.web.frontend import templates

from app.db.schemas.auth_db import upsert_api_key
from app.db.schemas.user_db import add_user, find_user_by_username
from app.utils.auth_utils import generate_api_key
from app.utils.logging import get_logger
from app.utils.session import invalidate_session_if_invalid

logger = get_logger(__name__)

core_router = APIRouter()

@core_router.get("/")
async def home(request: Request, _=Depends(invalidate_session_if_invalid)):
    return templates.TemplateResponse("index.html", {"request": request})

@core_router.get("/download")
async def download(request: Request, _=Depends(invalidate_session_if_invalid)):
    return templates.TemplateResponse("download.html", {"request": request})

@core_router.get("/faq")
async def faq(request: Request, _=Depends(invalidate_session_if_invalid)):
    return templates.TemplateResponse("faq.html", {"request": request})

@core_router.get("/setup")
async def setup_form(request: Request):
    if find_user_by_username() is not None:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse("setup.html", {"request": request})

@core_router.post("/setup")
async def setup_submit(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...)
):
    if find_user_by_username() is not None:
        return RedirectResponse(url="/login", status_code=303)

    user = add_user(username, email, password, is_admin=True)
    if user:
        logger.info(f"New admin user {username} created successfully")
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
        img_buffer = io.BytesIO()
        qr.make_image(fill_color="black", back_color="white").save(img_buffer, format='PNG')
        qr_code = base64.b64encode(img_buffer.getvalue()).decode()

        request.session["totp_setup"] = True
        request.session["username"] = username
        request.session["qr_code"] = qr_code
        request.session["totp_secret"] = user.totp_secret
        request.session["flash_messages"] = [("success", "Account created successfully! Please configure your SMTP credentials in Profile settings for password recovery.")]
        
        return RedirectResponse(url="/login", status_code=303)
    else:
        logger.error(f"Failed to create admin user {username}")
        request.session["flash_messages"] = [("error", "User already exists or an error occurred")]
        return RedirectResponse(url="/setup", status_code=303)