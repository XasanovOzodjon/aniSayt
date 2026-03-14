from django.urls import path
from .views import EpisodeListView, EpisodeDetailView

urlpatterns = [
    path("episodes/", EpisodeListView.as_view()),
    path("episodes/<int:pk>/", EpisodeDetailView.as_view()),
]