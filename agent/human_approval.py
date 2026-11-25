"""
Human-in-the-Loop — Chief's Sign-Off
======================================
Handles the approval workflow for high-cost orders (>₹2 000).
"""

import json
from mcp_server.tools.ordering import approve_order as _approve, reject_order as _reject


def format_approval_request(order_details: dict) -> dict:
    """Format an order for human review.

    Args:
        order_details: The order dict from the ordering tool.

    Returns:
        A presentation dict suitable for the interrupt payload.
    """
    return {
        "type": "approval_required",
        "order_id": order_details.get("order_id", "unknown"),
        "summary": (
            f"{order_details.get('quantity', '?')}× "
            f"'{order_details.get('part_name', '?')}' — "
            f"₹{order_details.get('total_cost', 0):,}"
        ),
        "operator": order_details.get("operator_name", "unknown"),
        "department": order_details.get("department", "unknown"),
        "total_cost": order_details.get("total_cost", 0),
        "breakdown": {
            "unit_cost": order_details.get("unit_cost", 0),
            "quantity": order_details.get("quantity", 0),
        },
        "instruction": (
            "Chief's sign-off required. Review the order and "
            "approve or reject."
        ),
    }


def process_approval(order_id: str, approved: bool, reason: str = "") -> str:
    """Process the Chief's decision on a pending order.

    Args:
        order_id: The order to approve or reject.
        approved: True to approve, False to reject.
        reason:   Optional rejection reason.

    Returns:
        Result message string.
    """
    if approved:
        raw = _approve(order_id)
    else:
        raw = _reject(order_id, reason)

    try:
        result = json.loads(raw)
        return result.get("message", raw)
    except json.JSONDecodeError:
        return raw
