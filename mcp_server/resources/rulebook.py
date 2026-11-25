"""
MCP Resource — Rulebook

Expose The Foundry's operational rulebook as an MCP resource.
"""

import json
from mcp_server.state import get_state


def get_rulebook_resource() -> str:
    """Return the full operational rulebook as a formatted JSON string."""
    state = get_state()
    return json.dumps(state.rulebook, indent=2, ensure_ascii=False)
