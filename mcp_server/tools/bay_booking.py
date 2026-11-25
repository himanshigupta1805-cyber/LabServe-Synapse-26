"""
MCP Tool — book_bay

Book a fabrication bay for a specific date.
Enforces: R003, R004, R007, R008.
"""

import json
from datetime import datetime, timedelta
from mcp_server.state import get_state


def book_bay(
    operator_id: str,
    bay_id: str,
    date: str,
    duration_hours: int = 1,
    part_category: str = "",
) -> str:
    """Book a fabrication bay for a given date and duration.

    Args:
        operator_id:    Operator making the booking.
        bay_id:         Bay to book (e.g. 'Bay-A').
        date:           Booking date in YYYY-MM-DD format.
        duration_hours: Shift duration in hours (default 1).
        part_category:  Category of parts to fabricate (for R007 check).

    Returns:
        JSON with status, booking details or refusal with alternatives.
    """
    state = get_state()

    # ── Validate operator ────────────────────────────────────────────
    operator = state.find_operator(operator_id)
    if not operator:
        return json.dumps({
            "status": "error",
            "message": f"REFUSAL: Operator '{operator_id}' not found.",
        })

    # R004 — Active Only
    if not operator["active"]:
        return json.dumps({
            "status": "refused", "rule": "R004",
            "message": (
                f"REFUSAL [R004 — Active Operator Only]: "
                f"Operator '{operator['name']}' is INACTIVE."
            ),
        })

    # ── Validate bay ─────────────────────────────────────────────────
    bay = state.find_bay(bay_id)
    if not bay:
        available = [b["bay_id"] for b in state.bays]
        return json.dumps({
            "status": "error",
            "message": f"REFUSAL: Bay '{bay_id}' not found. Available: {available}.",
        })

    # ── Parse date ───────────────────────────────────────────────────
    try:
        booking_date = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return json.dumps({
            "status": "error",
            "message": "Invalid date format. Use YYYY-MM-DD.",
        })

    # R008 — No Weekend Booking
    if booking_date.weekday() >= 5:
        day_name = booking_date.strftime("%A")
        # Suggest next weekday
        next_wd = booking_date
        while next_wd.weekday() >= 5:
            next_wd += timedelta(days=1)
        return json.dumps({
            "status": "refused", "rule": "R008",
            "message": (
                f"REFUSAL [R008 — No Weekend Booking]: Cannot book "
                f"on {day_name} ({date}). Weekend bookings are prohibited. "
                f"Nearest weekday: {next_wd.strftime('%Y-%m-%d')} "
                f"({next_wd.strftime('%A')})."
            ),
            "suggested_date": next_wd.strftime("%Y-%m-%d"),
        })

    # R007 — Bay Type Match
    if part_category:
        compat = bay.get("compatible_categories", [])
        if part_category.lower() not in [c.lower() for c in compat]:
            # Suggest compatible bays
            compatible_bays = [
                b["bay_id"]
                for b in state.bays
                if part_category.lower()
                in [c.lower() for c in b.get("compatible_categories", [])]
            ]
            return json.dumps({
                "status": "refused", "rule": "R007",
                "message": (
                    f"REFUSAL [R007 — Bay Type Match]: Bay '{bay_id}' "
                    f"(type: {bay['type']}) is not compatible with category "
                    f"'{part_category}'. Compatible categories for this bay: "
                    f"{compat}."
                ),
                "compatible_bays": compatible_bays,
            })

    # R003 — Bay Capacity
    bookings_on_date = [
        s for s in bay["booked_slots"] if s["date"] == date
    ]
    if len(bookings_on_date) >= bay["capacity"]:
        # Find alternatives
        alt_bays = []
        for b in state.bays:
            if b["bay_id"] == bay_id:
                continue
            slots_used = len([s for s in b["booked_slots"] if s["date"] == date])
            if slots_used < b["capacity"]:
                # Check category compat if relevant
                if part_category:
                    if part_category.lower() not in [
                        c.lower() for c in b.get("compatible_categories", [])
                    ]:
                        continue
                alt_bays.append({
                    "bay_id": b["bay_id"],
                    "type": b["type"],
                    "available_slots": b["capacity"] - slots_used,
                })

        # Find alternative dates (next 5 weekdays)
        alt_dates = []
        check = booking_date + timedelta(days=1)
        while len(alt_dates) < 5:
            if check.weekday() < 5:  # weekday
                slots_used = len([
                    s for s in bay["booked_slots"]
                    if s["date"] == check.strftime("%Y-%m-%d")
                ])
                if slots_used < bay["capacity"]:
                    alt_dates.append(check.strftime("%Y-%m-%d"))
            check += timedelta(days=1)

        return json.dumps({
            "status": "refused", "rule": "R003",
            "message": (
                f"REFUSAL [R003 — Bay Capacity]: Bay '{bay_id}' is at "
                f"full capacity ({bay['capacity']} slots) on {date}. "
                f"{len(bookings_on_date)} booking(s) already exist."
            ),
            "alternative_bays": alt_bays,
            "alternative_dates": alt_dates,
        })

    # ── Execute booking ──────────────────────────────────────────────
    booking = {
        "booking_id": state.next_booking_id(),
        "operator_id": operator_id,
        "operator_name": operator["name"],
        "date": date,
        "duration_hours": duration_hours,
        "part_category": part_category,
    }
    bay["booked_slots"].append(booking)

    return json.dumps({
        "status": "success",
        "message": (
            f"Bay '{bay_id}' booked for operator '{operator['name']}' "
            f"on {date} for {duration_hours}h."
        ),
        "booking": booking,
    })
