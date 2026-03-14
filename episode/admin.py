from django.contrib import admin
from django.http import JsonResponse
from django.urls import path
from .models import Episode, Video
from anime.models import Season, Anime


class VideoInline(admin.TabularInline):
    model = Video
    extra = 1


@admin.register(Episode)
class EpisodeAdmin(admin.ModelAdmin):
    inlines = [VideoInline]
    list_display = ["__str__", "season", "number"]
    list_filter = ["season__anime"]

    class Media:
        js = ("admin/js/episode_cascade.js",)

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path("get-animes/", self.admin_site.admin_view(self.get_animes)),
            path("seasons-by-anime/<int:anime_id>/", self.admin_site.admin_view(self.seasons_by_anime)),
        ]
        return custom + urls

    def get_animes(self, request):
        animes = Anime.objects.values("id", "title")
        return JsonResponse(list(animes), safe=False)

    def seasons_by_anime(self, request, anime_id):
        seasons = Season.objects.filter(anime_id=anime_id).values("id", "number")
        return JsonResponse(list(seasons), safe=False)


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ["__str__", "language", "translated_by", "created_at"]

    class Media:
        js = ("admin/js/video_cascade.js",)

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path("get-animes/", self.admin_site.admin_view(self.get_animes)),
            path("seasons-by-anime/<int:anime_id>/", self.admin_site.admin_view(self.seasons_by_anime)),
            path("episodes-by-season/<int:season_id>/", self.admin_site.admin_view(self.episodes_by_season)),
        ]
        return custom + urls

    def get_animes(self, request):
        animes = Anime.objects.values("id", "title")
        return JsonResponse(list(animes), safe=False)

    def seasons_by_anime(self, request, anime_id):
        seasons = Season.objects.filter(anime_id=anime_id).values("id", "number")
        return JsonResponse(list(seasons), safe=False)

    def episodes_by_season(self, request, season_id):
        episodes = Episode.objects.filter(season_id=season_id).values("id", "number", "title")
        return JsonResponse(list(episodes), safe=False)