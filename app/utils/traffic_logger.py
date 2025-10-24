from app.core.schemas.traffic_db import logs_session


class TrafficLoggerMiddleware:
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        path_info = environ.get('PATH_INFO', '')

        # Skip logging for:
        # 1. Static files and favicon
        # 2. Traffic monitoring endpoints themselves
        if (path_info.startswith('/static/') or
            path_info == '/favicon.ico' or
            path_info.startswith('/api/v1/latency/logs') or
            path_info.startswith('/traffic/') or
            path_info.startswith('/traffic/api/')):
            return self.app(environ, start_response)

        try:
            return self.app(environ, start_response)
        finally:
            # The original code removed the session in the finally block of log_request.
            # We should preserve this behavior.
            logs_session.remove()

def init_traffic_logging(app):
    """Initialize traffic logging middleware"""
    # Initialize the logs database
    from app.core.schemas.traffic_db import init_logs_db
    init_logs_db()

    # Add middleware
    app.wsgi_app = TrafficLoggerMiddleware(app.wsgi_app)
