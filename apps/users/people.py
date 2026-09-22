from django.db.models import Q

from .models import CustomUser
from .profile import avatar_url


def search_public(q, request=None, limit=8):
    needle = (q or '').strip()
    if len(needle) < 2:
        return []
    rows = (
        CustomUser.objects.filter(is_active=True, public_profile=True)
        .filter(Q(username__icontains=needle) | Q(first_name__icontains=needle))
        .order_by('username')[:limit]
    )
    return [
        {
            'username': user.username,
            'first_name': user.first_name or '',
            'photo': avatar_url(user, request),
        }
        for user in rows
    ]
