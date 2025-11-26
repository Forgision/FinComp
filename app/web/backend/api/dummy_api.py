from fastapi import APIRouter
from typing import List, Dict, Any
import random
from datetime import datetime, timedelta

dummy_router = APIRouter()


def generate_random_change():
    change = round(random.uniform(-50, 50), 2)
    percent = round(random.uniform(-2, 2), 2)
    return change, percent


@dummy_router.get("/market-summary")
async def get_market_summary():
    indices = ["NIFTY 50", "NIFTY BANK", "NIFTY FIN SERVICE", "SENSEX"]
    summary = []
    for index in indices:
        change, percent = generate_random_change()
        summary.append(
            {
                "symbol": index,
                "ltp": round(random.uniform(10000, 50000), 2),
                "change": change,
                "change_percent": percent,
                "open": round(random.uniform(10000, 50000), 2),
                "high": round(random.uniform(10000, 50000), 2),
                "low": round(random.uniform(10000, 50000), 2),
                "close": round(random.uniform(10000, 50000), 2),
            }
        )

    return {
        "indices": summary,
        "advancers": random.randint(10, 40),
        "decliners": random.randint(10, 40),
        "top_gainers": [
            {"symbol": "RELIANCE", "ltp": 2500.0, "change_percent": 1.5},
            {"symbol": "TCS", "ltp": 3500.0, "change_percent": 1.2},
        ],
        "top_losers": [
            {"symbol": "INFY", "ltp": 1400.0, "change_percent": -1.1},
            {"symbol": "HDFCBANK", "ltp": 1600.0, "change_percent": -0.8},
        ],
    }


@dummy_router.get("/orders")
async def get_orders():
    statuses = ["OPEN", "COMPLETE", "CANCELLED", "REJECTED"]
    orders = []
    for i in range(10):
        orders.append(
            {
                "order_id": f"ORD{i + 1000}",
                "symbol": random.choice(["RELIANCE", "TCS", "INFY", "SBIN"]),
                "quantity": random.randint(1, 100),
                "price": round(random.uniform(100, 3000), 2),
                "side": random.choice(["BUY", "SELL"]),
                "status": random.choice(statuses),
                "timestamp": (
                    datetime.now() - timedelta(minutes=random.randint(1, 60))
                ).isoformat(),
                "strategy_id": f"STRAT{random.randint(1, 3)}",
            }
        )
    return orders


@dummy_router.get("/positions")
async def get_positions():
    positions = []
    for i in range(5):
        qty = random.randint(1, 50)
        avg_price = round(random.uniform(100, 3000), 2)
        ltp = avg_price * (1 + random.uniform(-0.05, 0.05))
        pnl = (ltp - avg_price) * qty
        positions.append(
            {
                "symbol": random.choice(["RELIANCE", "TCS", "INFY", "SBIN"]),
                "quantity": qty,
                "average_price": avg_price,
                "ltp": round(ltp, 2),
                "pnl": round(pnl, 2),
                "pnl_percent": round((pnl / (avg_price * qty)) * 100, 2),
                "status": "OPEN",
            }
        )
    return positions


@dummy_router.get("/holdings")
async def get_holdings():
    holdings = []
    for i in range(5):
        qty = random.randint(10, 200)
        avg_price = round(random.uniform(100, 3000), 2)
        ltp = avg_price * (1 + random.uniform(-0.2, 0.2))
        pnl = (ltp - avg_price) * qty
        holdings.append(
            {
                "symbol": random.choice(["TATAMOTORS", "ITC", "WIPRO", "HCLTECH"]),
                "quantity": qty,
                "average_price": avg_price,
                "ltp": round(ltp, 2),
                "pnl": round(pnl, 2),
                "pnl_percent": round((pnl / (avg_price * qty)) * 100, 2),
            }
        )
    return holdings


@dummy_router.get("/strategies")
async def get_strategies():
    strategies = []
    for i in range(3):
        strategies.append(
            {
                "strategy_id": f"STRAT{i + 1}",
                "name": f"Strategy {i + 1}",
                "type": "Trend Following",
                "status": random.choice(["RUNNING", "STOPPED", "ERROR"]),
                "pnl": round(random.uniform(-1000, 5000), 2),
                "pnl_percent": round(random.uniform(-5, 20), 2),
                "open_positions": random.randint(0, 5),
                "trades_count": random.randint(10, 50),
            }
        )
    return strategies
