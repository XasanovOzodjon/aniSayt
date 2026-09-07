from rest_framework import serializers
from .models import Anime, Season, Genre
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

    class Meta:
        model = Anime
        fields = ["id", "title", "description", "poster", "genres", "seasons"]
