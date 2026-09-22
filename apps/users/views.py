from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.views import TokenObtainPairView
from django.core.cache import cache
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.shortcuts import redirect
from django.urls import reverse
from urllib.parse import urlencode
from .emailService import send_email, check_email_pincode
from .auth_services import GoogleAuthService
from rest_framework.permissions import AllowAny, IsAuthenticated
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers

from rest_framework.parsers import FormParser, MultiPartParser

CustomUser = get_user_model()

from .serializers import (
    RegistarSerializer,
    EmailCheckSerializer,
    GetUIDSerializer,
    AnimeeTokenObtainPairSerializer,
    ProfileUpdateSerializer,
    ListWriteSerializer,
    UserListSerializer,
)
from .profile import ProfileError, apply_settings, public_payload, validate_username, save_avatar, clear_avatar, save_banner, clear_banner
from . import lists as title_lists
from . import telegram as telegram_sessions
from . import notices as inbox
from . import progress as watch_progress
from .progress import ProgressError
from . import comments as talk
from .comments import CommentError
from . import reports as profile_reports
from .reports import ReportError
from . import moderation as user_mod
from .moderation import ModerationError


def _public_user(user, *, owner=False, request=None):
    return public_payload(user, owner=owner, request=request)


def _mod_fail(exc):
    payload = {'message': exc.message}
    extra = getattr(exc, 'payload', None)
    if extra:
        payload.update(extra)
    return Response(payload, status=getattr(exc, 'status', 400))


