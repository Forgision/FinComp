from fastapi import APIRouter, Depends, Request, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import secrets
from argon2 import PasswordHasher
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.utils.web.security import generate_api_key
from app.db.auth_db import upsert_api_key, get_api_key_for_tradingview
from app.web.frontend import templates
from app.core.config import settings
from app.utils.logging import logger

# Initialize Argon2 hasher
ph = PasswordHasher()

apikey_router = APIRouter()


async def check_session_validity_dependency(request: Request):
    if "user" not in request.session:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            detail="Session not valid",
            headers={"Location": "/login"}
        )
    return request.session["user"]

@apikey_router.get('/apikey', response_class=HTMLResponse)
async def get_manage_api_key(
    request: Request,
    login_username: str = Depends(check_session_validity_dependency)
):
    # Get the decrypted API key if it exists
    api_key = get_api_key_for_tradingview(login_username)
    has_api_key = api_key is not None
    logger.info(f"Checking API key status for user: {login_username}")
    return templates.TemplateResponse(
        "apikey.html",
        {
            "request": request,
            "login_username": login_username,
            "has_api_key": has_api_key,
            "api_key": api_key
        }
    )

@apikey_router.post('/apikey', response_class=JSONResponse)
async def post_manage_api_key(
    request: Request,
    db: Session = Depends(get_db),
    login_username: str = Depends(check_session_validity_dependency)
):
    try:
        request_json = await request.json()
        user_id = request_json.get('user_id')
    except Exception as e:
        logger.error(f"Error parsing JSON for API key update: {e}")
        return JSONResponse(
            content={'error': 'Invalid JSON format'},
            status_code=status.HTTP_400_BAD_REQUEST
        )

    if not user_id:
        logger.error("API key update attempted without user ID")
        return JSONResponse(
            content={'error': 'User ID is required'},
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    # Generate new API key
    api_key = generate_api_key()
    
    # Store the API key (upsert_api_key will handle both hashing and encryption)
    key_id = upsert_api_key(db, user_id, api_key) # Assuming upsert_api_key takes db session
    
    if key_id is not None:
        logger.info(f"API key updated successfully for user: {user_id}")
        return JSONResponse(
            content={
                'message': 'API key updated successfully.',
                'api_key': api_key,
                'key_id': key_id
            },
            status_code=status.HTTP_200_OK
        )
    else:
        logger.error(f"Failed to update API key for user: {user_id}")
        return JSONResponse(
            content={'error': 'Failed to update API key'},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )