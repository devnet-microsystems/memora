import os
from datetime import datetime
from zoneinfo import ZoneInfo

def now_local(now=None):
    """
    Returns the current local time based on the TZ_NAME environment variable.
    Allows injecting a mock 'now' for testing.
    """
    if now is not None:
        return now
    tz_name = os.getenv("TZ_NAME", "Europe/Rome")
    return datetime.now(ZoneInfo(tz_name))
