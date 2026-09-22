import secrets
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from apps.episode.models import Episode
from apps.anime.paths import watch_path
from apps.main.object_storage import public_file_url
from apps.users.profile import avatar_url

from .models import PartyMessage, WatchParty

MAX_MEMBERS = 8
CODE_LEN = 8
IDLE_HOURS = 4


class PartyError(ValueError):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.message = message
        self.status = status


def _new_code() -> str:
    alphabet = 'abcdefghjkmnpqrstuvwxyz23456789'
    for _ in range(20):
        code = ''.join(secrets.choice(alphabet) for _ in range(CODE_LEN))
        if not WatchParty.objects.filter(code=code, closed_at__isnull=True).exists():
            return code
    raise PartyError('Xona yaratilmadi')


def live_position(party: WatchParty) -> float:
    pos = float(party.position or 0)
    if party.playing and party.clock:
        pos += max(0, (timezone.now() - party.clock).total_seconds())
    return max(0, pos)


def invite_url(party: WatchParty, request=None) -> str:
    path = f'/party/{party.code}/'
    if request is not None:
        return request.build_absolute_uri(path)
    base = (getattr(settings, 'SITE_URL', '') or 'http://localhost:8000').rstrip('/')
    return f'{base}{path}'


def ice_servers():
    servers = [
        {'urls': 'stun:stun.l.google.com:19302'},
        {'urls': 'stun:stun1.l.google.com:19302'},
    ]
    urls = list(getattr(settings, 'TURN_URLS', None) or [])
    single = (getattr(settings, 'TURN_URL', '') or '').strip()
    if single and single not in urls:
        urls.append(single)
    if not urls:
        return servers
    entry = {'urls': urls if len(urls) > 1 else urls[0]}
    user = (getattr(settings, 'TURN_USERNAME', '') or '').strip()
    cred = (getattr(settings, 'TURN_CREDENTIAL', '') or '').strip()
    if user:
        entry['username'] = user
        entry['credential'] = cred
    servers.append(entry)
    return servers


def notify(code: str, payload: dict):
    from asgiref.sync import async_to_sync
    from channels.layers import get_channel_layer

    layer = get_channel_layer()
    if not layer:
        return
    try:
        async_to_sync(layer.group_send)(
            f'party_{code}',
            {'type': 'party.event', 'payload': payload},
        )
    except Exception:
        return


def member_payload(user, *, host_id, camera=False, request=None):
    return {
        'id': user.pk,
        'username': user.username,
        'photo': avatar_url(user, request),
        'host': user.pk == host_id,
        'camera': bool(camera),
    }


def party_payload(party: WatchParty, request=None, extra=None):
    episode = party.episode
    anime = episode.season.anime
    poster = ''
    if anime.poster:
        poster = public_file_url(anime.poster)
        if poster and request:
            poster = request.build_absolute_uri(poster)
    payload = {
        'code': party.code,
        'invite_url': invite_url(party, request),
        'control': party.control,
        'host_id': party.host_id,
        'episode': {
            'id': episode.id,
            'number': episode.number,
            'title': episode.title,
            'anime_id': anime.id,
            'anime_title': anime.title,
            'anime_kind': anime.kind,
            'anime_slug': anime.slug,
            'watch_path': watch_path(episode),
            'poster': poster,
        },
        'want_playing': party.want_playing,
        'playing': party.playing,
        'position': live_position(party),
        'buffering': list(party.buffering or []),
        'require_camera': bool(party.require_camera),
        'require_mic': bool(party.require_mic),
        'closed': party.closed_at is not None,
        'created_at': party.created_at.isoformat(),
        'host': {
            'id': party.host_id,
            'username': party.host.username if party.host_id else '',
            'photo': avatar_url(party.host, request) if party.host_id else '',
        },
    }
    if extra:
        payload.update(extra)
    return payload


