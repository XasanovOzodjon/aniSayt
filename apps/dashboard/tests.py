from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from django.test import TestCase
from unittest.mock import patch

from apps.anime.models import Anime
from apps.anime.tests import _tiny_gif
from apps.episode.demo import attach_demo_to_episodes
from apps.episode.ingest import IngestError, validate_source_url
from apps.episode.models import Episode, Video
from apps.users.models import Notice

CustomUser = get_user_model()


def _auth(user):
    client = APIClient()
    token = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')
    return client


class DashboardApiTests(TestCase):
    def setUp(self):
        self.admin = CustomUser.objects.create_user(
            username='ops', email='ops@example.com', password='Secret123!',
            is_staff=True, is_superuser=True,
        )
        self.mod = CustomUser.objects.create_user(
            username='mod', email='mod@example.com', password='Secret123!',
            is_moderator=True,
        )
        self.user = CustomUser.objects.create_user(
            username='regular', email='r@example.com', password='Secret123!',
        )
        self.client = _auth(self.admin)

    def test_guest_and_user_blocked(self):
        anon = APIClient()
        self.assertEqual(anon.get('/uz/api/dashboard/stats/').status_code, 401)
        other = _auth(self.user)
        self.assertEqual(other.get('/uz/api/dashboard/stats/').status_code, 403)

    def test_moderator_catalog_not_users(self):
        client = _auth(self.mod)
        self.assertEqual(client.get('/uz/api/dashboard/stats/').status_code, 200)
        gif = _tiny_gif()
        res = client.post('/uz/api/dashboard/catalog/', {
            'title': 'Mod Anime',
            'description': 'Tavsif',
            'kind': 'anime',
            'poster': gif,
        }, format='multipart')
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(res.json()['kind'], 'anime')
        self.assertEqual(client.get('/uz/api/dashboard/users/').status_code, 403)
        self.assertEqual(client.post('/uz/api/dashboard/notices/', {
            'title': 'x', 'body': 'y',
        }, format='json').status_code, 403)

    def test_stats_and_kind_sections(self):
        self.assertEqual(self.client.get('/dashboard/').status_code, 200)
        stats = self.client.get('/uz/api/dashboard/stats/')
        self.assertEqual(stats.status_code, 200)
        body = stats.json()
        self.assertIn('serial', body)
        self.assertTrue(body['is_admin'])
        gif = _tiny_gif()
        res = self.client.post('/uz/api/dashboard/catalog/', {
            'title': 'Yangi Neon',
            'description': 'Tavsif',
            'kind': 'anime',
            'poster': gif,
        }, format='multipart')
        self.assertEqual(res.status_code, 201, res.content)
        pk = res.json()['id']
        self.assertEqual(res.json()['seasons'], [])
        season = self.client.post(f'/uz/api/dashboard/catalog/{pk}/seasons/', {
            'number': 1, 'release_date': 2026,
        }, format='json')
        self.assertEqual(season.status_code, 201, season.content)
        sid = season.json()['id']
        ep = self.client.post(f'/uz/api/dashboard/seasons/{sid}/episodes/', {
            'number': 1, 'title': '1-qism',
        }, format='json')
        self.assertEqual(ep.status_code, 201)
        eid = ep.json()['episodes'][0]['id']
        blocked = self.client.post(f'/uz/api/dashboard/episodes/{eid}/videos/', {
            'language': 'uz', 'hls_path': '/media/hls/1/master.m3u8',
        }, format='json')
        self.assertEqual(blocked.status_code, 400)
        serial = self.client.post('/uz/api/dashboard/catalog/', {
            'title': 'Shahar Soati',
            'description': 'Serial tavsif',
            'kind': 'serial',
            'poster': _tiny_gif(),
        }, format='multipart')
        self.assertEqual(serial.status_code, 201, serial.content)
        self.assertEqual(serial.json()['kind'], 'serial')
        listed = self.client.get('/uz/api/dashboard/catalog/', {'kind': 'serial'})
        self.assertEqual(listed.status_code, 200)
        self.assertEqual([row['title'] for row in listed.json()['results']], ['Shahar Soati'])
        film = self.client.post('/uz/api/dashboard/catalog/', {
            'title': 'Qisqa metr',
            'description': 'Kino',
            'kind': 'film',
            'poster': _tiny_gif(),
        }, format='multipart')
        self.assertEqual(film.status_code, 201)
        self.assertEqual(len(film.json()['seasons'][0]['episodes']), 1)

    def test_video_upload_and_url(self):
        gif = _tiny_gif()
        res = self.client.post('/uz/api/dashboard/catalog/', {
            'title': 'Clip',
            'description': 'Tavsif',
            'kind': 'drama',
            'poster': gif,
        }, format='multipart')
        self.assertEqual(res.json()['seasons'], [])
        season = self.client.post(f'/uz/api/dashboard/catalog/{res.json()["id"]}/seasons/', {
            'number': 1, 'release_date': 2026,
        }, format='json')
        sid = season.json()['id']
        ep = self.client.post(f'/uz/api/dashboard/seasons/{sid}/episodes/', {
            'number': 1, 'title': '1-qism',
        }, format='json')
        eid = ep.json()['episodes'][0]['id']

        def fake_convert(instance):
            instance.hls_path = instance.video.url
            instance.save(update_fields=['hls_path'])

        with patch('apps.episode.signals.convert_to_hls', fake_convert):
            uploaded = self.client.post(
                f'/uz/api/dashboard/episodes/{eid}/videos/',
                {'language': 'uz', 'video': SimpleUploadedFile('clip.mp4', b'0' * 2048, content_type='video/mp4')},
                format='multipart',
            )
        self.assertEqual(uploaded.status_code, 201, uploaded.content)
        after = self.client.get(f'/uz/api/dashboard/seasons/{sid}/')
        self.assertTrue(after.json()['episodes'][0]['videos'][0]['hls_path'])

        ep2 = self.client.post(f'/uz/api/dashboard/seasons/{sid}/episodes/', {
            'number': 2, 'title': '2-qism',
        }, format='json')
        eid2 = ep2.json()['episodes'][1]['id']

        def fake_download(url, on_progress=None):
            from tempfile import NamedTemporaryFile
            tmp = NamedTemporaryFile(delete=False, suffix='.mp4')
            tmp.write(b'1' * 2048)
            tmp.close()
            return tmp.name, 'net.mp4'

        with patch('apps.episode.ingest.download_source', fake_download), patch(
            'apps.episode.signals.convert_to_hls', fake_convert
        ):
            remote = self.client.post(
                f'/uz/api/dashboard/episodes/{eid2}/videos/',
                {'language': 'uz', 'source_url': 'https://example.com/net.mp4'},
                format='json',
            )
        self.assertEqual(remote.status_code, 201, remote.content)
        after2 = self.client.get(f'/uz/api/dashboard/seasons/{sid}/')
        self.assertTrue(after2.json()['episodes'][1]['videos'][0]['hls_path'])
        self.assertEqual(after2.json()['episodes'][1]['videos'][0]['status'], 'ready')
        self.assertEqual(after2.json()['episodes'][1]['videos'][0]['progress'], 100)

    def test_source_url_queues_without_waiting(self):
        gif = _tiny_gif()
        res = self.client.post('/uz/api/dashboard/catalog/', {
            'title': 'Clip',
            'description': 'Tavsif',
            'kind': 'drama',
            'poster': gif,
        }, format='multipart')
        season = self.client.post(f'/uz/api/dashboard/catalog/{res.json()["id"]}/seasons/', {
            'number': 1, 'release_date': 2026,
        }, format='json')
        sid = season.json()['id']
        ep = self.client.post(f'/uz/api/dashboard/seasons/{sid}/episodes/', {
            'number': 1, 'title': '1-qism',
        }, format='json')
        eid = ep.json()['episodes'][0]['id']
        with patch('apps.dashboard.services.settings.TESTING', False), patch(
            'apps.episode.signals.settings.TESTING', False
        ), patch('apps.episode.signals.threading.Thread') as thread:
            with self.captureOnCommitCallbacks(execute=True):
                remote = self.client.post(
                    f'/uz/api/dashboard/episodes/{eid}/videos/',
                    {'language': 'uz', 'source_url': 'https://example.com/film.mp4'},
                    format='json',
                )
        self.assertEqual(remote.status_code, 201, remote.content)
        row = self.client.get(f'/uz/api/dashboard/seasons/{sid}/').json()['episodes'][0]['videos'][0]
        self.assertEqual(row['status'], 'queued')
        self.assertEqual(row['source_url'], 'https://example.com/film.mp4')
        self.assertFalse(row['hls_path'])
        self.assertEqual(row['progress'], 0)
        thread.assert_called()

    def test_broadcast_and_roles(self):
        res = self.client.post('/uz/api/dashboard/notices/', {
            'title': 'Texnik tanaffus',
            'body': 'Tun soat 02:00 da.',
        }, format='json')
        self.assertEqual(res.status_code, 201)
        self.assertEqual(Notice.objects.filter(kind='news').count(), 3)
        patched = self.client.patch(f'/uz/api/dashboard/users/{self.user.pk}/', {
            'is_moderator': True, 'is_admin': False,
        }, format='json')
        self.assertEqual(patched.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_moderator)
        self.assertFalse(self.user.is_staff)
        admined = self.client.patch(f'/uz/api/dashboard/users/{self.user.pk}/', {
            'is_admin': True,
        }, format='json')
        self.assertEqual(admined.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_staff)
        self.assertFalse(self.user.is_moderator)

    def test_attach_demo_mp4(self):
        anime = Anime.objects.create(title='Demo', description='x', poster=_tiny_gif(), kind='anime')
        from apps.anime.models import Season
        season = Season.objects.create(anime=anime, number=1, release_date=2026)
        Episode.objects.create(season=season, number=1, title='1-qism')
        Episode.objects.create(season=season, number=2, title='2-qism')
        from pathlib import Path
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmp:
            src = Path(tmp) / 'demo.mp4'
            src.write_bytes(b'd' * 4096)
            created, url = attach_demo_to_episodes(src)
        self.assertEqual(created, 2)
        self.assertTrue(url.endswith('demo.mp4'))
        self.assertEqual(Video.objects.filter(hls_path=url).count(), 2)

    def test_player_poster_admin_only(self):
        self.assertEqual(_auth(self.mod).get('/uz/api/dashboard/player-poster/').status_code, 403)
        got = self.client.get('/uz/api/dashboard/player-poster/')
        self.assertEqual(got.status_code, 200)
        self.assertIn('player-poster.jpg', got.json()['player_poster'])
        gif = _tiny_gif()
        gif.name = 'site-poster.gif'
        posted = self.client.post(
            '/uz/api/dashboard/player-poster/',
            {'poster': gif},
            format='multipart',
        )
        self.assertEqual(posted.status_code, 200, posted.content)
        self.assertIn('/media/', posted.json()['player_poster'])

    def test_admin_advances_party_episode(self):
        from apps.anime.models import Season
        from apps.episode.models import Episode
        from apps.party.models import WatchParty

        anime = Anime.objects.create(title='Neon Qish', description='x', poster=_tiny_gif())
        season = Season.objects.create(anime=anime, number=1, release_date=2025)
        first = Episode.objects.create(season=season, number=1, title='1-qism')
        second = Episode.objects.create(season=season, number=2, title='2-qism')
        party = WatchParty.objects.create(code='abcd2345', episode=first, host=self.user)
        res = self.client.patch(f'/uz/api/dashboard/parties/{party.code}/', {'action': 'next'}, format='json')
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(res.json()['episode'], 2)
        self.assertEqual(_auth(self.mod).patch(
            f'/uz/api/dashboard/parties/{party.code}/', {'action': 'next'}, format='json',
        ).status_code, 403)

    def test_seasonal_pages_and_film_sequel(self):
        gif = _tiny_gif()
        anime = self.client.post('/uz/api/dashboard/catalog/', {
            'title': 'Neon Qish',
            'description': 'Serial emas',
            'kind': 'anime',
            'poster': gif,
        }, format='multipart')
        self.assertEqual(anime.status_code, 201)
        pk = anime.json()['id']
        self.assertEqual(anime.json()['seasons'], [])
        first = self.client.post(f'/uz/api/dashboard/catalog/{pk}/seasons/', {
            'number': 1, 'release_date': 2024,
        }, format='json')
        self.assertEqual(first.status_code, 201)
        sid = first.json()['id']
        got = self.client.get(f'/uz/api/dashboard/seasons/{sid}/')
        self.assertEqual(got.status_code, 200)
        self.assertEqual(got.json()['episodes'], [])
        ep = self.client.post(f'/uz/api/dashboard/seasons/{sid}/episodes/', {
            'number': 1, 'title': 'Boshlanish',
        }, format='json')
        eid = ep.json()['episodes'][0]['id']
        self.assertEqual(self.client.get(f'/uz/api/dashboard/episodes/{eid}/').status_code, 200)

        one = self.client.post('/uz/api/dashboard/catalog/', {
            'title': 'O‘rgimchak odam 1',
            'description': 'Birinchi',
            'kind': 'film',
            'poster': _tiny_gif(),
        }, format='multipart')
        two = self.client.post('/uz/api/dashboard/catalog/', {
            'title': 'O‘rgimchak odam 2',
            'description': 'Ikkinchi',
            'kind': 'film',
            'poster': _tiny_gif(),
        }, format='multipart')
        a_id = one.json()['id']
        b_id = two.json()['id']
        self.assertEqual(len(one.json()['seasons'][0]['episodes']), 1)
        no_season = self.client.post(f'/uz/api/dashboard/catalog/{a_id}/seasons/', {
            'number': 2, 'release_date': 2025,
        }, format='json')
        self.assertEqual(no_season.status_code, 400)
        film_season = one.json()['seasons'][0]['id']
        extra_ep = self.client.post(f'/uz/api/dashboard/seasons/{film_season}/episodes/', {
            'number': 2, 'title': '2-qism',
        }, format='json')
        self.assertEqual(extra_ep.status_code, 400)
        linked = self.client.patch(f'/uz/api/dashboard/catalog/{a_id}/', {
            'next_title_id': b_id,
        }, format='json')
        self.assertEqual(linked.status_code, 200, linked.content)
        self.assertEqual(linked.json()['next_title']['id'], b_id)
        public = self.client.get(f'/uz/api/anime/{a_id}/')
        self.assertEqual(public.status_code, 200)
        self.assertEqual(public.json()['next_title']['id'], b_id)
        ep_id = one.json()['film_episode']['id']
        episode = self.client.get(f'/uz/api/episodes/{ep_id}/')
        self.assertEqual(episode.status_code, 200)
        self.assertTrue(episode.json()['next_watch_path'])


