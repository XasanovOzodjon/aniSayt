from django.urls import path
from .views import *

urlpatterns = [
    path("anime/", AnimeListCreateView.as_view()),
    path("anime/<int:pk>/", AnimeDetailView.as_view()),

    path("seasons/", SeasonListCreateView.as_view()),
    path("seasons/<int:pk>/", SeasonDetailView.as_view()),

    path("ganres/", GanreListCreateView.as_view()),
    path("ganres/<int:pk>/", GanreDetailView.as_view()),
]