from rest_framework.generics import ListAPIView, RetrieveAPIView
from .models import Anime, Season, Ganre
from .serializers import AnimeSerializer, SeasonSerializer, GanreSerializer


class AnimeListCreateView(ListAPIView):
    queryset = Anime.objects.all()
    serializer_class = AnimeSerializer


class AnimeDetailView(RetrieveAPIView):
    queryset = Anime.objects.all()
    serializer_class = AnimeSerializer


class SeasonListCreateView(ListAPIView):
    queryset = Season.objects.all()
    serializer_class = SeasonSerializer


class SeasonDetailView(RetrieveAPIView):
    queryset = Season.objects.all()
    serializer_class = SeasonSerializer


class GanreListCreateView(ListAPIView):
    queryset = Ganre.objects.all()
    serializer_class = GanreSerializer


class GanreDetailView(RetrieveAPIView):
    queryset = Ganre.objects.all()
    serializer_class = GanreSerializer