"""
MCP Tool — order_parts

Order new parts for The Foundry.  Includes human-approval helpers.
Enforces: R004, R005, R006.
"""

import json
from mcp_server.state import get_state


def order_parts(
    operator_id: str,
    part_id: str,
    quantity: int,
    department: str,
) -> str:
    """Order new parts.  Orders >₹2 000 are held for Chief's approval.

    Args:
        operator_id: Requesting operator.
        part_id:     Part to order.
        quantity:    Number of units.
        department:  Department budget to charge.

    Returns:
        JSON with status (success | refused | approval_required | error).
    """
    state = get_state()

    # ── Validate operator ────────────────────────────────────────────
    operator = state.find_operator(operator_id)
    if not operator:
        return json.dumps({
            "status": "error",
            "message": f"REFUSAL: Operator '{operator_id}' not found.",
        })

    # R004 — Active Only
    if not operator["active"]:
        return json.dumps({
            "status": "refused", "rule": "R004",
            "message": (
                f"REFUSAL [R004 — Active Operator Only]: "
                f"Operator '{operator['name']}' is INACTIVE."
            ),
        })

    # ── Validate part ────────────────────────────────────────────────
    part = state.find_part(part_id)
    if not part:
        return json.dumps({
            "status": "error",
            "message": f"REFUSAL: Part '{part_id}' not found in catalog.",
        })

    total_cost = part["unit_cost"] * quantity

    # ── Validate department ──────────────────────────────────────────
    if department not in state.budget:
        return json.dumps({
            "status": "error",
            "message": (
                f"REFUSAL: Department '{department}' not found. "
                f"Available: {list(state.budget.keys())}."
            ),
        })

    # R005 — Budget Enforcement
    budget = state.budget[department]
    remaining = budget["total"] - budget["spent"] - budget["pending"]
    if total_cost > remaining:
        return json.dumps({
            "status": "refused", "rule": "R005",
            "message": (
                f"REFUSAL [R005 — Budget Enforcement]: Order cost "
                f"₹{total_cost:,} exceeds remaining budget ₹{remaining:,} "
                f"for department '{department}' "
                f"(total ₹{budget['total']:,}, spent ₹{budget['spent']:,}, "
                f"pending ₹{budget['pending']:,})."
            ),
        })

    # R006 — Human Approval Threshold (>₹2 000)
    if total_cost > 2000:
        order = {
            "order_id": state.next_order_id(),
            "operator_id": operator_id,
            "operator_name": operator["name"],
            "part_id": part_id,
            "part_name": part["name"],
            "quantity": quantity,
            "unit_cost": part["unit_cost"],
            "total_cost": total_cost,
            "department": department,
            "status": "pending_approval",
        }
        state.pending_approvals.append(order)
        state.budget[department]["pending"] += total_cost
        return json.dumps({
            "status": "approval_required",
            "rule": "R006",
            "message": (
                f"ORDER HELD [R006 — Human Approval Threshold]: "
                f"{quantity}× '{part['name']}' totalling ₹{total_cost:,} "
                f"requires Chief's sign-off (exceeds ₹2,000). "
                f"Order ID: {order['order_id']}."
            ),
            "order": order,
        })

    # ── Execute immediately (≤₹2 000) ────────────────────────────────
    order = {
        "order_id": state.next_order_id(),
        "operator_id": operator_id,
        "operator_name": operator["name"],
        "part_id": part_id,
        "part_name": part["name"],
        "quantity": quantity,
        "unit_cost": part["unit_cost"],
        "total_cost": total_cost,
        "department": department,
        "status": "completed",
    }
    part["quantity"] += quantity
    state.budget[department]["spent"] += total_cost
    state.order_log.append(order)

    return json.dumps({
        "status": "success",
        "message": (
            f"Order completed: {quantity}× '{part['name']}' for "
            f"₹{total_cost:,}. Stock updated to {part['quantity']}."
        ),
        "order": order,
    })


# ═══════ Human-Approval Helpers ══════════════════════════════════════


def approve_order(order_id: str) -> str:
    """Approve a pending order after Chief's sign-off."""
    state = get_state()

    order = next(
        (o for o in state.pending_approvals if o["order_id"] == order_id),
        None,
    )
    if not order:
        return json.dumps({
            "status": "error",
            "message": f"Order '{order_id}' not found in pending approvals.",
        })

    part = state.find_part(order["part_id"])
    if not part:
        return json.dumps({
            "status": "error",
            "message": f"Part '{order['part_id']}' no longer exists.",
        })

    # Execute the order
    part["quantity"] += order["quantity"]
    state.budget[order["department"]]["pending"] -= order["total_cost"]
    state.budget[order["department"]]["spent"] += order["total_cost"]
    order["status"] = "approved"
    state.order_log.append(order)
    state.pending_approvals.remove(order)

    return json.dumps({
        "status": "success",
        "message": (
            f"Order {order_id} APPROVED. {order['quantity']}× "
            f"'{order['part_name']}' added to inventory. "
            f"₹{order['total_cost']:,} charged to {order['department']}."
        ),
        "order": order,
    })


def reject_order(order_id: str, reason: str = "") -> str:
    """Reject a pending order."""
    state = get_state()

    order = next(
        (o for o in state.pending_approvals if o["order_id"] == order_id),
        None,
    )
    if not order:
        return json.dumps({
            "status": "error",
            "message": f"Order '{order_id}' not found in pending approvals.",
        })

    # Release the pending budget
    state.budget[order["department"]]["pending"] -= order["total_cost"]
    order["status"] = "rejected"
    order["rejection_reason"] = reason
    state.order_log.append(order)
    state.pending_approvals.remove(order)

    return json.dumps({
        "status": "success",
        "message": (
            f"Order {order_id} REJECTED. ₹{order['total_cost']:,} "
            f"released back to {order['department']} budget. "
            f"Reason: {reason or 'No reason given'}."
        ),
        "order": order,
    })
