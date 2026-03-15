from rest_framework import serializers
from .models import Anime, Season, Ganre
from episode.serializers import EpisodeSerializer


class GanreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ganre
        fields = ["id", "name"]


class SeasonSerializer(serializers.ModelSerializer):
    episodes = EpisodeSerializer(many=True, read_only=True)
    
    class Meta:
        model = Season
        fields = ["id", "number", "release_date", "episodes"]


class AnimeSerializer(serializers.ModelSerializer):
    ganres = GanreSerializer(many=True, read_only=True)
    seasons = SeasonSerializer(many=True, read_only=True)

    class Meta:
        model = Anime
        fields = ["id", "title", "description", "poster", "ganres", "seasons"]