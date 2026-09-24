import json

from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render

from apps.anime.models import Anime
from apps.anime.paths import PREFIX_KIND, kind_prefix, title_path, watch_path
from apps.episode.models import Episode
from apps.main import seo
from apps.main.object_storage import public_file_url
from apps.main.site import player_poster_url


def _player_ctx(request, **extra):
    poster = player_poster_url(request)
    return {
        'player_poster': poster,
        'site_json': json.dumps({'player_poster': poster}),
        **extra,
    }


def index(request):
    return render(request, "index.html", seo.page_ctx(
        request,
        seo.HOME_TITLE,
        canonical_path='/',
        extra_json=[seo.nav_json_ld()],
    ))


def catalog(request, kind=None):
    hub = seo.hub_for(kind or '')
    if kind and hub is None:
        raise Http404()
    if hub is None:
        hub = seo.HUBS[0]
    return render(request, "catalog.html", {
        'catalog_hub': hub,
        'catalog_kind': hub['kind'],
        **seo.page_ctx(request, hub['title'], canonical_path=hub['path']),
    })


def robots_txt(request):
    origin = seo.site_origin()
    body = (
        'User-agent: *\n'
        'Allow: /\n'
        'Disallow: /dashboard/\n'
        'Disallow: /admin/\n'
        'Disallow: /api/\n'
        'Disallow: /auth/\n'
        'Disallow: /settings/\n'
        'Disallow: /profile/\n'
        'Disallow: /lists/\n'
        'Disallow: /notices/\n'
        'Disallow: /banned/\n'
        'Disallow: /party/\n'
        '\n'
        f'Sitemap: {origin}/sitemap.xml\n'
    )
    return HttpResponse(body, content_type='text/plain; charset=utf-8')


def sitemap_xml(request):
    origin = seo.site_origin()
    paths = ['/'] + [row['path'] for row in seo.HUBS]
    seen = set(paths)
    for anime in Anime.objects.only('slug', 'kind').order_by('-id')[:2000]:
        path = title_path(anime)
        if path not in seen:
            seen.add(path)
            paths.append(path)
    locs = ''.join(f'  <url><loc>{origin}{path}</loc></url>\n' for path in paths)
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f'{locs}'
        '</urlset>\n'
    )
    return HttpResponse(body, content_type='application/xml; charset=utf-8')


def opensearch_xml(request):
    origin = seo.site_origin()
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<OpenSearchDescription xmlns="http://a9.com/-/spec/opensearch/1.1/">\n'
        '  <ShortName>Animee</ShortName>\n'
        '  <Description>Animee.uz qidiruv</Description>\n'
        '  <InputEncoding>UTF-8</InputEncoding>\n'
        f'  <Url type="text/html" method="get" template="{origin}/catalog/?q={{searchTerms}}"/>\n'
        '</OpenSearchDescription>\n'
    )
    return HttpResponse(body, content_type='application/opensearchdescription+xml; charset=utf-8')


def _title_json(anime):
    return json.dumps({
        'id': anime.id,
        'slug': anime.slug,
        'kind': anime.kind,
        'path': title_path(anime),
    })


def detail(request):
    pk = request.GET.get('id')
    if pk:
        anime = Anime.objects.filter(pk=pk).first()
        if anime:
            return redirect(title_path(anime))
    return redirect('catalog')


def title_page(request, kind, slug):
    model_kind = PREFIX_KIND.get(kind)
    anime = Anime.objects.filter(slug=slug).first()
    if not anime:
        raise Http404()
    if not model_kind or kind_prefix(anime.kind) != kind:
        return redirect(title_path(anime))
    return render(request, "detail.html", {
        'anime_id': anime.id,
        'title_json': _title_json(anime),
    })


def player(request):
    ep_id = request.GET.get('episode')
    if ep_id:
        episode = (
            Episode.objects.select_related('season__anime')
            .filter(pk=ep_id)
            .first()
        )
        if episode:
            return redirect(watch_path(episode, party=request.GET.get('party') or ''))
    return render(request, "player.html", _player_ctx(request, party_code=request.GET.get("party") or ""))


def watch_page(request, kind, slug, number, season=None):
    model_kind = PREFIX_KIND.get(kind)
    anime = Anime.objects.filter(slug=slug).first()
    if not anime:
        raise Http404()
    if not model_kind or kind_prefix(anime.kind) != kind:
        episode = _find_episode(anime, number, season)
        if episode:
            return redirect(watch_path(episode, party=request.GET.get('party') or ''))
        return redirect(title_path(anime))
    episode = _find_episode(anime, number, season)
    if not episode:
        raise Http404()
    canonical = watch_path(episode)
    if season is None and episode.season.number != 1:
        return redirect(watch_path(episode, party=request.GET.get('party') or ''))
    party = request.GET.get("party") or ""
    return render(request, "player.html", _player_ctx(
        request,
        party_code=party,
        episode_id=episode.id,
        watch_json=json.dumps({
            'episode_id': episode.id,
            'watch_path': canonical,
        }),
    ))


def _find_episode(anime, number, season=None):
    qs = Episode.objects.select_related('season__anime').filter(
        season__anime=anime,
        number=number,
    )
    if season is not None:
        qs = qs.filter(season__number=season)
    return qs.order_by('season__number').first()


def party_lobby(request):
    return render(request, "party.html")


def party_join(request, code):
    return render(request, "party-invite.html", {'party_code': code})

def dashboard_page(request):
    return render(request, "dashboard.html")


def auth(request):
    slides = []
    catalog = (
        Anime.objects.exclude(poster="")
        .prefetch_related("genres", "seasons")
        .order_by("-id")[:8]
    )
    for anime in catalog:
        url = public_file_url(anime.poster)
        if not url:
            continue
        years = [s.release_date for s in anime.seasons.all() if s.release_date]
        slides.append({
            "title": anime.title,
            "poster": url,
            "genres": " · ".join(g.name for g in list(anime.genres.all())[:2]),
            "year": max(years) if years else "",
        })
    return render(request, "auth.html", {"slides": slides})

def profile(request):
    return render(request, "profile.html")


def lists_page(request):
    return render(request, "lists.html")

def settings_page(request):
    return render(request, "settings.html")


def notices_page(request):
    return render(request, "notices.html")


def banned_page(request):
    return render(request, "banned.html")

def public_profile(request, username):
    return render(request, "profile.html", {"profile_username": username})