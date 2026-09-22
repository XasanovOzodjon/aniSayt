from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from django.test import TestCase, TransactionTestCase, override_settings

from apps.anime.models import Anime, Season
from apps.anime.tests import _tiny_gif
from apps.episode.models import Episode
from apps.party.models import PartyMessage, WatchParty
from apps.party import services

CustomUser = get_user_model()


class PartyHttpTests(TestCase):
    def setUp(self):
        self.host = CustomUser.objects.create_user(
            username='host', email='host@example.com', password='Secret123!'
        )
        self.guest_user = CustomUser.objects.create_user(
            username='guestu', email='g@example.com', password='Secret123!'
        )
        anime = Anime.objects.create(title='Neon Qish', description='x', poster=_tiny_gif())
        season = Season.objects.create(anime=anime, number=1, release_date=2025)
        self.episode = Episode.objects.create(season=season, number=1, title='1-qism')
        self.client = APIClient()
        token = RefreshToken.for_user(self.host)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')

    def test_lobby_pages(self):
        page = self.client.get('/party/')
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, 'Xona yaratish')
        self.assertContains(page, 'createPicker')
        self.assertContains(page, 'Nomini yozing')
        code = self.client.post('/uz/api/party/', {'episode': self.episode.id}, format='json').json()['code']
        page = self.client.get(f'/party/{code}/')
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, 'Qo‘shilish')
        self.assertContains(page, 'invite-card')

    def test_guest_can_open_invite_preview(self):
        code = self.client.post('/uz/api/party/', {'episode': self.episode.id}, format='json').json()['code']
        anon = APIClient()
        res = anon.get(f'/uz/api/party/{code}/preview/')
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body['code'], code)
        self.assertEqual(body['episode']['id'], self.episode.id)
        self.assertFalse(body['require_camera'])
        self.assertNotIn('messages', body)
        self.assertEqual(anon.get(f'/uz/api/party/{code}/').status_code, 401)
        self.assertEqual(anon.get(f'/party/{code}/').status_code, 200)

    def test_host_sets_required_camera(self):
        res = self.client.post(
            '/uz/api/party/',
            {'episode': self.episode.id, 'require_camera': True, 'require_mic': False},
            format='json',
        )
        self.assertEqual(res.status_code, 201)
        self.assertTrue(res.json()['require_camera'])
        code = res.json()['code']
        patched = self.client.patch(
            f'/uz/api/party/{code}/',
            {'require_mic': True},
            format='json',
        )
        self.assertEqual(patched.status_code, 200)
        self.assertTrue(patched.json()['require_mic'])
        other = APIClient()
        token = RefreshToken.for_user(self.guest_user)
        other.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')
        denied = other.patch(f'/uz/api/party/{code}/', {'require_camera': False}, format='json')
        self.assertEqual(denied.status_code, 403)

    def test_guest_cannot_create(self):
        anon = APIClient()
        res = anon.post('/uz/api/party/', {'episode': self.episode.id}, format='json')
        self.assertEqual(res.status_code, 401)

    def test_create_and_fetch(self):
        res = self.client.post('/uz/api/party/', {'episode': self.episode.id}, format='json')
        self.assertEqual(res.status_code, 201)
        code = res.json()['code']
        self.assertTrue(res.json()['invite_url'].endswith(f'/party/{code}/'))
        self.assertEqual(res.json()['episode']['id'], self.episode.id)
        got = self.client.get(f'/uz/api/party/{code}/')
        self.assertEqual(got.status_code, 200)
        self.assertEqual(got.json()['host_id'], self.host.pk)

    def test_other_user_can_open_invite(self):
        code = self.client.post('/uz/api/party/', {'episode': self.episode.id}, format='json').json()['code']
        other = APIClient()
        token = RefreshToken.for_user(self.guest_user)
        other.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')
        res = other.get(f'/uz/api/party/{code}/')
        self.assertEqual(res.status_code, 200)

    def test_host_closes(self):
        code = self.client.post('/uz/api/party/', {'episode': self.episode.id}, format='json').json()['code']
        res = self.client.delete(f'/uz/api/party/{code}/')
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()['closed'])
        again = self.client.get(f'/uz/api/party/{code}/')
        self.assertEqual(again.status_code, 410)

    def test_non_host_cannot_close(self):
        code = self.client.post('/uz/api/party/', {'episode': self.episode.id}, format='json').json()['code']
        other = APIClient()
        token = RefreshToken.for_user(self.guest_user)
        other.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')
        res = other.delete(f'/uz/api/party/{code}/')
        self.assertEqual(res.status_code, 403)

    def test_host_advances_to_next_episode(self):
        second = Episode.objects.create(season=self.episode.season, number=2, title='2-qism')
        code = self.client.post('/uz/api/party/', {'episode': self.episode.id}, format='json').json()['code']
        res = self.client.patch(f'/uz/api/party/{code}/', {'action': 'next'}, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['episode']['id'], second.id)
        self.assertIn('/episode2/', res.json()['episode']['watch_path'])
        guest = APIClient()
        token = RefreshToken.for_user(self.guest_user)
        guest.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')
        denied = guest.patch(f'/uz/api/party/{code}/', {'action': 'next'}, format='json')
        self.assertEqual(denied.status_code, 403)


