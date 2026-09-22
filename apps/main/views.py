import json

from django.http import Http404
from django.shortcuts import redirect, render

from apps.anime.models import Anime
from apps.anime.paths import PREFIX_KIND, kind_prefix, title_path, watch_path
from apps.episode.models import Episode
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
    return render(request, "index.html")

def catalog(request):
    return render(request, "catalog.html")


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