from apps.episode.models import Episode

from .models import Progress


class ProgressError(ValueError):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.message = message
        self.status = status


def as_dict(row):
    return {
        'episode': row.episode_id,
        'position': float(row.position or 0),
        'duration': float(row.duration or 0),
        'updated_at': row.updated_at.isoformat() if row.updated_at else '',
    }


def get_for(user, episode_id):
    row = Progress.objects.filter(user=user, episode_id=episode_id).first()
    if not row:
        return {'episode': int(episode_id), 'position': 0, 'duration': 0}
    return as_dict(row)


def save_for(user, episode_id, position, duration=0):
    try:
        episode_pk = int(episode_id)
        pos = max(0, float(position))
        dur = max(0, float(duration or 0))
    except (TypeError, ValueError) as exc:
        raise ProgressError('Joylashuv noto‘g‘ri') from exc
    if not Episode.objects.filter(pk=episode_pk).exists():
        raise ProgressError('Qism topilmadi', 404)
    if dur and pos > dur:
        pos = dur
    row, _ = Progress.objects.update_or_create(
        user=user,
        episode_id=episode_pk,
        defaults={'position': pos, 'duration': dur},
    )
    from .streak import record_watch
    record_watch(user, pos)
    return as_dict(row)


def clear_for(user, episode_id):
    Progress.objects.filter(user=user, episode_id=episode_id).delete()
    return {'episode': int(episode_id), 'position': 0, 'duration': 0}
