import traceback
from datetime import datetime
from decimal import Decimal
import pytz
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.web.services.sandbox_service import sandbox_reload_squareoff_schedule, sandbox_get_squareoff_status
from app.db.sandbox_db import (
    get_config, set_config, get_all_configs,
    SandboxOrders, SandboxTrades, SandboxPositions,
    SandboxHoldings, SandboxFunds, db_session as sandbox_db_session
)
from app.utils.session import check_session_validity_fastapi
from app.utils.logging import logger
from app.db.session import get_db
from app.web.frontend import templates
from app.core.config import settings

# Use existing rate limits from .env (same as API endpoints)
API_RATE_LIMIT = settings.API_RATE_LIMIT


sandbox_router = APIRouter(
    prefix="/sandbox",
    tags=["Sandbox"],
    dependencies=[Depends(check_session_validity_fastapi)]
)

@sandbox_router.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code == 429:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                'status': 'error',
                'message': 'Rate limit exceeded. Please try again later.'
            }
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail}
    )

@sandbox_router.get('/', response_class=HTMLResponse)
async def sandbox_config(request: Request, db: Session = Depends(get_db)):
    """Render the sandbox configuration page"""
    try:
        # Get all current configuration values
        configs = get_all_configs()

        # Organize configs into categories for better UI presentation
        organized_configs = {
            'capital': {
                'title': 'Capital Settings',
                'configs': {
                    'starting_capital': configs.get('starting_capital', {}),
                    'reset_day': configs.get('reset_day', {}),
                    'reset_time': configs.get('reset_time', {})
                }
            },
            'leverage': {
                'title': 'Leverage Settings',
                'configs': {
                    'equity_mis_leverage': configs.get('equity_mis_leverage', {}),
                    'equity_cnc_leverage': configs.get('equity_cnc_leverage', {}),
                    'futures_leverage': configs.get('futures_leverage', {}),
                    'option_buy_leverage': configs.get('option_buy_leverage', {}),
                    'option_sell_leverage': configs.get('option_sell_leverage', {})
                }
            },
            'square_off': {
                'title': 'Square-Off Times (IST)',
                'configs': {
                    'nse_bse_square_off_time': configs.get('nse_bse_square_off_time', {}),
                    'cds_bcd_square_off_time': configs.get('cds_bcd_square_off_time', {}),
                    'mcx_square_off_time': configs.get('mcx_square_off_time', {}),
                    'ncdex_square_off_time': configs.get('ncdex_square_off_time', {})
                }
            },
            'intervals': {
                'title': 'Update Intervals (seconds)',
                'configs': {
                    'order_check_interval': configs.get('order_check_interval', {}),
                    'mtm_update_interval': configs.get('mtm_update_interval', {})
                }
            }
        }

        return templates.TemplateResponse('sandbox.html', {"request": request, "configs": organized_configs})
    except Exception as e:
        logger.error(f"Error rendering sandbox config: {str(e)}\n{traceback.format_exc()}")
        # In FastAPI, you might handle flashes differently, or redirect with a query parameter
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER) # Assuming '/' is home

