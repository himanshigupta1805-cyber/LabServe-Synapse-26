"""
The Foundry — Shared Mutable State.

Central in-memory state store for all MCP tools.  Loaded from seed-data JSON
files at startup.  Singleton so every tool sees the same live data, with full
reset support for evaluation / testing.
"""

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).parent.parent / "data"


class FoundryState:
    """Shared mutable state for The Foundry's operations."""

    def __init__(self, seed: dict | None = None):
        if seed:
            self._load_from_seed(seed)
        else:
            self._load_from_files()

        # Runtime-only state
        self.borrowed: dict[str, dict[str, int]] = {}   # {op_id: {part_id: qty}}
        self.order_log: list[dict] = []
        self.pending_approvals: list[dict] = []
        self._order_counter: int = 0
        self._booking_counter: int = 0

    # ── loaders ──────────────────────────────────────────────────────

    def _load_from_files(self) -> None:
        self.inventory: list[dict]      = self._read("inventory.json")
        self.operators: list[dict]      = self._read("operators.json")
        self.bays: list[dict]           = self._read("bays.json")
        self.budget: dict[str, dict]    = self._read("budget.json")
        self.rulebook: dict             = self._read("rulebook.json")

    def _load_from_seed(self, seed: dict) -> None:
        self.inventory = deepcopy(seed.get("inventory", []))
        self.operators = deepcopy(seed.get("operators", []))
        self.bays      = deepcopy(seed.get("bays", []))
        self.budget    = deepcopy(seed.get("budget", {}))
        self.rulebook  = deepcopy(seed.get("rulebook", {}))

    @staticmethod
    def _read(filename: str) -> Any:
        with open(DATA_DIR / filename, "r", encoding="utf-8") as f:
            return json.load(f)

    # ── lookup helpers ───────────────────────────────────────────────

    def find_part(self, part_id: str) -> dict | None:
        return next((p for p in self.inventory if p["part_id"] == part_id), None)

    def find_operator(self, operator_id: str) -> dict | None:
        return next((o for o in self.operators if o["operator_id"] == operator_id), None)

    def find_bay(self, bay_id: str) -> dict | None:
        return next((b for b in self.bays if b["bay_id"] == bay_id), None)

    def next_order_id(self) -> str:
        self._order_counter += 1
        return f"ORD-{self._order_counter:03d}"

    def next_booking_id(self) -> str:
        self._booking_counter += 1
        return f"BK-{self._booking_counter:03d}"

    def total_borrowed(self, operator_id: str) -> int:
        return sum(self.borrowed.get(operator_id, {}).values())

    def borrowed_qty(self, operator_id: str, part_id: str) -> int:
        return self.borrowed.get(operator_id, {}).get(part_id, 0)

    # ── reset ────────────────────────────────────────────────────────

    def reset(self, seed: dict | None = None) -> None:
        """Full state reset — used between evaluation test cases."""
        if seed:
            self._load_from_seed(seed)
        else:
            self._load_from_files()
        self.borrowed = {}
        self.order_log = []
        self.pending_approvals = []
        self._order_counter = 0
        self._booking_counter = 0


# ═══════ Singleton access ════════════════════════════════════════════

_state: FoundryState | None = None


def get_state() -> FoundryState:
    global _state
    if _state is None:
        _state = FoundryState()
    return _state


def reset_state(seed: dict | None = None) -> None:
    global _state
    if _state is None:
        _state = FoundryState(seed)
    else:
        _state.reset(seed)


def set_state(state: FoundryState) -> None:
    global _state
    _state = state
