import asyncio
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from pydantic import BaseModel, Field

from app.core.services.telegram_bot_service import telegram_bot_service
from app.core.models.auth_db import verify_api_key
from app.core.models.telegram_db import (
    get_all_telegram_users,
    get_bot_config,
    get_telegram_user_by_username,
    update_bot_config,
)
from app.utils.logging import logger

telegram_router = APIRouter(prefix="/telegram", tags=["Telegram"])

# Pydantic Models for Telegram API (formerly Flask-RestX models)
class BotConfig(BaseModel):
    token: Optional[str] = Field(None, description='Telegram Bot Token')
    webhook_url: Optional[str] = Field(None, description='Webhook URL for bot')
    polling_mode: Optional[bool] = Field(None, description='Use polling mode')
    broadcast_enabled: Optional[bool] = Field(None, description='Enable broadcast messages')
    rate_limit_per_minute: Optional[int] = Field(None, description='Rate limit per minute')
    apikey: Optional[str] = Field(None, description='API Key for authentication')

class UserLink(BaseModel):
    apikey: str = Field(..., description='API Key')
    telegram_id: int = Field(..., description='Telegram User ID')
    username: str = Field(..., description='OpenAlgo Username')

class Broadcast(BaseModel):
    apikey: str = Field(..., description='API Key')
    message: str = Field(..., description='Message to broadcast')
    filters: Optional[Dict[str, Any]] = Field(None, description='Optional filters for users')

class Notification(BaseModel):
    apikey: str = Field(..., description='API Key')
    username: str = Field(..., description='OpenAlgo Username')
    message: str = Field(..., description='Notification message')
    priority: int = Field(5, description='Priority (1-10)')

class UserPreferences(BaseModel):
    apikey: str = Field(..., description='API Key')
    telegram_id: int = Field(..., description='Telegram User ID')
    order_notifications: Optional[bool] = Field(None, description='Enable order notifications')
    trade_notifications: Optional[bool] = Field(None, description='Enable trade notifications')
    pnl_notifications: Optional[bool] = Field(None, description='Enable P&L notifications')
    daily_summary: Optional[bool] = Field(None, description='Enable daily summary')
    summary_time: Optional[str] = Field(None, description='Daily summary time (HH:MM)')
    language: Optional[str] = Field(None, description='Preferred language')
    timezone: Optional[str] = Field(None, description='User timezone')

# Dependency for API Key verification
async def get_api_key(x_api_key: Optional[str] = Depends(None), apikey: Optional[str] = None):
    api_key = x_api_key or apikey
    if not api_key or not verify_api_key(api_key):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing API key")
    return api_key

@telegram_router.get("/config", summary="Get current bot configuration")
async def get_bot_configuration(api_key: str = Depends(get_api_key)):
    """
    Get the current bot configuration.

    Args:
        api_key: The API key for authentication.

    Returns:
        A dictionary with the current bot configuration.

    Raises:
        HTTPException: If an error occurs while fetching the configuration.
    """
    try:
        config = get_bot_config()
        # Don't expose the full token for security
        if config.get('bot_token'):
            config['bot_token'] = config['bot_token'][:10] + '...' if len(config['bot_token']) > 10 else config['bot_token']
        return {"status": "success", "data": config}
    except Exception:
        logger.exception("Error getting bot config")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get bot configuration")

@telegram_router.post("/config", summary="Update bot configuration")
async def update_bot_configuration(config_data: BotConfig, api_key: str = Depends(get_api_key)):
    """
    Update the bot configuration.

    Args:
        config_data: The new configuration data.
        api_key: The API key for authentication.

    Returns:
        A dictionary with a success message.

    Raises:
        HTTPException: If an error occurs while updating the configuration.
    """
    try:
        config_update = config_data.model_dump(exclude_unset=True)
        # Remove apikey from config_update if present
        config_update.pop('apikey', None)

        success = await asyncio.to_thread(update_bot_config, config_update)
        if success:
            return {"status": "success", "message": "Bot configuration updated"}
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update bot configuration")
    except Exception:
        logger.exception("Error updating bot config")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update bot configuration")

@telegram_router.post("/start", summary="Start the Telegram bot")
async def start_bot(api_key: str = Depends(get_api_key)):
    """
    Start the Telegram bot.

    Args:
        api_key: The API key for authentication.

    Returns:
        A dictionary with a success message.

    Raises:
        HTTPException: If an error occurs while starting the bot.
    """
    try:
        config = get_bot_config()
        if not config.get('bot_token'):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bot token not configured")

        success, message = await telegram_bot_service.initialize_bot(
            token=config['bot_token'],
            webhook_url=config.get('webhook_url')
        )

        if not success:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=message)

        # Assuming telegram_bot_service handles starting polling or webhook internally after initialize
        return {"status": "success", "message": message}
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.exception("Error starting bot")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to start bot: {str(e)}")

@telegram_router.post("/stop", summary="Stop the Telegram bot")
async def stop_bot(api_key: str = Depends(get_api_key)):
    """
    Stop the Telegram bot.

    Args:
        api_key: The API key for authentication.

    Returns:
        A dictionary with a success message.

    Raises:
        HTTPException: If an error occurs while stopping the bot.
    """
    try:
        success, message = await telegram_bot_service.stop_bot()
        if success:
            return {"status": "success", "message": message}
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=message)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.exception("Error stopping bot")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to stop bot: {str(e)}")

