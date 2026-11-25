"""
LabServe MCP Server — The Foundry
==================================
FastMCP server exposing all Foundry tools and the operational rulebook
as an MCP resource.  Run standalone via:

    python -m mcp_server.server
"""

import sys
from pathlib import Path

# Ensure project root is on the path so intra-package imports work when
# the server is launched as a subprocess.
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from mcp.server.fastmcp import FastMCP

from mcp_server.tools.inventory import inventory_search as _inventory_search
from mcp_server.tools.clearance import check_operator_clearance as _clearance
from mcp_server.tools.borrow_return import borrow_part as _borrow, return_part as _return
from mcp_server.tools.bay_booking import book_bay as _book_bay
from mcp_server.tools.ordering import order_parts as _order, approve_order as _approve, reject_order as _reject
from mcp_server.tools.budget import check_budget as _budget
from mcp_server.resources.rulebook import get_rulebook_resource

# ═══════ Create FastMCP server ═══════════════════════════════════════

mcp = FastMCP("LabServe — The Foundry")


# ─── Tools ───────────────────────────────────────────────────────────

@mcp.tool()
def inventory_search(query: str = "", category: str = "") -> str:
    """Search The Foundry's parts inventory by name and/or category."""
    return _inventory_search(query, category)


@mcp.tool()
def check_operator_clearance(operator_id: str, required_clearance: int = 0) -> str:
    """Verify an operator's identity, active status, and clearance level."""
    return _clearance(operator_id, required_clearance)


@mcp.tool()
def borrow_part(operator_id: str, part_id: str, quantity: int = 1) -> str:
    """Borrow parts from inventory (enforces clearance, limits, stock reserve)."""
    return _borrow(operator_id, part_id, quantity)


@mcp.tool()
def return_part(operator_id: str, part_id: str, quantity: int = 1) -> str:
    """Return previously borrowed parts to inventory."""
    return _return(operator_id, part_id, quantity)


@mcp.tool()
def book_bay(
    operator_id: str,
    bay_id: str,
    date: str,
    duration_hours: int = 1,
    part_category: str = "",
) -> str:
    """Book a fabrication bay for a specific date and duration."""
    return _book_bay(operator_id, bay_id, date, duration_hours, part_category)


@mcp.tool()
def order_parts(operator_id: str, part_id: str, quantity: int = 1, department: str = "") -> str:
    """Order new parts. Orders >₹2 000 are held for Chief's approval (R006)."""
    return _order(operator_id, part_id, quantity, department)


@mcp.tool()
def check_budget(department: str) -> str:
    """Check the remaining budget for a department."""
    return _budget(department)


@mcp.tool()
def approve_order(order_id: str) -> str:
    """Approve a pending order after Chief's sign-off."""
    return _approve(order_id)


@mcp.tool()
def reject_order(order_id: str, reason: str = "") -> str:
    """Reject a pending order."""
    return _reject(order_id, reason)


# ─── Resources ───────────────────────────────────────────────────────

@mcp.resource("foundry://rulebook")
def rulebook() -> str:
    """The Foundry's complete operational rulebook (10 rules + meta-rules)."""
    return get_rulebook_resource()


# ─── Entry point ─────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()
