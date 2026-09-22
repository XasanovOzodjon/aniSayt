from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from drf_spectacular.utils import extend_schema

from . import services
from .permissions import IsAdminOnly, IsDashboardStaff


class DashView(APIView):
    permission_classes = [IsDashboardStaff]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def fail(self, exc):
        return Response({'message': exc.message}, status=exc.status)


class AdminDashView(DashView):
    permission_classes = [IsAdminOnly]


class StatsView(DashView):
    @extend_schema(tags=['Dashboard'])
    def get(self, request):
        return Response(services.stats(request))


class CatalogView(DashView):
    @extend_schema(tags=['Dashboard'])
    def get(self, request):
        try:
            return Response({
                'results': services.list_catalog(
                    request,
                    request.query_params.get('q') or '',
                    request.query_params.get('kind') or '',
                )
            })
        except services.DashError as exc:
            return self.fail(exc)

    @extend_schema(tags=['Dashboard'])
    def post(self, request):
        try:
            return Response(services.create_anime(request.data, request.FILES, request), status=status.HTTP_201_CREATED)
        except services.DashError as exc:
            return self.fail(exc)


class CatalogDetailView(DashView):
    @extend_schema(tags=['Dashboard'])
    def get(self, request, pk):
        try:
            return Response(services.get_anime(pk, request))
        except services.DashError as exc:
            return self.fail(exc)

    @extend_schema(tags=['Dashboard'])
    def patch(self, request, pk):
        try:
            return Response(services.update_anime(pk, request.data, request))
        except services.DashError as exc:
            return self.fail(exc)

    @extend_schema(tags=['Dashboard'])
    def delete(self, request, pk):
        try:
            services.delete_anime(pk)
        except services.DashError as exc:
            return self.fail(exc)
        return Response({'ok': True})


class PosterView(DashView):
    @extend_schema(tags=['Dashboard'])
    def post(self, request, pk):
        try:
            return Response(services.set_poster(pk, request.FILES.get('poster'), request))
        except services.DashError as exc:
            return self.fail(exc)


class SeasonCreateView(DashView):
    @extend_schema(tags=['Dashboard'])
    def post(self, request, pk):
        try:
            return Response(services.add_season(pk, request.data, request), status=status.HTTP_201_CREATED)
        except services.DashError as exc:
            return self.fail(exc)


class SeasonDetailView(DashView):
    @extend_schema(tags=['Dashboard'])
    def get(self, request, pk):
        try:
            return Response(services.get_season(pk, request))
        except services.DashError as exc:
            return self.fail(exc)

    @extend_schema(tags=['Dashboard'])
    def patch(self, request, pk):
        try:
            return Response(services.update_season(pk, request.data, request))
        except services.DashError as exc:
            return self.fail(exc)

    @extend_schema(tags=['Dashboard'])
    def delete(self, request, pk):
        try:
            return Response(services.delete_season(pk, request))
        except services.DashError as exc:
            return self.fail(exc)


class EpisodeCreateView(DashView):
    @extend_schema(tags=['Dashboard'])
    def post(self, request, pk):
        try:
            return Response(services.add_episode(pk, request.data, request), status=status.HTTP_201_CREATED)
        except services.DashError as exc:
            return self.fail(exc)


class EpisodeDetailView(DashView):
    @extend_schema(tags=['Dashboard'])
    def get(self, request, pk):
        try:
            return Response(services.get_episode(pk, request))
        except services.DashError as exc:
            return self.fail(exc)

    @extend_schema(tags=['Dashboard'])
    def patch(self, request, pk):
        try:
            return Response(services.update_episode(pk, request.data, request.FILES, request))
        except services.DashError as exc:
            return self.fail(exc)

    @extend_schema(tags=['Dashboard'])
    def delete(self, request, pk):
        try:
            return Response(services.delete_episode(pk, request))
        except services.DashError as exc:
            return self.fail(exc)


class VideoCreateView(DashView):
    @extend_schema(tags=['Dashboard'])
    def post(self, request, pk):
        try:
            return Response(services.add_video(pk, request.data, request.FILES, request), status=status.HTTP_201_CREATED)
        except services.DashError as exc:
            return self.fail(exc)


class VideoDetailView(DashView):
    @extend_schema(tags=['Dashboard'])
    def patch(self, request, pk):
        try:
            return Response(services.update_video(pk, request.data, request))
        except services.DashError as exc:
            return self.fail(exc)

    @extend_schema(tags=['Dashboard'])
    def delete(self, request, pk):
        try:
            return Response(services.delete_video(pk, request))
        except services.DashError as exc:
            return self.fail(exc)


