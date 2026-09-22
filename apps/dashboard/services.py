from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.text import slugify

from apps.anime.models import Anime, Genre, Season
from apps.anime.paths import title_path, watch_path
from apps.episode.ingest import IngestError, attach_file, get_progress, validate_source_url
from apps.episode.models import Episode, Video
from apps.party.models import WatchParty
from apps.person.models import Person
from apps.users.models import CustomUser, Notice
from apps.users.notices import send_telegram
from apps.users.profile import ProfileError, avatar_url, banner_url, dashboard_flags


class DashError(ValueError):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.message = message
        self.status = status


def media_url(field, request=None):
    from apps.main.object_storage import public_file_url

    url = public_file_url(field)
    if url and request:
        return request.build_absolute_uri(url)
    return url


def stats(request=None):
    today = timezone.now().date()
    open_parties = WatchParty.objects.filter(closed_at__isnull=True)
    admin = bool(request and request.user and request.user.is_staff)
    payload = {
        'anime': Anime.objects.filter(kind=Anime.Kind.ANIME).count(),
        'film': Anime.objects.filter(kind=Anime.Kind.FILM).count(),
        'drama': Anime.objects.filter(kind=Anime.Kind.DRAMA).count(),
        'serial': Anime.objects.filter(kind=Anime.Kind.SERIAL).count(),
        'titles': Anime.objects.count(),
        'episodes': Episode.objects.count(),
        'videos': Video.objects.count(),
        'users': CustomUser.objects.count() if admin else 0,
        'staff': CustomUser.objects.filter(is_staff=True).count() if admin else 0,
        'moderators': CustomUser.objects.filter(is_moderator=True, is_staff=False).count() if admin else 0,
        'genres': Genre.objects.count(),
        'parties_open': open_parties.count() if admin else 0,
        'notices_today': Notice.objects.filter(created_at__date=today).count() if admin else 0,
        'is_admin': admin,
        'recent_anime': [
            catalog_row(row, request)
            for row in Anime.objects.select_related('next_title').prefetch_related('genres').order_by('-id')[:6]
        ],
        'recent_users': [],
        'open_parties': [],
    }
    if admin:
        payload['recent_users'] = [
            user_row(row, request)
            for row in CustomUser.objects.order_by('-id')[:6]
        ]
        payload['open_parties'] = [
            party_row(row)
            for row in open_parties.select_related('episode__season__anime', 'host')[:8]
        ]
    return payload


def catalog_row(anime, request=None, extra=False):
    nxt = getattr(anime, 'next_title', None)
    payload = {
        'id': anime.id,
        'title': anime.title,
        'kind': anime.kind,
        'kind_label': dict(Anime.Kind.choices).get(anime.kind, anime.kind),
        'age_rating': anime.age_rating or '16+',
        'slug': anime.slug or '',
        'path': title_path(anime) if anime.slug else f'/detail/?id={anime.id}',
        'description': anime.description or '',
        'poster': media_url(anime.poster, request),
        'genres': [{'id': g.id, 'name': g.name} for g in anime.genres.all()],
        'seasons_count': getattr(anime, 'season_n', None),
        'episodes_count': getattr(anime, 'ep_n', None),
        'seasonal': anime.is_seasonal(),
        'next_title': None,
    }
    if nxt:
        payload['next_title'] = {
            'id': nxt.id,
            'title': nxt.title,
            'kind': nxt.kind,
            'path': title_path(nxt) if nxt.slug else f'/detail/?id={nxt.id}',
            'poster': media_url(nxt.poster, request),
        }
    if payload['seasons_count'] is None:
        payload['seasons_count'] = anime.seasons.count()
    if payload['episodes_count'] is None:
        payload['episodes_count'] = Episode.objects.filter(season__anime=anime).count()
    if extra:
        seasons = sorted(anime.seasons.all(), key=lambda s: s.number)
        payload['seasons'] = [season_summary(season, request, with_episodes=not anime.is_seasonal()) for season in seasons]
        payload['people'] = [
            person_row(person, request)
            for person in anime.persons.all()
        ]
        if not anime.is_seasonal():
            eps = payload['seasons'][0]['episodes'] if payload['seasons'] else []
            payload['film_episode'] = eps[0] if eps else None
    return payload


def season_summary(season, request=None, with_episodes=False):
    episodes = list(season.episodes.all())
    row = {
        'id': season.id,
        'number': season.number,
        'release_date': season.release_date,
        'episodes_count': len(episodes),
        'episodes': [],
    }
    if with_episodes:
        row['episodes'] = [episode_row(ep, request) for ep in episodes]
    return row


