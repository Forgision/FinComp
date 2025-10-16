import asyncio
import json
from typing import Dict, Any
from fastapi import APIRouter, Depends, Request, Response, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.db.telegram_db import (
    get_bot_config,
    update_bot_config,
    get_all_telegram_users,
    get_telegram_user_by_username,
    delete_telegram_user,
    get_command_stats,
    get_telegram_user
)
from app.web.services.telegram_bot_service import telegram_bot_service
from app.utils.logging import logger
from app.utils.session import check_session_validity_fastapi
from app.db.session import get_db
from app.web.frontend import templates
from app.core.config import settings

# Rate limiting configuration from environment
# Assuming slowapi integration will be handled via middleware or a custom dependency
TELEGRAM_MESSAGE_RATE_LIMIT = settings.TELEGRAM_MESSAGE_RATE_LIMIT

# Define the FastAPI router
telegram_router = APIRouter(prefix="/telegram", tags=["Telegram"])

@telegram_router.get("/", response_class=HTMLResponse)
async def telegram_index(
    request: Request,
    db: Session = Depends(get_db),
    current_user: str = Depends(check_session_validity_fastapi)
):
    """Main Telegram bot control panel"""
    try:
        # Get bot configuration
        config = get_bot_config(db)

        # Get bot status
        bot_status = {
            'is_running': telegram_bot_service.is_running,
            'bot_username': config.get('bot_username'),
            'is_configured': bool(config.get('bot_token'))
        }

        # Get user stats
        users = get_all_telegram_users(db)
        stats = get_command_stats(db, days=7)

        # Get current user's telegram link status
        telegram_user = get_telegram_user_by_username(db, current_user) if current_user else None

        return templates.TemplateResponse("telegram/index.html", {
            "request": request,
            "bot_status": bot_status,
            "config": config,
            "users": users,
            "stats": stats,
            "telegram_user": telegram_user
        })

    except Exception as e:
        logger.error(f"Error in telegram index: {str(e)}")
        raise HTTPException(status_code=500, detail="Error loading Telegram panel")

@telegram_router.get("/config", response_class=HTMLResponse)
async def telegram_config_get(
    request: Request,
    db: Session = Depends(get_db),
    current_user: str = Depends(check_session_validity_fastapi)
):
    """Bot configuration page - GET"""
    config = get_bot_config(db)
    logger.debug(f"Config loaded for display: broadcast_enabled={config.get('broadcast_enabled')}, bot_token={'[REDAACTED]' if config.get('bot_token') else 'absent'}")
    return templates.TemplateResponse("telegram/config.html", {"request": request, "config": config})

