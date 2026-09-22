from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.i18n import i18n_patterns

from apps.main.media import serve_media
from apps.users.views import GoogleACallBackView

admin.site.site_header = 'Animee'
admin.site.site_title = 'Animee'
admin.site.index_title = ''

urlpatterns = [
    path('admin/', admin.site.urls),
    path('media/<path:path>', serve_media),
    path('api/auth/googleCallback', GoogleACallBackView.as_view(), name='googleback_plain'),
    path("", include("apps.main.urls")),
]

if settings.DEBUG:
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns
    from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
    urlpatterns += [
        path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
        path('api/schema/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
        path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    ]
    urlpatterns += staticfiles_urlpatterns()

urlpatterns += i18n_patterns(
    path("api/", include("apps.anime.urls")),
    path("api/", include("apps.episode.urls")),
    path("api/", include("apps.search.urls")),
    path("api/", include("apps.person.urls")),
    path("api/auth/", include("apps.users.urls")),
    path("api/", include("apps.party.urls")),
    path("api/dashboard/", include("apps.dashboard.urls")),
)
