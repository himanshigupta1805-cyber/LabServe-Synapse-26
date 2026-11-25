"""
Executor Node — Tool Execution & Result Routing
=================================================
Calls MCP tools based on the LLM's tool_calls and routes the results
back through the graph.
"""

import json
from langchain_core.tools import tool
from mcp_server.tools.inventory import inventory_search as _inv
from mcp_server.tools.clearance import check_operator_clearance as _clr
from mcp_server.tools.borrow_return import borrow_part as _borrow, return_part as _return
from mcp_server.tools.bay_booking import book_bay as _book
from mcp_server.tools.ordering import order_parts as _order, approve_order as _approve, reject_order as _reject
from mcp_server.tools.budget import check_budget as _budget


# ═══════ LangChain @tool wrappers ════════════════════════════════════
# These wrap the raw MCP tool functions so LangGraph's ToolNode can
# invoke them.  Descriptions match the MCP tool schemas exactly.

@tool
def inventory_search(query: str = "", category: str = "") -> str:
    """Search The Foundry's parts inventory by name substring and/or category.
    Returns JSON with status, matched parts list, and count."""
    return _inv(query, category)


@tool
def check_operator_clearance(operator_id: str, required_clearance: int = 0) -> str:
    """Verify an operator's identity, active status, and clearance level.
    Pass required_clearance to check if the operator meets a minimum bar."""
    return _clr(operator_id, required_clearance)


@tool
def borrow_part(operator_id: str, part_id: str, quantity: int = 1) -> str:
    """Borrow parts from inventory. Enforces clearance (R001), borrow limit (R002),
    active-only (R004), return-before-reborrow (R009), stock reserve (R010)."""
    return _borrow(operator_id, part_id, quantity)


@tool
def return_part(operator_id: str, part_id: str, quantity: int = 1) -> str:
    """Return previously borrowed parts to inventory."""
    return _return(operator_id, part_id, quantity)


@tool
def book_bay(
    operator_id: str,
    bay_id: str,
    date: str,
    duration_hours: int = 1,
    part_category: str = "",
) -> str:
    """Book a fabrication bay. Enforces active-only (R004), no-weekend (R008),
    capacity (R003), and bay-type-match (R007). Provide part_category for R007."""
    return _book(operator_id, bay_id, date, duration_hours, part_category)


@tool
def order_parts(operator_id: str, part_id: str, quantity: int = 1, department: str = "") -> str:
    """Order new parts. Enforces active-only (R004), budget (R005).
    Orders >₹2,000 return approval_required (R006) and need Chief's sign-off."""
    return _order(operator_id, part_id, quantity, department)


@tool
def approve_order(order_id: str) -> str:
    """Approve a pending order after Chief's sign-off."""
    return _approve(order_id)


@tool
def reject_order(order_id: str, reason: str = "") -> str:
    """Reject a pending order."""
    return _reject(order_id, reason)


@tool
def check_budget(department: str) -> str:
    """Check the remaining budget for a department. Returns total, spent,
    pending, and remaining amounts."""
    return _budget(department)


# ── All tools list (order matters for LLM binding) ───────────────────

ALL_TOOLS = [
    inventory_search,
    check_operator_clearance,
    borrow_part,
    return_part,
    book_bay,
    order_parts,
    approve_order,
    reject_order,
    check_budget,
]
