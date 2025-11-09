from argon2 import PasswordHasher
from app.core.schemas.auth_db import get_api_key_for_tradingview, upsert_api_key
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse
from app.web.frontend import templates
from app.utils.auth_utils import generate_api_key
from app.utils.logging import logger
from app.utils.session import check_session_validity_fastapi, get_db

apikey_router = APIRouter(prefix="", tags=["apikey"])

# Initialize Argon2 hasher
ph = PasswordHasher()


@apikey_router.get("/apikey", response_class=HTMLResponse)
async def manage_api_key_get(
    request: Request,
    db=Depends(get_db),
    user: dict = Depends(check_session_validity_fastapi),
):
    login_username = user
    # Get the decrypted API key if it exists
    api_key = get_api_key_for_tradingview(db, login_username)
    has_api_key = api_key is not None
    logger.info(f"Checking API key status for user: {login_username}")
    return templates.TemplateResponse(
        "apikey.html",
        {
            "request": request,
            "login_username": login_username,
            "has_api_key": has_api_key,
            "api_key": api_key,
        },
    )


@apikey_router.post("/apikey")
async def manage_api_key_post(
    request: Request,
    db=Depends(get_db),
    user: dict = Depends(check_session_validity_fastapi),
):
    data = await request.json()
    user_id = data.get("user_id")
    if not user_id:
        logger.error("API key update attempted without user ID")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="User ID is required"
        )

    # Generate new API key
    api_key = generate_api_key()

    # Store the API key (auth_db will handle both hashing and encryption)
    key_id = upsert_api_key(db, user_id, api_key)

    if key_id is not None:
        logger.info(f"API key updated successfully for user: {user_id}")
        return JSONResponse(
            content={
                "message": "API key updated successfully.",
                "api_key": api_key,
                "key_id": key_id,
            }
        )
    else:
        logger.error(f"Failed to update API key for user: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update API key",
        )
