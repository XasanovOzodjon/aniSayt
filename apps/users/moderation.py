from datetime import timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import Comment, Notice, UnbanRequest, UserModeration
from .profile import ProfileError, clear_avatar, clear_banner, validate_username

MUTE_DAYS = 7

REASONS = (
    ('insult', 'Haqorat / Trolling'),
    ('racism', 'Irqchilik'),
    ('hate', 'Nafrat nutqi'),
    ('threat', 'Zo‘ravonlik tahdidi'),
    ('harassment', 'Jinsiy ta’qib'),
    ('porn', 'Pornografiya'),
    ('spam', 'Spam'),
    ('scam', 'Firibgarlik'),
    ('impersonation', 'Soxtalik'),
    ('other', 'Boshqa'),
)
REASON_IDS = {item[0] for item in REASONS}
REASON_LABELS = dict(REASONS)


class ModerationError(ProfileError):
    def __init__(self, message, status=400, payload=None):
        super().__init__(message)
        self.status = status
        self.payload = payload or {}


def _mod_or_none(user):
    try:
        return user.moderation
    except (AttributeError, UserModeration.DoesNotExist):
        return None


def get_mod(user) -> UserModeration:
    row, _ = UserModeration.objects.get_or_create(user=user)
    return row


def locks_dict(user) -> dict:
    row = _mod_or_none(user)
    empty = {
        'username': False,
        'photo': False,
        'photo_keep': False,
        'banner': False,
        'banner_keep': False,
        'bio': False,
        'bio_keep': False,
        'comments': False,
    }
    if not row:
        return empty
    return {
        'username': bool(row.lock_username),
        'photo': bool(row.lock_photo),
        'photo_keep': bool(row.keep_photo),
        'banner': bool(row.lock_banner),
        'banner_keep': bool(row.keep_banner),
        'bio': bool(row.lock_bio),
        'bio_keep': bool(row.keep_bio),
        'comments': bool(row.lock_comments),
    }


def is_banned(user) -> bool:
    if not user or not getattr(user, 'is_authenticated', True):
        return False
    if getattr(user, 'is_staff', False):
        return False
    row = _mod_or_none(user)
    if row is None:
        return False
    if not row.banned_at:
        return False
    if row.banned_until and row.banned_until <= timezone.now():
        return False
    return True


def as_ban(user) -> dict | None:
    if not is_banned(user):
        return None
    row = user.moderation
    pending = UnbanRequest.objects.filter(user=user, resolved_at__isnull=True).exists()
    return {
        'reason': row.ban_reason or 'Qoidabuzarlik',
        'allow_appeal': bool(row.ban_allow_appeal) and not pending,
        'appealed': pending,
        'until': row.banned_until.isoformat() if row.banned_until else '',
    }


def can_report(user) -> bool:
    if is_banned(user):
        return False
    row = _mod_or_none(user)
    if not row or not row.report_mute_until:
        return True
    return row.report_mute_until <= timezone.now()


def assert_can_report(user):
    if not can_report(user):
        until = getattr(_mod_or_none(user), 'report_mute_until', None)
        raise ModerationError(
            'Shikoyat yuborish vaqtincha yopiq. Noto‘g‘ri shikoyat uchun ogohlantirilgansiz.',
            payload={'until': until.isoformat() if until else ''},
        )


def assert_can_comment(user):
    if is_banned(user):
        raise ModerationError('Hisobingiz bloklangan', 403, as_ban(user) or {})
    if locks_dict(user)['comments']:
        raise ModerationError('Izoh yozish sizga yopiq')


def assert_can_edit(user, field, *, clearing=False):
    locks = locks_dict(user)
    if field == 'username' and locks['username']:
        raise ModerationError('Username o‘zgartirish yopiq')
    if field == 'photo' and (locks['photo'] if not clearing else locks['photo_keep'] or locks['photo']):
        raise ModerationError('Profil rasmini o‘zgartirish yopiq' if not clearing else 'Profil rasmini olib tashlash yopiq')
    if field == 'banner' and (locks['banner'] if not clearing else locks['banner_keep'] or locks['banner']):
        raise ModerationError('Bannerni o‘zgartirish yopiq' if not clearing else 'Bannerni olib tashlash yopiq')
    if field == 'bio' and (locks['bio'] if not clearing else locks['bio_keep'] or locks['bio']):
        raise ModerationError('Tavsifni o‘zgartirish yopiq' if not clearing else 'Tavsifni olib tashlash yopiq')
    if field == 'nick' and locks['username']:
        raise ModerationError('Nick o‘zgartirish yopiq')


