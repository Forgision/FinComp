from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp
from datetime import datetime, timedelta
import hmac
import secrets
import base64
from typing import Optional, Dict

from app.core.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

def get_csp_config() -> Optional[Dict[str, str]]:
    """
    Get Content Security Policy configuration from environment variables.
    Returns a dictionary with CSP directives.
    """
    csp_config = {}

    # Check if CSP is enabled
    if not settings.CSP_ENABLED:
        return None

    # Default source directive
    if settings.CSP_DEFAULT_SRC:
        csp_config['default-src'] = settings.CSP_DEFAULT_SRC

    # Script source directive
    if settings.CSP_SCRIPT_SRC:
        csp_config['script-src'] = settings.CSP_SCRIPT_SRC

    # Style source directive
    if settings.CSP_STYLE_SRC:
        csp_config['style-src'] = settings.CSP_STYLE_SRC

    # Image source directive
    if settings.CSP_IMG_SRC:
        csp_config['img-src'] = settings.CSP_IMG_SRC

    # Connect source directive (for WebSockets, etc.)
    if settings.CSP_CONNECT_SRC:
        csp_config['connect-src'] = settings.CSP_CONNECT_SRC

    # Font source directive
    if settings.CSP_FONT_SRC:
        csp_config['font-src'] = settings.CSP_FONT_SRC

    # Object source directive
    if settings.CSP_OBJECT_SRC:
        csp_config['object-src'] = settings.CSP_OBJECT_SRC

    # Media source directive
    if settings.CSP_MEDIA_SRC:
        csp_config['media-src'] = settings.CSP_MEDIA_SRC

    # Frame source directive
    if settings.CSP_FRAME_SRC:
        csp_config['frame-src'] = settings.CSP_FRAME_SRC

    # Child source directive (deprecated but included for compatibility)
    if settings.CSP_CHILD_SRC:
        csp_config['child-src'] = settings.CSP_CHILD_SRC

    # Form action directive
    if settings.CSP_FORM_ACTION:
        csp_config['form-action'] = settings.CSP_FORM_ACTION

    # Base URI directive
    if settings.CSP_BASE_URI:
        csp_config['base-uri'] = settings.CSP_BASE_URI

    # Frame ancestors directive (clickjacking protection)
    if settings.CSP_FRAME_ANCESTORS:
        csp_config['frame-ancestors'] = settings.CSP_FRAME_ANCESTORS

    # Additional custom directives
    if settings.CSP_UPGRADE_INSECURE_REQUESTS:
        csp_config['upgrade-insecure-requests'] = ''

    # Report URI for CSP violations
    if settings.CSP_REPORT_URI:
        csp_config['report-uri'] = settings.CSP_REPORT_URI

    # Report-To directive for CSP violations reporting
    if settings.CSP_REPORT_TO:
        csp_config['report-to'] = settings.CSP_REPORT_TO

    return csp_config

def build_csp_header(csp_config: Optional[Dict[str, str]]) -> Optional[str]:
    """
    Build the Content Security Policy header value from the configuration.
    """
    if not csp_config:
        return None

    directives = []
    for directive, value in csp_config.items():
        if value:
            directives.append(f"{directive} {value}")
        else:
            directives.append(directive)

    return "; ".join(directives)

def get_security_headers() -> Dict[str, str]:
    """
    Get additional security headers configuration from environment variables.
    """
    headers = {}

    # Referrer Policy
    if settings.REFERRER_POLICY:
        headers['Referrer-Policy'] = settings.REFERRER_POLICY

    # Permissions Policy
    if settings.PERMISSIONS_POLICY:
        headers['Permissions-Policy'] = settings.PERMISSIONS_POLICY

    return headers


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)

        # Add CSP header
        csp_config = get_csp_config()
        if csp_config:
            csp_header = build_csp_header(csp_config)
            if csp_header:
                header_type = 'Content-Security-Policy'
                if settings.CSP_REPORT_ONLY:
                    header_type = 'Content-Security-Policy-Report-Only'
                response.headers[header_type] = csp_header

        # Add other security headers
        security_headers = get_security_headers()
        for header_name, header_value in security_headers.items():
            response.headers[header_name] = header_value

        return response

def generate_csrf_token(session_id: str) -> str:
    """Generates a new CSRF token."""
    salt = secrets.token_bytes(16)
    timestamp = str(int(datetime.utcnow().timestamp())).encode('utf-8')
    secret_key = settings.APP_KEY.encode('utf-8')
    
    # Use HMAC to create a secure token
    h = hmac.new(secret_key, salt + timestamp + session_id.encode('utf-8'), 'sha256')
    
    # Encode salt, timestamp, and digest together
    token_parts = b"%s.%s.%s" % (base64.urlsafe_b64encode(salt), timestamp, base64.urlsafe_b64encode(h.digest()))
    return token_parts.decode('utf-8')