class IngestUrlTests(TestCase):
    def test_rejects_hls_and_private(self):
        with self.assertRaises(IngestError):
            validate_source_url('https://cdn.example.com/master.m3u8')
        with self.assertRaises(IngestError):
            validate_source_url('http://127.0.0.1/video.mp4')
        with self.assertRaises(IngestError):
            validate_source_url('ftp://files.example.com/a.mp4')
        self.assertEqual(
            validate_source_url('https://example.com/tarjima_kinolar/sinister_720.mp4'),
            'https://example.com/tarjima_kinolar/sinister_720.mp4',
        )


class IngestProgressTests(TestCase):
    def test_progress_roundtrip(self):
        from apps.episode.ingest import get_progress, set_progress
        self.assertEqual(get_progress(99), {})
        set_progress(99, 40, 's3')
        self.assertEqual(get_progress(99)['progress'], 40)
        self.assertEqual(get_progress(99)['stage'], 's3')

    def test_hls_disk_full_keeps_file_and_does_not_look_like_download_failure(self):
        from apps.anime.models import Season
        from apps.episode.ingest import ingest_video

        anime = Anime.objects.create(
            title='Disk', description='Tavsif', kind='film', poster=_tiny_gif(),
        )
        season = Season.objects.create(anime=anime, number=1, release_date=2026)
        episode = Episode.objects.create(season=season, number=1, title='1-qism')
        video = Video.objects.create(
            episode=episode, language='uz', source_url='https://example.com/film.mp4',
        )
        video.video.save(
            'clip.mp4',
            SimpleUploadedFile('clip.mp4', b'0' * 2048, content_type='video/mp4'),
            save=True,
        )
        with patch(
            'apps.episode.ingest.convert_to_hls',
            side_effect=OSError(122, 'Disk quota exceeded'),
        ):
            ingest_video(video.pk)
        video.refresh_from_db()
        self.assertTrue(video.video)
        self.assertFalse(video.hls_path)
        self.assertTrue(video.ingest_error)
        self.assertNotEqual(video.ingest_error, 'Videoni yuklab bo‘lmadi')
        self.assertIn('HLS', video.ingest_error)