def season_detail(season, request=None):
    anime = season.anime
    return {
        'id': season.id,
        'number': season.number,
        'release_date': season.release_date,
        'anime_id': anime.id,
        'anime_title': anime.title,
        'kind': anime.kind,
        'seasonal': anime.is_seasonal(),
        'path': title_path(anime) if anime.slug else f'/detail/?id={anime.id}',
        'episodes': [episode_row(ep, request) for ep in season.episodes.all()],
    }


def get_season(pk, request=None):
    season = (
        Season.objects.select_related('anime')
        .prefetch_related('episodes__videos')
        .filter(pk=pk)
        .first()
    )
    if not season:
        raise DashError('Sezon topilmadi', 404)
    return season_detail(season, request)


def season_row(season, request=None):
    return {
        'id': season.id,
        'number': season.number,
        'release_date': season.release_date,
        'episodes': [
            episode_row(ep, request)
            for ep in season.episodes.all()
        ],
    }


def video_payload(video):
    if video.ingest_error:
        status = 'error'
    elif video.hls_path:
        status = 'ready'
    elif video.video:
        status = 'processing'
    elif video.source_url:
        status = 'queued'
    else:
        status = 'empty'
    info = get_progress(video.pk)
    progress = 100 if video.hls_path else int(info.get('progress') or 0)
    return {
        'id': video.id,
        'language': video.language,
        'translated_by': video.translated_by,
        'hls_path': video.hls_path,
        'url': video.hls_path,
        'has_file': bool(video.video),
        'source_url': video.source_url,
        'ingest_error': video.ingest_error,
        'status': status,
        'progress': progress,
    }


def episode_row(episode, request=None):
    return {
        'id': episode.id,
        'number': episode.number,
        'title': episode.title,
        'thumbnail': media_url(episode.thumbnail, request),
        'videos': [video_payload(video) for video in episode.videos.all()],
    }


def person_row(person, request=None):
    return {
        'id': person.id,
        'fullname': person.fullname,
        'bio': person.bio or '',
        'age': person.age,
        'photo': media_url(person.photo, request),
        'rating': person.rating,
        'anime_id': person.anime_id,
    }


def user_row(user, request=None, *, detail=False):
    from apps.users.moderation import as_ban, is_banned, locks_dict
    flags = dashboard_flags(user)
    if flags['is_admin']:
        role = 'Admin'
    elif flags['is_moderator']:
        role = 'Moderator'
    else:
        role = 'User'
    try:
        mod = user.moderation
    except ObjectDoesNotExist:
        mod = None
    open_n = getattr(user, 'open_report_n', None)
    if open_n is None:
        open_n = user.profile_reports.filter(resolved_at__isnull=True).count()
    payload = {
        'id': user.pk,
        'username': user.username,
        'first_name': user.first_name or '',
        'email': user.email or '',
        'photo': avatar_url(user, request),
        'banner': banner_url(user, request),
        'bio': user.bio or '',
        'status_line': user.status_line or '',
        'is_admin': flags['is_admin'],
        'is_moderator': flags['is_moderator'],
        'role': role,
        'is_active': bool(user.is_active),
        'telegram': user.telegram_username or '',
        'date_joined': user.date_joined.isoformat() if user.date_joined else '',
        'banned': is_banned(user),
        'ban': as_ban(user),
        'ban_allow_appeal': bool(getattr(mod, 'ban_allow_appeal', True)),
        'locks': locks_dict(user),
        'open_reports': int(open_n or 0),
        'report_strikes': int(getattr(mod, 'report_strikes', 0) or 0),
        'report_muted': bool(mod and mod.report_mute_until),
    }
    if detail:
        from apps.users.reports import file_dict
        payload['reports'] = [
            file_dict(row)
            for row in (
                user.profile_reports.select_related('reporter', 'target')
                .order_by('resolved_at', '-created_at')[:50]
            )
        ]
        payload['filed'] = [
            file_dict(row)
            for row in (
                user.profile_reports_sent.select_related('reporter', 'target')
                .filter(resolved_at__isnull=True)[:20]
            )
        ]
    return payload


def get_user(pk, request=None):
    user = CustomUser.objects.filter(pk=pk).first()
    if not user:
        raise DashError('User topilmadi', 404)
    return user_row(user, request, detail=True)