def validate_csrf_token(token: str, session_id: str) -> bool:
    """Validates a given CSRF token."""
    if not token:
        return False

    try:
        token_parts = token.split('.')
        if len(token_parts) != 3:
            return False

        salt = base64.urlsafe_b64decode(token_parts[0])
        timestamp_str = token_parts[1].encode('utf-8')
        expected_digest = base64.urlsafe_b64decode(token_parts[2])

        # Check token expiry
        if settings.CSRF_TIME_LIMIT is not None:
            token_timestamp = int(timestamp_str.decode('utf-8'))
            current_timestamp = int(datetime.utcnow().timestamp())
            if (current_timestamp - token_timestamp) > settings.CSRF_TIME_LIMIT:
                logger.warning("CSRF token expired.")
                return False

        secret_key = settings.APP_KEY.encode('utf-8')
        h = hmac.new(secret_key, salt + timestamp_str + session_id.encode('utf-8'), 'sha256')
        
        # Use compare_digest to prevent timing attacks
        if hmac.compare_digest(h.digest(), expected_digest):
            return True
        else:
            logger.warning("CSRF token validation failed: Mismatch in digest.")
            return False
    except Exception as e:
        logger.error(f"Error validating CSRF token: {e}")
        return False

import argon2 # Import argon2-cffi

# Password Hashing
def hash_password(password: str) -> str:
    """Hashes a password using Argon2."""
    ph = argon2.PasswordHasher()
    return ph.hash(password)

def verify_password(password: str, hashed_password: str) -> bool:
    """Verifies a password against a hash using Argon2."""
    ph = argon2.PasswordHasher()
    try:
        ph.verify(hashed_password, password)
        return True
    except argon2.exceptions.VerifyMismatchError:
        return False
    except Exception as e:
        logger.error(f"Error verifying password: {e}")
        return False

class CSRFMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.exempt_routes = [route.strip() for route in settings.CSRF_EXEMPT_ROUTES.split(',') if route.strip()]

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if not settings.CSRF_ENABLED:
            return await call_next(request)

        # Skip CSRF for exempt routes
        for route in self.exempt_routes:
            if request.url.path.startswith(route):
                return await call_next(request)

        # Generate new session ID if not present
        session_id = request.cookies.get(settings.SESSION_COOKIE_NAME)
        if not session_id:
            session_id = secrets.token_urlsafe(32)
            logger.debug(f"Generated new session ID: {session_id}")

        if request.method in ["GET", "HEAD", "OPTIONS", "TRACE"]:
            # For safe methods, generate a new CSRF token and set it in a cookie
            csrf_token = generate_csrf_token(session_id)
            response = await call_next(request)
            self._set_csrf_cookie(response, csrf_token)
        else:
            # For unsafe methods, validate the CSRF token
            csrf_token_from_header = request.headers.get("X-CSRF-Token")
            
            # Read form data once, checking content type first
            content_type = request.headers.get("Content-Type", "")
            csrf_token_from_form = None
            if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
                try:
                    form_data = await request.form()
                    csrf_token_from_form = form_data.get("csrf_token")
                except Exception as e:
                    logger.debug(f"Could not parse form data for CSRF token: {e}")
            elif "application/json" in content_type:
                try:
                    json_data = await request.json()
                    csrf_token_from_form = json_data.get("csrf_token")
                except Exception as e:
                    logger.debug(f"Could not parse JSON data for CSRF token: {e}")


            csrf_token = csrf_token_from_header or csrf_token_from_form

            if not validate_csrf_token(csrf_token, session_id):
                logger.warning(f"CSRF validation failed for request to {request.url.path}")
                return Response("CSRF token missing or incorrect", status_code=403)
            response = await call_next(request)

        # Always ensure session cookie is set
        if settings.SESSION_COOKIE_NAME not in response.headers.get("Set-Cookie", ""):
            response.set_cookie(
                key=settings.SESSION_COOKIE_NAME,
                value=session_id,
                httponly=True,
                samesite="lax",
                secure=settings.USE_HTTPS,
                max_age=3600 * 24 # 1 day, adjust as needed
            )
        
        return response

    def _set_csrf_cookie(self, response: Response, csrf_token: str):
        """Helper to set the CSRF token in a cookie."""
        response.set_cookie(
            key=settings.CSRF_COOKIE_NAME,
            value=csrf_token,
            httponly=True,
            samesite="lax",
            secure=settings.USE_HTTPS,
            max_age=settings.CSRF_TIME_LIMIT if settings.CSRF_TIME_LIMIT is not None else 3600 * 24 * 30 # Default 30 days
        )
def flash(request: Request, message: str, category: str = "info"):
    if 'flash_messages' not in request.session:
        request.session['flash_messages'] = []
    request.session['flash_messages'].append((category, message))