from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from drf_spectacular.utils import extend_schema

from . import services


def _as_bool(value):
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in ('1', 'true', 'yes', 'on'):
        return True
    if text in ('0', 'false', 'no', 'off'):
        return False
    return None


class PartyCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Party"])
    def post(self, request):
        episode_id = request.data.get('episode')
        if not episode_id:
            return Response({'message': 'episode kerak'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            party = services.create_party(
                request.user,
                episode_id,
                request.data.get('control') or 'shared',
                require_camera=_as_bool(request.data.get('require_camera')) or False,
                require_mic=_as_bool(request.data.get('require_mic')) or False,
            )
        except services.PartyError as exc:
            return Response({'message': exc.message}, status=exc.status)
        return Response(services.party_payload(party, request), status=status.HTTP_201_CREATED)


class PartyPreviewView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(tags=["Party"])
    def get(self, request, code):
        try:
            party = services.get_open(code)
        except services.PartyError as exc:
            return Response({'message': exc.message}, status=exc.status)
        return Response(services.preview_payload(party, request))


class PartyDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Party"])
    def get(self, request, code):
        try:
            party = services.get_open(code)
        except services.PartyError as exc:
            return Response({'message': exc.message}, status=exc.status)
        payload = services.party_payload(party, request)
        payload['messages'] = services.recent_messages(party, request)
        return Response(payload)

    @extend_schema(tags=["Party"])
    def patch(self, request, code):
        if request.data.get('action') == 'next' or request.data.get('episode'):
            try:
                party = services.change_episode(
                    request.user,
                    code,
                    request.data.get('episode'),
                    advance=request.data.get('action') == 'next',
                )
            except services.PartyError as exc:
                return Response({'message': exc.message}, status=exc.status)
            payload = services.party_payload(party, request)
            services.notify(code, {'type': 'episode', 'party': payload, 'by': request.user.pk})
            return Response(payload)
        try:
            party = services.set_requirements(
                request.user,
                code,
                require_camera=_as_bool(request.data.get('require_camera')),
                require_mic=_as_bool(request.data.get('require_mic')),
            )
        except services.PartyError as exc:
            return Response({'message': exc.message}, status=exc.status)
        payload = services.party_payload(party, request)
        services.notify(code, {'type': 'state', 'party': payload, 'by': request.user.pk})
        return Response(payload)

    @extend_schema(tags=["Party"])
    def delete(self, request, code):
        try:
            party = services.close_party(request.user, code)
        except services.PartyError as exc:
            return Response({'message': exc.message}, status=exc.status)
        services.notify(code, {'type': 'closed', 'party': services.party_payload(party, request)})
        return Response(services.party_payload(party, request))
