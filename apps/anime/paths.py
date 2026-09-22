from django.utils.text import slugify

KIND_PREFIX = {
    'anime': 'anime',
    'drama': 'drama',
    'film': 'kino',
    'serial': 'serial',
}
PREFIX_KIND = {value: key for key, value in KIND_PREFIX.items()}


def kind_prefix(kind: str) -> str:
    return KIND_PREFIX.get(kind) or 'anime'


def unique_slug(title: str, exclude_pk=None) -> str:
    from .models import Anime

    base = slugify(title or '', allow_unicode=True) or 'title'
    base = base[:80].strip('-') or 'title'
    slug = base
    n = 2
    qs = Anime.objects.all()
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)
    while qs.filter(slug=slug).exists():
        slug = f'{base[:70]}-{n}'
        n += 1
    return slug


def ensure_slug(anime) -> str:
    if getattr(anime, 'slug', None):
        return anime.slug
    anime.slug = unique_slug(anime.title, exclude_pk=anime.pk)
    if anime.pk:
        anime.save(update_fields=['slug'])
    return anime.slug


def title_path(anime) -> str:
    slug = ensure_slug(anime)
    return f'/{kind_prefix(anime.kind)}/{slug}/'


def watch_path(episode, party='') -> str:
    anime = episode.season.anime
    slug = ensure_slug(anime)
    prefix = kind_prefix(anime.kind)
    season_n = episode.season.number
    if season_n and season_n != 1:
        path = f'/{prefix}/{slug}/s{season_n}/episode{episode.number}/'
    else:
        path = f'/{prefix}/{slug}/episode{episode.number}/'
    if party:
        path += f'?party={party}'
    return path
