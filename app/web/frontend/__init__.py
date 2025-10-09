import os
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from ...core.config import settings

from app.utils.flash import get_flashed_messages

def flash_context_processor(request: Request):
    return {"get_flashed_messages": lambda **kwargs: get_flashed_messages(request, **kwargs)}

templates = Jinja2Templates(
    directory=os.path.join(settings.BASE_DIR, "web/frontend/templates"),
    context_processors=[flash_context_processor],
)