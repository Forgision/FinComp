import qrcode  # type: ignore #Library stubs not installed for "qrcode"
import io
import base64
import re
import secrets
from typing import Annotated, Optional
from fastapi import APIRouter, Request, Depends, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi_csrf_protect.flexible import CsrfProtect
from fastapi_csrf_protect.exceptions import CsrfProtectError
from sqlalchemy.orm import Session
from app.core.config import settings
from ....utils.web import limiter
from ....db.session import get_db
from ....db.user_db import add_user, find_user_by_username, find_user_by_email
from ....db.settings_db import get_smtp_settings, set_smtp_settings
from ....db.auth_db import upsert_api_key, upsert_auth, auth_cache, feed_token_cache
from ...frontend import templates
from app.db.user_db import User
from ...models.auth import SMTPConfig, SMTPTest, SMTPDebug
from ....utils.auth_utils import mask_api_credential
from ....utils.web.security import verify_password
from ....utils.email_utils import send_password_reset_email, send_test_email
from ....utils.email_debug import debug_smtp_connection
from ...frontend import templates
from ...services import user_service
from ....utils.web.flash import flash
from ....utils.web.security import generate_api_key, generate_csrf_token, validate_csrf_token
from ....utils.logging import logger


auth_router = APIRouter(prefix="/auth", tags=["auth"])

# Rate limiting will be handled as a dependency or middleware later
# For now, we'll implement the basic login logic

@auth_router.get("/login", name="auth.login")
async def login_get(request: Request,
                    csrf_protect: CsrfProtect = Depends(),
                    db: Session = Depends(get_db)):
    if user_service.get_total_users_count(db) == 0:
        return RedirectResponse(url=auth_router.url_path_for('setup'), status_code=status.HTTP_302_FOUND)

    if request.session.get('logged_in'): # Check if already logged in
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
        
    csrf_token, signed_token = csrf_protect.generate_csrf_tokens()
    response = templates.TemplateResponse(
        "login.html", {"request": request, "csrf_token": csrf_token}
        )
    csrf_protect.set_csrf_cookie(signed_token, response)
    return response


@auth_router.post("/login", name="auth.login")
async def login_post(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = user_service.get_user_by_username(db, username)
    if user and verify_password(password, user.password_hash):
        request.session['user'] = username
        logger.info(f"Login success for user: {username}")
        # Redirect to broker login without marking as fully logged in
        return JSONResponse({'status': 'success'}, status_code=200)
    else:
        flash(request, "Invalid credentials", "error")
        # return JSONResponse({'status': 'error', 'message': 'Invalid credentials'}, status_code=401)


@auth_router.post("/logout", name="auth.logout")
async def logout(request: Request, db: Session = Depends(get_db)):
    if 'user' in request.session:
        username = request.session['user']
        
        # Clear cache entries
        cache_key_auth = f"auth-{username}"
        cache_key_feed = f"feed-{username}"
        if cache_key_auth in auth_cache:
            del auth_cache[cache_key_auth]
            logger.info(f"Cleared auth cache for user: {username}")
        if cache_key_feed in feed_token_cache:
            del feed_token_cache[cache_key_feed]
            logger.info(f"Cleared feed token cache for user: {username}")
            
        # Clear symbol cache
        try:
            from app.db.master_contract_cache_hook import clear_cache_on_logout
            clear_cache_on_logout()
            logger.info("Cleared symbol cache on logout")
        except Exception as cache_error:
            logger.error(f"Error clearing symbol cache on logout: {cache_error}")
        
        # Revoke auth token in the database
        inserted_id = upsert_auth(db, username, "", "", revoke=True)
        if inserted_id:
            logger.info(f"Auth revoked in the database for user: {username}")
        else:
            logger.error(f"Failed to upsert auth token for user: {username}")
        
        # Clear session data
        request.session.pop('user', None)
        request.session.pop('broker', None)
        request.session.pop('logged_in', None)

    flash(request, "You have been logged out.", "success")
    return RedirectResponse(url=request.url_for('auth.login'), status_code=status.HTTP_302_FOUND)


@auth_router.get("/change", name="auth.change_password", response_class=HTMLResponse)
async def change_password_get(request: Request, db: Session = Depends(get_db)):
    if 'user' not in request.session:
        flash(request, "You must be logged in to change your password.", "warning")
        return RedirectResponse(url=request.url_for('auth.login'))

    username = request.session['user']
    user = user_service.get_user_by_username(db, username)
    
    qr_code = None
    if user:
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(user.get_totp_uri())
        qr.make(fit=True)
        
        img_buffer = io.BytesIO()
        qr.make_image(fill_color="black", back_color="white").save(img_buffer, format='PNG')
        qr_code = base64.b64encode(img_buffer.getvalue()).decode()

    smtp_settings = get_smtp_settings(db)
    
    return templates.TemplateResponse("profile.html", {
        "request": request,
        "username": username,
        "smtp_settings": smtp_settings,
        "qr_code": qr_code,
        "totp_secret": user.totp_secret if user else None
    })


@auth_router.post("/change", name="auth.change_password")
async def change_password_post(
    request: Request,
    db: Session = Depends(get_db),
    old_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...)
):
    if 'user' not in request.session:
        flash(request, "You must be logged in to change your password.", "warning")
        return RedirectResponse(url=request.url_for('auth.login'))

    username = request.session['user']
    user = user_service.get_user_by_username(db, username)

    if user and verify_password(old_password, user.password_hash):
        if new_password == confirm_password:
            user.set_password(new_password)
            db.commit()
            flash(request, "Your password has been changed successfully.", "success")
        else:
            flash(request, "New password and confirm password do not match.", "error")
    else:
        flash(request, "Old Password is incorrect.", "error")
        
    return RedirectResponse(url=request.url_for('auth.change'), status_code=status.HTTP_303_SEE_OTHER)


