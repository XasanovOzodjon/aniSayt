from django.urls import path
from .views import *

urlpatterns = [
    path('search/anime/', AnimeSearchView.as_view(), name='anime-search'),
    path('search/person/', PersonSearchView.as_view(), name='person-search'),
    path('search/', CombinedSearchView.as_view(), name='combined-search'),
    path('search/genres/', GenreListView.as_view(), name='genre-list'),
]