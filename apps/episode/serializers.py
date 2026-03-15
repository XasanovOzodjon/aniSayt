from rest_framework import serializers
from .models import Episode, Video


class VideoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Video
        fields = [
            "id",
            "language",
            "translated_by",
            "hls_path",
        ]


class EpisodeSerializer(serializers.ModelSerializer):
    videos = VideoSerializer(many=True, read_only=True)

    class Meta:
        model = Episode
        fields = [
            "id",
            "number",
            "title",
            "thumbnail",
            "videos",
        ]