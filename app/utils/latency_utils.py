import csv
import io
from typing import List, Dict, Any

from app.utils.time_utils import format_ist_time

def generate_csv(logs: List[Dict[str, Any]]) -> str:
    """Generate CSV file from latency logs"""
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow(
        [
            "Timestamp",
            "Broker",
            "Order ID",
            "Symbol",
            "Order Type",
            "RTT (ms)",
            "Overhead (ms)",
            "Total Latency (ms)",
            "Status",
        ]
    )

    # Write data
    for log in logs:
        writer.writerow(
            [
                format_ist_time(log.timestamp),
                log.broker,
                log.order_id,
                log.symbol,
                log.order_type,
                round(log.rtt_ms, 2),
                round(log.overhead_ms, 2),
                round(log.total_latency_ms, 2),
                log.status,
            ]
        )

    return output.getvalue()
