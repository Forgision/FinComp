from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse

from app.utils.session import check_session_validity_fastapi as get_current_user

dashboard_router = APIRouter()

# Placeholder for session validation dependency
# This will be properly implemented later as a FastAPI dependency


@dashboard_router.get("/dashboard", response_class=HTMLResponse, name="dashboard")
async def dashboard(request: Request, current_user: str = Depends(get_current_user)):
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)

    # The original Flask code had a lot of logic related to fetching funds
    # and handling different modes (analyze vs live broker).
    # For migration, we'll keep a simplified version and add back the logic
    # once the corresponding services and database interactions are migrated.

    # Placeholder for actual funds data fetching logic
    # This will eventually call services.funds_service.get_funds

    return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)
