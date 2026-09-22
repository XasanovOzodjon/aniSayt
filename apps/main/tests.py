from pathlib import Path

from django.conf import settings
from django.test import TestCase, override_settings

from apps.anime.tests import _tiny_gif
from apps.main.site import player_poster_url, set_player_poster


class MediaRangeTests(TestCase):
    def setUp(self):
        self.root = Path(settings.MEDIA_ROOT)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / 'range-test.bin'
        self.path.write_bytes(b'0123456789abcdef')

    def tearDown(self):
        self.path.unlink(missing_ok=True)

    def test_full_file_advertises_ranges(self):
        response = self.client.get('/media/range-test.bin')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Accept-Ranges'], 'bytes')
        self.assertEqual(b''.join(response.streaming_content), b'0123456789abcdef')

    def test_byte_range_returns_slice(self):
        response = self.client.get('/media/range-test.bin', HTTP_RANGE='bytes=2-5')
        self.assertEqual(response.status_code, 206)
        self.assertEqual(response['Accept-Ranges'], 'bytes')
        self.assertEqual(response['Content-Range'], 'bytes 2-5/16')
        self.assertEqual(b''.join(response.streaming_content), b'2345')

    def test_hls_segment_is_cacheable(self):
        path = self.root / 'seek-seg.ts'
        path.write_bytes(b'fake-ts')
        self.addCleanup(path.unlink)
        response = self.client.get('/media/seek-seg.ts')
        self.assertEqual(response.status_code, 200)
        self.assertIn('max-age=86400', response['Cache-Control'])
        self.assertIn('immutable', response['Cache-Control'])

    def test_playlist_marks_independent_segments(self):
        path = self.root / 'seek-master.m3u8'
        path.write_text('#EXTM3U\n#EXTINF:4.0,\nseek-seg.ts\n')
        self.addCleanup(path.unlink)
        response = self.client.get('/media/seek-master.m3u8')
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn('#EXT-X-INDEPENDENT-SEGMENTS', body)
        self.assertIn('max-age=30', response['Cache-Control'])


