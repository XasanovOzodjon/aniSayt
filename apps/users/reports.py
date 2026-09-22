from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import CustomUser, ProfileReport
from .moderation import REASON_IDS, REASON_LABELS, ModerationError, assert_can_report
from .profile import ProfileError, avatar_url, banner_url

KINDS = {choice.value for choice in ProfileReport.Kind}


class ReportError(ProfileError):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def snapshot_for(user, kind) -> str:
    if kind == ProfileReport.Kind.PHOTO:
        return (avatar_url(user) or '')[:500]
    if kind == ProfileReport.Kind.BANNER:
        return (banner_url(user) or '')[:500]
    if kind == ProfileReport.Kind.NICK:
        name = (user.first_name or '').strip()
        handle = f'@{user.username}'
        return (f'{name} {handle}'.strip() if name else handle)[:500]
    if kind == ProfileReport.Kind.BIO:
        return (user.bio or '')[:500]
    return ''


def as_dict(row) -> dict:
    return {
        'id': row.id,
        'kind': row.kind,
        'reason': row.reason or 'other',
        'reason_label': REASON_LABELS.get(row.reason, row.reason or ''),
        'note': row.note or '',
        'created_at': row.created_at.isoformat() if row.created_at else '',
    }


def file_dict(row) -> dict:
    return {
        **as_dict(row),
        'snapshot': row.snapshot or '',
        'reporter': row.reporter.username,
        'reporter_id': row.reporter_id,
        'target': row.target.username,
        'target_id': row.target_id,
        'resolved': bool(row.resolved_at),
    }


def file_for(reporter, username, kind, reason, note='') -> dict:
    kind = (kind or '').strip()
    reason = (reason or '').strip()
    if kind not in KINDS:
        raise ReportError('Noto‘g‘ri shikoyat turi')
    if reason not in REASON_IDS:
        raise ReportError('Shikoyat sababini tanlang')
    try:
        assert_can_report(reporter)
    except ModerationError as exc:
        raise ReportError(exc.message, exc.status) from exc
    target = CustomUser.objects.filter(username__iexact=username).first()
    if not target:
        raise ReportError('Profil topilmadi', 404)
    if target.pk == reporter.pk:
        raise ReportError('O‘z profilingizni shikoyat qila olmaysiz')
    text = str(note or '').strip()
    if len(text) > 400:
        raise ReportError('Izoh 400 belgidan oshmasin')
    open_same = ProfileReport.objects.filter(
        reporter=reporter,
        target=target,
        kind=kind,
        resolved_at__isnull=True,
    )
    if open_same.exists():
        raise ReportError('Bu shikoyat allaqachon yuborilgan')
    try:
        with transaction.atomic():
            row = ProfileReport.objects.create(
                reporter=reporter,
                target=target,
                kind=kind,
                reason=reason,
                note=text,
                snapshot=snapshot_for(target, kind),
            )
    except IntegrityError as exc:
        raise ReportError('Bu shikoyat allaqachon yuborilgan') from exc
    return as_dict(row)


def list_reports():
    return [
        file_dict(row)
        for row in (
            ProfileReport.objects.select_related('reporter', 'target')
            .order_by('resolved_at', '-created_at')[:200]
        )
    ]


def resolve(pk, *, action='', extra=None) -> dict:
    from . import moderation as mod
    extra = extra or {}
    row = ProfileReport.objects.select_related('reporter', 'target').filter(pk=pk).first()
    if not row:
        raise ReportError('Shikoyat topilmadi', 404)
    try:
        if action == 'clear':
            mod.clear_profile_field(row.target, row.kind, value=extra.get('value'))
        elif action == 'ban':
            mod.ban(
                row.target,
                extra.get('ban_reason') or REASON_LABELS.get(row.reason, row.reason),
                allow_appeal=extra.get('allow_appeal', True),
            )
        elif action == 'warn_reporter':
            mod.warn_reporter(row.reporter)
        elif action == 'mute_reporter':
            mod.mute_reporter(row.reporter)
        elif action and action != 'dismiss':
            raise ReportError('Noto‘g‘ri amal')
    except ModerationError as exc:
        raise ReportError(exc.message, exc.status) from exc
    if not row.resolved_at:
        row.resolved_at = timezone.now()
        row.save(update_fields=['resolved_at'])
    return file_dict(row)