def get_open(code: str) -> WatchParty:
    party = (
        WatchParty.objects.select_related('episode__season__anime', 'host')
        .filter(code=code)
        .first()
    )
    if not party:
        raise PartyError('Xona topilmadi', 404)
    expire_if_idle(party)
    if party.closed_at:
        raise PartyError('Xona yopilgan', 410)
    return party


def preview_payload(party: WatchParty, request=None):
    full = party_payload(party, request)
    return {
        'code': full['code'],
        'invite_url': full['invite_url'],
        'host': full['host'],
        'episode': full['episode'],
        'require_camera': full['require_camera'],
        'require_mic': full['require_mic'],
        'closed': full['closed'],
        'control': full['control'],
    }


def next_episode(episode: Episode):
    nxt = (
        Episode.objects.filter(season=episode.season, number__gt=episode.number)
        .order_by('number')
        .first()
    )
    if nxt:
        return nxt
    return (
        Episode.objects.filter(
            season__anime_id=episode.season.anime_id,
            season__number__gt=episode.season.number,
        )
        .order_by('season__number', 'number')
        .first()
    )


def set_episode(party: WatchParty, episode: Episode) -> WatchParty:
    party.episode = episode
    party.position = 0
    party.want_playing = False
    party.playing = False
    party.buffering = []
    party.clock = timezone.now()
    party.save(update_fields=['episode', 'position', 'want_playing', 'playing', 'buffering', 'clock'])
    return party


def change_episode(user, code: str, episode_id=None, *, advance=False) -> WatchParty:
    party = get_open(code)
    staff = bool(getattr(user, 'is_staff', False))
    if party.host_id != user.pk and not staff:
        raise PartyError('Qismni host yoki Admin almashtiradi', 403)
    if advance:
        nxt = next_episode(party.episode)
        if not nxt:
            raise PartyError('Keyingi qism yo‘q', 400)
        return set_episode(party, nxt)
    episode = Episode.objects.select_related('season__anime').filter(pk=episode_id).first()
    if not episode:
        raise PartyError('Epizod topilmadi', 404)
    return set_episode(party, episode)


def create_party(user, episode_id, control='shared', require_camera=False, require_mic=False) -> WatchParty:
    if not user or not user.is_authenticated:
        raise PartyError('Avval kiring', 401)
    episode = Episode.objects.select_related('season__anime').filter(pk=episode_id).first()
    if not episode:
        raise PartyError('Epizod topilmadi', 404)
    if control not in (WatchParty.Control.HOST, WatchParty.Control.SHARED):
        control = WatchParty.Control.SHARED
    prune_idle()
    return WatchParty.objects.create(
        code=_new_code(),
        episode=episode,
        host=user,
        control=control,
        require_camera=bool(require_camera),
        require_mic=bool(require_mic),
        clock=timezone.now(),
    )


def set_requirements(user, code: str, require_camera=None, require_mic=None) -> WatchParty:
    party = get_open(code)
    if party.host_id != user.pk:
        raise PartyError('Sozlamani faqat host o‘zgartiradi', 403)
    fields = []
    if require_camera is not None:
        party.require_camera = bool(require_camera)
        fields.append('require_camera')
    if require_mic is not None:
        party.require_mic = bool(require_mic)
        fields.append('require_mic')
    if fields:
        party.save(update_fields=fields)
    return party


def close_party(user, code: str) -> WatchParty:
    party = get_open(code)
    if party.host_id != user.pk:
        raise PartyError('Xonani faqat host yopadi', 403)
    party.closed_at = timezone.now()
    party.playing = False
    party.want_playing = False
    party.save(update_fields=['closed_at', 'playing', 'want_playing'])
    return party


def _can_drive(party: WatchParty, user) -> bool:
    if party.control == WatchParty.Control.SHARED:
        return True
    return party.host_id == user.pk


def _live_ids(party: WatchParty):
    from . import presence
    return {int(m['id']) for m in presence.members(party.code)}


