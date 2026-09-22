from django.urls import path

from .views import (
    index, catalog, detail, player, title_page, watch_page, auth, profile, settings_page,
    notices_page, public_profile, party_lobby, party_join, dashboard_page, lists_page,
    banned_page,
)

urlpatterns = [
    path("", index, name="index"),
    path("catalog/", catalog, name="catalog"),
    path("detail/", detail, name="detail"),
    path("player/", player, name="player"),
    path("party/", party_lobby, name="party_lobby"),
    path("party/<str:code>/", party_join, name="party_join"),
    path("dashboard/", dashboard_page, name="dashboard"),
    path("auth/", auth, name="auth"),
    path("profile/", profile, name="profile"),
    path("lists/", lists_page, name="lists"),
    path("settings/", settings_page, name="settings"),
    path("notices/", notices_page, name="notices"),
    path("banned/", banned_page, name="banned"),
    path("u/<str:username>/", public_profile, name="public_profile"),
    path("<str:kind>/<str:slug>/s<int:season>/episode<int:number>/", watch_page, name="watch_season"),
    path("<str:kind>/<str:slug>/episode<int:number>/", watch_page, name="watch"),
    path("<str:kind>/<str:slug>/", title_page, name="title"),
]