class PartySyncTests(TestCase):
    def setUp(self):
        self.host = CustomUser.objects.create_user(
            username='host2', email='host2@example.com', password='Secret123!'
        )
        self.mate = CustomUser.objects.create_user(
            username='mate', email='mate@example.com', password='Secret123!'
        )
        anime = Anime.objects.create(title='Neon Qish', description='x', poster=_tiny_gif())
        season = Season.objects.create(anime=anime, number=1, release_date=2025)
        episode = Episode.objects.create(season=season, number=1, title='1-qism')
        self.party = services.create_party(self.host, episode.id, 'host')

    def test_host_only_rejects_guest_seek(self):
        with self.assertRaises(services.PartyError):
            services.apply_transport(self.party, self.mate, 'seek', 40)

    def test_shared_allows_seek_and_pause_saves_position(self):
        self.party.control = WatchParty.Control.SHARED
        self.party.save(update_fields=['control'])
        services.apply_transport(self.party, self.mate, 'seek', 12.5)
        self.party.refresh_from_db()
        self.assertEqual(self.party.position, 12.5)
        services.apply_transport(self.party, self.mate, 'play', 12.5)
        self.party.refresh_from_db()
        self.assertTrue(self.party.want_playing)
        services.set_buffering(self.party, self.mate, True)
        self.party.refresh_from_db()
        self.assertFalse(self.party.playing)
        self.assertTrue(self.party.want_playing)
        services.set_buffering(self.party, self.mate, False)
        self.party.refresh_from_db()
        self.assertTrue(self.party.playing)

    def test_chat_persists(self):
        row = services.add_message(self.party, self.host, 'Salom')
        self.assertEqual(row.body, 'Salom')
        self.assertEqual(PartyMessage.objects.filter(party=self.party).count(), 1)

    def test_leave_unblocks_playback(self):
        from apps.party import presence
        presence.reset()
        presence.remember(self.party.code, {'id': self.host.pk, 'username': 'h'})
        presence.remember(self.party.code, {'id': self.mate.pk, 'username': 'm'})
        self.party.control = WatchParty.Control.SHARED
        self.party.save(update_fields=['control'])
        services.apply_transport(self.party, self.host, 'play', 0)
        services.set_buffering(self.party, self.mate, True)
        self.party.refresh_from_db()
        self.assertFalse(self.party.playing)
        presence.forget(self.party.code, self.mate.pk)
        services.sync_after_leave(self.party)
        self.party.refresh_from_db()
        self.assertTrue(self.party.playing)
        self.assertEqual(self.party.buffering, [])

    def test_invite_url_uses_request_host(self):
        from django.test import RequestFactory
        req = RequestFactory().get('/')
        url = services.invite_url(self.party, req)
        self.assertTrue(url.endswith(f'/party/{self.party.code}/'))
        self.assertTrue(url.startswith('http://'))

    def test_idle_four_hours_without_watching_closes(self):
        from datetime import timedelta
        from django.utils import timezone
        self.party.playing = False
        self.party.clock = timezone.now() - timedelta(hours=5)
        self.party.save(update_fields=['playing', 'clock'])
        with self.assertRaises(services.PartyError) as raised:
            services.get_open(self.party.code)
        self.assertEqual(raised.exception.status, 410)
        self.party.refresh_from_db()
        self.assertIsNotNone(self.party.closed_at)

    def test_watching_members_keep_room_open_after_four_hours(self):
        from datetime import timedelta
        from django.utils import timezone
        from apps.party import presence
        presence.reset()
        presence.remember(self.party.code, {'id': self.host.pk, 'username': 'h'})
        self.party.playing = True
        self.party.want_playing = True
        self.party.clock = timezone.now() - timedelta(hours=5)
        self.party.save(update_fields=['playing', 'want_playing', 'clock'])
        opened = services.get_open(self.party.code)
        self.assertIsNone(opened.closed_at)

    def test_playing_without_members_closes_after_four_hours(self):
        from datetime import timedelta
        from django.utils import timezone
        from apps.party import presence
        presence.reset()
        self.party.playing = True
        self.party.want_playing = True
        self.party.clock = timezone.now() - timedelta(hours=5)
        self.party.save(update_fields=['playing', 'want_playing', 'clock'])
        with self.assertRaises(services.PartyError) as raised:
            services.get_open(self.party.code)
        self.assertEqual(raised.exception.status, 410)

    def test_recent_pause_does_not_close(self):
        from datetime import timedelta
        from django.utils import timezone
        self.party.playing = False
        self.party.clock = timezone.now() - timedelta(hours=1)
        self.party.save(update_fields=['playing', 'clock'])
        opened = services.get_open(self.party.code)
        self.assertIsNone(opened.closed_at)


