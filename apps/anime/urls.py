from django.urls import path
from .views import (
    AnimeListCreateView,
    AnimeDetailView,
    SeasonListCreateView,
    SeasonDetailView,
    GenreListCreateView,
    GenreDetailView,
    LegacyGanresRedirect,
)

urlpatterns = [
    path("anime/", AnimeListCreateView.as_view()),
    path("anime/<int:pk>/", AnimeDetailView.as_view()),
    path("seasons/", SeasonListCreateView.as_view()),
    path("seasons/<int:pk>/", SeasonDetailView.as_view()),
    path("genres/", GenreListCreateView.as_view()),
    path("genres/<int:pk>/", GenreDetailView.as_view()),
    path("ganres/", LegacyGanresRedirect.as_view()),
    path("ganres/<int:pk>/", LegacyGanresRedirect.as_view()),
]
