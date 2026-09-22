from rest_framework.generics import ListAPIView, RetrieveAPIView
from django_filters.rest_framework import DjangoFilterBackend
from .models import Episode
from .serializers import EpisodeSerializer
from drf_spectacular.utils import extend_schema_view, extend_schema


@extend_schema_view(
    get=extend_schema(tags=["Episodes"]),
)
class EpisodeListView(ListAPIView):
    queryset = Episode.objects.select_related("season__anime__next_title")
    serializer_class = EpisodeSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['season']


@extend_schema_view(
    get=extend_schema(tags=["Episodes"]),
)
class EpisodeDetailView(RetrieveAPIView):
    queryset = Episode.objects.select_related("season__anime__next_title").prefetch_related("videos")
    serializer_class = EpisodeSerializer