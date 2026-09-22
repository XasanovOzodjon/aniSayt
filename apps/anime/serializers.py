from rest_framework import serializers
from .models import Anime, Season, Genre
from .paths import title_path
from apps.episode.serializers import EpisodeSerializer


class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ["id", "name"]


class SeasonSerializer(serializers.ModelSerializer):
    episodes = EpisodeSerializer(many=True, read_only=True)

    class Meta:
        model = Season
        fields = ["id", "number", "release_date", "episodes"]


class AnimeSerializer(serializers.ModelSerializer):
    genres = GenreSerializer(many=True, read_only=True)
    seasons = SeasonSerializer(many=True, read_only=True)
    path = serializers.SerializerMethodField()
    next_title = serializers.SerializerMethodField()

    class Meta:
        model = Anime
        fields = [
            "id",
            "title",
            "slug",
            "path",
            "description",
            "poster",
            "genres",
            "seasons",
            "kind",
            "age_rating",
            "next_title",
        ]

    def get_path(self, obj):
        return title_path(obj)

    def get_next_title(self, obj):
        nxt = getattr(obj, 'next_title', None)
        if not nxt:
            return None
        return {
            'id': nxt.id,
            'title': nxt.title,
            'slug': nxt.slug or '',
            'path': title_path(nxt) if nxt.slug else f'/detail/?id={nxt.id}',
            'poster': nxt.poster.url if nxt.poster else '',
            'kind': nxt.kind,
        }