def party_row(party):
    episode = party.episode
    anime = episode.season.anime
    return {
        'code': party.code,
        'host': party.host.username,
        'anime_title': anime.title,
        'episode': episode.number,
        'episode_id': episode.id,
        'watch_path': watch_path(episode),
        'playing': party.playing,
        'closed': party.closed_at is not None,
        'created_at': party.created_at.isoformat(),
        'invite_url': f'/party/{party.code}/',
    }


def list_catalog(request, q='', kind=''):
    rows = (
        Anime.objects.select_related('next_title')
        .prefetch_related('genres')
        .annotate(season_n=Count('seasons', distinct=True), ep_n=Count('seasons__episodes', distinct=True))
        .order_by('-id')
    )
    if kind:
        if kind not in dict(Anime.Kind.choices):
            raise DashError('Kind noto‘g‘ri')
        rows = rows.filter(kind=kind)
    if q:
        rows = rows.filter(Q(title__icontains=q) | Q(description__icontains=q))
    return [catalog_row(row, request) for row in rows[:80]]


def get_anime(pk, request=None):
    anime = (
        Anime.objects.select_related('next_title')
        .prefetch_related('genres', 'persons', 'seasons__episodes__videos')
        .filter(pk=pk)
        .first()
    )
    if not anime:
        raise DashError('Anime topilmadi', 404)
    return catalog_row(anime, request, extra=True)


def _kind(value):
    if value in dict(Anime.Kind.choices):
        return value
    raise DashError('Kind: anime, kino, drama yoki serial')


def _age(value):
    allowed = {item[0] for item in Anime._meta.get_field('age_rating').choices}
    rating = (value or '16+').strip()
    if rating not in allowed:
        raise DashError('Yosh: 0+, 6+, 12+, 16+ yoki 18+')
    return rating


def create_anime(data, files, request=None):
    title = (data.get('title') or '').strip()
    description = (data.get('description') or '').strip()
    poster = files.get('poster') if files else None
    if not title:
        raise DashError('Nom kerak')
    if not description:
        raise DashError('Tavsif kerak')
    if not poster:
        raise DashError('Poster kerak')
    anime = Anime.objects.create(
        title=title,
        description=description,
        poster=poster,
        kind=_kind(data.get('kind') or Anime.Kind.ANIME),
        age_rating=_age(data.get('age_rating')),
    )
    _set_genres(anime, data.get('genres'))
    if anime.kind == Anime.Kind.FILM:
        season = Season.objects.create(
            anime=anime,
            number=1,
            release_date=timezone.now().year,
        )
        Episode.objects.create(season=season, number=1, title=title)
    return get_anime(anime.pk, request)


def update_anime(pk, data, request=None):
    anime = Anime.objects.filter(pk=pk).first()
    if not anime:
        raise DashError('Anime topilmadi', 404)
    if 'title' in data and data['title'] is not None:
        title = str(data['title']).strip()
        if not title:
            raise DashError('Nom bo‘sh')
        anime.title = title
    if 'description' in data and data['description'] is not None:
        anime.description = str(data['description']).strip()
    if 'kind' in data and data['kind'] is not None:
        anime.kind = _kind(data['kind'])
    if 'age_rating' in data and data['age_rating'] is not None:
        anime.age_rating = _age(data['age_rating'])
    if 'next_title_id' in data:
        _set_next_title(anime, data.get('next_title_id'))
    anime.save()
    if 'genres' in data:
        _set_genres(anime, data.get('genres'))
    return get_anime(anime.pk, request)


def set_poster(pk, uploaded, request=None):
    anime = Anime.objects.filter(pk=pk).first()
    if not anime:
        raise DashError('Anime topilmadi', 404)
    if not uploaded:
        raise DashError('Poster kerak')
    anime.poster = uploaded
    anime.save(update_fields=['poster'])
    return get_anime(anime.pk, request)


def delete_anime(pk):
    anime = Anime.objects.filter(pk=pk).first()
    if not anime:
        raise DashError('Anime topilmadi', 404)
    anime.delete()


def _set_next_title(anime, raw):
    if anime.kind != Anime.Kind.FILM:
        if raw not in (None, '', 0, '0'):
            raise DashError('Keyingi nom faqat kino uchun')
        anime.next_title = None
        return
    if raw in (None, '', 0, '0'):
        anime.next_title = None
        return
    try:
        pk = int(raw)
    except (TypeError, ValueError):
        raise DashError('Keyingi kino noto‘g‘ri')
    if pk == anime.pk:
        raise DashError('Kino o‘ziga ulanmaydi')
    nxt = Anime.objects.filter(pk=pk, kind=Anime.Kind.FILM).first()
    if not nxt:
        raise DashError('Keyingi kino topilmadi')
    anime.next_title = nxt


