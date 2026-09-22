from django.urls import path
from .views import (
    RegistarView,
    EmailCheckView,
    GoogleAuthView,
    GoogleACallBackView,
    TelegramAuth,
    AnimeeLoginView,
    MeView,
    MePhotoView,
    MeBannerView,
    TelegramUnlinkView,
    NoticeListView,
    NoticeReadView,
    NoticeReadAllView,
    PublicProfileView,
    PublicProfileReportView,
    BanAppealView,
    UserListView,
    PublicListView,
    ListStatusView,
    ProgressView,
    EpisodeCommentsView,
    CommentDetailView,
    CommentLikeView,
    EpisodeLikeView,
)
from rest_framework_simplejwt.views import (
    TokenRefreshView,
    TokenBlacklistView,
)

urlpatterns = [
    path('registar/', RegistarView.as_view(), name='registar'),
    path('emailcheck/', EmailCheckView.as_view(), name='emailcheck'),
    path('google/', GoogleAuthView.as_view(), name='google'),
    path('googleCallback', GoogleACallBackView.as_view(), name='googleback'),
    
    path('telegram-login/', TelegramAuth.as_view(), name='get-tg'),
    path('telegram-unlink/', TelegramUnlinkView.as_view(), name='auth_telegram_unlink'),
    path('notices/', NoticeListView.as_view(), name='auth_notices'),
    path('notices/read-all/', NoticeReadAllView.as_view(), name='auth_notices_read_all'),
    path('notices/<int:pk>/read/', NoticeReadView.as_view(), name='auth_notice_read'),
    path('me/', MeView.as_view(), name='auth_me'),
    path('me/photo/', MePhotoView.as_view(), name='auth_me_photo'),
    path('me/banner/', MeBannerView.as_view(), name='auth_me_banner'),
    path('u/<str:username>/', PublicProfileView.as_view(), name='auth_public_profile'),
    path('u/<str:username>/report/', PublicProfileReportView.as_view(), name='auth_public_report'),
    path('ban/appeal/', BanAppealView.as_view(), name='auth_ban_appeal'),
    path('u/<str:username>/lists/', PublicListView.as_view(), name='auth_public_lists'),
    path('lists/', UserListView.as_view(), name='auth_lists'),
    path('lists/<int:anime_id>/', ListStatusView.as_view(), name='auth_list_status'),
    path('progress/<int:episode_id>/', ProgressView.as_view(), name='auth_progress'),
    path('episodes/<int:episode_id>/comments/', EpisodeCommentsView.as_view(), name='episode_comments'),
    path('episodes/<int:episode_id>/like/', EpisodeLikeView.as_view(), name='episode_like'),
    path('comments/<int:pk>/', CommentDetailView.as_view(), name='comment_detail'),
    path('comments/<int:pk>/like/', CommentLikeView.as_view(), name='comment_like'),
    path('login/', AnimeeLoginView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', TokenBlacklistView.as_view(), name='token_blacklist'),
    
    
    
]