from fastapi.templating import Jinja2Templates
from ...core.config import settings
from ...utils.web.flash import get_flashed_messages
from ...utils.number_formatter import format_indian_currency, format_indian_number

templates = Jinja2Templates(directory=settings.BASE_DIR / "web/frontend/templates")
templates.env.globals['get_flashed_messages'] = get_flashed_messages
templates.env.filters['indian_currency'] = format_indian_currency
templates.env.filters['indian_number'] = format_indian_number