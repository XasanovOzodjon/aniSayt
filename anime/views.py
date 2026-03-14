from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from .models import Anime, Season, Ganre
from .serializers import AnimeSerializer, SeasonSerializer, GanreSerializer


class AnimeListCreateView(ListCreateAPIView):
    queryset = Anime.objects.all()
    serializer_class = AnimeSerializer


class AnimeDetailView(RetrieveUpdateDestroyAPIView):
    queryset = Anime.objects.all()
    serializer_class = AnimeSerializer


class SeasonListCreateView(ListCreateAPIView):
    queryset = Season.objects.all()
    serializer_class = SeasonSerializer


class SeasonDetailView(RetrieveUpdateDestroyAPIView):
    queryset = Season.objects.all()
    serializer_class = SeasonSerializer


class GanreListCreateView(ListCreateAPIView):
    queryset = Ganre.objects.all()
    serializer_class = GanreSerializer


class GanreDetailView(RetrieveUpdateDestroyAPIView):
    queryset = Ganre.objects.all()
    serializer_class = GanreSerializer