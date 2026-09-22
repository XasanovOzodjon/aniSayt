from django.views.generic import RedirectView
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from .models import Anime, Season, Genre
from .serializers import AnimeSerializer, SeasonSerializer, GenreSerializer
from drf_spectacular.utils import extend_schema_view, extend_schema


@extend_schema_view(
    get=extend_schema(tags=["Anime"]),
)
class AnimeListCreateView(ListAPIView):
    queryset = Anime.objects.select_related('next_title').prefetch_related("genres", "seasons__episodes")
    serializer_class = AnimeSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['genres', 'kind']
    search_fields = ['title', 'description', 'slug']
    ordering_fields = ['id', 'title']
    ordering = ['-id']


@extend_schema_view(
    get=extend_schema(tags=["Anime"]),
)
class AnimeDetailView(RetrieveAPIView):
    queryset = Anime.objects.select_related('next_title').prefetch_related("genres", "seasons__episodes")
    serializer_class = AnimeSerializer


@extend_schema_view(
    get=extend_schema(tags=["Seasons"]),
)
class SeasonListCreateView(ListAPIView):
    queryset = Season.objects.all()
    serializer_class = SeasonSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['anime']


@extend_schema_view(
    get=extend_schema(tags=["Seasons"]),
)
class SeasonDetailView(RetrieveAPIView):
    queryset = Season.objects.all()
    serializer_class = SeasonSerializer


@extend_schema_view(
    get=extend_schema(tags=["Genres"]),
)
class GenreListCreateView(ListAPIView):
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer


@extend_schema_view(
    get=extend_schema(tags=["Genres"]),
)
class GenreDetailView(RetrieveAPIView):
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer


class LegacyGanresRedirect(RedirectView):
    permanent = True
    query_string = True

    def get_redirect_url(self, *args, **kwargs):
        lang = getattr(self.request, "LANGUAGE_CODE", "uz")
        pk = kwargs.get("pk")
        if pk:
            return f"/{lang}/api/genres/{pk}/"
        return f"/{lang}/api/genres/"
