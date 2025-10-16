import os

from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from ....utils.logging import logger
from ....core.config import settings
from ...frontend import templates


dashboard_router = APIRouter()

# Placeholder for session validation dependency
# This will be properly implemented later as a FastAPI dependency
async def get_current_user(request: Request):
    # For now, just check if 'user' is in session.
    # A proper implementation will involve token verification etc.
    if "user" not in request.session:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            detail="Not authenticated",
            headers={"Location": "/auth/login"}
        )
    return request.session.get("user")


@dashboard_router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, current_user: str = Depends(get_current_user)):
    # The original Flask code had a lot of logic related to fetching funds
    # and handling different modes (analyze vs live broker).
    # For migration, we'll keep a simplified version and add back the logic
    # once the corresponding services and database interactions are migrated.

    # Placeholder for actual funds data fetching logic
    # This will eventually call services.funds_service.get_funds
    margin_data = {
        "availablecash": "100000.00",
        "collateral": "50000.00",
        "utiliseddebits": "0.00"
    }

    # The original Flask code also handled redirects to logout on auth failure.
    # In FastAPI, this would typically be handled by the authentication dependency
    # or specific error handling. For now, we assume current_user is valid.

    return templates.TemplateResponse("dashboard.html", {"request": request, "margin_data": margin_data})
