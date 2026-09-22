import re
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.validators import URLValidator
from PIL import Image

from apps.main.object_storage import public_file_url

CustomUser = get_user_model()

RESERVED_USERNAMES = frozenset({
    'admin', 'api', 'auth', 'catalog', 'detail', 'player', 'profile', 'settings',
    'me', 'u', 'static', 'media', 'login', 'register', 'animee', 'root',
    'party', 'notices', 'dashboard', 'lists',
    'support', 'moderator', 'null', 'undefined',
})

USERNAME_RE = re.compile(r'^[A-Za-z0-9._-]{3,30}$')
PHOTO_VALIDATOR = URLValidator(schemes=['http', 'https'])


class ProfileError(ValueError):
    def __init__(self, message):
        super().__init__(message)
        self.message = message


def is_username_taken(name, exclude_pk=None) -> bool:
    if (name or '').lower() in RESERVED_USERNAMES:
        return True
    qs = CustomUser.objects.filter(username__iexact=name)
    if exclude_pk is not None:
        qs = qs.exclude(pk=exclude_pk)
    return qs.exists()


def validate_username(name, exclude_pk=None) -> str:
    username = (name or '').strip()
    if not USERNAME_RE.match(username):
        raise ProfileError('Username 3–30 belgi: harf, raqam, nuqta, _ yoki -')
    if is_username_taken(username, exclude_pk=exclude_pk):
        raise ProfileError('Bu username band')
    return username


def avatar_url(user, request=None) -> str:
    photo = getattr(user, 'photo', None)
    if photo:
        url = public_file_url(photo)
        if url and request:
            return request.build_absolute_uri(url)
        if url:
            return url
    return user.photo_url or ''


def banner_url(user, request=None) -> str:
    banner = getattr(user, 'banner', None)
    if not banner:
        return ''
    url = public_file_url(banner)
    if url and request:
        return request.build_absolute_uri(url)
    return url or ''


def _open_image(uploaded, limit_mb):
    if not uploaded:
        raise ProfileError('Rasm tanlang')
    if uploaded.size > limit_mb * 1024 * 1024:
        raise ProfileError(f'Rasm {limit_mb} MB dan oshmasin')
    try:
        image = Image.open(uploaded)
        image.load()
    except Exception as exc:
        raise ProfileError('Rasm ochilmadi. JPG, PNG yoki WEBP yuboring.') from exc
    return image.convert('RGB')


def save_avatar(user, uploaded):
    image = _open_image(uploaded, 2)
    side = min(image.size)
    left = (image.width - side) // 2
    top = (image.height - side) // 2
    image = image.crop((left, top, left + side, top + side))
    image.thumbnail((512, 512))
    buf = BytesIO()
    image.save(buf, format='JPEG', quality=88)
    if user.photo:
        user.photo.delete(save=False)
    user.photo.save(f'{user.pk}.jpg', ContentFile(buf.getvalue()), save=True)
    return user


def clear_avatar(user):
    if user.photo:
        user.photo.delete(save=False)
        user.photo = None
    user.photo_url = ''
    user.save(update_fields=['photo', 'photo_url'])
    return user


def save_banner(user, uploaded):
    image = _open_image(uploaded, 4)
    target_w, target_h = 1600, 480
    w, h = image.size
    scale = max(target_w / max(w, 1), target_h / max(h, 1))
    nw, nh = max(int(w * scale), target_w), max(int(h * scale), target_h)
    image = image.resize((nw, nh), Image.LANCZOS)
    left = (nw - target_w) // 2
    top = (nh - target_h) // 2
    image = image.crop((left, top, left + target_w, top + target_h))
    buf = BytesIO()
    image.save(buf, format='JPEG', quality=86)
    if user.banner:
        user.banner.delete(save=False)
    user.banner.save(f'{user.pk}.jpg', ContentFile(buf.getvalue()), save=True)
    return user


def clear_banner(user):
    if user.banner:
        user.banner.delete(save=False)
        user.banner = None
        user.save(update_fields=['banner'])
    return user


def _streak_payload(user, owner=False) -> dict:
    from .streak import as_dict
    data = as_dict(user)
    if not owner:
        data = {**data, 'today': True if data.get('current') else bool(data.get('today'))}
    return data


def display_role(user) -> str:
    if getattr(user, 'is_staff', False):
        return 'Admin'
    if getattr(user, 'is_moderator', False):
        return 'Moderator'
    return 'User'


def profile_stats(user) -> dict:
    from django.utils import timezone
    from .models import Comment, Progress

    joined = user.date_joined
    days = 0
    if joined:
        days = max(0, (timezone.now().date() - joined.date()).days)
    return {
        'joined_at': joined.isoformat() if joined else '',
        'days_with_us': days,
        'comments': Comment.objects.filter(user=user).count(),
        'episodes_watched': Progress.objects.filter(user=user).count(),
        'last_login': user.last_login.isoformat() if user.last_login else '',
    }