def _sync_playing(party: WatchParty):
    ready = not (party.buffering or [])
    party.playing = bool(party.want_playing and ready)
    party.clock = timezone.now()
    party.save(update_fields=['want_playing', 'playing', 'position', 'clock', 'buffering', 'control'])
    return party


def sync_after_leave(party: WatchParty) -> WatchParty:
    live = _live_ids(party)
    party.buffering = [int(x) for x in (party.buffering or []) if int(x) in live]
    party.position = live_position(party)
    return _sync_playing(party)


def apply_transport(party: WatchParty, user, action: str, position=None) -> WatchParty:
    if not _can_drive(party, user):
        raise PartyError('Boshqaruv hostda')
    now = timezone.now()
    current = live_position(party)
    if action == 'play':
        party.position = current if position is None else float(position)
        party.want_playing = True
    elif action == 'pause':
        party.position = current if position is None else float(position)
        party.want_playing = False
    elif action == 'seek':
        if position is None:
            raise PartyError('Vaqt kerak')
        party.position = max(0, float(position))
    else:
        raise PartyError('Noma’lum harakat')
    party.clock = now
    return _sync_playing(party)


def set_buffering(party: WatchParty, user, waiting: bool) -> WatchParty:
    party.position = live_position(party)
    buf = [int(x) for x in (party.buffering or [])]
    uid = int(user.pk)
    if waiting and uid not in buf:
        buf.append(uid)
    if not waiting:
        buf = [x for x in buf if x != uid]
    party.buffering = buf
    party.clock = timezone.now()
    return _sync_playing(party)


def set_control(party: WatchParty, user, mode: str) -> WatchParty:
    if party.host_id != user.pk:
        raise PartyError('Boshqaruvni faqat host o‘zgartiradi', 403)
    if mode not in (WatchParty.Control.HOST, WatchParty.Control.SHARED):
        raise PartyError('control host yoki shared')
    party.control = mode
    party.save(update_fields=['control'])
    return party


def add_message(party: WatchParty, user, body: str) -> PartyMessage:
    text = (body or '').strip()
    if not text:
        raise PartyError('Xabar bo‘sh')
    if len(text) > 500:
        raise PartyError('Xabar 500 belgidan oshmasin')
    return PartyMessage.objects.create(party=party, user=user, body=text)


def recent_messages(party: WatchParty, request=None, limit=80):
    rows = (
        PartyMessage.objects.filter(party=party)
        .select_related('user')
        .order_by('-created_at')[:limit]
    )
    return [
        {
            'id': row.id,
            'user_id': row.user_id,
            'username': row.user.username,
            'photo': avatar_url(row.user, request),
            'body': row.body,
            'created_at': row.created_at.isoformat(),
        }
        for row in reversed(list(rows))
    ]


def _is_watched_now(party: WatchParty) -> bool:
    if not party.playing:
        return False
    from . import presence
    return bool(presence.members(party.code))


def _mark_closed(party: WatchParty) -> WatchParty:
    party.closed_at = timezone.now()
    party.playing = False
    party.want_playing = False
    party.save(update_fields=['closed_at', 'playing', 'want_playing'])
    notify(party.code, {'type': 'closed', 'party': party_payload(party)})
    return party


def expire_if_idle(party: WatchParty, hours=IDLE_HOURS) -> WatchParty:
    if party.closed_at:
        return party
    stamp = party.clock or party.created_at
    if not stamp:
        return party
    if stamp >= timezone.now() - timedelta(hours=hours):
        return party
    if _is_watched_now(party):
        return party
    return _mark_closed(party)


def prune_idle(hours=IDLE_HOURS):
    cutoff = timezone.now() - timedelta(hours=hours)
    stale = WatchParty.objects.select_related('episode__season__anime', 'host').filter(
        closed_at__isnull=True,
        clock__lt=cutoff,
    )
    closed = []
    for party in stale:
        if _is_watched_now(party):
            continue
        closed.append(_mark_closed(party))
    return closed


def prune_old(hours=IDLE_HOURS):
    return prune_idle(hours)
