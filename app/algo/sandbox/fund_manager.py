# sandbox/fund_manager.py
"""
Fund Manager - Handles simulated capital and margin calculations

Features:
- ₹10,000,000 (1 Crore) starting capital (configurable)
- Automatic reset via APScheduler on configured day/time (default: Sunday 00:00 IST)
- Leverage-based margin calculations
- Real-time available balance tracking

Auto-Reset:
- Runs as APScheduler background job (see squareoff_thread.py)
- Configurable day (Monday-Sunday) and time (HH:MM format)
- Resets all user funds to starting capital even if app was stopped during reset time
- Schedule automatically reloads when reset_day or reset_time config is changed
"""

from datetime import datetime
from decimal import Decimal

import pytz
from sqlmodel import Session

from app.core.models.sandbox_db import (
    SandboxFunds,
    SandboxHoldings,
    SandboxPositions,
    get_config,
)
from app.db.session import get_db
from app.core.models.symbol import SymToken
from app.utils.logging import logger


def is_option(symbol, exchange):
    """Check if symbol is an option based on exchange and symbol suffix"""
    if exchange in ['NFO', 'BFO', 'MCX', 'CDS', 'BCD', 'NCDEX']:
        return symbol.endswith('CE') or symbol.endswith('PE')
    return False


def is_future(symbol, exchange):
    """Check if symbol is a future based on exchange and symbol suffix"""
    if exchange in ['NFO', 'BFO', 'MCX', 'CDS', 'BCD', 'NCDEX']:
        return symbol.endswith('FUT')
    return False


