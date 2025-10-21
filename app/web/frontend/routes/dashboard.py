from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from starlette.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db.schemas.auth_db import get_auth_token
from app.core.services.funds_service import get_funds
from app.utils.logging import logger
from app.utils.session import check_session_validity_fastapi, get_db

templates = Jinja2Templates(directory="app/frontend/templates")

dashboard_router = APIRouter()

@dashboard_router.get("/dashboard")
async def dashboard(request: Request, user: dict = Depends(check_session_validity_fastapi), db: Session = Depends(get_db)):
    login_username = user
    AUTH_TOKEN = get_auth_token(db, login_username)

    if AUTH_TOKEN is None:
        logger.warning(f"No auth token found for user {login_username}")
        return RedirectResponse(url="/logout")

    broker = request.session.get("broker")
    if not broker:
        logger.error("Broker not set in session")
        # In a real app, you'd probably redirect to a broker selection page
        return templates.TemplateResponse("error.html", {"request": request, "error_message": "Broker not set in session."}, status_code=400)

    # In FastAPI, blocking calls should be run in a thread pool
    # For now, we call it directly but this is a candidate for `run_in_threadpool`
    # success, response, status_code = await run_in_threadpool(get_funds, auth_token=AUTH_TOKEN, broker=broker)
    
    # For now, let's assume get_funds is not heavily blocking for the sake of refactoring
    # This might need to be revisited for production performance.
    success, response, status_code = get_funds(db, auth_token=AUTH_TOKEN, broker=broker)


    if not success:
        logger.error(f"Failed to get funds data: {response.get('message', 'Unknown error')}")
        # Redirect to logout, as it's likely an expired token
        return RedirectResponse(url="/logout")

    margin_data = response.get("data", {})

    if not margin_data:
        logger.error(f"Failed to get margin data for user {login_username} - authentication may have expired")
        return RedirectResponse(url="/logout")

    return templates.TemplateResponse("dashboard.html", {"request": request, "margin_data": margin_data})