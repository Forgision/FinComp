from fastapi.templating import Jinja2Templates
from ...core.config import settings
from ...utils.web.flash import get_flashed_messages

templates = Jinja2Templates(directory=settings.BASE_DIR / "web/frontend/templates")
templates.env.globals['get_flashed_messages'] = get_flashed_messages