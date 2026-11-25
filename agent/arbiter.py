"""
Multi-Agent Bay Arbiter
========================
Resolves resource contention when competing requests target the same
fabrication bay.  Provides alternative bays and time-slots.
"""

from datetime import datetime, timedelta
from mcp_server.state import get_state


def arbitrate_bay(bay_id: str, date: str, part_category: str = "") -> dict:
    """Evaluate bay contention and suggest alternatives.

    Args:
        bay_id:        The originally requested bay.
        date:          Requested date (YYYY-MM-DD).
        part_category: Part category for compatibility filtering.

    Returns:
        dict with 'alternative_bays' and 'alternative_dates'.
    """
    state = get_state()
    target_bay = state.find_bay(bay_id)

    # ── Alternative bays with capacity on the same date ──────────────
    alt_bays: list[dict] = []
    for bay in state.bays:
        if bay["bay_id"] == bay_id:
            continue
        slots_used = len([s for s in bay["booked_slots"] if s["date"] == date])
        if slots_used >= bay["capacity"]:
            continue
        # Category compatibility check
        if part_category:
            compat = [c.lower() for c in bay.get("compatible_categories", [])]
            if part_category.lower() not in compat:
                continue
        alt_bays.append({
            "bay_id": bay["bay_id"],
            "type": bay["type"],
            "available_slots": bay["capacity"] - slots_used,
            "equipment": bay["equipment"],
        })

    # ── Alternative dates on the original bay ────────────────────────
    alt_dates: list[str] = []
    if target_bay:
        try:
            base = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            base = datetime.now()

        check = base + timedelta(days=1)
        while len(alt_dates) < 5:
            if check.weekday() < 5:  # R008: weekdays only
                d_str = check.strftime("%Y-%m-%d")
                used = len([s for s in target_bay["booked_slots"] if s["date"] == d_str])
                if used < target_bay["capacity"]:
                    alt_dates.append(d_str)
            check += timedelta(days=1)

    return {
        "original_bay": bay_id,
        "original_date": date,
        "alternative_bays": alt_bays,
        "alternative_dates": alt_dates,
        "recommendation": (
            f"Bay '{alt_bays[0]['bay_id']}' on {date}"
            if alt_bays
            else f"Bay '{bay_id}' on {alt_dates[0]}" if alt_dates
            else "No alternatives found"
        ),
    }