def notify(user, title, body):
    from .notices import send_telegram
    notice = Notice.objects.create(
        user=user,
        kind=Notice.Kind.MODERATION,
        title=title,
        body=body,
    )
    if user.telegram_id and user.notify_telegram:
        notice.sent_telegram = send_telegram(user.telegram_id, f'Animee\n{title}\n{body}')
        notice.save(update_fields=['sent_telegram'])
    return notice


def ban(user, reason, *, allow_appeal=True, until=None):
    if getattr(user, 'is_staff', False):
        raise ModerationError('Adminni ban qilib bo‘lmaydi')
    row = get_mod(user)
    row.banned_at = timezone.now()
    row.banned_until = until
    row.ban_reason = (reason or 'Qoidabuzarlik').strip()[:400]
    row.ban_allow_appeal = bool(allow_appeal)
    row.save()
    if not row.ban_allow_appeal:
        UnbanRequest.objects.filter(user=user, resolved_at__isnull=True).update(
            resolved_at=timezone.now(),
            accepted=False,
        )
    notify(user, 'Hisob bloklandi', row.ban_reason)
    return as_ban(user)


def unban(user):
    row = get_mod(user)
    row.banned_at = None
    row.banned_until = None
    row.ban_reason = ''
    row.save(update_fields=['banned_at', 'banned_until', 'ban_reason'])
    UnbanRequest.objects.filter(user=user, resolved_at__isnull=True).update(
        resolved_at=timezone.now(),
        accepted=True,
    )
    notify(user, 'Ban olib tashlandi', 'Hisobingiz yana ochiq.')
    return True


def appeal(user, body):
    if not is_banned(user):
        raise ModerationError('Ban yo‘q')
    row = user.moderation
    if not row.ban_allow_appeal:
        raise ModerationError('Bu banda so‘rov yuborib bo‘lmaydi')
    text = (body or '').strip()
    if len(text) < 8:
        raise ModerationError('So‘rovni yozing')
    if len(text) > 800:
        raise ModerationError('So‘rov juda uzun')
    if UnbanRequest.objects.filter(user=user, resolved_at__isnull=True).exists():
        raise ModerationError('So‘rov allaqachon yuborilgan')
    try:
        with transaction.atomic():
            UnbanRequest.objects.create(user=user, body=text)
    except IntegrityError as exc:
        raise ModerationError('So‘rov allaqachon yuborilgan') from exc
    return {'ok': True, 'appealed': True}


def list_appeals():
    rows = UnbanRequest.objects.select_related('user').order_by('resolved_at', '-created_at')[:100]
    return [
        {
            'id': row.id,
            'user_id': row.user_id,
            'username': row.user.username,
            'body': row.body,
            'created_at': row.created_at.isoformat(),
            'resolved': bool(row.resolved_at),
            'accepted': row.accepted,
            'reason': getattr(_mod_or_none(row.user), 'ban_reason', '') or '',
        }
        for row in rows
    ]


def resolve_appeal(pk, accepted):
    row = UnbanRequest.objects.select_related('user').filter(pk=pk).first()
    if not row:
        raise ModerationError('So‘rov topilmadi', 404)
    if not row.resolved_at:
        row.resolved_at = timezone.now()
        row.accepted = bool(accepted)
        row.save(update_fields=['resolved_at', 'accepted'])
        if row.accepted:
            unban(row.user)
        else:
            notify(row.user, 'So‘rov rad etildi', 'Ban olib tashlanmadi.')
    return {'id': row.id, 'accepted': row.accepted, 'resolved': True}


