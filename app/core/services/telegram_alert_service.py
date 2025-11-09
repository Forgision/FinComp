"""
Telegram Alert Service for Order Notifications
Handles asynchronous sending of order-related alerts to users via Telegram
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, Optional

from app.core.schemas.auth_db import get_username_by_apikey
from app.core.schemas.telegram_db import (
    add_notification,
    get_all_telegram_users,
    get_telegram_user_by_username,
)
from app.utils.logging import logger
from sqlalchemy.ext.asyncio import AsyncSession

# Lazy import telegram bot service to avoid import errors if telegram package not installed properly
telegram_bot_service = None


def _get_telegram_bot_service():
    """Lazy load telegram bot service"""
    global telegram_bot_service
    if telegram_bot_service is None:
        try:
            from services.telegram_bot_service import telegram_bot_service as tbs

            telegram_bot_service = tbs
        except ImportError as e:
            logger.warning(f"Telegram bot service not available: {e}")

            # Create a mock object with minimal interface
            class MockTelegramBotService:
                is_running = False

                async def send_notification(self, *args, **kwargs):
                    return False

            telegram_bot_service = MockTelegramBotService()
    return telegram_bot_service


class TelegramAlertService:
    """Service for sending order-related alerts via Telegram"""

    def __init__(self):
        self.enabled = True
        self.alert_templates = {
            "placeorder": "📈 *Order Placed*\n{details}",
            "placesmartorder": "🎯 *Smart Order Placed*\n{details}",
            "basketorder": "🛒 *Basket Order Executed*\n{details}",
            "splitorder": "✂️ *Split Order Executed*\n{details}",
            "modifyorder": "✏️ *Order Modified*\n{details}",
            "cancelorder": "❌ *Order Cancelled*\n{details}",
            "cancelallorder": "🚫 *All Orders Cancelled*\n{details}",
            "closeposition": "🔒 *Position Closed*\n{details}",
        }

    def format_order_details(
        self, order_type: str, order_data: Dict[str, Any], response: Dict[str, Any]
    ) -> str:
        """Format order details for Telegram message"""
        try:
            details = []
            timestamp = datetime.now().strftime("%H:%M:%S")

            # Add mode indicator at the top
            mode = response.get("mode", "live")
            if mode == "analyze":
                details.append("🔬 **ANALYZE MODE - No Real Order**")
                details.append("─────────────────────")
            else:
                details.append("💰 **LIVE MODE - Real Order**")
                details.append("─────────────────────")

            if order_type == "placeorder":
                details.extend(
                    [
                        f"Symbol: `{order_data.get('symbol', 'N/A')}`",
                        f"Action: {order_data.get('action', 'N/A')}",
                        f"Quantity: {order_data.get('quantity', 'N/A')}",
                        f"Price Type: {order_data.get('pricetype', 'N/A')}",
                        f"Exchange: {order_data.get('exchange', 'N/A')}",
                        f"Product: {order_data.get('product', 'N/A')}",
                    ]
                )
                if response.get("status") == "success":
                    details.append(f"Order ID: `{response.get('orderid', 'N/A')}`")
                else:
                    details.append(f"Error: {response.get('message', 'Failed')}")

            elif order_type == "placesmartorder":
                details.extend(
                    [
                        f"Symbol: `{order_data.get('symbol', 'N/A')}`",
                        f"Action: {order_data.get('action', 'N/A')}",
                        f"Quantity: {order_data.get('quantity', 'N/A')}",
                        f"Position Size: {order_data.get('position_size', 'N/A')}",
                        f"Exchange: {order_data.get('exchange', 'N/A')}",
                    ]
                )
                if response.get("status") == "success":
                    details.append(f"Order ID: `{response.get('orderid', 'N/A')}`")

            elif order_type == "basketorder":
                if response.get("status") == "success":
                    results = response.get("results", [])
                    success_count = len(
                        [r for r in results if r.get("status") == "success"]
                    )
                    failed_count = len(
                        [r for r in results if r.get("status") != "success"]
                    )
                    details.extend(
                        [
                            f"Total Orders: {len(results)}",
                            f"✅ Successful: {success_count}",
                            f"❌ Failed: {failed_count}",
                        ]
                    )
                    # Add first few order details
                    for result in results[:3]:  # Show first 3 orders
                        status_emoji = (
                            "✅" if result.get("status") == "success" else "❌"
                        )
                        details.append(
                            f"{status_emoji} {result.get('symbol', 'N/A')}: {result.get('orderid', result.get('message', 'N/A'))}"
                        )
                    if len(results) > 3:
                        details.append(f"... and {len(results) - 3} more")

            elif order_type == "splitorder":
                if response.get("status") == "success":
                    details.extend(
                        [
                            f"Symbol: `{order_data.get('symbol', 'N/A')}`",
                            f"Total Quantity: {response.get('total_quantity', 'N/A')}",
                            f"Split Size: {response.get('split_size', 'N/A')}",
                            f"Orders Created: {len(response.get('results', []))}",
                        ]
                    )

            elif order_type == "modifyorder":
                details.extend(
                    [
                        f"Order ID: `{order_data.get('orderid', 'N/A')}`",
                        f"Symbol: `{order_data.get('symbol', 'N/A')}`",
                        f"New Quantity: {order_data.get('quantity', 'N/A')}",
                        f"New Price: {order_data.get('price', 'N/A')}",
                    ]
                )
                if response.get("status") == "success":
                    details.append("✅ Modification Successful")
                else:
                    details.append(f"❌ Error: {response.get('message', 'Failed')}")

            elif order_type == "cancelorder":
                details.extend([f"Order ID: `{order_data.get('orderid', 'N/A')}`"])
                if response.get("status") == "success":
                    details.append("✅ Cancellation Successful")
                else:
                    details.append(f"❌ Error: {response.get('message', 'Failed')}")

            elif order_type == "cancelallorder":
                if response.get("status") == "success":
                    canceled = response.get("canceled_orders", [])
                    failed = response.get("failed_cancellations", [])
                    details.extend(
                        [
                            f"✅ Cancelled: {len(canceled)} orders",
                            f"❌ Failed: {len(failed)} orders",
                        ]
                    )
                    if canceled and len(canceled) <= 5:
                        details.append(f"Order IDs: {', '.join(canceled[:5])}")

            elif order_type == "closeposition":
                if response.get("status") == "success":
                    details.append("✅ All positions closed successfully")
                else:
                    details.append(f"❌ Error: {response.get('message', 'Failed')}")

            details.append(f"⏰ Time: {timestamp}")

            # Add strategy if available
            if order_data.get("strategy"):
                details.insert(0, f"Strategy: *{order_data.get('strategy')}*")

            return "\n".join(details)

        except Exception as e:
            logger.error(f"Error formatting order details: {e}")
            return (
                f"Order Type: {order_type}\nStatus: {response.get('status', 'unknown')}"
            )

    async def send_alert(
        self, db: AsyncSession, telegram_id: int, message: str
    ) -> bool:
        """Send alert message asynchronously"""
        try:
            bot_service = _get_telegram_bot_service()
            if not bot_service.is_running:
                logger.debug("Telegram bot is not running, queueing notification")
                await add_notification(db, telegram_id, message, priority=8)
                return True

            success = await bot_service.send_notification(telegram_id, message)
            if not success:
                await add_notification(db, telegram_id, message, priority=8)

            logger.info(f"Telegram notification sent: {success}")
            return success
        except Exception as e:
            logger.error(f"Error sending telegram alert: {e}")
            await add_notification(db, telegram_id, message, priority=8)
            return False

    async def send_order_alert(
        self,
        db: AsyncSession,
        order_type: str,
        order_data: Dict[str, Any],
        response: Dict[str, Any],
        api_key: Optional[str] = None,
    ):
        """
        Send order alert to telegram user asynchronously

        Args:
            order_type: Type of order (placeorder, basketorder, etc.)
            order_data: Original order data
            response: Order response
            api_key: API key to identify user
        """
        try:
            logger.info(
                f"Telegram alert triggered for {order_type}, response: {response.get('status', 'unknown')}"
            )

            if not self.enabled:
                logger.debug("Telegram alerts are disabled globally")
                return

            username = None
            api_key_used = api_key or order_data.get("apikey")

            if api_key_used:
                logger.debug(
                    f"Looking up username for API key (first 10 chars): {api_key_used[:10] if api_key_used else 'None'}..."
                )
                username = await get_username_by_apikey(
                    db, provided_api_key=api_key_used
                )
                logger.debug(f"Username lookup result: {username}")
            else:
                logger.warning("No API key provided for telegram alert")

            if not username:
                logger.warning(
                    f"No username found for telegram alert - api_key present: {bool(api_key_used)}, api_key_length: {len(api_key_used) if api_key_used else 0}"
                )
                try:
                    from flask import has_request_context, session

                    if has_request_context() and session.get("user"):
                        username = session.get("user")
                        logger.info(f"Using username from session: {username}")
                except ImportError:
                    logger.warning("Flask modules not available for session lookup.")
                except Exception as e:
                    logger.warning(
                        f"An unexpected error occurred during session lookup: {e}"
                    )

                if not username:
                    return

            telegram_user = await get_telegram_user_by_username(db, username)
            if not telegram_user or not telegram_user.get("notifications_enabled"):
                logger.info(
                    f"No telegram user or notifications disabled for username: {username}"
                )
                return

            logger.info(
                f"Sending telegram alert to user {username} (telegram_id: {telegram_user['telegram_id']})"
            )

            template = self.alert_templates.get(
                order_type, "📊 *Order Update*\n{details}"
            )
            details = self.format_order_details(order_type, order_data, response)
            message = template.format(details=details)

            await self.send_alert(db, telegram_user["telegram_id"], message)
            logger.info(f"Telegram alert queued successfully for {order_type}")

        except Exception as e:
            logger.error(f"Error queuing telegram alert: {e}", exc_info=True)

    async def send_broadcast_alert(
        self, db: AsyncSession, message: str, filters: Optional[Dict] = None
    ):
        """Send broadcast alert to multiple users"""
        try:
            users = await get_all_telegram_users(db, filters)
            tasks = [
                self.send_alert(db, user["telegram_id"], message)
                for user in users
                if user.get("notifications_enabled")
            ]
            await asyncio.gather(*tasks)
        except Exception as e:
            logger.error(f"Error sending broadcast alert: {e}")

    def toggle_alerts(self, enabled: bool):
        """Enable or disable telegram alerts"""
        self.enabled = enabled
        logger.info(f"Telegram alerts {'enabled' if enabled else 'disabled'}")


# Initialize global instance
telegram_alert_service = TelegramAlertService()
