"""
MCP Tool — inventory_search

Search The Foundry's parts inventory by name and/or category.
"""

import json
from mcp_server.state import get_state


def inventory_search(query: str = "", category: str = "") -> str:
    """Search the inventory for parts matching a name substring and/or category.

    Args:
        query:    Case-insensitive substring to match against part names.
        category: Exact category filter (e.g. 'electronics', 'mechanical').

    Returns:
        JSON string with status, matched parts list, and count.
    """
    state = get_state()
    results = []

    for part in state.inventory:
        match = True
        if query and query.lower() not in part["name"].lower():
            match = False
        if category and category.lower() != part["category"].lower():
            match = False
        if match:
            results.append({
                "part_id": part["part_id"],
                "name": part["name"],
                "category": part["category"],
                "quantity": part["quantity"],
                "unit_cost": part["unit_cost"],
                "min_clearance": part["min_clearance"],
                "location": part["location"],
                "substitutes": part.get("substitutes", []),
            })

    if not results:
        return json.dumps({
            "status": "success",
            "parts": [],
            "count": 0,
            "message": f"No parts found matching query='{query}' category='{category}'. "
                       f"Available categories: {sorted({p['category'] for p in state.inventory})}.",
        })

    return json.dumps({
        "status": "success",
        "parts": results,
        "count": len(results),
        "message": f"Found {len(results)} part(s) matching your criteria.",
    })
