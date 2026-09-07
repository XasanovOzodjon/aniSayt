from rest_framework import serializers
from apps.anime.models import Anime
from apps.anime.serializers import GenreSerializer
from apps.person.models import Person
from drf_spectacular.utils import extend_schema_field


class AnimeSearchSerializer(serializers.ModelSerializer):
    genres = GenreSerializer(many=True, read_only=True)

    class Meta:
        model = Anime
        fields = ["id", "title", "description", "poster", "genres"]


class PersonSearchSerializer(serializers.ModelSerializer):
    anime = serializers.StringRelatedField()
    anime_id = serializers.IntegerField(source="anime.id", read_only=True)

    class Meta:
        model = Person
        fields = ["id", "fullname", "bio", "age", "photo", "rating", "anime", "anime_id"]


class CombinedSearchSerializer(serializers.Serializer):
    animes = AnimeSearchSerializer(many=True)
    persons = PersonSearchSerializer(many=True)
    total = serializers.SerializerMethodField()

    @extend_schema_field(serializers.DictField())
    def get_total(self, obj):
        return {
            "animes": len(obj["animes"]),
            "persons": len(obj["persons"]),
        }