class RegistarView(APIView):
    serializer_class = RegistarSerializer
    permission_classes = [AllowAny]

    @extend_schema(tags=["Auth"])
    def post(self, request: Request) -> Response:
        serializer = RegistarSerializer(data=request.data)

        if serializer.is_valid(raise_exception=True):
            validated_data = serializer.validated_data

            try:
                validate_username(validated_data['username'])
            except ProfileError as exc:
                return Response(
                    {'message': exc.message},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if CustomUser.objects.filter(email__iexact=validated_data['email']).exists():
                return Response(
                    {'message': 'Bu email ruyxatdan utgan'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            try:
                uid = send_email(validated_data)
            except Exception:
                return Response(
                    {'message': 'Kod yuborilmadi. Keyinroq urinib ko‘ring.'},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )
            return Response({
                'uid': uid,
                'message': 'Emailga tasdiqlash kodi yuborildi',
            })


class EmailCheckView(APIView):
    serializer_class = EmailCheckSerializer
    permission_classes = [AllowAny]

    @extend_schema(tags=["Auth"])
    def post(self, request: Request) -> Response:
        serializer = EmailCheckSerializer(data=request.data)

        if serializer.is_valid(raise_exception=True):
            data = check_email_pincode(**serializer.validated_data)

            match data:
                case 404:
                    return Response({'message': 'Kod topilmadi'}, status=status.HTTP_404_NOT_FOUND)
                case 408:
                    return Response({'message': 'Kod muddati o‘tgan'}, status=status.HTTP_408_REQUEST_TIMEOUT)
                case 401:
                    return Response({'message': 'Kod noto‘g‘ri'}, status=status.HTTP_401_UNAUTHORIZED)
                case 400:
                    return Response({'message': 'Bad request'}, status=status.HTTP_400_BAD_REQUEST)

            user = CustomUser(
                username=data['username'],
                email=data['email'],
                password=data['password'],
            )
            try:
                user.save()
            except IntegrityError:
                return Response(
                    {'message': 'Bu email ruyxatdan utgan'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            tokens = GoogleAuthService.get_token(user)
            tokens.update(_public_user(user, owner=True, request=request))
            return Response(tokens, status=status.HTTP_201_CREATED)


class GoogleAuthView(APIView):
    serializer_class = None
    permission_classes = [AllowAny]
    @extend_schema(
        tags=["Auth"],
        responses={200: inline_serializer(
            name="GoogleAuthResponse",
            fields={
                "message": serializers.CharField(),
                "google_auth_link": serializers.URLField(),
            },
        )},
    )
    def post(self, request: Request) -> Response:
        url = GoogleAuthService.generate_google_auth_url()
        return Response(
            {
                'message': 'google orqali auth qilish uchun link',
                'google_auth_link': url
            }
        )


class TelegramAuth(APIView):
    serializer_class = GetUIDSerializer
    permission_classes = [AllowAny]

    @extend_schema(tags=["Auth"])
    def get(self, request: Request) -> Response:
        purpose = request.query_params.get('purpose') or 'login'
        if purpose == 'link':
            if not request.user.is_authenticated:
                return Response({'message': 'Avval kiring'}, status=status.HTTP_401_UNAUTHORIZED)
            unic_id, tg_url = telegram_sessions.begin_link(request.user)
        else:
            unic_id, tg_url = telegram_sessions.begin_login()
        return Response({'tg_url': tg_url, 'unicID': unic_id})

    @extend_schema(tags=["Auth"])
    def post(self, request: Request) -> Response:
        serializer = GetUIDSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        unic_id = serializer.validated_data['unicID']
        data = telegram_sessions.poll_session(unic_id)
        status_name = data.get('status')
        if status_name == 'expired':
            return Response({'status': 'expired', 'message': 'Havola eskirgan'}, status=status.HTTP_400_BAD_REQUEST)
        if status_name == 'error':
            return Response(data, status=status.HTTP_400_BAD_REQUEST)
        if status_name == 'pending':
            return Response({'status': 'pending'})
        if status_name == 'linked':
            payload = _public_user(request.user, owner=True, request=request) if request.user.is_authenticated else {}
            payload.update(data)
            return Response(payload)
        return Response(data)



class GoogleACallBackView(APIView):
    permission_classes = [AllowAny]
    @extend_schema(
        tags=["Auth"],
        parameters=[],
        responses={302: None},
        description="Google OAuth2 callback. Redirects with tokens as URL params.",
    )
    def get(self, request: Request) -> Response:
        code = request.query_params.get('code')
        if code is None:
            return redirect('/auth/?google_auth=error')

        tokens = GoogleAuthService.login_by_google(code)

        if not tokens:
            return redirect('/auth/?google_auth=error')

        user = tokens['user']
        params = urlencode({
            'access': tokens.get('access', ''),
            'refresh': tokens.get('refresh', ''),
            'google_auth': 'success',
            'username': user.username,
            'photo': user.photo_url or '',
            'email': user.email or '',
        })
        return redirect(f"{reverse('profile')}?{params}")


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Auth"])
    def get(self, request: Request) -> Response:
        return Response(_public_user(request.user, owner=True, request=request))

    @extend_schema(tags=["Auth"])
    def patch(self, request: Request) -> Response:
        serializer = ProfileUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            user = apply_settings(request.user, serializer.validated_data)
        except ProfileError as exc:
            return _mod_fail(exc)
        except IntegrityError:
            return Response({'message': 'Bu username band'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(_public_user(user, owner=True, request=request))


class MePhotoView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(tags=["Auth"])
    def post(self, request: Request) -> Response:
        uploaded = request.FILES.get('photo')
        try:
            user_mod.assert_can_edit(request.user, 'photo')
            user = save_avatar(request.user, uploaded)
        except ProfileError as exc:
            return _mod_fail(exc)
        return Response(_public_user(user, owner=True, request=request))

    @extend_schema(tags=["Auth"])
    def delete(self, request: Request) -> Response:
        try:
            user_mod.assert_can_edit(request.user, 'photo', clearing=True)
            user = clear_avatar(request.user)
        except ProfileError as exc:
            return _mod_fail(exc)
        return Response(_public_user(user, owner=True, request=request))


class MeBannerView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(tags=["Auth"])
    def post(self, request: Request) -> Response:
        uploaded = request.FILES.get('banner') or request.FILES.get('photo')
        try:
            user_mod.assert_can_edit(request.user, 'banner')
            user = save_banner(request.user, uploaded)
        except ProfileError as exc:
            return _mod_fail(exc)
        return Response(_public_user(user, owner=True, request=request))

    @extend_schema(tags=["Auth"])
    def delete(self, request: Request) -> Response:
        try:
            user_mod.assert_can_edit(request.user, 'banner', clearing=True)
            user = clear_banner(request.user)
        except ProfileError as exc:
            return _mod_fail(exc)
        return Response(_public_user(user, owner=True, request=request))


class TelegramUnlinkView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Auth"])
    def post(self, request: Request) -> Response:
        user = telegram_sessions.unlink_telegram(request.user)
        return Response(_public_user(user, owner=True, request=request))


class NoticeListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Auth"])
    def get(self, request: Request) -> Response:
        unread_only = request.query_params.get('unread') in ('1', 'true')
        try:
            limit = min(int(request.query_params.get('limit') or 50), 100)
        except (TypeError, ValueError):
            limit = 50
        rows = inbox.queryset_for(request.user, unread_only=unread_only)[:limit]
        return Response({
            'unread_count': inbox.unread_count_for(request.user),
            'results': [inbox.notice_dict(row, request) for row in rows],
        })


class NoticeReadView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Auth"])
    def post(self, request: Request, pk: int) -> Response:
        notice = inbox.mark_read(request.user, pk)
        if not notice:
            return Response({'message': 'Xabar topilmadi'}, status=status.HTTP_404_NOT_FOUND)
        return Response({
            'unread_count': inbox.unread_count_for(request.user),
            'notice': inbox.notice_dict(notice, request),
        })


class NoticeReadAllView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Auth"])
    def post(self, request: Request) -> Response:
        inbox.mark_all_read(request.user)
        return Response({'unread_count': 0})


class PublicProfileView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(tags=["Auth"])
    def get(self, request: Request, username: str) -> Response:
        user = CustomUser.objects.filter(username__iexact=username).first()
        if not user:
            return Response({'message': 'Profil topilmadi'}, status=status.HTTP_404_NOT_FOUND)
        owner = request.user.is_authenticated and request.user.pk == user.pk
        payload = _public_user(user, owner=owner, request=request)
        payload['counts'] = title_lists.counts_for(user)
        if not user.public_profile and not owner:
            payload['private'] = True
            payload['counts'] = {key: 0 for key in payload['counts']}
            payload['stats'] = {
                'joined_at': payload.get('stats', {}).get('joined_at', ''),
                'days_with_us': payload.get('stats', {}).get('days_with_us', 0),
                'comments': 0,
                'episodes_watched': 0,
                'last_login': '',
            }
        return Response(payload)


class PublicProfileReportView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Auth"])
    def post(self, request: Request, username: str) -> Response:
        try:
            payload = profile_reports.file_for(
                request.user,
                username,
                request.data.get('kind'),
                request.data.get('reason'),
                request.data.get('note') or '',
            )
        except ReportError as exc:
            return Response({'message': exc.message}, status=exc.status)
        return Response(payload, status=status.HTTP_201_CREATED)


class BanAppealView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Auth"])
    def post(self, request: Request) -> Response:
        try:
            return Response(user_mod.appeal(request.user, request.data.get('body') or ''))
        except ModerationError as exc:
            return _mod_fail(exc)


class UserListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Lists"])
    def get(self, request: Request) -> Response:
        status_filter = request.query_params.get('status')
        try:
            rows = title_lists.queryset_for(request.user, status_filter)
        except ProfileError as exc:
            return Response({'message': exc.message}, status=status.HTTP_400_BAD_REQUEST)
        return Response({
            'counts': title_lists.counts_for(request.user),
            'results': UserListSerializer(rows, many=True).data,
        })

    @extend_schema(tags=["Lists"])
    def put(self, request: Request) -> Response:
        serializer = ListWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            row = title_lists.upsert(
                request.user,
                serializer.validated_data['anime'],
                serializer.validated_data['status'],
                serializer.validated_data.get('score'),
            )
        except ProfileError as exc:
            return Response({'message': exc.message}, status=status.HTTP_400_BAD_REQUEST)
        return Response(UserListSerializer(row).data)

    @extend_schema(tags=["Lists"])
    def delete(self, request: Request) -> Response:
        anime_id = request.query_params.get('anime')
        if not anime_id:
            return Response({'message': 'anime kerak'}, status=status.HTTP_400_BAD_REQUEST)
        title_lists.remove(request.user, anime_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


class PublicListView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(tags=["Lists"])
    def get(self, request: Request, username: str) -> Response:
        user = CustomUser.objects.filter(username__iexact=username).first()
        if not user:
            return Response({'message': 'Profil topilmadi'}, status=status.HTTP_404_NOT_FOUND)
        owner = request.user.is_authenticated and request.user.pk == user.pk
        if not user.public_profile and not owner:
            return Response({'message': 'Bu profil yopiq', 'results': [], 'counts': {}})
        status_filter = request.query_params.get('status')
        try:
            rows = title_lists.queryset_for(user, status_filter)
        except ProfileError as exc:
            return Response({'message': exc.message}, status=status.HTTP_400_BAD_REQUEST)
        return Response({
            'counts': title_lists.counts_for(user),
            'results': UserListSerializer(rows, many=True).data,
        })


class ListStatusView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Lists"])
    def get(self, request: Request, anime_id: int) -> Response:
        row = title_lists.status_for(request.user, anime_id)
        if not row:
            return Response({'status': None, 'score': None})
        return Response({'status': row.status, 'score': row.score})


class ProgressView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Progress"])
    def get(self, request: Request, episode_id: int) -> Response:
        return Response(watch_progress.get_for(request.user, episode_id))

    @extend_schema(tags=["Progress"])
    def put(self, request: Request, episode_id: int) -> Response:
        try:
            payload = watch_progress.save_for(
                request.user,
                episode_id,
                request.data.get('position'),
                request.data.get('duration') or 0,
            )
        except ProgressError as exc:
            return Response({'message': exc.message}, status=exc.status)
        return Response(payload)

    @extend_schema(tags=["Progress"])
    def delete(self, request: Request, episode_id: int) -> Response:
        return Response(watch_progress.clear_for(request.user, episode_id))


class EpisodeCommentsView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(tags=["Comments"])
    def get(self, request: Request, episode_id: int) -> Response:
        try:
            return Response(talk.list_for(episode_id, request.user, request))
        except CommentError as exc:
            return Response({'message': exc.message}, status=exc.status)

    @extend_schema(tags=["Comments"])
    def post(self, request: Request, episode_id: int) -> Response:
        if not request.user.is_authenticated:
            return Response({'message': 'Izoh uchun kiring'}, status=status.HTTP_401_UNAUTHORIZED)
        try:
            payload = talk.create(
                request.user,
                episode_id,
                request.data.get('body'),
                request.data.get('parent'),
                request,
            )
        except CommentError as exc:
            return Response({'message': exc.message}, status=exc.status)
        return Response(payload, status=status.HTTP_201_CREATED)


class CommentDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Comments"])
    def delete(self, request: Request, pk: int) -> Response:
        try:
            return Response(talk.delete(request.user, pk))
        except CommentError as exc:
            return Response({'message': exc.message}, status=exc.status)


class CommentLikeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Comments"])
    def post(self, request: Request, pk: int) -> Response:
        try:
            return Response(talk.toggle_comment_like(request.user, pk))
        except CommentError as exc:
            return Response({'message': exc.message}, status=exc.status)


class EpisodeLikeView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(tags=["Comments"])
    def get(self, request: Request, episode_id: int) -> Response:
        try:
            return Response(talk.episode_like_state(episode_id, request.user))
        except CommentError as exc:
            return Response({'message': exc.message}, status=exc.status)

    @extend_schema(tags=["Comments"])
    def post(self, request: Request, episode_id: int) -> Response:
        if not request.user.is_authenticated:
            return Response({'message': 'Like uchun kiring'}, status=status.HTTP_401_UNAUTHORIZED)
        try:
            return Response(talk.toggle_episode_like(request.user, episode_id))
        except CommentError as exc:
            return Response({'message': exc.message}, status=exc.status)


class AnimeeLoginView(TokenObtainPairView):
    """JWT login with a short IP lock after 5 failed attempts."""

    serializer_class = AnimeeTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        ip = (
            request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', '0'))
            .split(',')[0]
            .strip()
        )
        lock_key = f'auth_lock:{ip}'
        if cache.get(lock_key):
            return Response({'detail': 'Biroz kuting...'}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        response = super().post(request, *args, **kwargs)
        fail_key = f'auth_fail:{ip}'
        if response.status_code >= 400:
            n = int(cache.get(fail_key) or 0) + 1
            cache.set(fail_key, n, 60 * 10)
            if n >= 5:
                cache.set(lock_key, 1, 15)
                cache.delete(fail_key)
        else:
            cache.delete(fail_key)
        return response
