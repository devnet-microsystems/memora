from datetime import date, time
from src.schedule import occurs_on

def test_occurs_on_daily():
    assert occurs_on("08:00", date(2026, 10, 5)) == time(8, 0)
    assert occurs_on("23:59", date(2026, 10, 5)) == time(23, 59)

def test_occurs_on_weekly():
    # 2026-10-05 is a Monday
    assert occurs_on("MON,WED 15:30", date(2026, 10, 5)) == time(15, 30)
    assert occurs_on("TUE,THU 15:30", date(2026, 10, 5)) is None


def test_occurs_on_italian_weekday():
    # 2026-10-08 is a Thursday ("giovedì"); 2026-10-05 is a Monday
    assert occurs_on("giovedì 09:00", date(2026, 10, 8)) == time(9, 0)
    assert occurs_on("GIOVEDÌ 09:00", date(2026, 10, 8)) == time(9, 0)
    assert occurs_on("giovedì 09:00", date(2026, 10, 5)) is None
    assert occurs_on("lunedì 08:00", date(2026, 10, 5)) == time(8, 0)


def test_occurs_on_italian_weekday_no_time():
    # 2026-10-08 is a Thursday ("giovedì"); 2026-10-05 is a Monday
    assert occurs_on("giovedì", date(2026, 10, 8)) == time(0, 0)
    assert occurs_on("giovedi", date(2026, 10, 8)) == time(0, 0)
    assert occurs_on("GIOVEDÌ", date(2026, 10, 8)) == time(0, 0)
    assert occurs_on("GIOVEDI", date(2026, 10, 8)) == time(0, 0)
    # Different day: not today's event
    assert occurs_on("giovedì", date(2026, 10, 5)) is None
    # Other Italian weekdays
    assert occurs_on("lunedì", date(2026, 10, 5)) == time(0, 0)
    assert occurs_on("martedì", date(2026, 10, 6)) == time(0, 0)
    assert occurs_on("mercoledì", date(2026, 10, 7)) == time(0, 0)
    assert occurs_on("venerdì", date(2026, 10, 9)) == time(0, 0)
    assert occurs_on("sabato", date(2026, 10, 10)) == time(0, 0)
    assert occurs_on("domenica", date(2026, 10, 11)) == time(0, 0)

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