@sandbox_router.post('/update')
async def update_config(request: Request, db: Session = Depends(get_db)):
    """Update sandbox configuration values"""
    try:
        data = await request.json()
        config_key = data.get('config_key')
        config_value = data.get('config_value')

        if not config_key or config_value is None:
            raise HTTPException(status_code=400, detail='Missing config_key or config_value')

        # Validate config value based on key
        validation_error = validate_config(config_key, config_value)
        if validation_error:
            raise HTTPException(status_code=400, detail=validation_error)

        # Update the configuration
        success = set_config(config_key, config_value)

        if success:
            logger.info(f"Sandbox config updated: {config_key} = {config_value}")

            # If starting_capital was updated, update all user funds immediately
            if config_key == 'starting_capital':
                try:
                    # from database.sandbox_db import SandboxFunds, db_session
                    # from decimal import Decimal

                    new_capital = Decimal(str(config_value))

                    # Update all user funds with new starting capital
                    # This resets their balance to the new capital value
                    funds = sandbox_db_session.query(SandboxFunds).all()
                    for fund in funds:
                        # New available = new_capital - used_margin + total_pnl
                        fund.total_capital = new_capital
                        fund.available_balance = new_capital - fund.used_margin + fund.total_pnl

                    sandbox_db_session.commit()
                    logger.info(f"Updated {len(funds)} user funds with new starting capital: ₹{new_capital}")
                except Exception as e:
                    logger.error(f"Error updating user funds with new capital: {e}")
                    sandbox_db_session.rollback()

            # If square-off time was updated, reload the schedule automatically
            if config_key.endswith('square_off_time') or config_key in ['reset_day', 'reset_time']:
                try:
                    reload_success, reload_response, reload_status = sandbox_reload_squareoff_schedule()
                    if reload_success:
                        logger.info(f"Schedule reloaded after {config_key} update")
                    else:
                        logger.warning(f"Failed to reload schedule: {reload_response.get('message')}")
                except Exception as e:
                    logger.error(f"Error auto-reloading schedule: {e}")

            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    'status': 'success',
                    'message': f'Configuration {config_key} updated successfully'
                }
            )
        else:
            raise HTTPException(status_code=500, detail='Failed to update configuration')

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error updating sandbox config: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f'Error updating configuration: {str(e)}')

@sandbox_router.post('/reset')
async def reset_config(request: Request, db: Session = Depends(get_db)):
    """Reset sandbox configuration to defaults and clear all sandbox data"""
    try:
        # In FastAPI, user_id would typically come from authentication dependencies
        # For now, let's assume a placeholder or get it from a header/cookie if not using full auth yet
        # user_id = request.state.user.id # Example if user object is attached to state by auth middleware
        # For now, let's assume a default user_id or get it from a query param for testing if needed
        # In a real app, this would be secured.
        user_id = 1 # Placeholder, replace with actual user ID from auth

        # Default configurations
        default_configs = {
            'starting_capital': '10000000.00',
            'reset_day': 'Sunday',
            'reset_time': '00:00',
            'order_check_interval': '5',
            'mtm_update_interval': '5',
            'nse_bse_square_off_time': '15:15',
            'cds_bcd_square_off_time': '16:45',
            'mcx_square_off_time': '23:30',
            'ncdex_square_off_time': '17:00',
            'equity_mis_leverage': '5',
            'equity_cnc_leverage': '1',
            'futures_leverage': '10',
            'option_buy_leverage': '1',
            'option_sell_leverage': '1'
        }

        # Reset all configurations
        for key, value in default_configs.items():
            set_config(key, value)

        # Clear all sandbox data for the current user
        try:
            # Delete all orders
            deleted_orders = sandbox_db_session.query(SandboxOrders).filter_by(user_id=user_id).delete()
            logger.info(f"Deleted {deleted_orders} sandbox orders for user {user_id}")

            # Delete all trades
            deleted_trades = sandbox_db_session.query(SandboxTrades).filter_by(user_id=user_id).delete()
            logger.info(f"Deleted {deleted_trades} sandbox trades for user {user_id}")

            # Delete all positions
            deleted_positions = sandbox_db_session.query(SandboxPositions).filter_by(user_id=user_id).delete()
            logger.info(f"Deleted {deleted_positions} sandbox positions for user {user_id}")

            # Delete all holdings
            deleted_holdings = sandbox_db_session.query(SandboxHoldings).filter_by(user_id=user_id).delete()
            logger.info(f"Deleted {deleted_holdings} sandbox holdings for user {user_id}")

            # Reset funds to starting capital
            starting_capital = Decimal(default_configs['starting_capital'])

            fund = sandbox_db_session.query(SandboxFunds).filter_by(user_id=user_id).first()

            if fund:
                # Reset existing fund
                fund.total_capital = starting_capital
                fund.available_balance = starting_capital
                fund.used_margin = Decimal('0.00')
                fund.unrealized_pnl = Decimal('0.00')
                fund.realized_pnl = Decimal('0.00')
                fund.total_pnl = Decimal('0.00')
                fund.last_reset_date = datetime.now(pytz.timezone('Asia/Kolkata'))
                fund.reset_count = (fund.reset_count or 0) + 1
                logger.info(f"Reset sandbox funds for user {user_id}")
            else:
                # Create new fund record
                fund = SandboxFunds(
                    user_id=user_id,
                    total_capital=starting_capital,
                    available_balance=starting_capital,
                    used_margin=Decimal('0.00'),
                    unrealized_pnl=Decimal('0.00'),
                    realized_pnl=Decimal('0.00'),
                    total_pnl=Decimal('0.00'),
                    last_reset_date=datetime.now(pytz.timezone('Asia/Kolkata')),
                    reset_count=1
                )
                sandbox_db_session.add(fund)
                logger.info(f"Created new sandbox funds for user {user_id}")

            sandbox_db_session.commit()
            logger.info(f"Successfully reset all sandbox data for user {user_id}")

        except Exception as e:
            sandbox_db_session.rollback()
            logger.error(f"Error clearing sandbox data: {str(e)}\n{traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=f"Error clearing sandbox data: {str(e)}")

        logger.info("Sandbox configuration and data reset to defaults")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                'status': 'success',
                'message': 'Configuration and data reset to defaults successfully. All orders, trades, positions, and holdings have been cleared.'
            }
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error resetting sandbox config: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f'Error resetting configuration: {str(e)}')

