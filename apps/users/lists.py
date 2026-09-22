from django.shortcuts import get_object_or_404

from apps.anime.models import Anime

from .models import UserList
from .profile import ProfileError

STATUSES = {choice.value for choice in UserList.Status}


def counts_for(user):
    out = {status: 0 for status in STATUSES}
    for row in UserList.objects.filter(user=user).values_list('status', flat=True):
        out[row] = out.get(row, 0) + 1
    return out


def queryset_for(user, status=None):
    qs = (
        UserList.objects.filter(user=user)
        .select_related('anime')
        .prefetch_related('anime__genres', 'anime__seasons')
        .order_by('-updated_at')
    )
    if status:
        if status not in STATUSES:
            raise ProfileError('Noto‘g‘ri ro‘yxat holati')
        qs = qs.filter(status=status)
    return qs[:200]


def upsert(user, anime_id, status, score=None):
    if status not in STATUSES:
        raise ProfileError('Noto‘g‘ri ro‘yxat holati')
    anime = get_object_or_404(Anime, pk=anime_id)
    defaults = {'status': status}
    if score not in (None, ''):
        try:
            parsed_score = int(score)
        except (TypeError, ValueError) as exc:
            raise ProfileError('Baho 1–10 oralig‘ida') from exc
        if parsed_score < 1 or parsed_score > 10:
            raise ProfileError('Baho 1–10 oralig‘ida')
        defaults['score'] = parsed_score
    row, _ = UserList.objects.update_or_create(
        user=user,
        anime=anime,
        defaults=defaults,
    )
    return row


def remove(user, anime_id):
    deleted, _ = UserList.objects.filter(user=user, anime_id=anime_id).delete()
    return deleted > 0


def status_for(user, anime_id):
    return UserList.objects.filter(user=user, anime_id=anime_id).first()
