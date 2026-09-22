import logging

import requests
from django.conf import settings
from django.utils import timezone

from apps.anime.paths import title_path
from apps.main.object_storage import public_file_url

from .models import CustomUser, Notice, UserList

logger = logging.getLogger(__name__)

_MUTED = False

WATCH_STATUSES = (
    UserList.Status.WATCHING,
    UserList.Status.PLANNED,
    UserList.Status.FAVORITE,
    UserList.Status.COMPLETED,
)

KIND_LABELS = {
    Notice.Kind.NEW_SEASON: 'Yangi sezon',
    Notice.Kind.NEW_EPISODE: 'Yangi qism',
    Notice.Kind.NEWS: 'Yangilik',
    Notice.Kind.MODERATION: 'Moderatsiya',
}


class mute_notices:
    def __enter__(self):
        global _MUTED
        self.prev = _MUTED
        _MUTED = True
        return self

    def __exit__(self, *exc):
        global _MUTED
        _MUTED = self.prev


def send_telegram(chat_id, text) -> bool:
    token = getattr(settings, 'BOT_TOKEN', '') or ''
    if not token or not chat_id:
        return False
    try:
        response = requests.post(
            f'https://api.telegram.org/bot{token}/sendMessage',
            json={'chat_id': chat_id, 'text': text, 'disable_web_page_preview': False},
            timeout=8,
        )
        return response.status_code == 200
    except requests.RequestException:
        logger.warning('telegram notice failed', extra={'chat_id': chat_id})
        return False


def _site_url():
    return (getattr(settings, 'SITE_URL', '') or 'http://localhost:8000').rstrip('/')


def unread_count_for(user) -> int:
    return Notice.objects.filter(user=user, read_at__isnull=True).count()


def queryset_for(user, *, unread_only=False):
    rows = Notice.objects.filter(user=user).select_related('anime')
    if unread_only:
        rows = rows.filter(read_at__isnull=True)
    return rows


def notice_dict(notice, request=None) -> dict:
    poster = ''
    anime = notice.anime
    if anime and anime.poster:
        poster = public_file_url(anime.poster)
        if poster and request:
            poster = request.build_absolute_uri(poster)
    href = title_path(notice.anime) if notice.anime_id else '/notices/'
    return {
        'id': notice.id,
        'kind': notice.kind,
        'kind_label': KIND_LABELS.get(notice.kind, 'Yangilik'),
        'title': notice.title,
        'body': notice.body,
        'read': notice.read_at is not None,
        'sent_telegram': notice.sent_telegram,
        'created_at': notice.created_at.isoformat(),
        'anime_id': notice.anime_id,
        'poster': poster,
        'href': href,
    }


def mark_read(user, pk):
    notice = Notice.objects.filter(user=user, pk=pk).first()
    if not notice:
        return None
    if notice.read_at is None:
        notice.read_at = timezone.now()
        notice.save(update_fields=['read_at'])
    return notice


def mark_all_read(user) -> int:
    return Notice.objects.filter(user=user, read_at__isnull=True).update(read_at=timezone.now())


def notify_new_season(season):
    if _MUTED or not season or getattr(season, 'number', 0) <= 1:
        return 0
    anime = season.anime
    users = (
        CustomUser.objects.filter(
            title_lists__anime=anime,
            title_lists__status__in=WATCH_STATUSES,
            notify_new_season=True,
        )
        .distinct()
    )
    sent = 0
    body = f'{anime.title} — {season.number}-sezon chiqdi. Katalogda oching.'
    link = f'{_site_url()}{title_path(anime)}'
    text = f'Animee\n{body}\n{link}'
    for user in users:
        notice = Notice.objects.create(
            user=user,
            anime=anime,
            kind=Notice.Kind.NEW_SEASON,
            title=f'{anime.title}: yangi sezon',
            body=body,
        )
        if user.telegram_id and user.notify_telegram:
            notice.sent_telegram = send_telegram(user.telegram_id, text)
            notice.save(update_fields=['sent_telegram'])
        sent += 1
    return sent
