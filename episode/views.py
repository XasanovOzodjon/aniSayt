from rest_framework.generics import ListAPIView, RetrieveAPIView
from .models import Episode
from .serializers import EpisodeSerializer


class EpisodeListView(ListAPIView):
    queryset = Episode.objects.all()
    serializer_class = EpisodeSerializer


class EpisodeDetailView(RetrieveAPIView):
    queryset = Episode.objects.all()
    serializer_class = EpisodeSerializer