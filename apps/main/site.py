from django.templatetags.static import static

from .models import SiteSettings

DEFAULT_PLAYER_POSTER = 'img/player-poster.jpg'


class SiteError(ValueError):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.message = message
        self.status = status


def current():
    row, _ = SiteSettings.objects.get_or_create(pk=1)
    return row


def _abs(url, request=None):
    if not url:
        return ''
    if request:
        return request.build_absolute_uri(url)
    return url


def player_poster_url(request=None):
    row = current()
    if row.player_poster:
        from apps.main.object_storage import public_file_url

        url = public_file_url(row.player_poster)
        if url:
            return _abs(url, request)
    return _abs(f'{static(DEFAULT_PLAYER_POSTER)}?v=3', request)


def as_dict(request=None):
    return {'player_poster': player_poster_url(request)}


def set_player_poster(uploaded, request=None):
    if not uploaded:
        raise SiteError('Poster yuklang')
    name = (getattr(uploaded, 'name', '') or '').lower()
    if not name.endswith(('.png', '.jpg', '.jpeg', '.webp', '.gif')):
        raise SiteError('Rasm yuklang')
    row = current()
    if row.player_poster:
        row.player_poster.delete(save=False)
    row.player_poster.save(uploaded.name, uploaded, save=True)
    return as_dict(request)
