from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken
from django.contrib.auth import get_user_model


@database_sync_to_async
def _user_from_token(raw):
    if not raw:
        return AnonymousUser()
    try:
        token = AccessToken(raw)
        user = get_user_model().objects.filter(pk=token['user_id']).first()
        return user or AnonymousUser()
    except Exception:
        return AnonymousUser()


class JwtAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        query = parse_qs((scope.get('query_string') or b'').decode())
        raw = (query.get('token') or [None])[0]
        scope['user'] = await _user_from_token(raw)
        return await super().__call__(scope, receive, send)
