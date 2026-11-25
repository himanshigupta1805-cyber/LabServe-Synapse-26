"""
Seed Data Generator for The Foundry.
Provides functions to load / regenerate fresh seed data for testing.
"""

import json
from pathlib import Path
from copy import deepcopy

DATA_DIR = Path(__file__).parent


def load_default_seed() -> dict:
    """Load the default seed data from JSON files."""
    return {
        "inventory": _load_json("inventory.json"),
        "operators": _load_json("operators.json"),
        "bays": _load_json("bays.json"),
        "budget": _load_json("budget.json"),
        "rulebook": _load_json("rulebook.json"),
    }


def _load_json(filename: str):
    with open(DATA_DIR / filename, "r", encoding="utf-8") as f:
        return json.load(f)


def generate_fresh_seed() -> dict:
    """Deep copy of default seed for isolated test runs."""
    return deepcopy(load_default_seed())
