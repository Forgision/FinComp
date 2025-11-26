from typing import Dict, Any


def get_margin_data(auth_token: str) -> Dict[str, Any]:
    """
    Return dummy margin data for development.
    """
    return {
        "available_cash": 100000.0,
        "used_margin": 25000.0,
        "total_collateral": 125000.0,
        "utilization_percent": 20.0,
    }
