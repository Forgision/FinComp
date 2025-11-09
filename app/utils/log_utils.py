import json
import traceback
from typing import Any, Dict, List
import csv
import io

import pytz

from app.core.schemas.apilog_db import OrderLog
from app.utils.logging import logger


def sanitize_request_data(data: Any) -> Dict[str, Any]:
    """Remove sensitive information from request data"""
    try:
        if isinstance(data, str):
            data = json.loads(data)
        if isinstance(data, dict):
            # Create a copy to avoid modifying the original
            sanitized = data.copy()
            # Remove apikey if present
            sanitized.pop("apikey", None)
            return sanitized
    except json.JSONDecodeError:
        logger.error(f"Error decoding JSON: {data}")
        return {}
    except Exception as e:
        logger.error(f"Error sanitizing data: {str(e)}")
        return {}
    return {}


def format_log_entry(log: OrderLog, ist: "pytz.tzinfo.DstTzInfo") -> Dict[str, Any]:
    """Format a single log entry"""
    try:
        request_data = sanitize_request_data(log.request_data)
        try:
            response_data = json.loads(log.response_data) if log.response_data else {}
        except json.JSONDecodeError:
            logger.error(f"Error decoding response JSON for log {log.id}")
            response_data = {}
        except Exception as e:
            logger.error(f"Error processing response data for log {log.id}: {str(e)}")
            response_data = {}

        # Extract strategy from request data
        strategy = (
            request_data.get("strategy", "Unknown")
            if isinstance(request_data, dict)
            else "Unknown"
        )

        return {
            "id": log.id,
            "api_type": log.api_type,
            "request_data": request_data,
            "response_data": response_data,
            "strategy": strategy,
            "created_at": log.created_at.astimezone(ist).strftime(
                "%Y-%m-%d %I:%M:%S %p"
            ),
        }
    except Exception as e:
        logger.error(
            f"Error formatting log {log.id}: {str(e)}\n{traceback.format_exc()}"
        )
        return {
            "id": log.id,
            "api_type": log.api_type,
            "request_data": {},
            "response_data": {},
            "strategy": "Unknown",
            "created_at": log.created_at.astimezone(ist).strftime(
                "%Y-%m-%d %I:%M:%S %p"
            ),
        }


def generate_csv(logs: List[Dict[str, Any]]) -> str:
    """Generate CSV file from logs"""
    try:
        si = io.StringIO()
        writer = csv.writer(si)

        # Write headers - include all possible fields from all request types
        headers = [
            "ID",
            "Timestamp",
            "API Type",
            "Strategy",
            "Exchange",
            "Symbol",
            "Action",
            "Product",
            "Price Type",
            "Quantity",
            "Position Size",  # For placesmartorder
            "Price",
            "Trigger Price",
            "Disclosed Quantity",
            "Order ID",  # For modifyorder, cancelorder
            "Response",
        ]
        writer.writerow(headers)

        # Write data
        for log in logs:
            try:
                request_data = log["request_data"]
                if not isinstance(request_data, dict):
                    request_data = {}

                # Format response data for CSV
                response_data = log["response_data"]
                if isinstance(response_data, dict):
                    response_str = json.dumps(response_data)
                else:
                    response_str = str(response_data)

                # Build row with all possible fields
                row = [
                    log["id"],
                    log["created_at"],
                    log["api_type"],
                    log["strategy"],
                    request_data.get("exchange", ""),
                    request_data.get("symbol", ""),
                    request_data.get("action", ""),
                    request_data.get("product", ""),
                    request_data.get("pricetype", ""),
                    request_data.get("quantity", ""),
                    request_data.get("position_size", ""),  # Only for placesmartorder
                    request_data.get("price", ""),
                    request_data.get("trigger_price", ""),
                    request_data.get("disclosed_quantity", ""),
                    request_data.get("orderid", ""),  # For modifyorder, cancelorder
                    response_str,
                ]
                writer.writerow(row)
                logger.debug(f"Wrote row: {row}")
            except Exception as e:
                logger.error(f"Error writing row for log {log.get('id')}: {str(e)}")
                continue

        return si.getvalue()

    except Exception as e:
        logger.error(f"Error generating CSV: {str(e)}\n{traceback.format_exc()}")
        raise
