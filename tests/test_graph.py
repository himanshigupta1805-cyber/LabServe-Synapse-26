"""
Tests — Graph Structure
========================
Tests for the LangGraph agent graph structure and node wiring.
(Does not require a live LLM — tests the graph topology and
non-LLM nodes.)
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_server.state import FoundryState, set_state
from agent.guard import check_voight_kampff
from agent.arbiter import arbitrate_bay
from agent.optimizer import optimize_plan
from agent.human_approval import format_approval_request, process_approval
from data.seed_data import generate_fresh_seed


@pytest.fixture(autouse=True)
def fresh():
    set_state(FoundryState(generate_fresh_seed()))
    yield


# ═══════ Bay Arbiter ═════════════════════════════════════════════════

class TestArbiter:
    def test_alternatives_returned(self):
        # Fill Bay-C (capacity 1)
        from mcp_server.tools.bay_booking import book_bay
        book_bay("OP-001", "Bay-C", "2049-12-01")

        result = arbitrate_bay("Bay-C", "2049-12-01", "electronics")
        assert len(result["alternative_bays"]) > 0
        assert len(result["alternative_dates"]) > 0

    def test_recommendation_format(self):
        result = arbitrate_bay("Bay-A", "2049-12-01", "electronics")
        assert "recommendation" in result


# ═══════ Optimizer ═══════════════════════════════════════════════════

class TestOptimizer:
    def test_substitute_cheaper(self):
        # SYN-005 (₹1500) has substitute SYN-009 (₹600)
        plan = [{
            "tool": "borrow_part",
            "args": {"operator_id": "OP-005", "part_id": "SYN-005", "quantity": 1},
            "estimated_cost": 1500,
        }]
        result = optimize_plan(plan)
        assert result[0]["args"]["part_id"] == "SYN-009"
        assert "optimization_notes" in result[0]

    def test_borrow_instead_of_order(self):
        plan = [{
            "tool": "order_parts",
            "args": {"operator_id": "OP-001", "part_id": "SYN-003",
                     "quantity": 1, "department": "Assembly"},
            "estimated_cost": 800,
        }]
        result = optimize_plan(plan)
        # Should convert to borrow (SYN-003 has 25 in stock)
        assert result[0]["tool"] == "borrow_part"


# ═══════ Human Approval ═════════════════════════════════════════════

class TestHumanApproval:
    def test_format_request(self):
        order = {
            "order_id": "ORD-001",
            "part_name": "Neural Processor Unit",
            "quantity": 2,
            "total_cost": 9000,
            "unit_cost": 4500,
            "operator_name": "Deckard",
            "department": "Assembly",
        }
        req = format_approval_request(order)
        assert req["type"] == "approval_required"
        assert req["total_cost"] == 9000

    def test_process_approve(self):
        from mcp_server.tools.ordering import order_parts
        r = json.loads(order_parts("OP-001", "SYN-001", 1, "Assembly"))
        oid = r["order"]["order_id"]
        result = process_approval(oid, approved=True)
        assert "APPROVED" in result

    def test_process_reject(self):
        from mcp_server.tools.ordering import order_parts
        r = json.loads(order_parts("OP-001", "SYN-001", 1, "Assembly"))
        oid = r["order"]["order_id"]
        result = process_approval(oid, approved=False, reason="Budget concern")
        assert "REJECTED" in result