@auth_router.get('/setup', name="setup")
async def setup_get(request: Request,
                    csrf_protect: CsrfProtect = Depends(),
                    db: Session = Depends(get_db)):
    if user_service.get_total_users_count(db) > 0:
        flash(request, "Setup has already been completed.", "warning")
        return RedirectResponse(url=auth_router.url_path_for('auth.login'))

    csrf_token, signed_token = csrf_protect.generate_csrf_tokens()
    response = templates.TemplateResponse(
        "setup.html", {"request": request, "csrf_token": csrf_token}
    )
    csrf_protect.set_csrf_cookie(signed_token, response)
    return response


@auth_router.post('/setup', name="setup")
async def setup_post(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    csrf_token: str = Form(...),
    csrf_protect: CsrfProtect = Depends(),
    db: Session = Depends(get_db)
):
    #TODO: make crsf validation working. There is "The CSRF token is invalid" error.
    # try:
    #     # cs = await csrf_protect.get_csrf_from_body(re)
    #     await csrf_protect.validate_csrf(request)
    # except CsrfProtectError as e:
    #     raise HTTPException(status_code=400, detail=f"CSRF token validation error:{e.message}")

    if user_service.get_total_users_count(db) > 0:
        flash(request, "Setup has already been completed.", "warning")
        return RedirectResponse(url=auth_router.url_path_for('auth.login'))

    # Add the new admin user
    user = add_user(username, email, password, is_admin=True)
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
        flash(request, 'Account created successfully! Please configure your SMTP credentials in Profile settings for password recovery.', 'success')
        return RedirectResponse(auth_router.url_path_for('auth.login'))
    else:
        # If the user already exists or an error occurred, show an error message
        logger.error(f"Failed to create admin user {username}")
        flash('User already exists or an error occurred', 'error')
        return RedirectResponse(auth_router.url_path_for('setup'))
    

@auth_router.get('/broker', name='broker_login', response_class=HTMLResponse)
async def broker_login_get(request: Request):
    if 'user' not in request.session:
        flash(request, "Please log in to continue.", "warning")
        return RedirectResponse(url=request.url_for('auth.login'))

    if request.session.get('logged_in'):
        return RedirectResponse(url=request.url_for('dashboard'))

    redirect_url = settings.REDIRECT_URL
    broker_name_match = re.search(r'/([^/]+)/callback$', redirect_url)
    broker_name = broker_name_match.group(1) if broker_name_match else "default"

    context = {
        "request": request,
        "broker_api_key": settings.BROKER_API_KEY,
        "broker_api_key_masked": mask_api_credential(settings.BROKER_API_KEY),
        "broker_api_secret": settings.BROKER_API_SECRET,
        "broker_api_secret_masked": mask_api_credential(settings.BROKER_API_SECRET),
        "redirect_url": redirect_url,
        "broker_name": broker_name,
    }
    return templates.TemplateResponse("broker.html", context)


