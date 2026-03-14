from rest_framework import serializers
from .models import Anime, Season, Ganre


class GanreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ganre
        fields = "__all__"


class SeasonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Season
        fields = "__all__"


class AnimeSerializer(serializers.ModelSerializer):
    ganres = GanreSerializer(many=True, read_only=True)

    class Meta:
        model = Anime
        fields = "__all__"