class GenreView(DashView):
    @extend_schema(tags=['Dashboard'])
    def get(self, request):
        return Response({'results': services.list_genres()})

    @extend_schema(tags=['Dashboard'])
    def post(self, request):
        try:
            return Response(services.save_genre(request.data), status=status.HTTP_201_CREATED)
        except services.DashError as exc:
            return self.fail(exc)


class GenreDetailView(DashView):
    @extend_schema(tags=['Dashboard'])
    def patch(self, request, pk):
        try:
            return Response(services.save_genre(request.data, pk=pk))
        except services.DashError as exc:
            return self.fail(exc)

    @extend_schema(tags=['Dashboard'])
    def delete(self, request, pk):
        try:
            services.delete_genre(pk)
        except services.DashError as exc:
            return self.fail(exc)
        return Response({'ok': True})


class PersonCreateView(DashView):
    @extend_schema(tags=['Dashboard'])
    def post(self, request):
        try:
            return Response(services.add_person(request.data, request.FILES, request), status=status.HTTP_201_CREATED)
        except services.DashError as exc:
            return self.fail(exc)


class PersonDetailView(DashView):
    @extend_schema(tags=['Dashboard'])
    def delete(self, request, pk):
        try:
            return Response(services.delete_person(pk, request))
        except services.DashError as exc:
            return self.fail(exc)


class UsersView(AdminDashView):
    @extend_schema(tags=['Dashboard'])
    def get(self, request):
        return Response({'results': services.list_users(request, request.query_params.get('q') or '')})


class UserDetailView(AdminDashView):
    @extend_schema(tags=['Dashboard'])
    def get(self, request, pk):
        try:
            return Response(services.get_user(pk, request))
        except services.DashError as exc:
            return self.fail(exc)

    @extend_schema(tags=['Dashboard'])
    def patch(self, request, pk):
        try:
            return Response(services.update_user(pk, request.data, request.user))
        except services.DashError as exc:
            return self.fail(exc)


class NoticeBroadcastView(AdminDashView):
    @extend_schema(tags=['Dashboard'])
    def post(self, request):
        try:
            return Response(services.broadcast_news(
                request.data.get('title'),
                request.data.get('body'),
                request.data.get('anime'),
            ), status=status.HTTP_201_CREATED)
        except services.DashError as exc:
            return self.fail(exc)


class PartiesView(AdminDashView):
    @extend_schema(tags=['Dashboard'])
    def get(self, request):
        return Response({'results': services.list_parties()})


class PartyCloseView(AdminDashView):
    @extend_schema(tags=['Dashboard'])
    def patch(self, request, code):
        try:
            return Response(services.advance_party(code))
        except services.DashError as exc:
            return self.fail(exc)

    @extend_schema(tags=['Dashboard'])
    def delete(self, request, code):
        try:
            return Response(services.close_party(code))
        except services.DashError as exc:
            return self.fail(exc)


class PlayerPosterView(AdminDashView):
    @extend_schema(tags=['Dashboard'])
    def get(self, request):
        from apps.main.site import as_dict
        return Response(as_dict(request))

    @extend_schema(tags=['Dashboard'])
    def post(self, request):
        from apps.main.site import SiteError, set_player_poster
        try:
            return Response(set_player_poster(request.FILES.get('poster'), request))
        except SiteError as exc:
            return Response({'message': exc.message}, status=exc.status)


class ReportsView(AdminDashView):
    @extend_schema(tags=['Dashboard'])
    def get(self, request):
        from apps.users.reports import list_reports
        return Response({'results': list_reports()})


class ReportDetailView(AdminDashView):
    @extend_schema(tags=['Dashboard'])
    def patch(self, request, pk):
        from apps.users.reports import ReportError, resolve
        action = request.data.get('action') or ('dismiss' if request.data.get('resolved') else '')
        if not action and not request.data.get('resolved'):
            return Response({'message': 'resolved yoki action kerak'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            return Response(resolve(pk, action=action, extra=request.data))
        except ReportError as exc:
            return Response({'message': exc.message}, status=exc.status)


class AppealsView(AdminDashView):
    @extend_schema(tags=['Dashboard'])
    def get(self, request):
        from apps.users.moderation import list_appeals
        return Response({'results': list_appeals()})


class AppealDetailView(AdminDashView):
    @extend_schema(tags=['Dashboard'])
    def patch(self, request, pk):
        from apps.users.moderation import ModerationError, resolve_appeal
        try:
            return Response(resolve_appeal(pk, bool(request.data.get('accepted'))))
        except ModerationError as exc:
            return Response({'message': exc.message}, status=exc.status)