@auth_router.post('/broker', name='broker_login_post')
async def broker_login_post(request: Request):
    if 'user' not in request.session:
        flash(request, "Please log in to continue.", "warning")
        return RedirectResponse(url=request.url_for('auth.login'))

    # In a real scenario, you'd validate the submitted broker credentials.
    # For this task, we'll assume successful validation.

    redirect_url = settings.REDIRECT_URL
    broker_name_match = re.search(r'/([^/]+)/callback$', redirect_url)
    broker_name = broker_name_match.group(1) if broker_name_match else "default"

    request.session['logged_in'] = True
    request.session['broker'] = broker_name

    flash(request, f"Successfully logged in with {broker_name.title()}.", "success")
    return RedirectResponse(url='/dashboard', status_code=status.HTTP_302_FOUND)


@auth_router.get('/reset-password', name='auth.reset_password', response_class=HTMLResponse)
async def reset_password_get(request: Request):
    return templates.TemplateResponse('reset_password.html', {"request": request, "email_sent": False})

@auth_router.post('/reset-password', name='reset_password')
async def reset_password_post(
    request: Request,
    db: Session = Depends(get_db),
    step: str = Form(...),
    email: str = Form(...),
    totp_code: Optional[str] = Form(None),
    password: Optional[str] = Form(None),
    token: Optional[str] = Form(None)
):
    if step == 'email':
        user = find_user_by_email(email, db)
        if user:
            request.session['reset_email'] = email
        return templates.TemplateResponse('reset_password.html', {
            "request": request,
            "email_sent": True,
            "method_selected": False,
            "email": email
        })

    elif step == 'select_totp':
        request.session['reset_method'] = 'totp'
        return templates.TemplateResponse('reset_password.html', {
            "request": request,
            "email_sent": True,
            "method_selected": 'totp',
            "totp_verified": False,
            "email": email
        })

    elif step == 'select_email':
        request.session['reset_method'] = 'email'
        smtp_settings = get_smtp_settings(db)
        if not smtp_settings or not smtp_settings.smtp_server:
            flash(request, 'Email reset is not available. Please use TOTP authentication.', 'error')
            return templates.TemplateResponse('reset_password.html', {
                "request": request,
                "email_sent": True,
                "method_selected": False,
                "email": email
            })
        
        user = find_user_by_email(email, db)
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
                flash(request, 'Failed to send reset email. Please try TOTP authentication instead.', 'error')
                return templates.TemplateResponse('reset_password.html', {
                    "request": request,
                    "email_sent": True,
                    "method_selected": False,
                    "email": email
                })
        
        return templates.TemplateResponse('reset_password.html', {
            "request": request,
            "email_sent": True,
            "method_selected": 'email',
            "email_verified": False,
            "email": email
        })

    elif step == 'totp':
        user = find_user_by_email(email, db)
        if user and user.verify_totp(totp_code):
            token = secrets.token_urlsafe(32)
            request.session['reset_token'] = token
            request.session['reset_email'] = email
            return templates.TemplateResponse('reset_password.html', {
                "request": request,
                "email_sent": True,
                "method_selected": 'totp',
                "totp_verified": True,
                "email": email,
                "token": token
            })
        else:
            flash(request, 'Invalid TOTP code. Please try again.', 'error')
            return templates.TemplateResponse('reset_password.html', {
                "request": request,
                "email_sent": True,
                "method_selected": 'totp',
                "totp_verified": False,
                "email": email
            })

    elif step == 'password':
        valid_token = (token == request.session.get('reset_token') or token == request.session.get('email_reset_token'))
        if not valid_token or email != request.session.get('reset_email'):
            flash(request, 'Invalid or expired reset token.', 'error')
            return RedirectResponse(url=request.url_for('reset_password'), status_code=status.HTTP_302_FOUND)
        
        user = find_user_by_email(email, db)
        if user:
            user.set_password(password)
            db.commit()
            
            request.session.pop('reset_token', None)
            request.session.pop('reset_email', None)
            request.session.pop('reset_method', None)
            request.session.pop('email_reset_token', None)
            
            flash(request, 'Your password has been reset successfully.', 'success')
            return RedirectResponse(url=request.url_for('auth.login'), status_code=status.HTTP_302_FOUND)
        else:
            flash(request, 'Error resetting password.', 'error')
            return RedirectResponse(url=request.url_for('reset_password'), status_code=status.HTTP_302_FOUND)
    
    return RedirectResponse(url=request.url_for('reset_password'), status_code=status.HTTP_302_FOUND)