def set_locks(user, data: dict) -> dict:
    row = get_mod(user)
    mapping = {
        'username': 'lock_username',
        'photo': 'lock_photo',
        'photo_keep': 'keep_photo',
        'banner': 'lock_banner',
        'banner_keep': 'keep_banner',
        'bio': 'lock_bio',
        'bio_keep': 'keep_bio',
        'comments': 'lock_comments',
    }
    fields = []
    for key, attr in mapping.items():
        if key in data and data[key] is not None:
            setattr(row, attr, bool(data[key]))
            fields.append(attr)
    if fields:
        row.save(update_fields=fields)
    return locks_dict(user)


def warn_reporter(user):
    row = get_mod(user)
    row.report_strikes = int(row.report_strikes or 0) + 1
    if row.report_strikes >= 2:
        row.report_mute_until = timezone.now() + timedelta(days=MUTE_DAYS)
        row.save(update_fields=['report_strikes', 'report_mute_until'])
        notify(
            user,
            'Shikoyat yuborish yopildi',
            f'Noto‘g‘ri shikoyatlar uchun {MUTE_DAYS} kunga shikoyat yuborish yopildi.',
        )
        return {'strikes': row.report_strikes, 'muted': True}
    row.save(update_fields=['report_strikes'])
    notify(
        user,
        'Ogohlantirish: noto‘g‘ri shikoyat',
        'Shikoyatingiz asossiz deb topildi. Yana takrorlasangiz, shikoyat yuborish vaqtincha yopiladi.',
    )
    return {'strikes': row.report_strikes, 'muted': False}


def mute_reporter(user, days=MUTE_DAYS):
    row = get_mod(user)
    row.report_mute_until = timezone.now() + timedelta(days=int(days) or MUTE_DAYS)
    row.report_strikes = max(int(row.report_strikes or 0), 2)
    row.save(update_fields=['report_mute_until', 'report_strikes'])
    notify(user, 'Shikoyat yuborish yopildi', f'{days} kunga shikoyat yubora olmaysiz.')
    return {'muted': True}


def clear_profile_field(user, kind, *, value=None):
    kind = (kind or '').strip()
    if kind == 'photo':
        clear_avatar(user)
        notify(user, 'Profil rasmi olib tashlandi', 'Moderator profil rasmingizni olib tashladi.')
        return 'photo'
    if kind == 'banner':
        clear_banner(user)
        notify(user, 'Banner olib tashlandi', 'Moderator banneringizni olib tashladi.')
        return 'banner'
    if kind == 'bio':
        user.bio = (value or '').strip()[:280]
        user.save(update_fields=['bio'])
        notify(
            user,
            'Tavsif o‘zgartirildi' if value else 'Tavsif olib tashlandi',
            'Moderator profilingiz tavsifini yangiladi.' if value else 'Moderator tavsifni olib tashladi.',
        )
        return 'bio'
    if kind == 'nick':
        if value:
            name = str(value).strip()
            if name.startswith('@') or '.' in name or '_' in name:
                try:
                    user.username = validate_username(name.lstrip('@'), exclude_pk=user.pk)
                except ProfileError:
                    user.first_name = name[:80]
            else:
                user.first_name = name[:80]
            user.save()
            notify(user, 'Nick o‘zgartirildi', 'Moderator nick yoki username ni yangiladi.')
        else:
            user.first_name = ''
            user.save(update_fields=['first_name'])
            notify(user, 'Nick olib tashlandi', 'Moderator ko‘rinadigan ismni olib tashladi.')
        return 'nick'
    if kind == 'comments':
        Comment.objects.filter(user=user).delete()
        notify(user, 'Izohlar o‘chirildi', 'Moderator izohlaringizni olib tashladi.')
        return 'comments'
    raise ModerationError('Noto‘g‘ri maydon')


def set_profile_field(user, data: dict):
    changed = []
    if data.get('username'):
        user.username = validate_username(data['username'], exclude_pk=user.pk)
        changed.append('username')
    if 'first_name' in data and data['first_name'] is not None:
        user.first_name = str(data['first_name']).strip()[:80]
        changed.append('nick')
    if 'bio' in data and data['bio'] is not None:
        user.bio = str(data['bio']).strip()[:280]
        changed.append('bio')
    if changed:
        user.save()
        notify(user, 'Profil o‘zgartirildi', 'Moderator profilingizni yangiladi.')
    return changed
