"""Simulated week of activity for the public demo (clearly flagged as simulated=1 in the UI).

Uses the exact event kinds that the application logs, so the weekly report and the charts are real aggregations.
The story: a stable first half-week, then more repeated questions, one missed pill and some confusion.
"""

# day offset (0 = today) -> {kind: count}
THIS_WEEK = {
    6: {"interaction": 6, "med_confirmed": 1},
    5: {"interaction": 7, "repeat_flag": 1, "med_confirmed": 1, "diary_turn": 2},
    4: {"interaction": 6, "repeat_flag": 1, "med_confirmed": 1},
    3: {"interaction": 8, "repeat_flag": 2, "med_confirmed": 1, "diary_turn": 3},
    2: {"interaction": 9, "repeat_flag": 3, "med_confirmed": 1, "confusion_flag": 1},
    1: {"interaction": 10, "repeat_flag": 4, "med_missed": 1, "confusion_flag": 1, "diary_turn": 2},
    0: {"interaction": 6, "repeat_flag": 2, "med_confirmed": 1},
}
PREVIOUS_WEEK = {
    13: {"interaction": 5, "med_confirmed": 1},
    12: {"interaction": 5, "repeat_flag": 1, "med_confirmed": 1},
    11: {"interaction": 4, "med_confirmed": 1},
    10: {"interaction": 6, "med_confirmed": 1, "diary_turn": 1},
    9: {"interaction": 5, "repeat_flag": 1, "med_confirmed": 1},
    8: {"interaction": 5, "med_confirmed": 1},
    7: {"interaction": 4, "med_confirmed": 1},
}


def demo_events():
    events = []
    for week in (PREVIOUS_WEEK, THIS_WEEK):
        for days_ago, kinds in week.items():
            for kind, n in kinds.items():
                events.extend({"kind": kind, "simulated": 1, "days_ago": days_ago} for _ in range(n))
    return events