@auth_router.get('/reset-password-email/{token}', name='reset_password_email', response_class=HTMLResponse)
async def reset_password_email(request: Request, token: str):
    try:
        if not token or len(token) != 43:
            flash(request, 'Invalid reset link.', 'error')
            return RedirectResponse(url=request.url_for('reset_password'), status_code=status.HTTP_302_FOUND)
        
        if token != request.session.get('reset_token'):
            flash(request, 'Invalid or expired reset link.', 'error')
            return RedirectResponse(url=request.url_for('reset_password'), status_code=status.HTTP_302_FOUND)
        
        reset_email = request.session.get('reset_email')
        if not reset_email:
            flash(request, 'Reset session expired. Please start again.', 'error')
            return RedirectResponse(url=request.url_for('reset_password'), status_code=status.HTTP_302_FOUND)
        
        request.session['email_reset_token'] = token
        
        return templates.TemplateResponse('reset_password.html', {
            "request": request,
            "email_sent": True,
            "method_selected": 'email',
            "email_verified": True,
            "email": reset_email,
            "token": token
        })
                             
    except Exception as e:
        logger.error(f"Error processing email reset link: {e}")
        flash(request, 'Invalid or expired reset link.', 'error')
        return RedirectResponse(url=request.url_for('reset_password'), status_code=status.HTTP_302_FOUND)


@auth_router.post("/smtp-config", name="auth.configure_smtp", status_code=status.HTTP_200_OK)
async def configure_smtp(
    request: Request,
    smtp_config: SMTPConfig,
    db: Session = Depends(get_db)
):
    """
    Configure SMTP settings.
    """
    if 'user' not in request.session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="You must be logged in")

    try:
        set_smtp_settings(
            smtp_server=smtp_config.smtp_server,
            smtp_port=smtp_config.smtp_port,
            smtp_username=smtp_config.smtp_username,
            smtp_password=smtp_config.smtp_password,
            smtp_use_tls=smtp_config.smtp_use_tls,
            smtp_from_email=str(smtp_config.smtp_from_email) if smtp_config.smtp_from_email else None,
            smtp_helo_hostname=smtp_config.smtp_helo_hostname,
            db=db
        )
        logger.info(f"SMTP settings updated by user: {request.session['user']}")
        return {"message": "SMTP settings updated successfully."}
    except Exception as e:
        logger.error(f"Error updating SMTP settings: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error updating SMTP settings: {str(e)}")


@auth_router.post("/test-smtp", name="auth.test_smtp", status_code=status.HTTP_200_OK)
async def test_smtp(
    request: Request,
    smtp_test: SMTPTest,
    db: Session = Depends(get_db)
):
    """
    Send a test email to verify SMTP configuration.
    """
    if 'user' not in request.session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="You must be logged in")

    try:
        result = send_test_email(smtp_test.test_email, sender_name=request.session['user'], db=db)
        if result['success']:
            logger.info(f"Test email sent successfully by user: {request.session['user']} to {smtp_test.test_email}")
            return result
        else:
            logger.warning(f"Test email failed for user: {request.session['user']} - {result['message']}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result['message'])
    except Exception as e:
        error_msg = f'Error sending test email: {str(e)}'
        logger.error(f"Test email error for user {request.session['user']}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_msg)


@auth_router.post("/debug-smtp", name="auth.debug_smtp", response_model=SMTPDebug)
async def debug_smtp(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Debug SMTP connection with detailed logging.
    """
    if 'user' not in request.session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="You must be logged in")

    try:
        logger.info(f"SMTP debug requested by user: {request.session['user']}")
        result = debug_smtp_connection(db=db)
        return result
    except Exception as e:
        error_msg = f'Error debugging SMTP: {str(e)}'
        logger.error(f"SMTP debug error for user {request.session['user']}: {e}")
        return {
            'success': False,
            'message': error_msg,
            'details': [f"Unexpected error: {e}"]
        }
