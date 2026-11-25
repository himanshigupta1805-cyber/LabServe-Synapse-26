"""
Cost-Aware Optimizer
=====================
Analyses a proposed plan and rewrites it to minimise total cost while
keeping every step valid.
"""

from mcp_server.state import get_state


def optimize_plan(plan_steps: list[dict]) -> list[dict]:
    """Optimise a list of planned actions for lowest valid cost.

    Each step is a dict like:
        {"tool": "borrow_part", "args": {...}, "estimated_cost": 0}

    Optimisation strategies
    -----------------------
    1. Substitute parts — prefer cheaper alternatives with sufficient
       stock and clearance.
    2. Borrow vs. order — if stock allows, borrow instead of ordering.
    3. Bay preference — prefer the general bay (Bay-D) with higher
       capacity when it is compatible with the part category.

    Returns:
        Optimised plan_steps with an added 'optimization_notes' field
        where changes were made.
    """
    state = get_state()
    optimised: list[dict] = []

    for step in plan_steps:
        new_step = dict(step)
        notes: list[str] = []
        args = dict(step.get("args", {}))

        tool = step.get("tool", "")

        # ── 1. Part substitution (cheaper alternative) ───────────────
        if tool in ("borrow_part", "order_parts") and "part_id" in args:
            part = state.find_part(args["part_id"])
            if part:
                for sub_id in part.get("substitutes", []):
                    sub = state.find_part(sub_id)
                    if not sub:
                        continue
                    if sub["unit_cost"] >= part["unit_cost"]:
                        continue  # not cheaper

                    # Check clearance if operator is known
                    op_id = args.get("operator_id", "")
                    if op_id:
                        op = state.find_operator(op_id)
                        if op and op["clearance_level"] < sub["min_clearance"]:
                            continue  # operator can't access substitute

                    qty = args.get("quantity", 1)
                    if tool == "borrow_part" and sub["quantity"] - qty < 2:
                        continue  # would violate R010

                    # Substitute is valid and cheaper
                    savings = (part["unit_cost"] - sub["unit_cost"]) * qty
                    notes.append(
                        f"Substituted '{part['name']}' (₹{part['unit_cost']}) "
                        f"→ '{sub['name']}' (₹{sub['unit_cost']}). "
                        f"Savings: ₹{savings:,}."
                    )
                    args["part_id"] = sub_id
                    new_step["estimated_cost"] = sub["unit_cost"] * qty
                    break

        # ── 2. Borrow instead of order ───────────────────────────────
        if tool == "order_parts" and "part_id" in args:
            part = state.find_part(args["part_id"])
            if part:
                qty = args.get("quantity", 1)
                available = max(0, part["quantity"] - 2)  # respect R010
                if available >= qty:
                    notes.append(
                        f"Changed order → borrow for '{part['name']}' "
                        f"({available} available in stock). Saves ₹{part['unit_cost'] * qty:,}."
                    )
                    new_step["tool"] = "borrow_part"
                    new_step["estimated_cost"] = 0
                    # Remove department from args (not needed for borrow)
                    args.pop("department", None)

        # ── 3. Bay preference: prefer Bay-D (general, higher cap) ────
        if tool == "book_bay" and "bay_id" in args:
            bay_id = args["bay_id"]
            cat = args.get("part_category", "")
            if bay_id != "Bay-D" and cat:
                bay_d = state.find_bay("Bay-D")
                if bay_d:
                    compat = [c.lower() for c in bay_d.get("compatible_categories", [])]
                    if cat.lower() in compat:
                        date = args.get("date", "")
                        used = len([s for s in bay_d["booked_slots"] if s["date"] == date])
                        if used < bay_d["capacity"]:
                            notes.append(
                                f"Switched bay '{bay_id}' → 'Bay-D' (general, "
                                f"higher capacity, {bay_d['capacity'] - used} "
                                f"slots free)."
                            )
                            args["bay_id"] = "Bay-D"

        new_step["args"] = args
        if notes:
            new_step["optimization_notes"] = notes
        optimised.append(new_step)

    return optimised
