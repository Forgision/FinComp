import socketio

sio = socketio.AsyncServer(
    cors_allowed_origins='*',
    ping_timeout=10,
    ping_interval=5,
    logger=False,
    engineio_logger=False,
    async_mode='asgi'
)

socket_app = socketio.ASGIApp(sio)