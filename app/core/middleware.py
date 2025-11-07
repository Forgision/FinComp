import time
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from app.core.schemas.traffic_db import LogSessionLocal, log_request, track_404, is_ip_banned
from app.utils.logging import logger


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
        
        # Extract client IP
        client_ip = request.client.host if request.client else "unknown"

        # Define paths to skip logging for
        path = request.url.path
        if (
            path.startswith("/static/")
            or path == "/favicon.ico"
            or path.startswith("/api/v1/latency/logs")
            or path.startswith("/traffic/")
            or path.startswith("/traffic/api/")
        ):
            response = await call_next(request)
            return response

        # Check if IP is banned before processing the request
        async with LogSessionLocal() as db:
            if await is_ip_banned(db, client_ip):
                logger.warning(f"Banned IP {client_ip} attempted to access {path}")
                return Response("Access Denied", status_code=403)

        response = await call_next(request)
        process_time = time.time() - start_time
        duration_ms = process_time * 1000

        async with LogSessionLocal() as db:
            user_id: Optional[int] = None
            # Assuming user_id might be in request.state if authenticated
            if hasattr(request.state, "user") and request.state.user:
                user_id = request.state.user.id

            error_message: Optional[str] = None
            if response.status_code >= 400:
                error_message = f"HTTP Error {response.status_code}"
                if response.status_code == 404:
                    await track_404(db, client_ip, path)
                # You might want to add more specific error tracking here
                # For example, if it's an API key related error
                # track_invalid_api_key(db, client_ip, api_key_hash)

            await log_request(
                db,
                client_ip=client_ip,
                method=request.method,
                path=path,
                status_code=response.status_code,
                duration_ms=duration_ms,
                host=request.headers.get("host"),
                error=error_message,
                user_id=user_id,
            )
        
        logger.debug(f"Request: {request.method} {request.url.path} - "
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
