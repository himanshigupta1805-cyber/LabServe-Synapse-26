"""
MCP Tools — borrow_part / return_part

Borrow and return parts from The Foundry's inventory.
Enforces: R001, R002, R004, R009, R010.
"""

import json
from mcp_server.state import get_state


def borrow_part(operator_id: str, part_id: str, quantity: int = 1) -> str:
    """Borrow parts from inventory.

    Args:
        operator_id: Operator requesting the part.
        part_id:     Part to borrow.
        quantity:    Number of units (default 1).

    Returns:
        JSON with status, borrowed info, or refusal citing specific rule.
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
            "message": f"REFUSAL: Part '{part_id}' not found in inventory.",
        })

    # R001 — Clearance Enforcement
    if operator["clearance_level"] < part["min_clearance"]:
        substitutes = part.get("substitutes", [])
        alt_msg = ""
        if substitutes:
            alt_parts = [state.find_part(s) for s in substitutes]
            accessible = [
                p for p in alt_parts
                if p and operator["clearance_level"] >= p["min_clearance"]
            ]
            if accessible:
                alt_msg = (
                    f" Suggested substitutes within your clearance: "
                    f"{[a['part_id'] + ' (' + a['name'] + ')' for a in accessible]}."
                )
        return json.dumps({
            "status": "refused", "rule": "R001",
            "message": (
                f"REFUSAL [R001 — Clearance Enforcement]: Operator "
                f"'{operator['name']}' (clearance {operator['clearance_level']}) "
                f"cannot access '{part['name']}' (requires clearance "
                f"{part['min_clearance']}).{alt_msg}"
            ),
            "substitutes": part.get("substitutes", []),
        })

    # R009 — Return Before Re-borrow
    if state.borrowed_qty(operator_id, part_id) > 0:
        return json.dumps({
            "status": "refused", "rule": "R009",
            "message": (
                f"REFUSAL [R009 — Return Before Re-borrow]: Operator "
                f"'{operator['name']}' already has '{part['name']}' "
                f"({part_id}) borrowed. Return it before borrowing again."
            ),
        })

    # R002 — Borrow Limit (max 5)
    current = state.total_borrowed(operator_id)
    if current + quantity > 5:
        return json.dumps({
            "status": "refused", "rule": "R002",
            "message": (
                f"REFUSAL [R002 — Borrow Limit]: Operator "
                f"'{operator['name']}' already has {current} part(s) "
                f"borrowed. Adding {quantity} would exceed the 5-part limit. "
                f"Can borrow at most {5 - current} more."
            ),
        })

    # R010 — Minimum Stock Reserve (keep ≥ 2)
    if part["quantity"] - quantity < 2:
        available = max(0, part["quantity"] - 2)
        return json.dumps({
            "status": "refused", "rule": "R010",
            "message": (
                f"REFUSAL [R010 — Minimum Stock Reserve]: Cannot borrow "
                f"{quantity} of '{part['name']}'. Current stock: "
                f"{part['quantity']}, safety reserve: 2. "
                f"Maximum available to borrow: {available}."
            ),
            "substitutes": part.get("substitutes", []),
        })

    # ── Execute borrow ───────────────────────────────────────────────
    part["quantity"] -= quantity
    if operator_id not in state.borrowed:
        state.borrowed[operator_id] = {}
    state.borrowed[operator_id][part_id] = (
        state.borrowed[operator_id].get(part_id, 0) + quantity
    )

    return json.dumps({
        "status": "success",
        "message": (
            f"Operator '{operator['name']}' borrowed {quantity}× "
            f"'{part['name']}'. Remaining stock: {part['quantity']}."
        ),
        "part_id": part_id,
        "borrowed_quantity": quantity,
        "remaining_stock": part["quantity"],
    })


def return_part(operator_id: str, part_id: str, quantity: int = 1) -> str:
    """Return previously borrowed parts to inventory.

    Args:
        operator_id: Operator returning the part.
        part_id:     Part to return.
        quantity:    Number of units (default 1).

    Returns:
        JSON with status and updated stock info.
    """
    state = get_state()

    operator = state.find_operator(operator_id)
    if not operator:
        return json.dumps({
            "status": "error",
            "message": f"REFUSAL: Operator '{operator_id}' not found.",
        })

    borrowed = state.borrowed_qty(operator_id, part_id)
    if borrowed < quantity:
        return json.dumps({
            "status": "error",
            "message": (
                f"REFUSAL: Operator '{operator['name']}' has only "
                f"{borrowed} of part '{part_id}' borrowed. "
                f"Cannot return {quantity}."
            ),
        })

    part = state.find_part(part_id)
    if not part:
        return json.dumps({
            "status": "error",
            "message": f"Part '{part_id}' not found in inventory records.",
        })

    # Execute return
    part["quantity"] += quantity
    state.borrowed[operator_id][part_id] -= quantity
    if state.borrowed[operator_id][part_id] == 0:
        del state.borrowed[operator_id][part_id]
        if not state.borrowed[operator_id]:
            del state.borrowed[operator_id]

    return json.dumps({
        "status": "success",
        "message": (
            f"Operator '{operator['name']}' returned {quantity}× "
            f"'{part['name']}'. Stock updated to: {part['quantity']}."
        ),
        "part_id": part_id,
        "returned_quantity": quantity,
        "new_stock": part["quantity"],
    })
