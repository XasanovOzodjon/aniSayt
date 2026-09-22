from rest_framework import serializers
from .models import Episode, Video
from apps.anime.paths import watch_path


def _file_url(field):
    if not field:
        return ''
    try:
        return field.url or ''
    except ValueError:
        return ''


class VideoSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = Video
        fields = [
            "id",
            "language",
            "translated_by",
            "hls_path",
            "url",
        ]

    def get_url(self, obj):
        return obj.hls_path or _file_url(obj.video)


class EpisodeSerializer(serializers.ModelSerializer):
    videos = VideoSerializer(many=True, read_only=True)
    season = serializers.IntegerField(source="season_id", read_only=True)
    anime_id = serializers.IntegerField(source="season.anime_id", read_only=True)
    anime_title = serializers.CharField(source="season.anime.title", read_only=True)
    anime_poster = serializers.ImageField(source="season.anime.poster", read_only=True)
    anime_kind = serializers.CharField(source="season.anime.kind", read_only=True)
    age_rating = serializers.CharField(source="season.anime.age_rating", read_only=True)
    anime_slug = serializers.CharField(source="season.anime.slug", read_only=True)
    season_number = serializers.IntegerField(source="season.number", read_only=True)
    thumbnail = serializers.SerializerMethodField()
    hls_url = serializers.SerializerMethodField()
    video_url = serializers.SerializerMethodField()
    watch_path = serializers.SerializerMethodField()
    next_watch_path = serializers.SerializerMethodField()

    class Meta:
        model = Episode
        fields = [
            "id",
            "number",
            "title",
            "thumbnail",
            "videos",
            "season",
            "season_number",
            "anime_id",
            "anime_title",
            "anime_slug",
            "anime_poster",
            "anime_kind",
            "age_rating",
            "hls_url",
            "video_url",
            "watch_path",
            "next_watch_path",
        ]

    def _abs(self, url):
        request = self.context.get('request')
        if url and request:
            return request.build_absolute_uri(url)
        return url

    def get_thumbnail(self, obj):
        return self._abs(_file_url(obj.thumbnail) or _file_url(obj.season.anime.poster))

    def _first_video(self, obj):
        videos = list(obj.videos.all())
        return videos[0] if videos else None

    def get_hls_url(self, obj):
        video = self._first_video(obj)
        return (video.hls_path if video else '') or ''

    def get_video_url(self, obj):
        video = self._first_video(obj)
        if not video:
            return ''
        return video.hls_path or _file_url(video.video)

    def get_watch_path(self, obj):
        return watch_path(obj)

    def get_next_watch_path(self, obj):
        anime = obj.season.anime
        nxt = getattr(anime, 'next_title', None)
        if not nxt or anime.kind != 'film':
            return ''
        sequel = (
            Episode.objects.filter(season__anime=nxt)
            .select_related('season__anime')
            .order_by('season__number', 'number')
            .first()
        )
        return watch_path(sequel) if sequel else ''
