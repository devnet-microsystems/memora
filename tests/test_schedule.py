from datetime import date, time
from src.schedule import occurs_on

def test_occurs_on_daily():
    assert occurs_on("08:00", date(2026, 10, 5)) == time(8, 0)
    assert occurs_on("23:59", date(2026, 10, 5)) == time(23, 59)

def test_occurs_on_weekly():
    # 2026-10-05 is a Monday
    assert occurs_on("MON,WED 15:30", date(2026, 10, 5)) == time(15, 30)
    assert occurs_on("TUE,THU 15:30", date(2026, 10, 5)) is None

def test_occurs_on_single_date():
    assert occurs_on("2026-10-05 14:00", date(2026, 10, 5)) == time(14, 0)
    assert occurs_on("2026-10-06 14:00", date(2026, 10, 5)) is None

def test_occurs_on_invalid_format():
    assert occurs_on("invalid", date(2026, 10, 5)) is None
    assert occurs_on("30:00", date(2026, 10, 5)) is None
    assert occurs_on("MON 25:00", date(2026, 10, 5)) is None
    assert occurs_on("2026-10-05 25:00", date(2026, 10, 5)) is None
    assert occurs_on(None, date(2026, 10, 5)) is None
    assert occurs_on("", date(2026, 10, 5)) is None
