from datetime import datetime

import pytest

from personal_reply.time_parse import hours_between, parse_flexible_timestamp


def test_parse_browser_timestamp() -> None:
    parsed = parse_flexible_timestamp("9/7/26, 13:52")
    assert parsed == datetime(2026, 9, 7, 13, 52)


def test_parse_export_timestamp_with_am_pm() -> None:
    parsed = parse_flexible_timestamp("1/15/24, 10:30:45 AM")
    assert parsed == datetime(2024, 1, 15, 10, 30, 45)


def test_hours_between_returns_none_for_unknown() -> None:
    assert hours_between(datetime.min, datetime(2026, 1, 1)) is None


def test_hours_between_computes_gap() -> None:
    earlier = datetime(2026, 1, 1, 10, 0)
    later = datetime(2026, 1, 3, 10, 0)
    assert hours_between(earlier, later) == pytest.approx(48.0)