class ProfileReportDashTests(TestCase):
    def setUp(self):
        self.admin = CustomUser.objects.create_user(
            username='ops', email='ops@example.com', password='Secret123!',
            is_staff=True, is_superuser=True,
        )
        self.reporter = CustomUser.objects.create_user(
            username='rep', email='rep@example.com', password='Secret123!',
        )
        self.target = CustomUser.objects.create_user(
            username='tgt', email='tgt@example.com', password='Secret123!',
            bio='x',
        )
        self.client = _auth(self.admin)
        self.user_client = _auth(self.reporter)

    def test_admin_lists_and_resolves_a_report(self):
        posted = self.user_client.post(
            f'/uz/api/auth/u/{self.target.username}/report/',
            {'kind': 'bio', 'reason': 'insult', 'note': 'Yomon so‘z'},
            format='json',
        )
        self.assertEqual(posted.status_code, 201, posted.content)
        listed = self.client.get('/uz/api/dashboard/reports/')
        self.assertEqual(listed.status_code, 200)
        rows = listed.json()['results']
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['kind'], 'bio')
        self.assertEqual(rows[0]['target'], 'tgt')
        self.assertFalse(rows[0]['resolved'])
        profile = self.client.get(f'/uz/api/dashboard/users/{self.target.pk}/')
        self.assertEqual(profile.status_code, 200)
        self.assertEqual(profile.json()['username'], 'tgt')
        self.assertEqual(profile.json()['bio'], 'x')
        self.assertEqual(profile.json()['open_reports'], 1)
        self.assertEqual(profile.json()['reports'][0]['reason'], 'insult')
        done = self.client.patch(f'/uz/api/dashboard/reports/{rows[0]["id"]}/', {'resolved': True}, format='json')
        self.assertEqual(done.status_code, 200)
        self.assertTrue(done.json()['resolved'])
