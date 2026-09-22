from datetime import date, timedelta

from django.utils import timezone

MIN_WATCH_SECONDS = 30


def as_dict(user, today=None) -> dict:
    today = today or timezone.localdate()
    last = getattr(user, 'streak_last_on', None)
    current = int(getattr(user, 'streak_count', 0) or 0)
    started = getattr(user, 'streak_started_on', None)
    if not last or (today - last).days > 1:
        current = 0
        started = None
    return {
        'current': current,
        'best': int(getattr(user, 'streak_best', 0) or 0),
        'days': int(getattr(user, 'streak_days', 0) or 0),
        'started_on': started.isoformat() if started else '',
        'last_on': last.isoformat() if last else '',
        'alive': current > 0,
        'today': bool(last and last == today),
    }


def record_watch(user, position=0, on=None) -> dict:
    try:
        pos = float(position or 0)
    except (TypeError, ValueError):
        pos = 0
    today = on or timezone.localdate()
    if not isinstance(today, date):
        today = timezone.localdate()
    if pos < MIN_WATCH_SECONDS:
        return as_dict(user, today)
    last = user.streak_last_on
    if last == today:
        return as_dict(user, today)
    if last and today - last == timedelta(days=1):
        current = int(user.streak_count or 0) + 1
        started = user.streak_started_on or today
    else:
        current = 1
        started = today
    user.streak_count = current
    user.streak_best = max(int(user.streak_best or 0), current)
    user.streak_days = int(user.streak_days or 0) + 1
    user.streak_started_on = started
    user.streak_last_on = today
    user.save(update_fields=[
        'streak_count', 'streak_best', 'streak_days',
        'streak_started_on', 'streak_last_on',
    ])
    return as_dict(user, today)
