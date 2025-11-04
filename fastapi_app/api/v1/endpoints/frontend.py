from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from fastapi_app.api.v1.dependencies import get_templates

router = APIRouter()

@router.get("/websocket/dashboard", response_class=HTMLResponse)
async def get_websocket_dashboard(request: Request, templates: Jinja2Templates = Depends(get_templates)):
    """
    Serves the WebSocket dashboard page.
    """
    return templates.TemplateResponse(request, "websocket/dashboard.html")

@router.get("/websocket/test", response_class=HTMLResponse)
async def get_websocket_test(request: Request, templates: Jinja2Templates = Depends(get_templates)):
    """
    Serves the WebSocket test page.
    """
    return templates.TemplateResponse(request, "websocket/test_market_data.html")
