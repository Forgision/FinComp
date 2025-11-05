from starlette.types import ASGIApp, Scope, Receive, Send

from app.core.schemas.traffic_db import LogSessionLocal


class TrafficLoggerMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")

        # Skip logging for:
        # 1. Static files and favicon
        # 2. Traffic monitoring endpoints themselves
        if (
            path.startswith("/static/")
            or path == "/favicon.ico"
            or path.startswith("/api/v1/latency/logs")
            or path.startswith("/traffic/")
            or path.startswith("/traffic/api/")
        ):
            await self.app(scope, receive, send)
            return

        try:
            await self.app(scope, receive, send)
        finally:
            # The original code removed the session in the finally block of log_request.
            # We should preserve this behavior.
            with LogSessionLocal() as logs_session:
                logs_session.remove()