def _set_genres(anime, raw):
    ids = _id_list(raw)
    anime.genres.set(Genre.objects.filter(pk__in=ids))


def _id_list(raw):
    if raw is None or raw == '':
        return []
    if isinstance(raw, list):
        values = raw
    else:
        values = str(raw).split(',')
    ids = []
    for item in values:
        try:
            ids.append(int(item))
        except (TypeError, ValueError):
            continue
    return ids


def add_season(anime_id, data, request=None):
    anime = Anime.objects.filter(pk=anime_id).first()
    if not anime:
        raise DashError('Anime topilmadi', 404)
    if not anime.is_seasonal():
        raise DashError('Kinoda sezon yo‘q. Har bir kino alohida yaratiladi')
    try:
        number = int(data.get('number'))
        year = int(data.get('release_date') or timezone.now().year)
    except (TypeError, ValueError):
        raise DashError('Sezon raqami kerak')
    if Season.objects.filter(anime=anime, number=number).exists():
        raise DashError('Bu sezon allaqachon bor')
    season = Season.objects.create(anime=anime, number=number, release_date=year)
    return get_season(season.pk, request)


def update_season(pk, data, request=None):
    season = Season.objects.select_related('anime').filter(pk=pk).first()
    if not season:
        raise DashError('Sezon topilmadi', 404)
    if 'number' in data and data['number'] is not None:
        season.number = int(data['number'])
    if 'release_date' in data and data['release_date'] is not None:
        season.release_date = int(data['release_date'])
    season.save()
    return get_season(season.pk, request)


def delete_season(pk, request=None):
    season = Season.objects.select_related('anime').filter(pk=pk).first()
    if not season:
        raise DashError('Sezon topilmadi', 404)
    if not season.anime.is_seasonal():
        raise DashError('Kino sezonini o‘chirib bo‘lmaydi')
    anime_id = season.anime_id
    season.delete()
    return get_anime(anime_id, request)


def add_episode(season_id, data, request=None):
    season = Season.objects.select_related('anime').filter(pk=season_id).first()
    if not season:
        raise DashError('Sezon topilmadi', 404)
    if not season.anime.is_seasonal():
        raise DashError('Kinoda qism yo‘q. Tarjima Master sifatida qo‘shiladi')
    try:
        number = int(data.get('number'))
    except (TypeError, ValueError):
        raise DashError('Qism raqami kerak')
    title = (data.get('title') or f'{number}-qism').strip()
    if Episode.objects.filter(season=season, number=number).exists():
        raise DashError('Bu qism allaqachon bor')
    Episode.objects.create(season=season, number=number, title=title)
    return get_season(season.pk, request)


def update_episode(pk, data, files=None, request=None):
    episode = Episode.objects.select_related('season').filter(pk=pk).first()
    if not episode:
        raise DashError('Qism topilmadi', 404)
    if 'number' in data and data['number'] is not None:
        episode.number = int(data['number'])
    if 'title' in data and data['title'] is not None:
        episode.title = str(data['title']).strip() or episode.title
    if files and files.get('thumbnail'):
        episode.thumbnail = files.get('thumbnail')
    episode.save()
    return get_season(episode.season_id, request)


def delete_episode(pk, request=None):
    episode = Episode.objects.select_related('season__anime').filter(pk=pk).first()
    if not episode:
        raise DashError('Qism topilmadi', 404)
    if not episode.season.anime.is_seasonal():
        raise DashError('Kino qismini o‘chirib bo‘lmaydi')
    season_id = episode.season_id
    episode.delete()
    return get_season(season_id, request)


def get_episode(pk, request=None):
    episode = (
        Episode.objects.select_related('season__anime')
        .prefetch_related('videos')
        .filter(pk=pk)
        .first()
    )
    if not episode:
        raise DashError('Qism topilmadi', 404)
    row = episode_row(episode, request)
    row['season_id'] = episode.season_id
    row['season_number'] = episode.season.number
    row['anime_id'] = episode.season.anime_id
    row['anime_title'] = episode.season.anime.title
    row['kind'] = episode.season.anime.kind
    return row


