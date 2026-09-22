from django.db.models import Count

from apps.episode.models import Episode

from .models import Comment, CommentLike, EpisodeLike
from .profile import avatar_url

MAX_BODY = 2000


class CommentError(ValueError):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.message = message
        self.status = status


def _photo(user, request=None):
    return avatar_url(user, request)


def _author(user, request=None):
    return {
        'username': user.username,
        'photo': _photo(user, request),
    }


def as_dict(row, *, liked=False, likes=0, replies=None, request=None):
    return {
        'id': row.id,
        'body': row.body,
        'parent': row.parent_id,
        'created_at': row.created_at.isoformat() if row.created_at else '',
        'likes': int(likes),
        'liked': bool(liked),
        'user': _author(row.user, request),
        'replies': replies or [],
    }


def _liked_ids(user, comment_ids):
    if not user or not user.is_authenticated or not comment_ids:
        return set()
    return set(
        CommentLike.objects.filter(user=user, comment_id__in=comment_ids)
        .values_list('comment_id', flat=True)
    )


def list_for(episode_id, user=None, request=None):
    if not Episode.objects.filter(pk=episode_id).exists():
        raise CommentError('Qism topilmadi', 404)
    qs = (
        Comment.objects.filter(episode_id=episode_id)
        .select_related('user')
        .annotate(like_n=Count('likes', distinct=True))
    )
    tops = list(qs.filter(parent__isnull=True).order_by('-created_at')[:50])
    top_ids = [row.id for row in tops]
    replies = list(qs.filter(parent_id__in=top_ids).order_by('created_at'))
    liked = _liked_ids(user, top_ids + [row.id for row in replies])
    grouped = {}
    for row in replies:
        grouped.setdefault(row.parent_id, []).append(
            as_dict(row, liked=row.id in liked, likes=row.like_n, request=request)
        )
    results = [
        as_dict(
            row,
            liked=row.id in liked,
            likes=row.like_n,
            replies=grouped.get(row.id, []),
            request=request,
        )
        for row in tops
    ]
    return {
        'count': Comment.objects.filter(episode_id=episode_id, parent__isnull=True).count(),
        'results': results,
    }


def create(user, episode_id, body, parent_id=None, request=None):
    from .moderation import ModerationError, assert_can_comment
    try:
        assert_can_comment(user)
    except ModerationError as exc:
        raise CommentError(exc.message, exc.status) from exc
    text = (body or '').strip()
    if not text:
        raise CommentError('Izoh yozing')
    if len(text) > MAX_BODY:
        raise CommentError('Izoh juda uzun')
    if not Episode.objects.filter(pk=episode_id).exists():
        raise CommentError('Qism topilmadi', 404)
    parent = None
    if parent_id:
        parent = Comment.objects.filter(pk=parent_id, episode_id=episode_id).first()
        if not parent:
            raise CommentError('Izoh topilmadi', 404)
        if parent.parent_id:
            parent = Comment.objects.filter(pk=parent.parent_id).first()
    row = Comment.objects.create(
        user=user,
        episode_id=episode_id,
        parent=parent,
        body=text,
    )
    return as_dict(row, request=request)


def delete(user, comment_id):
    row = Comment.objects.filter(pk=comment_id).first()
    if not row:
        raise CommentError('Izoh topilmadi', 404)
    if row.user_id != user.id and not user.is_staff:
        raise CommentError('O‘chirish mumkin emas', 403)
    row.delete()
    return {'ok': True}


def toggle_comment_like(user, comment_id):
    row = Comment.objects.filter(pk=comment_id).first()
    if not row:
        raise CommentError('Izoh topilmadi', 404)
    existing = CommentLike.objects.filter(user=user, comment=row).first()
    if existing:
        existing.delete()
        liked = False
    else:
        CommentLike.objects.create(user=user, comment=row)
        liked = True
    return {
        'id': row.id,
        'liked': liked,
        'likes': CommentLike.objects.filter(comment=row).count(),
    }


def toggle_episode_like(user, episode_id):
    if not Episode.objects.filter(pk=episode_id).exists():
        raise CommentError('Qism topilmadi', 404)
    existing = EpisodeLike.objects.filter(user=user, episode_id=episode_id).first()
    if existing:
        existing.delete()
        liked = False
    else:
        EpisodeLike.objects.create(user=user, episode_id=episode_id)
        liked = True
    return episode_like_state(episode_id, user)


def episode_like_state(episode_id, user=None):
    liked = False
    if user and user.is_authenticated:
        liked = EpisodeLike.objects.filter(user=user, episode_id=episode_id).exists()
    return {
        'likes': EpisodeLike.objects.filter(episode_id=episode_id).count(),
        'liked': liked,
    }
