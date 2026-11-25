"""
MCP Tool — check_operator_clearance

Verify an operator's identity, active status, and clearance level.
Enforces: R001 (Clearance), R004 (Active Only).
"""

import json
from mcp_server.state import get_state


def check_operator_clearance(operator_id: str, required_clearance: int = 0) -> str:
    """Check whether an operator exists, is active, and meets a clearance bar.

    Args:
        operator_id:        The operator's ID (e.g. 'OP-001').
        required_clearance: Minimum clearance level required (0 = just verify).

    Returns:
        JSON string with status and operator info or refusal.
    """
    state = get_state()
    operator = state.find_operator(operator_id)

    if not operator:
        available = [o["operator_id"] + " (" + o["name"] + ")" for o in state.operators]
        return json.dumps({
            "status": "error",
            "message": f"REFUSAL: Operator '{operator_id}' not found in records. "
                       f"Available operators: {available}",
        })

    # R004 — Active Operator Only
    if not operator["active"]:
        return json.dumps({
            "status": "refused",
            "rule": "R004",
            "message": (
                f"REFUSAL [R004 — Active Operator Only]: Operator "
                f"'{operator['name']}' ({operator_id}) is INACTIVE. "
                f"Only active operators may perform operations."
            ),
        })

    # R001 — Clearance Enforcement
    if required_clearance > 0 and operator["clearance_level"] < required_clearance:
        return json.dumps({
            "status": "refused",
            "rule": "R001",
            "message": (
                f"REFUSAL [R001 — Clearance Enforcement]: Operator "
                f"'{operator['name']}' has clearance level "
                f"{operator['clearance_level']}, but level "
                f"{required_clearance} is required."
            ),
        })

    return json.dumps({
        "status": "success",
        "operator": {
            "operator_id": operator["operator_id"],
            "name": operator["name"],
            "clearance_level": operator["clearance_level"],
            "department": operator["department"],
            "active": operator["active"],
        },
        "message": (
            f"Operator '{operator['name']}' verified — clearance level "
            f"{operator['clearance_level']}, department {operator['department']}."
        ),
    })
