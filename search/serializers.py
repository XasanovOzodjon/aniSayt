from rest_framework import serializers
from anime.models import Anime, Ganre
from person.models import Person


class GanreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ganre
        fields = ["id", "name"]


class AnimeSearchSerializer(serializers.ModelSerializer):
    ganres = GanreSerializer(many=True, read_only=True)

    class Meta:
        model = Anime
        fields = ["id", "title", "discription", "poster", "release_year", "ganres"]


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

    def get_total(self, obj):
        return {
            "animes": len(obj["animes"]),
            "persons": len(obj["persons"]),
        }