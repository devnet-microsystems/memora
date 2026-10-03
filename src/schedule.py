import logging
import re
from datetime import date, time, datetime
from typing import Optional

logger = logging.getLogger("memora.schedule")

def occurs_on(schedule_str: str, target_date: date) -> Optional[time]:
    """
    Checks if a given schedule string occurs on a specific date.
    Returns the time if it does, None otherwise.
    
    Supported formats:
    - "HH:MM" -> every day
    - "MON,THU HH:MM" -> specific week days (MON TUE WED THU FRI SAT SUN)
    - "YYYY-MM-DD HH:MM" -> single specific date
    """
    if not schedule_str:
        return None
        
    schedule_str = schedule_str.strip()
    
    # 1. "HH:MM"
    m1 = re.match(r"^(\d{2}):(\d{2})$", schedule_str)
    if m1:
        try:
            return time(int(m1.group(1)), int(m1.group(2)))
        except ValueError as e:
            logger.warning(f"Invalid time format in schedule '{schedule_str}': {e}")
            return None
            
    # 2. "MON,THU HH:MM"
    m2 = re.match(r"^([A-Z,]+)\s+(\d{2}):(\d{2})$", schedule_str)
    if m2:
        days_str, hh, mm = m2.groups()
        days = [d.strip() for d in days_str.split(",")]
        
        # Convert target_date to weekday str
        weekdays = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
        target_weekday = weekdays[target_date.weekday()]
        
        if target_weekday in days:
            try:
                return time(int(hh), int(mm))
            except ValueError as e:
                logger.warning(f"Invalid time format in schedule '{schedule_str}': {e}")
                return None
        return None
        
    # 3. "YYYY-MM-DD HH:MM"
    m3 = re.match(r"^(\d{4}-\d{2}-\d{2})\s+(\d{2}):(\d{2})$", schedule_str)
    if m3:
        date_str, hh, mm = m3.groups()
        if date_str == target_date.isoformat():
            try:
                return time(int(hh), int(mm))
            except ValueError as e:
                logger.warning(f"Invalid time format in schedule '{schedule_str}': {e}")
                return None
        return None
        
    logger.warning(f"Unrecognized schedule format: '{schedule_str}'")
    return None

def med_state(node_data: dict, now: datetime) -> str:
    """
    Returns the current state of a medication node.
    """
    schedule = node_data.get("schedule")
    if not schedule:
        return "upcoming"
        
    occ_time = occurs_on(schedule, now.date())
    if not occ_time:
        return "upcoming"
        
    # Check if we have a confirmation for today
    last_status = node_data.get("last_status")
    last_conf = node_data.get("last_confirmation")
    
    if last_status in ["confirmed", "denied", "unsure"] and last_conf:
        conf_date = datetime.fromtimestamp(last_conf, now.tzinfo).date()
        if conf_date == now.date():
            return last_status
            
    meta = node_data.get("meta") or {}
    
    snoozed_until = meta.get("snoozed_until")
    if snoozed_until and snoozed_until > now.timestamp():
        return "snoozed"
        
    sched_dt = datetime.combine(now.date(), occ_time)
    if now.tzinfo:
        sched_dt = sched_dt.replace(tzinfo=now.tzinfo)
    
    diff_minutes = (now - sched_dt).total_seconds() / 60.0
    
    if diff_minutes < 0:
        return "upcoming"
    elif diff_minutes < 30:
        return "due"
    else:
        return "missed"

