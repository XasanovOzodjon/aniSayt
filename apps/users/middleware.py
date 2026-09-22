from django.http import JsonResponse

from core.auth import SoftJWTAuthentication

from .moderation import as_ban, is_banned


class BanGateMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.auth = SoftJWTAuthentication()

    def __call__(self, request):
        path = request.path
        if self._is_api(path) and not self._allowed(path, request.method):
            user = self._user(request)
            if user and is_banned(user):
                payload = as_ban(user) or {}
                return JsonResponse(
                    {
                        'code': 'banned',
                        'message': 'Hisobingiz bloklangan',
                        **payload,
                    },
                    status=403,
                )
        return self.get_response(request)

    def _is_api(self, path):
        return path.startswith('/uz/api/') or path.startswith('/api/')

    def _allowed(self, path, method):
        method = (method or 'GET').upper()
        if path.endswith('/auth/me/') and method == 'GET':
            return True
        if path.endswith('/auth/ban/appeal/') and method == 'POST':
            return True
        if path.endswith('/auth/logout/') or path.endswith('/auth/token/refresh/'):
            return True
        if '/auth/login/' in path or '/auth/registar/' in path or '/auth/emailcheck/' in path:
            return True
        if '/auth/google' in path or '/auth/telegram-login/' in path:
            return True
        return False

    def _user(self, request):
        try:
            result = self.auth.authenticate(request)
        except Exception:
            return None
        if not result:
            return None
        return result[0]
