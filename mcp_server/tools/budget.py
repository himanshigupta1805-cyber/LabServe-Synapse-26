"""
MCP Tool — check_budget

Check the remaining budget for a department.
"""

import json
from mcp_server.state import get_state


def check_budget(department: str) -> str:
    """Check the remaining budget for a department.

    Args:
        department: Department name (e.g. 'Assembly', 'Quality').

    Returns:
        JSON with budget breakdown or error listing available departments.
    """
    state = get_state()

    if department not in state.budget:
        return json.dumps({
            "status": "error",
            "message": (
                f"Department '{department}' not found. "
                f"Available departments: {list(state.budget.keys())}."
            ),
        })

    b = state.budget[department]
    remaining = b["total"] - b["spent"] - b["pending"]

    return json.dumps({
        "status": "success",
        "department": department,
        "total_budget": b["total"],
        "spent": b["spent"],
        "pending_approval": b["pending"],
        "remaining": remaining,
        "message": (
            f"Department '{department}': ₹{remaining:,} remaining "
            f"(₹{b['total']:,} total, ₹{b['spent']:,} spent, "
            f"₹{b['pending']:,} pending)."
        ),
    })