def add_video(episode_id, data, files=None, request=None):
    episode = Episode.objects.select_related('season').filter(pk=episode_id).first()
    if not episode:
        raise DashError('Qism topilmadi', 404)
    language = (data.get('language') or 'uz').strip()[:50]
    uploaded = files.get('video') if files else None
    source_url = (data.get('source_url') or data.get('video_url') or '').strip()
    if data.get('hls_path'):
        raise DashError('HLS yo‘lini yozmang. Video fayl yoki video havolasini yuboring')
    video = Video(
        episode=episode,
        language=language,
        translated_by=(data.get('translated_by') or '').strip()[:120],
    )
    try:
        if uploaded:
            attach_file(video, uploaded=uploaded, source_url='')
        elif source_url:
            validate_source_url(source_url)
            video.source_url = source_url
            if settings.TESTING:
                attach_file(video, source_url=source_url)
        else:
            raise IngestError('Video fayl yoki internetdagi video havolasi kerak')
    except IngestError as exc:
        raise DashError(exc.message) from exc
    video.save()
    return get_anime(episode.season.anime_id, request)


def update_video(pk, data, request=None):
    video = Video.objects.select_related('episode__season').filter(pk=pk).first()
    if not video:
        raise DashError('Video topilmadi', 404)
    if 'language' in data and data['language'] is not None:
        video.language = str(data['language']).strip()[:50]
    if 'translated_by' in data and data['translated_by'] is not None:
        video.translated_by = str(data['translated_by']).strip()[:120]
    video.save()
    return get_anime(video.episode.season.anime_id, request)


def delete_video(pk, request=None):
    video = Video.objects.select_related('episode__season').filter(pk=pk).first()
    if not video:
        raise DashError('Video topilmadi', 404)
    anime_id = video.episode.season.anime_id
    video.delete()
    return get_anime(anime_id, request)


def list_genres():
    return [{'id': g.id, 'name': g.name, 'slug': g.slug or ''} for g in Genre.objects.order_by('name')]


def save_genre(data, pk=None):
    name = (data.get('name') or '').strip()
    if not name:
        raise DashError('Janr nomi kerak')
    slug = slugify(name) or 'janr'
    base = slug
    n = 2
    while Genre.objects.filter(slug=slug).exclude(pk=pk or 0).exists():
        slug = f'{base}-{n}'
        n += 1
    if pk:
        genre = Genre.objects.filter(pk=pk).first()
        if not genre:
            raise DashError('Janr topilmadi', 404)
        genre.name = name
        genre.slug = slug
        genre.save()
        return {'id': genre.id, 'name': genre.name, 'slug': genre.slug}
    genre = Genre.objects.create(name=name, slug=slug)
    return {'id': genre.id, 'name': genre.name, 'slug': genre.slug}


def delete_genre(pk):
    genre = Genre.objects.filter(pk=pk).first()
    if not genre:
        raise DashError('Janr topilmadi', 404)
    genre.delete()


def add_person(data, files, request=None):
    anime = Anime.objects.filter(pk=data.get('anime')).first()
    if not anime:
        raise DashError('Anime topilmadi', 404)
    fullname = (data.get('fullname') or '').strip()
    if not fullname:
        raise DashError('Ism kerak')
    photo = files.get('photo') if files else None
    if not photo:
        raise DashError('Rasm kerak')
    Person.objects.create(
        anime=anime,
        fullname=fullname,
        bio=(data.get('bio') or '').strip(),
        age=str(data.get('age') or '0')[:3],
        photo=photo,
    )
    return get_anime(anime.pk, request)


def delete_person(pk, request=None):
    person = Person.objects.filter(pk=pk).first()
    if not person:
        raise DashError('Odam topilmadi', 404)
    anime_id = person.anime_id
    person.delete()
    return get_anime(anime_id, request)


def list_users(request, q=''):
    rows = CustomUser.objects.annotate(
        open_report_n=Count(
            'profile_reports',
            filter=Q(profile_reports__resolved_at__isnull=True),
        )
    ).order_by('-id')
    if q:
        rows = rows.filter(
            Q(username__icontains=q) | Q(email__icontains=q) | Q(telegram_username__icontains=q)
        )
    return [user_row(row, request) for row in rows[:80]]


