from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp
from app.core.config import settings
import hmac
import hashlib
import time

class SecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        return response

class TrafficLoggerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        # In a real application, you'd log this to a file or a logging service
        #TODO: implement logging
        print(f"Request: {request.method} {request.url.path} - "
              f"Status: {response.status_code} - Time: {process_time:.4f}s")
        return response

class ContentSecurityPolicyMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, csp_policy: str = None):
        super().__init__(app)
        self.csp_policy = csp_policy if csp_policy else self._get_default_csp()

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if self.csp_policy and "Content-Security-Policy" not in response.headers:
            response.headers["Content-Security-Policy"] = self.csp_policy
        return response

    def _get_default_csp(self) -> str:
        # Define a strict default CSP. Customize as needed for your application.
        return (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "connect-src 'self' ws: wss:; "
            "frame-ancestors 'none';"
        )