def public_payload(user, *, owner=False, request=None):
    payload = {
        'username': user.username,
        'first_name': user.first_name or '',
        'photo': avatar_url(user, request),
        'banner': banner_url(user, request),
        'bio': user.bio or '',
        'status_line': user.status_line or '',
        'show_watching': bool(user.show_watching),
        'public_profile': bool(user.public_profile),
        'role': display_role(user),
        'stats': profile_stats(user),
        'streak': _streak_payload(user, owner=owner),
    }
    if owner:
        payload.update({
            'email': user.email or '',
            'last_name': user.last_name or '',
            'preferred_audio': user.preferred_audio or 'uz',
            'preferred_subs': user.preferred_subs or 'uz',
            'autoplay_next': bool(user.autoplay_next),
            'telegram_linked': bool(user.telegram_id),
            'telegram_username': user.telegram_username or '',
            'notify_telegram': bool(user.notify_telegram),
            'notify_new_season': bool(user.notify_new_season),
            'notify_new_episode': bool(user.notify_new_episode),
            **dashboard_flags(user),
        })
        from .moderation import as_ban, can_report, locks_dict
        banned = as_ban(user)
        if banned:
            payload['banned'] = banned
        payload['locks'] = locks_dict(user)
        payload['can_report'] = can_report(user)
    return payload


def dashboard_flags(user) -> dict:
    is_admin = bool(getattr(user, 'is_staff', False))
    is_moderator = bool(getattr(user, 'is_moderator', False))
    return {
        'is_admin': is_admin,
        'is_moderator': is_moderator,
        'can_dashboard': is_admin or is_moderator,
    }


def apply_settings(user, data: dict):
    from .moderation import assert_can_edit
    if 'username' in data and data['username'] is not None:
        new_name = (data['username'] or '').strip()
        if new_name != user.username:
            assert_can_edit(user, 'username')
            user.username = validate_username(new_name, exclude_pk=user.pk)

    if 'first_name' in data and data['first_name'] is not None:
        name = str(data['first_name']).strip()
        if len(name) > 80:
            raise ProfileError('Ism 80 belgidan oshmasin')
        if name != (user.first_name or ''):
            assert_can_edit(user, 'nick')
        user.first_name = name

    if 'bio' in data and data['bio'] is not None:
        bio = str(data['bio']).strip()
        if len(bio) > 280:
            raise ProfileError('Bio 280 belgidan oshmasin')
        if bio != (user.bio or ''):
            assert_can_edit(user, 'bio', clearing=not bio)
        user.bio = bio

    if 'status_line' in data and data['status_line'] is not None:
        line = str(data['status_line']).strip()
        if len(line) > 80:
            raise ProfileError('Status 80 belgidan oshmasin')
        user.status_line = line

    if 'show_watching' in data and data['show_watching'] is not None:
        user.show_watching = bool(data['show_watching'])

    if 'photo' in data and data['photo'] is not None:
        photo = str(data['photo']).strip()
        if photo:
            try:
                PHOTO_VALIDATOR(photo)
            except ValidationError as exc:
                raise ProfileError('Rasm havolasi noto‘g‘ri') from exc
            if len(photo) > 500:
                raise ProfileError('Rasm havolasi juda uzun')
            user.photo_url = photo
        else:
            user.photo_url = ''

    if 'preferred_audio' in data and data['preferred_audio'] is not None:
        audio = str(data['preferred_audio']).lower()
        if audio not in ('uz', 'ru'):
            raise ProfileError('Til faqat uz yoki ru')
        user.preferred_audio = audio

    if 'autoplay_next' in data and data['autoplay_next'] is not None:
        user.autoplay_next = bool(data['autoplay_next'])

    if 'public_profile' in data and data['public_profile'] is not None:
        user.public_profile = bool(data['public_profile'])

    if 'preferred_subs' in data and data['preferred_subs'] is not None:
        subs = str(data['preferred_subs']).lower()
        if subs not in ('uz', 'ru', 'off'):
            raise ProfileError('Subtitle faqat uz, ru yoki off')
        user.preferred_subs = subs

    if 'notify_telegram' in data and data['notify_telegram'] is not None:
        user.notify_telegram = bool(data['notify_telegram'])
    if 'notify_new_season' in data and data['notify_new_season'] is not None:
        user.notify_new_season = bool(data['notify_new_season'])
    if 'notify_new_episode' in data and data['notify_new_episode'] is not None:
        user.notify_new_episode = bool(data['notify_new_episode'])

    user.save()
    return user