class FundManager:
    """Manages virtual funds for sandbox mode"""

    def __init__(self, user_id):
        self.user_id = user_id
        self.db = next(get_db())
        self.starting_capital = Decimal(get_config(self.db, 'starting_capital', '10000000.00'))

    def initialize_funds(self):
        """Initialize funds for a new user"""
        try:
            funds = self.db.query(SandboxFunds).filter_by(user_id=self.user_id).first()

            if not funds:
                funds = SandboxFunds(
                    user_id=self.user_id,
                    total_capital=self.starting_capital,
                    available_balance=self.starting_capital,
                    used_margin=Decimal('0.00'),
                    realized_pnl=Decimal('0.00'),
                    unrealized_pnl=Decimal('0.00'),
                    total_pnl=Decimal('0.00'),
                    last_reset_date=datetime.now(pytz.timezone('Asia/Kolkata')),
                    reset_count=0
                )
                self.db.add(funds)
                self.db.commit()
                logger.info(f"Initialized funds for user {self.user_id} with ₹{self.starting_capital}")
                return True, "Funds initialized successfully"
            else:
                logger.debug(f"User {self.user_id} already has funds initialized")
                return True, "Funds already initialized"

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error initializing funds for user {self.user_id}: {e}")
            return False, f"Error initializing funds: {str(e)}"

    def get_funds(self):
        """Get current fund status for user"""
        try:
            funds = self.db.query(SandboxFunds).filter_by(user_id=self.user_id).first()

            if not funds:
                success, message = self.initialize_funds()
                if not success:
                    return None
                funds = self.db.query(SandboxFunds).filter_by(user_id=self.user_id).first()

            if not funds:
                return None

            self._check_and_reset_funds(funds)

            return {
                'availablecash': float(funds.available_balance),
                'collateral': 0.00,
                'm2munrealized': float(funds.unrealized_pnl),
                'm2mrealized': float(funds.realized_pnl),
                'utiliseddebits': float(funds.used_margin),
                'grossexposure': float(funds.used_margin),
                'totalpnl': float(funds.total_pnl),
                'last_reset': funds.last_reset_date.strftime('%Y-%m-%d %H:%M:%S'),
                'reset_count': funds.reset_count
            }

        except Exception as e:
            logger.error(f"Error getting funds for user {self.user_id}: {e}")
            return None

    def _check_and_reset_funds(self, funds):
        """Check if funds need to be reset"""
        try:
            ist = pytz.timezone('Asia/Kolkata')
            now = datetime.now(ist)
            last_reset = funds.last_reset_date

            if last_reset.tzinfo is None:
                last_reset = ist.localize(last_reset)

            reset_day = get_config(self.db, 'reset_day', 'Sunday')
            reset_time_str = get_config(self.db, 'reset_time', '00:00')

            if now.strftime('%A') == reset_day:
                reset_hour, reset_minute = map(int, reset_time_str.split(':'))
                reset_time_today = now.replace(
                    hour=reset_hour,
                    minute=reset_minute,
                    second=0,
                    microsecond=0
                )

                if now >= reset_time_today and last_reset < reset_time_today:
                    self._reset_funds(funds)

        except Exception as e:
            logger.error(f"Error checking fund reset for user {self.user_id}: {e}")

    def _reset_funds(self, funds):
        """Reset funds to starting capital"""
        try:
            logger.info(f"Resetting funds for user {self.user_id}")

            funds.total_capital = self.starting_capital
            funds.available_balance = self.starting_capital
            funds.used_margin = Decimal('0.00')
            funds.realized_pnl = Decimal('0.00')
            funds.unrealized_pnl = Decimal('0.00')
            funds.total_pnl = Decimal('0.00')
            funds.last_reset_date = datetime.now(pytz.timezone('Asia/Kolkata'))
            funds.reset_count += 1

            self.db.commit()

            self.db.query(SandboxPositions).filter_by(user_id=self.user_id).delete()
            self.db.query(SandboxHoldings).filter_by(user_id=self.user_id).delete()
            self.db.commit()

            logger.info(f"Funds reset successfully for user {self.user_id} (Reset #{funds.reset_count})")

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error resetting funds for user {self.user_id}: {e}")

    def check_margin_available(self, required_margin):
        """Check if user has sufficient margin available"""
        try:
            funds = self.db.query(SandboxFunds).filter_by(user_id=self.user_id).first()

            if not funds:
                return False, "Funds not initialized"

            required_margin = Decimal(str(required_margin))

            if funds.available_balance >= required_margin:
                return True, "Sufficient margin available"
            else:
                shortage = required_margin - funds.available_balance
                return False, f"Insufficient funds. Required: ₹{required_margin}, Available: ₹{funds.available_balance}, Shortage: ₹{shortage}"

        except Exception as e:
            logger.error(f"Error checking margin for user {self.user_id}: {e}")
            return False, f"Error checking margin: {str(e)}"

    def block_margin(self, amount, description=""):
        """Block margin for a trade"""
        try:
            funds = self.db.query(SandboxFunds).filter_by(user_id=self.user_id).first()

            if not funds:
                return False, "Funds not initialized"

            amount = Decimal(str(amount))

            if funds.available_balance < amount:
                return False, f"Insufficient funds. Required: ₹{amount}, Available: ₹{funds.available_balance}"

            funds.available_balance -= amount
            funds.used_margin += amount

            self.db.commit()

            logger.info(f"Blocked ₹{amount} margin for user {self.user_id}. {description}")
            return True, f"Margin blocked: ₹{amount}"

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error blocking margin for user {self.user_id}: {e}")
            return False, f"Error blocking margin: {str(e)}"

    def release_margin(self, amount, realized_pnl: Decimal = Decimal('0'), description=""):
        """Release blocked margin and update P&L"""
        try:
            funds = self.db.query(SandboxFunds).filter_by(user_id=self.user_id).first()

            if not funds:
                return False, "Funds not initialized"

            amount = Decimal(str(amount))
            realized_pnl = Decimal(str(realized_pnl))

            funds.used_margin -= amount
            funds.available_balance += amount
            funds.available_balance += realized_pnl
            funds.realized_pnl += realized_pnl
            funds.total_pnl = funds.realized_pnl + funds.unrealized_pnl

            self.db.commit()

            logger.info(f"Released ₹{amount} margin for user {self.user_id}. Realized P&L: ₹{realized_pnl}. {description}")
            return True, f"Margin released: ₹{amount}, P&L: ₹{realized_pnl}"

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error releasing margin for user {self.user_id}: {e}")
            return False, f"Error releasing margin: {str(e)}"

    def transfer_margin_to_holdings(self, amount, description=""):
        """Transfer margin to holdings during T+1 settlement"""
        try:
            funds = self.db.query(SandboxFunds).filter_by(user_id=self.user_id).first()

            if not funds:
                return False, "Funds not initialized"

            amount = Decimal(str(amount))
            funds.used_margin -= amount
            self.db.commit()

            logger.info(f"Transferred ₹{amount} margin to holdings for user {self.user_id}. {description}")
            return True, f"Margin transferred to holdings: ₹{amount}"

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error transferring margin to holdings for user {self.user_id}: {e}")
            return False, f"Error transferring margin to holdings: {str(e)}"

    def credit_sale_proceeds(self, amount, description=""):
        """Credit sale proceeds from selling CNC holdings"""
        try:
            funds = self.db.query(SandboxFunds).filter_by(user_id=self.user_id).first()

            if not funds:
                return False, "Funds not initialized"

            amount = Decimal(str(amount))
            funds.available_balance += amount
            self.db.commit()

            logger.info(f"Credited ₹{amount} sale proceeds for user {self.user_id}. {description}")
            return True, f"Sale proceeds credited: ₹{amount}"

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error crediting sale proceeds for user {self.user_id}: {e}")
            return False, f"Error crediting sale proceeds: {str(e)}"

    def update_unrealized_pnl(self, unrealized_pnl):
        """Update unrealized P&L from open positions"""
        try:
            funds = self.db.query(SandboxFunds).filter_by(user_id=self.user_id).first()

            if not funds:
                return False, "Funds not initialized"

            unrealized_pnl = Decimal(str(unrealized_pnl))
            funds.unrealized_pnl = unrealized_pnl
            funds.total_pnl = funds.realized_pnl + funds.unrealized_pnl
            self.db.commit()

            return True, "Unrealized P&L updated"

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating unrealized P&L for user {self.user_id}: {e}")
            return False, f"Error updating unrealized P&L: {str(e)}"

    def calculate_margin_required(self, symbol, exchange, product, quantity, price, action=None):
        """Calculate margin required for a trade based on leverage rules"""
        try:
            quantity = abs(int(quantity))
            price = Decimal(str(price))
            from app.db.session import get_db
            from sqlalchemy import select
            db = next(get_db())
            stmt = select(SymToken).filter_by(symbol=symbol, exchange=exchange)
            symbol_obj = db.execute(stmt).scalars().first()

            if not symbol_obj:
                logger.error(f"Symbol {symbol} not found on {exchange}")
                return None, "Symbol not found"

            trade_value = quantity * price
            leverage = self._get_leverage(exchange, product, symbol, action)

            if leverage is None:
                return None, "Unable to determine leverage"

            margin = trade_value / Decimal(str(leverage))
            logger.debug(f"Margin for {symbol} {exchange} {product} {action}: ₹{margin} (Trade value: ₹{trade_value}, Leverage: {leverage}x)")
            return margin, "Margin calculated successfully"

        except Exception as e:
            logger.error(f"Error calculating margin: {e}")
            return None, f"Error calculating margin: {str(e)}"

    def _get_leverage(self, exchange, product, symbol, action=None):
        """Get leverage multiplier"""
        try:
            if exchange in ['NSE', 'BSE']:
                if product == 'MIS':
                    return Decimal(get_config(self.db, 'equity_mis_leverage', '5'))
                elif product == 'CNC':
                    return Decimal(get_config(self.db, 'equity_cnc_leverage', '1'))
                else:
                    return Decimal(get_config(self.db, 'equity_cnc_leverage', '1'))
            elif is_future(symbol, exchange):
                return Decimal(get_config(self.db, 'futures_leverage', '10'))
            elif is_option(symbol, exchange):
                if action == 'BUY':
                    return Decimal(get_config(self.db, 'option_buy_leverage', '1'))
                else:
                    return Decimal(get_config(self.db, 'option_sell_leverage', '1'))
            return Decimal('1')
        except Exception as e:
            logger.error(f"Error getting leverage: {e}")
            return Decimal('1')


def get_user_funds(user_id):
    """Helper function to get user funds"""
    fund_manager = FundManager(user_id)
    return fund_manager.get_funds()


def initialize_user_funds(user_id):
    """Helper function to initialize user funds"""
    fund_manager = FundManager(user_id)
    return fund_manager.initialize_funds()


def reset_all_user_funds():
    """Reset funds for all users"""
    try:
        logger.info("=== AUTO-RESET: Starting scheduled fund reset for all users ===")
        db = next(get_db())
        all_funds = db.query(SandboxFunds).all()

        if not all_funds:
            logger.info("No user funds to reset")
            return

        reset_count = 0
        for fund in all_funds:
            try:
                fm = FundManager(fund.user_id)
                fm._reset_funds(fund)
                reset_count += 1
            except Exception as e:
                logger.error(f"Error resetting funds for user {fund.user_id}: {e}")
                continue
        logger.info(f"=== AUTO-RESET: Successfully reset {reset_count} user fund accounts ===")
    except Exception as e:
        logger.error(f"Error in scheduled auto-reset: {e}")