def update_user(pk, data, actor):
    user = CustomUser.objects.filter(pk=pk).first()
    if not user:
        raise DashError('User topilmadi', 404)
    if user.pk == actor.pk and data.get('is_admin') is False:
        raise DashError('O‘zingizni Admin qatoridan chiqara olmaysiz')
    if user.pk == actor.pk and data.get('is_moderator') is False and data.get('is_admin') is False:
        raise DashError('O‘zingizni rolni olib tashlay olmaysiz')
    if user.pk == actor.pk and data.get('is_active') is False:
        raise DashError('O‘zingizni o‘chira olmaysiz')
    if 'is_admin' in data and data['is_admin'] is not None:
        user.is_staff = bool(data['is_admin'])
        if user.is_staff:
            user.is_superuser = True
            user.is_moderator = False
        else:
            user.is_superuser = False
    if 'is_moderator' in data and data['is_moderator'] is not None:
        if user.is_staff and bool(data['is_moderator']) and data.get('is_admin') is not False:
            raise DashError('Adminni Moderator qilish uchun avval Adminni oling')
        user.is_moderator = bool(data['is_moderator'])
        if user.is_moderator:
            user.is_staff = False
            user.is_superuser = False
    if 'is_active' in data and data['is_active'] is not None:
        user.is_active = bool(data['is_active'])
    from apps.users import moderation as mod
    from apps.users.moderation import ModerationError
    try:
        if data.get('unban'):
            mod.unban(user)
        elif data.get('ban'):
            ban = data['ban'] if isinstance(data['ban'], dict) else {}
            until = None
            raw_until = ban.get('until')
            if raw_until:
                from django.utils.dateparse import parse_datetime
                until = parse_datetime(str(raw_until))
            mod.ban(
                user,
                ban.get('reason') or data.get('ban_reason') or 'Qoidabuzarlik',
                allow_appeal=ban.get('allow_appeal', data.get('allow_appeal', True)),
                until=until,
            )
        if data.get('locks') and isinstance(data['locks'], dict):
            mod.set_locks(user, data['locks'])
        if data.get('clear'):
            mod.clear_profile_field(user, data['clear'], value=data.get('value'))
        if data.get('set') and isinstance(data['set'], dict):
            mod.set_profile_field(user, data['set'])
        if data.get('warn_reporter'):
            mod.warn_reporter(user)
        if data.get('mute_reporter'):
            mod.mute_reporter(user)
    except (ModerationError, ProfileError) as exc:
        raise DashError(exc.message, getattr(exc, 'status', 400)) from exc
    user.save()
    return user_row(user)


def broadcast_news(title, body, anime_id=None):
    title = (title or '').strip()
    body = (body or '').strip()
    if not title or not body:
        raise DashError('Sarlavha va matn kerak')
    anime = None
    if anime_id:
        anime = Anime.objects.filter(pk=anime_id).first()
        if not anime:
            raise DashError('Anime topilmadi', 404)
    users = CustomUser.objects.all()
    sent = 0
    tg = 0
    text = f'Animee\n{title}\n{body}'
    for user in users.iterator():
        notice = Notice.objects.create(
            user=user,
            anime=anime,
            kind=Notice.Kind.NEWS,
            title=title,
            body=body,
        )
        sent += 1
        if user.telegram_id and user.notify_telegram:
            notice.sent_telegram = send_telegram(user.telegram_id, text)
            notice.save(update_fields=['sent_telegram'])
            if notice.sent_telegram:
                tg += 1
    return {'sent': sent, 'telegram': tg}


def list_parties():
    from apps.party import services as party_services

    party_services.prune_idle()
    rows = WatchParty.objects.select_related('episode__season__anime', 'host').order_by('-created_at')[:60]
    return [party_row(row) for row in rows]


def close_party(code):
    from apps.party import services as party_services

    party = WatchParty.objects.filter(code=code, closed_at__isnull=True).first()
    if not party:
        raise DashError('Xona topilmadi', 404)
    party.closed_at = timezone.now()
    party.playing = False
    party.want_playing = False
    party.save(update_fields=['closed_at', 'playing', 'want_playing'])
    party_services.notify(code, {'type': 'closed', 'party': party_services.party_payload(party)})
    return party_row(party)


def advance_party(code):
    from apps.party import services as party_services

    party = WatchParty.objects.select_related('episode__season__anime', 'host').filter(
        code=code, closed_at__isnull=True,
    ).first()
    if not party:
        raise DashError('Xona topilmadi', 404)
    nxt = party_services.next_episode(party.episode)
    if not nxt:
        raise DashError('Keyingi qism yo‘q')
    party = party_services.set_episode(party, nxt)
    payload = party_services.party_payload(party)
    party_services.notify(code, {'type': 'episode', 'party': payload})
    return party_row(party)