class PlayerPosterTests(TestCase):
    def test_player_page_ships_default_poster(self):
        response = self.client.get('/player/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'player-poster.jpg')
        self.assertIn('player-poster.jpg', player_poster_url())
        self.assertContains(response, 'watch-comments')
        self.assertContains(response, 'watch-page')

    def test_upload_replaces_default(self):
        gif = _tiny_gif()
        gif.name = 'brand.gif'
        payload = set_player_poster(gif)
        self.assertIn('/media/', payload['player_poster'])
        self.assertTrue(payload['player_poster'].endswith('brand.gif') or 'brand' in payload['player_poster'])


class PlaylistRewriteTests(TestCase):
    def test_relative_segments_become_signed_urls(self):
        from apps.main.object_storage import rewrite_playlist, s3_enabled

        self.assertFalse(s3_enabled())
        body = '#EXTM3U\n#EXTINF:6.0,\nseg0.ts\n#EXTINF:6.0,\nseg1.ts\n'
        out = rewrite_playlist(body, 'hls/9', lambda key: f'https://s3.example/{key}?sig=1')
        self.assertIn('https://s3.example/hls/9/seg0.ts?sig=1', out)
        self.assertIn('https://s3.example/hls/9/seg1.ts?sig=1', out)
        self.assertIn('#EXTM3U', out)

    def test_public_file_url_stays_on_django_media(self):
        from apps.main.object_storage import public_file_url

        self.assertEqual(public_file_url('anime/posters/x.png'), '/media/anime/posters/x.png')
        self.assertEqual(public_file_url('/anime/posters/x.png'), '/media/anime/posters/x.png')

        class Field:
            name = 'episodes/thumbs/a.png'

        self.assertEqual(public_file_url(Field()), '/media/episodes/thumbs/a.png')
        self.assertEqual(public_file_url(''), '')
    def test_relative_segments_become_signed_urls(self):
        from apps.main.object_storage import rewrite_playlist, s3_enabled

        self.assertFalse(s3_enabled())
        body = '#EXTM3U\n#EXTINF:6.0,\nseg0.ts\n#EXTINF:6.0,\nseg1.ts\n'
        out = rewrite_playlist(body, 'hls/9', lambda key: f'https://s3.example/{key}?sig=1')
        self.assertIn('https://s3.example/hls/9/seg0.ts?sig=1', out)
        self.assertIn('https://s3.example/hls/9/seg1.ts?sig=1', out)
        self.assertIn('#EXTM3U', out)


class CatalogSlugUrlTests(TestCase):
    def test_title_and_watch_paths_and_legacy_redirect(self):
        from apps.anime.models import Anime, Season
        from apps.episode.models import Episode

        anime = Anime.objects.create(
            title='Qora Poyezd',
            description='x',
            poster=_tiny_gif(),
            kind=Anime.Kind.DRAMA,
        )
        season = Season.objects.create(anime=anime, number=1, release_date=2025)
        episode = Episode.objects.create(season=season, number=21, title='21-qism')
        self.assertEqual(anime.slug, 'qora-poyezd')

        title = self.client.get('/drama/qora-poyezd/')
        self.assertEqual(title.status_code, 200)

        watch = self.client.get('/drama/qora-poyezd/episode21/')
        self.assertEqual(watch.status_code, 200)
        self.assertContains(watch, 'watch-page')

        legacy = self.client.get('/detail/?id=' + str(anime.id), follow=False)
        self.assertIn(legacy.status_code, (301, 302))
        self.assertEqual(legacy['Location'], '/drama/qora-poyezd/')

        legacy_player = self.client.get(f'/player/?episode={episode.id}', follow=False)
        self.assertIn(legacy_player.status_code, (301, 302))
        self.assertEqual(legacy_player['Location'], '/drama/qora-poyezd/episode21/')

    def test_film_uses_kino_prefix(self):
        from apps.anime.models import Anime, Season
        from apps.episode.models import Episode

        film = Anime.objects.create(
            title='Oxirgi Stansiya',
            description='x',
            poster=_tiny_gif(),
            kind=Anime.Kind.FILM,
        )
        season = Season.objects.create(anime=film, number=1, release_date=2024)
        Episode.objects.create(season=season, number=1, title=film.title)
        self.assertEqual(self.client.get('/kino/oxirgi-stansiya/').status_code, 200)
        self.assertEqual(self.client.get('/kino/oxirgi-stansiya/episode1/').status_code, 200)


class ProductionSecretsTests(TestCase):
    def test_email_password_comes_from_env(self):
        import core.settings as settings_mod

        text = Path(settings_mod.__file__).read_text()
        self.assertIn("config('EMAIL_HOST_PASSWORD'", text)
        self.assertIn("config('EMAIL_HOST_USER'", text)
        self.assertNotRegex(text, r'EMAIL_HOST_PASSWORD\s*=\s*["\'][^"\']+["\']')
        self.assertIn('console.EmailBackend', text)

    def test_schema_docs_are_debug_only(self):
        from pathlib import Path as P
        import core.urls as urls_mod

        text = P(urls_mod.__file__).read_text()
        self.assertIn('if settings.DEBUG', text)
        self.assertIn('SpectacularSwaggerView', text)

    def test_google_callback_exists_without_locale_prefix(self):
        self.assertEqual(self.client.get('/api/auth/googleCallback').status_code, 302)

    def test_production_checks_catch_localhost_google(self):
        from apps.main.checks import production_ready

        with override_settings(
            DEBUG=False,
            TESTING=False,
            SECRET_KEY='x' * 50,
            REDIS_URL='redis://127.0.0.1:6379/0',
            ALLOWED_HOSTS=['animee.uz'],
            SITE_URL='https://animee.uz',
            GOOGLE_REDIRECT_URL='http://127.0.0.1:8000/api/auth/googleCallback',
        ):
            ids = {item.id for item in production_ready(None)}
        self.assertIn('animee.E005', ids)

    def test_production_checks_pass_on_https(self):
        from apps.main.checks import production_ready

        with override_settings(
            DEBUG=False,
            TESTING=False,
            SECRET_KEY='x' * 50,
            REDIS_URL='redis://127.0.0.1:6379/0',
            ALLOWED_HOSTS=['animee.uz'],
            SITE_URL='https://animee.uz',
            GOOGLE_REDIRECT_URL='https://animee.uz/uz/api/auth/googleCallback',
        ):
            self.assertEqual(production_ready(None), [])


class BanPageTests(TestCase):
    def test_banned_page_renders(self):
        response = self.client.get('/banned/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Hisob bloklangan', response.content)
        self.assertNotIn(b'Django', response.content)


class PublicShellTests(TestCase):
    def test_core_pages_load(self):
        for path in ('/', '/catalog/', '/auth/', '/profile/', '/lists/', '/dashboard/'):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, path)
            self.assertNotIn(b'Django', response.content)


class PageSplitTests(TestCase):
    def test_lists_and_profile_are_separate_pages(self):
        lists = self.client.get('/lists/')
        profile = self.client.get('/profile/')
        self.assertEqual(lists.status_code, 200)
        self.assertEqual(profile.status_code, 200)
        self.assertIn(b'listsRoot', lists.content)
        self.assertIn(b'profileRoot', profile.content)
        self.assertNotIn(b'listTabs', profile.content)
