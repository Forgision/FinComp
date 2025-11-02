import os
import re
import secrets

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel, EmailStr
from argon2 import PasswordHasher

from app.core.config import settings
from app.core.schemas.auth_db import auth_cache, feed_token_cache, upsert_auth
from app.core.schemas.settings_db import get_smtp_settings, set_smtp_settings
from app.core.schemas.user_db import (
    User,
    authenticate_user,
    find_user_by_email,
    find_admin_user,
)
from app.core.schemas import get_db
from app.utils.email_debug import debug_smtp_connection
from app.utils.email_utils import send_password_reset_email, send_test_email
from app.utils.logging import logger
from app.utils.session import check_session_validity_fastapi
from app.utils.web.limiter import limiter
from app.web.frontend import templates

auth_router = APIRouter(prefix="/auth", tags=["auth"])

ph = PasswordHasher()

class UserLogin(BaseModel):
    username: str
    password: str

class ResetPasswordEmail(BaseModel):
    email: EmailStr

class ResetPasswordTotp(BaseModel):
    email: EmailStr
    totp_code: str

class ResetPassword(BaseModel):
    email: EmailStr
    token: str
    password: str

@auth_router.get("/login", response_class=HTMLResponse, name="auth.login")
async def login_get(request: Request):
    if find_admin_user() is None:
        return RedirectResponse(url='/setup', status_code=status.HTTP_32_FOUND)
    if 'user' in request.session:
        return RedirectResponse(url='/auth/broker', status_code=status.HTTP_302_FOUND)
    if request.session.get('logged_in'):
        return RedirectResponse(url='/dashboard', status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse("login.html", {"request": request})

@auth_router.post("/login")
@limiter.limit(settings.LOGIN_RATE_LIMIT_MIN)
@limiter.limit(settings.LOGIN_RATE_LIMIT_HOUR)
async def login_post(request: Request, db = Depends(get_db), username: str = Form(...), password: str = Form(...)):
    if authenticate_user(username, password):
        request.session['user'] = username
        logger.info(f"Login success for user: {username}")
        return JSONResponse(content={'status': 'success'}, status_code=200)
    else:
        return JSONResponse(content={'status': 'error', 'message': 'Invalid credentials'}, status_code=401)

@auth_router.get("/broker", response_class=HTMLResponse)
@limiter.limit(settings.LOGIN_RATE_LIMIT_MIN)
@limiter.limit(settings.LOGIN_RATE_LIMIT_HOUR)
async def broker_login_get(request: Request):
    if request.session.get('logged_in'):
        return RedirectResponse(url='/dashboard', status_code=status.HTTP_302_FOUND)
    if 'user' not in request.session:
        return RedirectResponse(url='/auth/login', status_code=status.HTTP_302_FOUND)

    BROKER_API_KEY = os.getenv('BROKER_API_KEY')
    BROKER_API_SECRET = os.getenv('BROKER_API_SECRET')
    REDIRECT_URL = os.getenv('REDIRECT_URL')
    broker_name = re.search(r'/([^/]+)/callback$', REDIRECT_URL).group(1)

    from app.utils.auth_utils import mask_api_credential

    return templates.TemplateResponse('broker.html', {
        "request": request,
        "broker_api_key": BROKER_API_KEY,
        "broker_api_key_masked": mask_api_credential(BROKER_API_KEY),
        "broker_api_secret": BROKER_API_SECRET,
        "broker_api_secret_masked": mask_api_credential(BROKER_API_SECRET),
        "redirect_url": REDIRECT_URL,
        "broker_name": broker_name
    })

@auth_router.get('/reset-password', response_class=HTMLResponse, name="auth.reset_password")
@limiter.limit(settings.RESET_RATE_LIMIT)
async def reset_password_get(request: Request):
    return templates.TemplateResponse("reset_password.html", {"request": request, "email_sent": False})

@auth_router.post('/reset-password')
@limiter.limit(settings.RESET_RATE_LIMIT)
async def reset_password_post(request: Request, db = Depends(get_db), step: str = Form(...), email: str = Form(None), totp_code: str = Form(None), token: str = Form(None), password: str = Form(None)):
    if step == 'email':
        user = find_user_by_email(db, email)
        if user:
            request.session['reset_email'] = email
        return templates.TemplateResponse('reset_password.html', {"request": request, "email_sent": True, "method_selected": False, "email": email})

    elif step == 'select_totp':
        request.session['reset_method'] = 'totp'
        return templates.TemplateResponse('reset_password.html', {"request": request, "email_sent": True, "method_selected": 'totp', "totp_verified": False, "email": email})

    elif step == 'select_email':
        user = find_user_by_email(db, email)
        request.session['reset_method'] = 'email'

        smtp_settings = get_smtp_settings(db)
        if not smtp_settings or not smtp_settings.get('smtp_server'):
            return templates.TemplateResponse('reset_password.html', {"request": request, "email_sent": True, "method_selected": False, "email": email, "error": "Email reset is not available. Please use TOTP authentication."})

        if user:
            try:
                token = secrets.token_urlsafe(32)
                request.session['reset_token'] = token
                request.session['reset_email'] = email
                reset_link = request.url_for('reset_password_email', token=token)
                send_password_reset_email(email, reset_link, user.username)
                logger.info(f"Password reset email sent to {email}")
            except Exception as e:
                logger.error(f"Failed to send password reset email to {email}: {e}")
                return templates.TemplateResponse('reset_password.html', {"request": request, "email_sent": True, "method_selected": False, "email": email, "error": "Failed to send reset email. Please try TOTP authentication instead."})

        return templates.TemplateResponse('reset_password.html', {"request": request, "email_sent": True, "method_selected": 'email', "email_verified": False, "email": email})

    elif step == 'totp':
        user = find_user_by_email(db, email)
        if user and user.verify_totp(totp_code):
            token = secrets.token_urlsafe(32)
            request.session['reset_token'] = token
            request.session['reset_email'] = email
            return templates.TemplateResponse('reset_password.html', {"request": request, "email_sent": True, "method_selected": 'totp', "totp_verified": True, "email": email, "token": token})
        else:
            return templates.TemplateResponse('reset_password.html', {"request": request, "email_sent": True, "method_selected": 'totp', "totp_verified": False, "email": email, "error": "Invalid TOTP code. Please try again."})

    elif step == 'password':
        valid_token = (token == request.session.get('reset_token') or token == request.session.get('email_reset_token'))
        if not valid_token or email != request.session.get('reset_email'):
            return RedirectResponse(url='/auth/reset-password', status_code=status.HTTP_302_FOUND)

        user = find_user_by_email(db, email)
        if user:
            user.set_password(password)
            db.commit()
            request.session.pop('reset_token', None)
            request.session.pop('reset_email', None)
            request.session.pop('reset_method', None)
            request.session.pop('email_reset_token', None)
            return RedirectResponse(url='/auth/login', status_code=status.HTTP_302_FOUND)
        else:
            return RedirectResponse(url='/auth/reset-password', status_code=status.HTTP_302_FOUND)

    return templates.TemplateResponse('reset_password.html', {"request": request, "email_sent": False})


@auth_router.get('/reset-password-email/{token}')
async def reset_password_email(request: Request, token: str):
    try:
        if not token or len(token) != 43:
            return RedirectResponse(url='/auth/reset-password', status_code=status.HTTP_302_FOUND)
        if token != request.session.get('reset_token'):
            return RedirectResponse(url='/auth/reset-password', status_code=status.HTTP_302_FOUND)
        reset_email = request.session.get('reset_email')
        if not reset_email:
            return RedirectResponse(url='/auth/reset-password', status_code=status.HTTP_302_FOUND)
        request.session['email_reset_token'] = token
        return templates.TemplateResponse('reset_password.html', {"request": request, "email_sent": True, "method_selected": 'email', "email_verified": True, "email": reset_email, "token": token})
    except Exception as e:
        logger.error(f"Error processing email reset link: {e}")
        return RedirectResponse(url='/auth/reset-password', status_code=status.HTTP_302_FOUND)

@auth_router.get('/change', response_class=HTMLResponse)
async def change_password_get(request: Request, db = Depends(get_db), user: dict = Depends(check_session_validity_fastapi)):
    smtp_settings = get_smtp_settings(db)
    user_obj = db.query(User).filter_by(username=user).first()
    qr_code = None
    totp_secret = None
    if user_obj:
        import base64
        import io
        import qrcode
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(user_obj.get_totp_uri())
        qr.make(fit=True)
        img_buffer = io.BytesIO()
        qr.make_image(fill_color="black", back_color="white").save(img_buffer, format='PNG')
        qr_code = base64.b64encode(img_buffer.getvalue()).decode()
        totp_secret = user_obj.totp_secret
    return templates.TemplateResponse('profile.html', {"request": request, "username": user, "smtp_settings": smtp_settings, "qr_code": qr_code, "totp_secret": totp_secret})

@auth_router.post('/change')
async def change_password_post(request: Request, db = Depends(get_db), user: dict = Depends(check_session_validity_fastapi), old_password: str = Form(...), new_password: str = Form(...), confirm_password: str = Form(...)):
    user_obj = db.query(User).filter_by(username=user).first()
    if user_obj and user_obj.check_password(old_password):
        if new_password == confirm_password:
            user_obj.set_password(new_password)
            db.commit()
            return RedirectResponse(url='/auth/change', status_code=status.HTTP_302_FOUND)
        else:
            return RedirectResponse(url='/auth/change', status_code=status.HTTP_302_FOUND)
    else:
        return RedirectResponse(url='/auth/change', status_code=status.HTTP_302_FOUND)

@auth_router.post('/smtp-config')
async def configure_smtp(request: Request, db = Depends(get_db), user: dict = Depends(check_session_validity_fastapi), smtp_server: str = Form(...), smtp_port: int = Form(...), smtp_username: str = Form(...), smtp_password: str = Form(None), smtp_use_tls: bool = Form(...), smtp_from_email: str = Form(...), smtp_helo_hostname: str = Form(None)):
    try:
        if smtp_password and smtp_password.strip():
            set_smtp_settings(smtp_server=smtp_server, smtp_port=smtp_port, smtp_username=smtp_username, smtp_password=smtp_password, smtp_use_tls=smtp_use_tls, smtp_from_email=smtp_from_email, smtp_helo_hostname=smtp_helo_hostname)
        else:
            set_smtp_settings(smtp_server=smtp_server, smtp_port=smtp_port, smtp_username=smtp_username, smtp_use_tls=smtp_use_tls, smtp_from_email=smtp_from_email, smtp_helo_hostname=smtp_helo_hostname)
        logger.info(f"SMTP settings updated by user: {user}")
    except Exception as e:
        logger.error(f"Error updating SMTP settings: {str(e)}")
    return RedirectResponse(url='/auth/change?tab=smtp', status_code=status.HTTP_302_FOUND)

@auth_router.post('/test-smtp')
async def test_smtp(request: Request, user: dict = Depends(check_session_validity_fastapi), test_email: EmailStr = Form(...)):
    try:
        result = send_test_email(test_email, sender_name=user)
        if result['success']:
            logger.info(f"Test email sent successfully by user: {user} to {test_email}")
            return JSONResponse(content={'success': True, 'message': result['message']}, status_code=200)
        else:
            logger.warning(f"Test email failed for user: {user} - {result['message']}")
            return JSONResponse(content={'success': False, 'message': result['message']}, status_code=400)
    except Exception as e:
        error_msg = f'Error sending test email: {str(e)}'
        logger.error(f"Test email error for user {user}: {e}")
        return JSONResponse(content={'success': False, 'message': error_msg}, status_code=500)

@auth_router.post('/debug-smtp')
async def debug_smtp(request: Request, user: dict = Depends(check_session_validity_fastapi)):
    try:
        logger.info(f"SMTP debug requested by user: {user}")
        result = debug_smtp_connection()
        return JSONResponse(content={'success': result['success'], 'message': result['message'], 'details': result['details']}, status_code=200)
    except Exception as e:
        error_msg = f'Error debugging SMTP: {str(e)}'
        logger.error(f"SMTP debug error for user {user}: {e}")
        return JSONResponse(content={'success': False, 'message': error_msg, 'details': [f"Unexpected error: {e}"]}, status_code=500)

@auth_router.route('/logout', methods=['GET', 'POST'])
async def logout(request: Request, db = Depends(get_db)):
    if request.session.get('logged_in'):
        username = request.session['user']
        cache_key_auth = f"auth-{username}"
        cache_key_feed = f"feed-{username}"
        if cache_key_auth in auth_cache:
            del auth_cache[cache_key_auth]
            logger.info(f"Cleared auth cache for user: {username}")
        if cache_key_feed in feed_token_cache:
            del feed_token_cache[cache_key_feed]
            logger.info(f"Cleared feed token cache for user: {username}")
        try:
            from app.core.schemas.master_contract_cache_hook import clear_cache_on_logout
            clear_cache_on_logout()
            logger.info("Cleared symbol cache on logout")
        except Exception as cache_error:
            logger.error(f"Error clearing symbol cache on logout: {cache_error}")
        inserted_id = upsert_auth(username, "", "", revoke=True)
        if inserted_id is not None:
            logger.info(f"Database Upserted record with ID: {inserted_id}")
            logger.info(f'Auth Revoked in the Database for user: {username}')
        else:
            logger.error(f"Failed to upsert auth token for user: {username}")
        request.session.pop('user', None)
        request.session.pop('broker', None)
        request.session.pop('logged_in', None)
    return RedirectResponse(url='/auth/login', status_code=status.HTTP_302_FOUND)