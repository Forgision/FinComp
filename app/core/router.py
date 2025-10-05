from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.utils.logging import get_logger

logger = get_logger(__name__)
templates = Jinja2Templates(directory="templates")

core_router = APIRouter()

@core_router.get("/setup", response_class=HTMLResponse)
async def setup(request: Request):
    """Placeholder for the setup page."""
    return templates.TemplateResponse("setup.html", {"request": request})

@core_router.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Root endpoint to redirect to dashboard or login."""
    if request.session.get('logged_in'):
        return templates.TemplateResponse("dashboard.html", {"request": request})
    return templates.TemplateResponse("login.html", {"request": request})
