from django.urls import path

from . import views

urlpatterns = [
    path('stats/', views.StatsView.as_view(), name='dash_stats'),
    path('catalog/', views.CatalogView.as_view(), name='dash_catalog'),
    path('catalog/<int:pk>/', views.CatalogDetailView.as_view(), name='dash_catalog_detail'),
    path('catalog/<int:pk>/poster/', views.PosterView.as_view(), name='dash_poster'),
    path('catalog/<int:pk>/seasons/', views.SeasonCreateView.as_view(), name='dash_seasons'),
    path('seasons/<int:pk>/', views.SeasonDetailView.as_view(), name='dash_season'),
    path('seasons/<int:pk>/episodes/', views.EpisodeCreateView.as_view(), name='dash_episodes'),
    path('episodes/<int:pk>/', views.EpisodeDetailView.as_view(), name='dash_episode'),
    path('episodes/<int:pk>/videos/', views.VideoCreateView.as_view(), name='dash_videos'),
    path('videos/<int:pk>/', views.VideoDetailView.as_view(), name='dash_video'),
    path('videos/<int:pk>/chunk/', views.VideoChunkView.as_view(), name='dash_video_chunk'),
    path('videos/<int:pk>/complete/', views.VideoCompleteView.as_view(), name='dash_video_complete'),
    path('genres/', views.GenreView.as_view(), name='dash_genres'),
    path('genres/<int:pk>/', views.GenreDetailView.as_view(), name='dash_genre'),
    path('people/', views.PersonCreateView.as_view(), name='dash_people'),
    path('people/<int:pk>/', views.PersonDetailView.as_view(), name='dash_person'),
    path('users/', views.UsersView.as_view(), name='dash_users'),
    path('users/<int:pk>/', views.UserDetailView.as_view(), name='dash_user'),
    path('notices/', views.NoticeBroadcastView.as_view(), name='dash_notices'),
    path('parties/', views.PartiesView.as_view(), name='dash_parties'),
    path('parties/<str:code>/', views.PartyCloseView.as_view(), name='dash_party'),
    path('player-poster/', views.PlayerPosterView.as_view(), name='dash_player_poster'),
    path('reports/', views.ReportsView.as_view(), name='dash_reports'),
    path('reports/<int:pk>/', views.ReportDetailView.as_view(), name='dash_report'),
    path('appeals/', views.AppealsView.as_view(), name='dash_appeals'),
    path('appeals/<int:pk>/', views.AppealDetailView.as_view(), name='dash_appeal'),
]
