from __future__ import annotations

from datetime import datetime


def parse_flexible_timestamp(raw: str) -> datetime:
    """Parse WhatsApp export or browser time labels into a datetime."""
    cleaned = raw.strip()
    if not cleaned:
        return datetime.min

    # Browser labels often keep the comma: "9/7/26, 13:52"
    candidates = [cleaned, cleaned.replace(",", "")]
    formats = (
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%m/%d/%Y %H:%M:%S %p",
        "%m/%d/%Y %H:%M %p",
        "%m/%d/%y %H:%M:%S %p",
        "%m/%d/%y %H:%M %p",
        "%m/%d/%y %H:%M:%S",
        "%m/%d/%y %H:%M",
        "%d/%m/%y %H:%M:%S",
        "%d/%m/%y %H:%M",
        "%m/%d/%y",
        "%d/%m/%y",
    )
    for value in candidates:
        for fmt in formats:
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
    return datetime.min


def hours_between(earlier: datetime, later: datetime) -> float | None:
    if earlier == datetime.min or later == datetime.min:
        return None
    delta = later - earlier
    return max(delta.total_seconds() / 3600.0, 0.0)