@sandbox_router.post('/reload-squareoff')
async def reload_squareoff(db: Session = Depends(get_db)):
    """Manually reload square-off schedule from config"""
    try:

        success, response, status_code = sandbox_reload_squareoff_schedule()

        if success:
            return JSONResponse(content=response, status_code=status_code)
        else:
            return JSONResponse(content=response, status_code=status_code)

    except Exception as e:
        logger.error(f"Error reloading square-off schedule: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f'Error reloading square-off schedule: {str(e)}')


@sandbox_router.get('/squareoff-status')
async def squareoff_status(db: Session = Depends(get_db)):
    """Get current square-off scheduler status"""
    try:
        success, response, status_code = sandbox_get_squareoff_status()

        if success:
            return JSONResponse(content=response, status_code=status_code)
        else:
            return JSONResponse(content=response, status_code=status_code)

    except Exception as e:
        logger.error(f"Error getting square-off status: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f'Error getting square-off status: {str(e)}')


def validate_config(config_key, config_value):
    """Validate configuration values"""
    try:
        # Validate numeric values
        if config_key in ['starting_capital', 'equity_mis_leverage', 'equity_cnc_leverage',
                          'futures_leverage', 'option_buy_leverage', 'option_sell_leverage',
                          'order_check_interval', 'mtm_update_interval']:
            try:
                value = float(config_value)
                if value < 0:
                    return f'{config_key} must be a positive number'

                # Additional validations
                if config_key == 'starting_capital':
                    valid_capitals = [100000, 500000, 1000000, 2500000, 5000000, 10000000]
                    if value not in valid_capitals:
                        return 'Starting capital must be one of: ₹1L, ₹5L, ₹10L, ₹25L, ₹50L, or ₹1Cr'

                if config_key.endswith('_leverage'):
                    if value < 1:
                        return 'Leverage must be at least 1x'
                    if value > 50:
                        return 'Leverage cannot exceed 50x'

                # Interval validations
                if config_key == 'order_check_interval':
                    if value < 1 or value > 30:
                        return 'Order check interval must be between 1-30 seconds'

                if config_key == 'mtm_update_interval':
                    if value < 0 or value > 60:
                        return 'MTM update interval must be between 0-60 seconds (0 = manual only)'

            except ValueError:
                return f'{config_key} must be a valid number'

        # Validate time format (HH:MM)
        if config_key.endswith('_time'):
            if ':' not in config_value:
                return 'Time must be in HH:MM format'
            try:
                hours, minutes = config_value.split(':')
                if not (0 <= int(hours) <= 23 and 0 <= int(minutes) <= 59):
                    return 'Invalid time format'
            except:
                return 'Time must be in HH:MM format'

        # Validate day of week
        if config_key == 'reset_day':
            valid_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            if config_value not in valid_days:
                return f'Reset day must be one of: {", ".join(valid_days)}'

        return None  # No validation error

    except Exception as e:
        logger.error(f"Error validating config: {str(e)}")
        return f'Validation error: {str(e)}'