@telegram_router.post("/config", response_class=JSONResponse)
async def telegram_config_post(
    request: Request,
    db: Session = Depends(get_db),
    current_user: str = Depends(check_session_validity_fastapi)
):
    """Bot configuration page - POST"""
    try:
        data = await request.json()

        # Update configuration
        config_update = {}
        if 'token' in data:
            config_update['bot_token'] = data['token']
        if 'broadcast_enabled' in data:
            config_update['broadcast_enabled'] = bool(data['broadcast_enabled'])
        if 'rate_limit_per_minute' in data:
            config_update['rate_limit_per_minute'] = int(data['rate_limit_per_minute'])

        # Log config save without exposing token
        safe_config = {k: '[REDACTED]' if k == 'bot_token' else v for k, v in config_update.items()}
        logger.debug(f"Saving config: {safe_config}")
        success = update_bot_config(db, config_update)

        if success:
            # Verify what was saved
            saved_config = get_bot_config(db)
            logger.debug(f"Config after save: broadcast_enabled={saved_config.get('broadcast_enabled')}, bot_token={'[REDACTED]' if saved_config.get('bot_token') else 'absent'}")
            return JSONResponse({'status': 'success', 'message': 'Configuration updated'})
        else:
            raise HTTPException(status_code=500, detail='Failed to update configuration')

    except Exception as e:
        logger.error(f"Error updating config: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@telegram_router.get("/users", response_class=HTMLResponse)
async def telegram_users(
    request: Request,
    db: Session = Depends(get_db),
    current_user: str = Depends(check_session_validity_fastapi)
):
    """Telegram users management page"""
    users = get_all_telegram_users(db)
    stats = get_command_stats(db, days=30)

    return templates.TemplateResponse("telegram/users.html", {
        "request": request,
        "users": users,
        "stats": stats
    })

@telegram_router.get("/analytics", response_class=HTMLResponse)
async def telegram_analytics(
    request: Request,
    db: Session = Depends(get_db),
    current_user: str = Depends(check_session_validity_fastapi)
):
    """Analytics and statistics page"""
    # Get stats for different periods
    stats_7d = get_command_stats(db, days=7)
    stats_30d = get_command_stats(db, days=30)

    # Get all users for additional analytics
    users = get_all_telegram_users(db)

    # Calculate additional metrics
    active_users_count = len([u for u in users if u.get('notifications_enabled')])
    total_users = len(users)

    analytics_data = {
        'stats_7d': stats_7d,
        'stats_30d': stats_30d,
        'total_users': total_users,
        'active_users': active_users_count,
        'users': users
    }

    return templates.TemplateResponse("telegram/analytics.html", {
        "request": request,
        "analytics": analytics_data
    })

@telegram_router.post("/bot/start", response_class=JSONResponse)
async def start_bot(
    db: Session = Depends(get_db),
    current_user: str = Depends(check_session_validity_fastapi)
):
    """Start the telegram bot"""
    try:
        config = get_bot_config(db)

        if not config.get('bot_token'):
            raise HTTPException(status_code=400, detail='Bot token not configured')

        logger.info("Initializing bot with async method")
        success, message = await telegram_bot_service.initialize_bot(token=config['bot_token'])

        if not success:
            raise HTTPException(status_code=500, detail=message)

        success, message = await telegram_bot_service.start_bot()

        if success:
            return JSONResponse({'status': 'success', 'message': message})
        else:
            raise HTTPException(status_code=500, detail=message)

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error starting bot: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@telegram_router.post("/bot/stop", response_class=JSONResponse)
async def stop_bot(
    current_user: str = Depends(check_session_validity_fastapi)
):
    """Stop the telegram bot"""
    try:
        success, message = await telegram_bot_service.stop_bot()

        if success:
            return JSONResponse({'status': 'success', 'message': message})
        else:
            raise HTTPException(status_code=500, detail=message)

    except Exception as e:
        logger.error(f"Error stopping bot: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@telegram_router.get("/bot/status", response_class=JSONResponse)
async def bot_status(
    db: Session = Depends(get_db),
    current_user: str = Depends(check_session_validity_fastapi)
):
    """Get bot status"""
    try:
        config = get_bot_config(db)

        status = {
            'is_running': telegram_bot_service.is_running,
            'is_configured': bool(config.get('bot_token')),
            'bot_username': config.get('bot_username'),
            'is_active': config.get('is_active', False)
        }

        return JSONResponse({'status': 'success', 'data': status})

    except Exception as e:
        logger.error(f"Error getting bot status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@telegram_router.post("/broadcast", response_class=JSONResponse)
async def broadcast(
    data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: str = Depends(check_session_validity_fastapi)
):
    """Send broadcast message"""
    try:
        message = data.get('message')
        filters = data.get('filters', {})

        if not message:
            raise HTTPException(status_code=400, detail='Message is required')

        # Check if broadcast is enabled
        config = get_bot_config(db)
        if not config.get('broadcast_enabled', True):
            raise HTTPException(status_code=403, detail='Broadcast is disabled')

        # Run broadcast using the bot's event loop
        if telegram_bot_service.bot_loop and telegram_bot_service.is_running:
            success_count, fail_count = await asyncio.to_thread(
                telegram_bot_service.broadcast_message, message, filters
            )
        else:
            success_count, fail_count = 0, 0
            logger.error("Bot not running or loop not available")

        return JSONResponse({
            'status': 'success',
            'message': f'Sent to {success_count} users, failed for {fail_count}',
            'success_count': success_count,
            'fail_count': fail_count
        })

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error broadcasting: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@telegram_router.post("/user/{telegram_id}/unlink", response_class=JSONResponse)
async def unlink_user(
    telegram_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(check_session_validity_fastapi)
):
    """Unlink a telegram user"""
    try:
        success = delete_telegram_user(db, telegram_id)

        if success:
            return JSONResponse({'status': 'success', 'message': 'User unlinked'})
        else:
            raise HTTPException(status_code=500, detail='Failed to unlink user')

    except Exception as e:
        logger.error(f"Error unlinking user: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@telegram_router.post("/test-message", response_class=JSONResponse)
async def send_test_message(
    db: Session = Depends(get_db),
    current_user: str = Depends(check_session_validity_fastapi)
):
    """Send a test message to the current user or first available user"""
    try:
        if not current_user:
            raise HTTPException(status_code=404, detail='User not found')

        # Get all telegram users
        all_users = get_all_telegram_users(db)

        # Try to find user by openalgo_username
        telegram_user = None
        for user in all_users:
            if user.get('openalgo_username') == current_user:
                telegram_user = user
                break

        # If no linked user found, try to send to the first available user (for admin testing)
        message: str
        if not telegram_user and all_users:
            telegram_user = all_users[0]  # Use first available user for testing
            message = f"🔔 Test Message from OpenAlgo (Admin: {current_user})\n\nYour Telegram integration is working correctly!"
        elif telegram_user:
            message = "🔔 Test Message from OpenAlgo\n\nYour Telegram integration is working correctly!"
        else:
            raise HTTPException(
                status_code=404,
                detail='No Telegram users found. Please ensure at least one user has started the bot with /start'
            )

        # Run notification using the bot's event loop
        if telegram_bot_service.bot_loop and telegram_bot_service.is_running:
            success = await asyncio.to_thread(
                telegram_bot_service.send_notification, telegram_user['telegram_id'], message
            )
        else:
            success = False
            logger.error("Bot not running or loop not available")

        if success:
            return JSONResponse({'status': 'success', 'message': 'Test message sent'})
        else:
            raise HTTPException(status_code=500, detail='Failed to send test message')

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error sending test message: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@telegram_router.post("/send-message", response_class=JSONResponse)
# This route needs slowapi integration for rate limiting. Placeholder for now.
async def send_message(
    data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: str = Depends(check_session_validity_fastapi)
):
    """Send a message to a specific Telegram user (Admin only)"""
    try:
        # Admin-only check (you can customize this based on your admin logic)
        # For now, we'll add basic protections

        telegram_id = data.get('telegram_id')
        message = data.get('message')

        if not telegram_id or not message:
            raise HTTPException(status_code=400, detail='Missing telegram_id or message')

        # Validate telegram_id is an integer to prevent injection
        try:
            telegram_id = int(telegram_id)
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail='Invalid telegram_id')

        # Check if the telegram_id belongs to a registered user
        user = get_telegram_user(db, telegram_id)
        if not user:
            raise HTTPException(status_code=404, detail='User not found')

        # Limit message length to prevent abuse
        if len(message) > 4096:  # Telegram's max message length
            raise HTTPException(status_code=400, detail='Message too long (max 4096 characters)')

        # Check if bot is running
        if not telegram_bot_service.is_running:
            raise HTTPException(status_code=503, detail='Bot is not running')

        # Log who sent the message for audit trail
        logger.info(f"User {current_user} sending message to Telegram ID {telegram_id}")

        # Run notification using the bot's event loop
        if telegram_bot_service.bot_loop and telegram_bot_service.is_running:
            success = await asyncio.to_thread(
                telegram_bot_service.send_notification, telegram_id, message
            )
        else:
            success = False
            logger.error("Bot not running or loop not available")

        if success:
            logger.info(f"Message sent to Telegram ID {telegram_id}")
            return JSONResponse({'status': 'success', 'message': 'Message sent successfully'})
        else:
            raise HTTPException(status_code=500, detail='Failed to send message')

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error sending message: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))