@telegram_router.post("/webhook", summary="Handle Telegram webhook updates")
async def handle_webhook(request: Request):
    """
    Handle Telegram webhook updates.

    Args:
        request: The incoming request object.

    Returns:
        A status code indicating the result of the operation.
    """
    try:
        update_data = await request.json()
        if not update_data:
            return status.HTTP_200_OK # Always return 200 to Telegram

        # Process update asynchronously (assuming a method in telegram_bot_service)
        # For now, just log and return 200
        logger.info(f"Webhook update received: {update_data}")
        return status.HTTP_200_OK
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        return status.HTTP_200_OK # Still return 200 to avoid Telegram retries

@telegram_router.get("/users", summary="Get all linked Telegram users")
async def get_telegram_users(api_key: str = Depends(get_api_key), broker: Optional[str] = None, notifications_enabled: Optional[bool] = None):
    """
    Get all linked Telegram users.

    Args:
        api_key: The API key for authentication.
        broker: An optional broker to filter by.
        notifications_enabled: An optional flag to filter by.

    Returns:
        A dictionary with a list of users.

    Raises:
        HTTPException: If an error occurs while fetching the users.
    """
    try:
        filters = {}
        if broker:
            filters['broker'] = broker
        if notifications_enabled is not None:
            filters['notifications_enabled'] = notifications_enabled

        users = await asyncio.to_thread(get_all_telegram_users, filters)
        return {"status": "success", "data": users, "count": len(users)}
    except Exception:
        logger.exception("Error getting telegram users")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get users")

@telegram_router.post("/broadcast", summary="Broadcast message to multiple users")
async def broadcast_message(broadcast_data: Broadcast, api_key: str = Depends(get_api_key)):
    """
    Broadcast a message to multiple users.

    Args:
        broadcast_data: The broadcast data.
        api_key: The API key for authentication.

    Returns:
        A dictionary with the result of the broadcast.

    Raises:
        HTTPException: If an error occurs during the broadcast.
    """
    try:
        if not broadcast_data.message:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Message is required")

        config = get_bot_config()
        if not config.get('broadcast_enabled', True):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Broadcast is disabled")

        # Assuming telegram_bot_service has a broadcast method
        success_count, fail_count = await telegram_bot_service.broadcast_message(broadcast_data.message, broadcast_data.filters)

        return {
            "status": "success",
            "message": f"Broadcast sent to {success_count} users, failed for {fail_count} users",
            "success_count": success_count,
            "fail_count": fail_count
        }
    except HTTPException as e:
        raise e
    except Exception:
        logger.exception("Error broadcasting message")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to broadcast message")

@telegram_router.post("/notify", summary="Send notification to a specific user")
async def send_notification(notification_data: Notification, api_key: str = Depends(get_api_key)):
    """
    Send a notification to a specific user.

    Args:
        notification_data: The notification data.
        api_key: The API key for authentication.

    Returns:
        A dictionary with a success message.

    Raises:
        HTTPException: If an error occurs while sending the notification.
    """
    try:
        if not notification_data.username or not notification_data.message:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username and message are required")

        user = await asyncio.to_thread(get_telegram_user_by_username, notification_data.username)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found or not linked to Telegram")

        # Assuming telegram_bot_service has a send_notification method
        success = await telegram_bot_service.send_notification(
            telegram_id=user['telegram_id'], # Assuming user object has telegram_id
            message=notification_data.message,
            priority=notification_data.priority
        )

        if success:
            return {"status": "success", "message": "Notification sent successfully"}
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to send notification")
    except HTTPException as e:
        raise e
    except Exception:
        logger.exception("Error sending notification")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to send notification")

@telegram_router.get("/stats", summary="Get bot usage statistics")
async def get_telegram_stats(api_key: str = Depends(get_api_key), days: int = 7):
    """
    Get bot usage statistics.

    Args:
        api_key: The API key for authentication.
        days: The number of days to get stats for.

    Returns:
        A dictionary with bot usage statistics.

    Raises:
        HTTPException: If an error occurs while fetching the statistics.
    """
    try:
        stats = await asyncio.to_thread(get_command_stats, days)
        return {"status": "success", "data": stats}
    except Exception:
        logger.exception("Error getting stats")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get statistics")

@telegram_router.get("/preferences", summary="Get user preferences")
async def get_user_telegram_preferences(api_key: str = Depends(get_api_key), telegram_id: int = Query(..., description="Telegram User ID")):
    """
    Get user preferences.

    Args:
        api_key: The API key for authentication.
        telegram_id: The user's Telegram ID.

    Returns:
        A dictionary with the user's preferences.

    Raises:
        HTTPException: If an error occurs while fetching the preferences.
    """
    try:
        preferences = await asyncio.to_thread(get_user_preferences, telegram_id)
        return {"status": "success", "data": preferences}
    except Exception:
        logger.exception("Error getting preferences")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get preferences")

@telegram_router.post("/preferences", summary="Update user preferences")
async def update_user_telegram_preferences(preferences_data: UserPreferences, api_key: str = Depends(get_api_key)):
    """
    Update user preferences.

    Args:
        preferences_data: The new preferences data.
        api_key: The API key for authentication.

    Returns:
        A dictionary with a success message.

    Raises:
        HTTPException: If an error occurs while updating the preferences.
    """
    try:
        if not preferences_data.telegram_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="telegram_id is required")

        preferences_update = preferences_data.model_dump(exclude_unset=True)
        preferences_update.pop('apikey', None) # Remove apikey from update payload

        success = await asyncio.to_thread(update_user_preferences, preferences_data.telegram_id, preferences_update)
        if success:
            return {"status": "success", "message": "Preferences updated successfully"}
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update preferences")
    except HTTPException as e:
        raise e
    except Exception:
        logger.exception("Error updating preferences")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update preferences")
