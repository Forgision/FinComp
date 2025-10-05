from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional
from app.db.session import get_db
from app.schemas.telegram import BotConfigSchema, UserLinkSchema, BroadcastSchema, NotificationSchema, PreferencesSchema, StatsSchema
from database.telegram_db import (
    get_all_telegram_users,
    get_telegram_user_by_username,
    update_bot_config,
    get_bot_config,
    get_command_stats,
    update_user_preferences,
    get_user_preferences
)
from database.auth_db import verify_api_key
from services.telegram_bot_service import telegram_bot_service
from utils.logging import get_logger
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor

logger = get_logger(__name__)

router = APIRouter()

# Thread pool for async operations
executor = ThreadPoolExecutor(max_workers=2)

# Rate limit for telegram operations (This will be handled by a middleware later)
TELEGRAM_RATE_LIMIT = os.getenv("TELEGRAM_RATE_LIMIT", "30 per minute")

def run_async(coro):
    """Helper to run async coroutine in sync context"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

@router.get("/config")
async def get_bot_configuration(request: Request, db: Session = Depends(get_db)):
    """Get current bot configuration"""
    api_key = request.headers.get('X-API-KEY') or request.query_params.get('apikey')

    if not api_key or not verify_api_key(api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key"
        )

    config = get_bot_config()

    # Don't expose the full token for security
    if config.get('bot_token'):
        config['bot_token'] = config['bot_token'][:10] + '...' if len(config['bot_token']) > 10 else config['bot_token']

    return JSONResponse(content={
        'status': 'success',
        'data': config
    }, status_code=status.HTTP_200_OK)

@router.post("/config")
async def update_bot_configuration(bot_config: BotConfigSchema, request: Request, db: Session = Depends(get_db)):
    """Update bot configuration"""
    api_key = bot_config.apikey or request.headers.get('X-API-KEY')

    if not api_key or not verify_api_key(api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key"
        )

    config_update = bot_config.model_dump(exclude_unset=True)

    success = update_bot_config(config_update)

    if success:
        return JSONResponse(content={
            'status': 'success',
            'message': 'Bot configuration updated'
        }, status_code=status.HTTP_200_OK)
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update bot configuration"
        )

@router.post("/start")
async def start_telegram_bot(request: Request, db: Session = Depends(get_db)):
    """Start the Telegram bot"""
    api_key = request.headers.get('X-API-KEY') or request.query_params.get('apikey')

    if not api_key or not verify_api_key(api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key"
        )

    config = get_bot_config()

    if not config.get('bot_token'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bot token not configured"
        )
    
    # Run the bot initialization and start in a separate thread to avoid blocking
    # and to handle the asyncio loop correctly.
    loop = asyncio.get_event_loop()
    if loop.is_running():
        # If an event loop is already running, run in default executor
        success, message = await loop.run_in_executor(
            executor,
            lambda: run_async(telegram_bot_service.initialize_bot(
                token=config['bot_token']
            ))
        )
    else:
        # If no event loop is running, create and run a new one
        success, message = await asyncio.to_thread(
            lambda: run_async(telegram_bot_service.initialize_bot(
                token=config['bot_token']
            ))
        )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=message
        )

    # Note: Starting the bot (polling or webhook) should ideally be handled by a background task
    # or a separate process managed by the lifespan events of the FastAPI app.
    # For now, we'll keep the placeholder logic similar to the Flask-RESTX version.
    # The actual bot instance (bot) is not directly accessible here as it's managed by telegram_bot_service.
    
    # Assuming telegram_bot_service.start_polling() or similar is handled internally after initialize_bot
    # For a proper FastAPI integration, this would likely involve a background task or a separate process.
    # For now, we'll return a success message assuming the service handles the start.
    
    return JSONResponse(content={
        'status': 'success',
        'message': "Bot initialized. Polling/Webhook start should be handled by the service."
    }, status_code=status.HTTP_200_OK)


@router.post("/stop")
async def stop_telegram_bot(request: Request, db: Session = Depends(get_db)):
    """Stop the Telegram bot"""
    api_key = request.headers.get('X-API-KEY') or request.query_params.get('apikey')

    if not api_key or not verify_api_key(api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key"
        )

    # Stop bot
    loop = asyncio.get_event_loop()
    if loop.is_running():
        success, message = await loop.run_in_executor(executor, lambda: run_async(telegram_bot_service.stop_bot()))
    else:
        success, message = await asyncio.to_thread(lambda: run_async(telegram_bot_service.stop_bot()))

    if success:
        return JSONResponse(content={
            'status': 'success',
            'message': message
        }, status_code=status.HTTP_200_OK)
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=message
        )

@router.post("/webhook")
async def handle_telegram_webhook(request: Request):
    """Handle Telegram webhook updates"""
    update_data = await request.json()

    if not update_data:
        return JSONResponse(content="", status_code=status.HTTP_200_OK)

    logger.info(f"Webhook update received: {update_data}")
    # Here, you would typically pass the update to your telegram_bot_service for processing.
    # For example: await telegram_bot_service.process_webhook_update(update_data)

    return JSONResponse(content="", status_code=status.HTTP_200_OK)

@router.get("/users")
async def get_telegram_users(request: Request, db: Session = Depends(get_db),
                             broker: Optional[str] = None, notifications_enabled: Optional[bool] = None):
    # This endpoint does not directly use UserLinkSchema for input,
    # but the output might conform to a list of UserLinkSchema.
    # For now, it's primarily for fetching.
    """Get all linked Telegram users"""
    api_key = request.headers.get('X-API-KEY') or request.query_params.get('apikey')

    if not api_key or not verify_api_key(api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key"
        )

    filters = {}
    if broker:
        filters['broker'] = broker
    if notifications_enabled is not None:
        filters['notifications_enabled'] = notifications_enabled

    users = get_all_telegram_users(filters)

    return JSONResponse(content={
        'status': 'success',
        'data': users,
        'count': len(users)
    }, status_code=status.HTTP_200_OK)

@router.post("/broadcast")
async def broadcast_message(broadcast_data: BroadcastSchema, request: Request, db: Session = Depends(get_db)):
    """Broadcast message to multiple users"""
    api_key = broadcast_data.apikey or request.headers.get('X-API-KEY')

    if not api_key or not verify_api_key(api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key"
        )

    if not broadcast_data.message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message is required"
        )

    config = get_bot_config()
    if not config.get('broadcast_enabled', True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Broadcast is disabled"
        )

    success_count, fail_count = await telegram_bot_service.broadcast_message(
        message=broadcast_data.message,
        filters=broadcast_data.filters
    )

    return JSONResponse(content={
        'status': 'success',
        'message': f'Broadcast sent to {success_count} users, failed for {fail_count} users',
        'success_count': success_count,
        'fail_count': fail_count
    }, status_code=status.HTTP_200_OK)

@router.post("/notify")
async def send_notification(notification_data: NotificationSchema, request: Request, db: Session = Depends(get_db)):
    """Send notification to a specific user"""
    api_key = notification_data.apikey or request.headers.get('X-API-KEY')

    if not api_key or not verify_api_key(api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key"
        )

    if not notification_data.username or not notification_data.message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username and message are required"
        )

    user = get_telegram_user_by_username(notification_data.username)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found or not linked to Telegram"
        )

    success = await telegram_bot_service.send_notification(
        telegram_id=user.get('telegram_id'),
        message=notification_data.message
    )

    if success:
        return JSONResponse(content={
            'status': 'success',
            'message': 'Notification sent successfully'
        }, status_code=status.HTTP_200_OK)
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send notification"
        )

@router.get("/stats")
async def get_telegram_stats(request: Request, db: Session = Depends(get_db), stats_params: StatsSchema = Depends()):
    """Get bot usage statistics"""
    api_key = request.headers.get('X-API-KEY') or request.query_params.get('apikey')

    if not api_key or not verify_api_key(api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key"
        )

    stats = get_command_stats(stats_params.days)

    return JSONResponse(content={
        'status': 'success',
        'data': stats
    }, status_code=status.HTTP_200_OK)

@router.get("/preferences")
async def get_user_preferences_endpoint(request: Request, db: Session = Depends(get_db), telegram_id: int = None):
    """Get user preferences"""
    api_key = request.headers.get('X-API-KEY') or request.query_params.get('apikey')

    if not api_key or not verify_api_key(api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key"
        )

    if not telegram_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="telegram_id is required"
        )

    preferences = get_user_preferences(telegram_id)

    return JSONResponse(content={
        'status': 'success',
        'data': preferences
    }, status_code=status.HTTP_200_OK)

@router.post("/preferences")
async def update_user_preferences_endpoint(user_preferences: PreferencesSchema, request: Request, db: Session = Depends(get_db)):
    """Update user preferences"""
    api_key = user_preferences.apikey or request.headers.get('X-API-KEY')

    if not api_key or not verify_api_key(api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key"
        )

    if not user_preferences.telegram_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="telegram_id is required"
        )

    preferences_update = user_preferences.model_dump(exclude_unset=True, exclude={'apikey', 'telegram_id'})

    success = update_user_preferences(user_preferences.telegram_id, preferences_update)

    if success:
        return JSONResponse(content={
            'status': 'success',
            'message': 'Preferences updated successfully'
        }, status_code=status.HTTP_200_OK)
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update preferences"
        )