@override_settings(REDIS_URL='')
class PresenceTests(TestCase):
    def setUp(self):
        from apps.party import presence
        presence.reset()
        self.presence = presence

    def test_reconnect_does_not_drop_new_socket(self):
        self.presence.remember('room', {'id': 7, 'username': 'a', '_ch': 'old'})
        self.presence.remember('room', {'id': 7, 'username': 'a', '_ch': 'new'})
        self.presence.forget('room', 7, 'old')
        members = self.presence.members('room')
        self.assertEqual([m['id'] for m in members], [7])
        self.assertNotIn('_ch', members[0])

    def test_is_full_allows_existing_member(self):
        for i in range(services.MAX_MEMBERS):
            self.presence.remember('full', {'id': i + 1, 'username': str(i)})
        self.assertTrue(self.presence.is_full('full', 99))
        self.assertFalse(self.presence.is_full('full', 1))


class IceServersTests(TestCase):
    def test_stun_only_without_turn(self):
        with override_settings(TURN_URL='', TURN_URLS=[], TURN_USERNAME='', TURN_CREDENTIAL=''):
            urls = [row['urls'] for row in services.ice_servers()]
        self.assertTrue(any(str(item).startswith('stun:') for item in urls))
        self.assertFalse(any('turn:' in str(item) for item in urls))

    def test_turn_urls_and_credentials(self):
        with override_settings(
            TURN_URL='turn:127.0.0.1:3478',
            TURN_URLS=['turn:127.0.0.1:3478?transport=tcp'],
            TURN_USERNAME='animee',
            TURN_CREDENTIAL='secret',
        ):
            servers = services.ice_servers()
        turn = servers[-1]
        self.assertEqual(turn['username'], 'animee')
        self.assertEqual(turn['credential'], 'secret')
        self.assertIn('turn:127.0.0.1:3478', turn['urls'])
        self.assertIn('turn:127.0.0.1:3478?transport=tcp', turn['urls'])


CHANNEL_INMEM = {
    'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'},
}


@override_settings(CHANNEL_LAYERS=CHANNEL_INMEM, REDIS_URL='')
class PartySocketTests(TransactionTestCase):
    def setUp(self):
        from apps.party import presence
        presence.reset()
        self.host = CustomUser.objects.create_user(
            username='sockhost', email='sockhost@example.com', password='Secret123!'
        )
        self.mate = CustomUser.objects.create_user(
            username='sockmate', email='sockmate@example.com', password='Secret123!'
        )
        anime = Anime.objects.create(title='Neon Qish', description='x', poster=_tiny_gif())
        season = Season.objects.create(anime=anime, number=1, release_date=2025)
        episode = Episode.objects.create(season=season, number=1, title='1-qism')
        self.party = services.create_party(self.host, episode.id, 'shared')

    def _token(self, user):
        return str(RefreshToken.for_user(user).access_token)

    async def _join(self, user):
        from core.asgi import application
        from channels.testing import WebsocketCommunicator
        comm = WebsocketCommunicator(
            application,
            f'/ws/party/{self.party.code}/?token={self._token(user)}',
        )
        connected, _ = await comm.connect()
        return comm, connected

    async def test_guest_socket_rejected(self):
        from core.asgi import application
        from channels.testing import WebsocketCommunicator
        comm = WebsocketCommunicator(application, f'/ws/party/{self.party.code}/')
        connected, _ = await comm.connect()
        self.assertFalse(connected)

    async def test_play_reaches_the_other_member(self):
        host_ws, ok = await self._join(self.host)
        self.assertTrue(ok)
        hello = await host_ws.receive_json_from()
        self.assertEqual(hello['type'], 'hello')
        self.assertEqual(hello['you']['id'], self.host.pk)
        join_self = await host_ws.receive_json_from()
        self.assertEqual(join_self['type'], 'member-join')

        mate_ws, ok2 = await self._join(self.mate)
        self.assertTrue(ok2)
        mate_hello = await mate_ws.receive_json_from()
        self.assertEqual(mate_hello['type'], 'hello')
        host_saw = await host_ws.receive_json_from()
        self.assertEqual(host_saw['type'], 'member-join')
        self.assertEqual(len(host_saw['members']), 2)

        await mate_ws.send_json_to({'type': 'play', 'position': 8})
        host_state = await host_ws.receive_json_from()
        self.assertEqual(host_state['type'], 'state')
        self.assertTrue(host_state['party']['want_playing'])
        self.assertAlmostEqual(host_state['party']['position'], 8, places=1)

        await mate_ws.send_json_to({'type': 'ping'})
        pong = await mate_ws.receive_json_from()
        while pong.get('type') != 'pong':
            pong = await mate_ws.receive_json_from()
        self.assertTrue(pong['party']['want_playing'])

        await mate_ws.disconnect()
        leave = await host_ws.receive_json_from()
        while leave.get('type') != 'member-leave':
            leave = await host_ws.receive_json_from()
        self.assertEqual(leave['user_id'], self.mate.pk)
        self.assertEqual(len(leave['members']), 1)
        await host_ws.disconnect()

