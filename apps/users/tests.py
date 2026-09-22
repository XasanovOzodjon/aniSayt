import json
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.users.auth_services import GoogleAuthService
from apps.users.emailService import check_email_pincode, send_email

CustomUser = get_user_model()


class GoogleUsernameTests(TestCase):
    def test_username_is_email_local_part(self):
        user = GoogleAuthService.get_user({
            'email': 'xasanov.hdjsks@gmail.com',
            'given_name': 'Hasan',
            'family_name': 'X',
            'picture': 'https://lh3.googleusercontent.com/a/demo=s96-c',
        })
        self.assertEqual(user.username, 'xasanov.hdjsks')
        self.assertEqual(user.email, 'xasanov.hdjsks@gmail.com')
        self.assertIn('s256', user.photo_url)

    def test_existing_email_keeps_username_and_updates_photo(self):
        existing = CustomUser.objects.create_user(
            username='chosen',
            email='xasanov.hdjsks@gmail.com',
            password='Secret123!',
        )
        user = GoogleAuthService.get_user({
            'email': 'xasanov.hdjsks@gmail.com',
            'picture': 'https://example.com/avatar.png',
        })
        self.assertEqual(user.pk, existing.pk)
        self.assertEqual(user.username, 'chosen')
        self.assertEqual(user.photo_url, 'https://example.com/avatar.png')

    def test_duplicate_local_part_gets_suffix(self):
        CustomUser.objects.create_user(
            username='same.user',
            email='same.user@other.com',
            password='Secret123!',
        )
        user = GoogleAuthService.get_user({
            'email': 'same.user@gmail.com',
        })
        self.assertEqual(user.username, 'same.user_2')
        self.assertEqual(user.email, 'same.user@gmail.com')


class EmailPinTests(TestCase):
    def _redis_store(self):
        store = {}
        client = MagicMock()
        client.set.side_effect = lambda key, value, ex=None: store.__setitem__(str(key), value)
        client.get.side_effect = lambda key: store.get(str(key))
        client.delete.side_effect = lambda key: store.pop(str(key), None)
        return store, client

    @patch('apps.users.emailService.send_mail')
    @patch('apps.users.emailService.redis.StrictRedis')
    def test_send_stores_hashed_pin_and_tries(self, redis_cls, send_mail):
        store, client = self._redis_store()
        redis_cls.return_value = client
        uid = send_email({
            'username': 'ali',
            'email': 'ali@example.com',
            'password': 'Secret123!',
        })
        self.assertTrue(send_mail.called)
        subject = send_mail.call_args.kwargs.get('subject') or send_mail.call_args[1].get('subject')
        if subject is None:
            subject = send_mail.call_args[0][0] if send_mail.call_args[0] else send_mail.call_args.kwargs['subject']
        self.assertIn('Animee', subject)
        payload = json.loads(store[uid])
        self.assertEqual(payload['count_try'], 5)
        self.assertIn('pin_code', payload)
        self.assertNotEqual(payload['pin_code'], '123456')
        self.assertIn('create_at', payload)

    @patch('apps.users.emailService.send_mail')
    @patch('apps.users.emailService.redis.StrictRedis')
    def test_wrong_pin_returns_401(self, redis_cls, send_mail):
        store, client = self._redis_store()
        redis_cls.return_value = client
        uid = send_email({
            'username': 'ali',
            'email': 'ali@example.com',
            'password': 'Secret123!',
        })
        self.assertEqual(check_email_pincode(uid, 111111), 401)
        payload = json.loads(store[uid])
        self.assertEqual(payload['count_try'], 4)

    @patch('apps.users.emailService.send_mail')
    @patch('apps.users.emailService.redis.StrictRedis')
    def test_correct_pin_returns_payload_and_deletes_key(self, redis_cls, send_mail):
        store, client = self._redis_store()
        redis_cls.return_value = client
        uid = send_email({
            'username': 'ali',
            'email': 'ali@example.com',
            'password': 'Secret123!',
        })
        body = send_mail.call_args.kwargs.get('message')
        if body is None:
            body = send_mail.call_args[1]['message'] if len(send_mail.call_args) > 1 else send_mail.call_args.kwargs['message']
        pin = int(body.split('kod: ')[1].split('\n')[0])
        data = check_email_pincode(uid, pin)
        self.assertEqual(data['email'], 'ali@example.com')
        self.assertNotIn(uid, store)


class ProfileSettingsTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='ali',
            email='ali@example.com',
            password='Secret123!',
        )
        from rest_framework.test import APIClient
        from rest_framework_simplejwt.tokens import RefreshToken
        self.client = APIClient()
        token = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')

    def test_change_username_and_bio(self):
        res = self.client.patch('/uz/api/auth/me/', {
            'username': 'ali.bek',
            'bio': 'Drama yaxshi ko‘raman',
        }, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['username'], 'ali.bek')
        self.assertEqual(res.json()['bio'], 'Drama yaxshi ko‘raman')
        self.assertIn('first_name', res.json())
        named = self.client.patch('/uz/api/auth/me/', {'first_name': 'Ozodjon Xasanov'}, format='json')
        self.assertEqual(named.status_code, 200)
        self.assertEqual(named.json()['first_name'], 'Ozodjon Xasanov')
        self.assertEqual(named.json()['role'], 'User')
        styled = self.client.patch('/uz/api/auth/me/', {
            'status_line': 'Hozir drama tomosha',
            'show_watching': False,
        }, format='json')
        self.assertEqual(styled.status_code, 200)
        self.assertEqual(styled.json()['status_line'], 'Hozir drama tomosha')
        self.assertFalse(styled.json()['show_watching'])
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'ali.bek')
        self.assertEqual(self.user.status_line, 'Hozir drama tomosha')
        self.assertFalse(self.user.show_watching)

    def test_reserved_username_rejected(self):
        res = self.client.patch('/uz/api/auth/me/', {'username': 'admin'}, format='json')
        self.assertEqual(res.status_code, 400)

    def test_duplicate_username_rejected(self):
        CustomUser.objects.create_user(username='taken', email='t@example.com', password='Secret123!')
        res = self.client.patch('/uz/api/auth/me/', {'username': 'taken'}, format='json')
        self.assertEqual(res.status_code, 400)

    def test_list_upsert_one_row_per_title(self):
        from apps.anime.tests import _tiny_gif
        from apps.anime.models import Anime
        from apps.users.models import UserList
        anime = Anime.objects.create(title='Neon Qish', description='x', poster=_tiny_gif(), kind='anime')
        first = self.client.put('/uz/api/auth/lists/', {'anime': anime.id, 'status': 'watching'}, format='json')
        second = self.client.put('/uz/api/auth/lists/', {'anime': anime.id, 'status': 'completed'}, format='json')
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(UserList.objects.filter(user=self.user, anime=anime).count(), 1)
        self.assertEqual(UserList.objects.get(user=self.user, anime=anime).status, 'completed')

    def test_notify_and_subs_patch(self):
        res = self.client.patch('/uz/api/auth/me/', {
            'preferred_subs': 'ru',
            'notify_telegram': False,
            'notify_new_season': False,
            'notify_new_episode': True,
        }, format='json')
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body['preferred_subs'], 'ru')
        self.assertFalse(body['notify_telegram'])
        self.assertFalse(body['notify_new_season'])
        self.assertTrue(body['notify_new_episode'])
        self.assertFalse(body['telegram_linked'])


class KindFilterTests(TestCase):
    def test_filter_by_kind(self):
        from rest_framework.test import APIClient
        from apps.anime.tests import _tiny_gif
        from apps.anime.models import Anime
        Anime.objects.create(title='A', description='x', poster=_tiny_gif(), kind='anime')
        Anime.objects.create(title='D', description='x', poster=_tiny_gif(), kind='drama')
        Anime.objects.create(title='K', description='x', poster=_tiny_gif(), kind='film')
        Anime.objects.create(title='S', description='x', poster=_tiny_gif(), kind='serial')
        client = APIClient()
        res = client.get('/uz/api/anime/', {'kind': 'drama'})
        self.assertEqual(res.status_code, 200)
        payload = res.json()
        rows = payload['results'] if isinstance(payload, dict) else payload
        self.assertEqual([row['title'] for row in rows], ['D'])
        serial = client.get('/uz/api/anime/', {'kind': 'serial'})
        serial_rows = serial.json()['results'] if isinstance(serial.json(), dict) else serial.json()
        self.assertEqual([row['title'] for row in serial_rows], ['S'])


class PhotoUploadTests(TestCase):
    def setUp(self):
        import tempfile
        from django.test import override_settings
        from rest_framework.test import APIClient
        from rest_framework_simplejwt.tokens import RefreshToken

        self.user = CustomUser.objects.create_user(
            username='rasm',
            email='rasm@example.com',
            password='Secret123!',
        )
        self.client = APIClient()
        token = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')
        self._tmp = tempfile.TemporaryDirectory()
        self._cm = override_settings(MEDIA_ROOT=self._tmp.name)
        self._cm.enable()

    def tearDown(self):
        self._cm.disable()
        self._tmp.cleanup()

    def _jpeg(self):
        from io import BytesIO
        from django.core.files.uploadedfile import SimpleUploadedFile
        from PIL import Image
        buf = BytesIO()
        Image.new('RGB', (24, 24), 'purple').save(buf, format='JPEG')
        return SimpleUploadedFile('face.jpg', buf.getvalue(), content_type='image/jpeg')

    def test_upload_and_clear_photo(self):
        res = self.client.post('/uz/api/auth/me/photo/', {'photo': self._jpeg()}, format='multipart')
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()['photo'])
        self.user.refresh_from_db()
        self.assertTrue(self.user.photo)
        gone = self.client.delete('/uz/api/auth/me/photo/')
        self.assertEqual(gone.status_code, 200)
        self.assertEqual(gone.json()['photo'], '')

    def test_upload_and_clear_banner(self):
        res = self.client.post('/uz/api/auth/me/banner/', {'banner': self._jpeg()}, format='multipart')
        self.assertEqual(res.status_code, 200, res.content)
        self.assertTrue(res.json()['banner'])
        self.user.refresh_from_db()
        self.assertTrue(self.user.banner)
        gone = self.client.delete('/uz/api/auth/me/banner/')
        self.assertEqual(gone.status_code, 200)
        self.assertEqual(gone.json()['banner'], '')
        me = self.client.get('/uz/api/auth/me/')
        self.assertIn('stats', me.json())
        self.assertIn('joined_at', me.json()['stats'])


class TelegramLinkTests(TestCase):
    def _redis_store(self):
        store = {}
        client = MagicMock()
        client.set.side_effect = lambda key, value, ex=None: store.__setitem__(str(key), value)
        client.get.side_effect = lambda key: store.get(str(key))
        client.close.side_effect = lambda: None
        return store, client

    def setUp(self):
        from rest_framework.test import APIClient
        from rest_framework_simplejwt.tokens import RefreshToken
        self.user = CustomUser.objects.create_user(
            username='tguser',
            email='tguser@example.com',
            password='Secret123!',
        )
        self.client = APIClient()
        token = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')

    def test_link_requires_login(self):
        from rest_framework.test import APIClient
        res = APIClient().get('/uz/api/auth/telegram-login/', {'purpose': 'link'})
        self.assertEqual(res.status_code, 401)

    @patch('apps.users.telegram.Redis')
    def test_link_and_poll(self, redis_cls):
        from apps.users.telegram import complete_bot_start
        store, client = self._redis_store()
        redis_cls.return_value = client
        res = self.client.get('/uz/api/auth/telegram-login/', {'purpose': 'link'})
        self.assertEqual(res.status_code, 200)
        unic = res.json()['unicID']
        self.assertTrue(res.json()['tg_url'])
        reply = complete_bot_start(unic, {'telegram_id': 4242, 'username': 'ali_tg'})
        self.assertIn('ulandi', reply.lower())
        poll = self.client.post('/uz/api/auth/telegram-login/', {'unicID': unic}, format='json')
        self.assertEqual(poll.status_code, 200)
        self.assertEqual(poll.json()['status'], 'linked')
        self.user.refresh_from_db()
        self.assertEqual(self.user.telegram_id, 4242)
        self.assertEqual(self.user.telegram_username, 'ali_tg')
        unlinked = self.client.post('/uz/api/auth/telegram-unlink/', {}, format='json')
        self.assertEqual(unlinked.status_code, 200)
        self.assertFalse(unlinked.json()['telegram_linked'])


class NewSeasonNoticeTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='watcher',
            email='watcher@example.com',
            password='Secret123!',
            telegram_id=9001,
            notify_telegram=True,
            notify_new_season=True,
        )

    @patch('apps.users.notices.send_telegram', return_value=True)
    def test_season_two_notifies_list_user(self, send):
        from apps.anime.models import Anime, Season
        from apps.anime.tests import _tiny_gif
        from apps.users.models import Notice, UserList
        anime = Anime.objects.create(title='Neon Qish', description='x', poster=_tiny_gif(), kind='anime')
        UserList.objects.create(user=self.user, anime=anime, status='watching')
        Season.objects.create(anime=anime, number=2, release_date=2026)
        notice = Notice.objects.get(user=self.user)
        self.assertEqual(notice.kind, 'new_season')
        self.assertTrue(notice.sent_telegram)
        send.assert_called()
        from rest_framework.test import APIClient
        from rest_framework_simplejwt.tokens import RefreshToken
        client = APIClient()
        token = RefreshToken.for_user(self.user)
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')
        listing = client.get('/uz/api/auth/notices/')
        self.assertEqual(listing.status_code, 200)
        body = listing.json()
        self.assertEqual(body['unread_count'], 1)
        self.assertFalse(body['results'][0]['read'])
        self.assertEqual(body['results'][0]['kind'], 'new_season')
        read = client.post(f'/uz/api/auth/notices/{notice.id}/read/', {}, format='json')
        self.assertEqual(read.status_code, 200)
        self.assertEqual(read.json()['unread_count'], 0)
        self.assertTrue(read.json()['notice']['read'])
        listing2 = client.get('/uz/api/auth/notices/?unread=1')
        self.assertEqual(listing2.json()['results'], [])

    def test_mark_all_read(self):
        from apps.users.models import Notice
        from rest_framework.test import APIClient
        from rest_framework_simplejwt.tokens import RefreshToken
        Notice.objects.create(user=self.user, kind='news', title='Animee yangilik', body='Inbox ochiq.')
        Notice.objects.create(user=self.user, kind='news', title='Ikkinchi', body='Yana.')
        client = APIClient()
        token = RefreshToken.for_user(self.user)
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')
        res = client.post('/uz/api/auth/notices/read-all/', {}, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['unread_count'], 0)
        self.assertEqual(client.get('/uz/api/auth/notices/').json()['unread_count'], 0)

    def test_season_one_is_silent(self):
        from apps.anime.models import Anime, Season
        from apps.anime.tests import _tiny_gif
        from apps.users.models import Notice, UserList
        anime = Anime.objects.create(title='Yangi', description='x', poster=_tiny_gif(), kind='anime')
        UserList.objects.create(user=self.user, anime=anime, status='watching')
        Season.objects.create(anime=anime, number=1, release_date=2026)
        self.assertEqual(Notice.objects.count(), 0)


class ProgressApiTests(TestCase):
    def setUp(self):
        from rest_framework.test import APIClient
        from rest_framework_simplejwt.tokens import RefreshToken
        from apps.anime.models import Anime, Season
        from apps.anime.tests import _tiny_gif
        from apps.episode.models import Episode

        self.user = CustomUser.objects.create_user(
            username='watch', email='watch@example.com', password='Secret123!',
        )
        anime = Anime.objects.create(title='Neon Qish', description='x', poster=_tiny_gif(), kind='anime')
        season = Season.objects.create(anime=anime, number=1, release_date=2026)
        self.episode = Episode.objects.create(season=season, number=1, title='1-qism')
        self.client = APIClient()
        token = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')

    def test_guest_denied(self):
        from rest_framework.test import APIClient
        anon = APIClient()
        self.assertEqual(anon.put(f'/uz/api/auth/progress/{self.episode.pk}/', {
            'position': 293,
        }, format='json').status_code, 401)

    def test_save_and_resume(self):
        url = f'/uz/api/auth/progress/{self.episode.pk}/'
        empty = self.client.get(url)
        self.assertEqual(empty.status_code, 200)
        self.assertEqual(empty.json()['position'], 0)
        saved = self.client.put(url, {'position': 293, 'duration': 1336}, format='json')
        self.assertEqual(saved.status_code, 200, saved.content)
        self.assertEqual(saved.json()['position'], 293)
        again = self.client.get(url)
        self.assertEqual(again.json()['position'], 293)
        self.client.delete(url)
        self.assertEqual(self.client.get(url).json()['position'], 0)

    def test_watching_an_episode_lights_olovcha(self):
        url = f'/uz/api/auth/progress/{self.episode.pk}/'
        self.client.put(url, {'position': 10, 'duration': 1336}, format='json')
        cold = self.client.get('/uz/api/auth/me/').json()['streak']
        self.assertEqual(cold['current'], 0)
        self.assertFalse(cold['alive'])
        self.client.put(url, {'position': 293, 'duration': 1336}, format='json')
        lit = self.client.get('/uz/api/auth/me/').json()['streak']
        self.assertEqual(lit['current'], 1)
        self.assertEqual(lit['best'], 1)
        self.assertEqual(lit['days'], 1)
        self.assertTrue(lit['alive'])
        self.assertTrue(lit['today'])
        self.assertTrue(lit['started_on'])
        self.client.put(url, {'position': 400, 'duration': 1336}, format='json')
        again = self.client.get('/uz/api/auth/me/').json()['streak']
        self.assertEqual(again['current'], 1)
        self.assertEqual(again['days'], 1)


class StreakTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='olov', email='olov@example.com', password='Secret123!',
        )

    def test_consecutive_days_grow_and_a_gap_keeps_the_best(self):
        from datetime import date
        from apps.users.streak import as_dict, record_watch

        record_watch(self.user, 120, on=date(2026, 9, 18))
        record_watch(self.user, 120, on=date(2026, 9, 19))
        record_watch(self.user, 120, on=date(2026, 9, 20))
        three = as_dict(self.user, today=date(2026, 9, 20))
        self.assertEqual(three['current'], 3)
        self.assertEqual(three['best'], 3)
        self.assertEqual(three['started_on'], '2026-09-18')
        self.assertEqual(three['days'], 3)
        self.assertTrue(three['today'])

        waiting = as_dict(self.user, today=date(2026, 9, 21))
        self.assertEqual(waiting['current'], 3)
        self.assertTrue(waiting['alive'])
        self.assertFalse(waiting['today'])

        broken = as_dict(self.user, today=date(2026, 9, 22))
        self.assertEqual(broken['current'], 0)
        self.assertFalse(broken['alive'])
        self.assertEqual(broken['best'], 3)
        self.assertEqual(broken['started_on'], '')

        record_watch(self.user, 120, on=date(2026, 9, 22))
        restarted = as_dict(self.user, today=date(2026, 9, 22))
        self.assertEqual(restarted['current'], 1)
        self.assertEqual(restarted['best'], 3)
        self.assertEqual(restarted['started_on'], '2026-09-22')
        self.assertEqual(restarted['days'], 4)


class ProfileReportTests(TestCase):
    def setUp(self):
        from rest_framework.test import APIClient
        from rest_framework_simplejwt.tokens import RefreshToken
        self.reporter = CustomUser.objects.create_user(
            username='reporter', email='rep@example.com', password='Secret123!',
        )
        self.target = CustomUser.objects.create_user(
            username='target.user', email='tgt@example.com', password='Secret123!',
            first_name='Ali', bio='Oddiy bio',
        )
        self.client = APIClient()
        token = RefreshToken.for_user(self.reporter)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')
        self.url = f'/uz/api/auth/u/{self.target.username}/report/'

    def test_guest_cannot_report(self):
        from rest_framework.test import APIClient
        anon = APIClient()
        self.assertEqual(anon.post(self.url, {'kind': 'bio'}, format='json').status_code, 401)

    def test_user_reports_photo_banner_nick_or_bio(self):
        posted = self.client.post(self.url, {'kind': 'bio', 'reason': 'insult', 'note': 'Haqorat'}, format='json')
        self.assertEqual(posted.status_code, 201, posted.content)
        self.assertEqual(posted.json()['kind'], 'bio')
        self.assertEqual(posted.json()['reason'], 'insult')
        self.assertEqual(self.client.post(self.url, {'kind': 'nick'}, format='json').status_code, 400)
        again = self.client.post(self.url, {'kind': 'bio', 'reason': 'spam'}, format='json')
        self.assertEqual(again.status_code, 400)
        nick = self.client.post(self.url, {'kind': 'nick', 'reason': 'impersonation'}, format='json')
        self.assertEqual(nick.status_code, 201)
        self.assertEqual(self.client.post(self.url, {'kind': 'photo', 'reason': 'porn'}, format='json').status_code, 201)
        self.assertEqual(self.client.post(self.url, {'kind': 'banner', 'reason': 'hate'}, format='json').status_code, 201)
        own = self.client.post(f'/uz/api/auth/u/{self.reporter.username}/report/', {'kind': 'bio', 'reason': 'insult'}, format='json')
        self.assertEqual(own.status_code, 400)
        bad = self.client.post(self.url, {'kind': 'spam', 'reason': 'insult'}, format='json')
        self.assertEqual(bad.status_code, 400)


class CommentApiTests(TestCase):
    def setUp(self):
        from rest_framework.test import APIClient
        from rest_framework_simplejwt.tokens import RefreshToken
        from apps.anime.models import Anime, Season
        from apps.anime.tests import _tiny_gif
        from apps.episode.models import Episode

        self.user = CustomUser.objects.create_user(
            username='talk', email='talk@example.com', password='Secret123!',
        )
        anime = Anime.objects.create(title='Neon Qish', description='x', poster=_tiny_gif(), kind='anime')
        season = Season.objects.create(anime=anime, number=1, release_date=2026)
        self.episode = Episode.objects.create(season=season, number=1, title='1-qism')
        self.client = APIClient()
        token = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')
        self.url = f'/uz/api/auth/episodes/{self.episode.pk}/comments/'
        self.like = f'/uz/api/auth/episodes/{self.episode.pk}/like/'

    def test_guest_reads_but_cannot_write(self):
        from rest_framework.test import APIClient
        anon = APIClient()
        self.assertEqual(anon.get(self.url).status_code, 200)
        self.assertEqual(anon.post(self.url, {'body': 'salom'}, format='json').status_code, 401)
        self.assertEqual(anon.post(self.like, {}, format='json').status_code, 401)

    def test_comment_reply_and_likes(self):
        posted = self.client.post(self.url, {'body': 'Yaxshi qism'}, format='json')
        self.assertEqual(posted.status_code, 201, posted.content)
        cid = posted.json()['id']
        reply = self.client.post(self.url, {'body': 'Roziman', 'parent': cid}, format='json')
        self.assertEqual(reply.status_code, 201)
        self.assertEqual(reply.json()['parent'], cid)
        listed = self.client.get(self.url)
        self.assertEqual(listed.json()['count'], 1)
        self.assertEqual(len(listed.json()['results'][0]['replies']), 1)
        liked = self.client.post(f'/uz/api/auth/comments/{cid}/like/', {}, format='json')
        self.assertTrue(liked.json()['liked'])
        self.assertEqual(liked.json()['likes'], 1)
        ep_like = self.client.post(self.like, {}, format='json')
        self.assertTrue(ep_like.json()['liked'])
        self.assertEqual(ep_like.json()['likes'], 1)


class ModerationTests(TestCase):
    def setUp(self):
        from rest_framework.test import APIClient
        from rest_framework_simplejwt.tokens import RefreshToken
        self.admin = CustomUser.objects.create_user(
            username='ops', email='ops@example.com', password='Secret123!',
            is_staff=True, is_superuser=True,
        )
        self.user = CustomUser.objects.create_user(
            username='banned.one', email='b@example.com', password='Secret123!',
            first_name='Bek', bio='Salom',
        )
        self.client = APIClient()
        token = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')
        self.admin_client = APIClient()
        admin_token = RefreshToken.for_user(self.admin)
        self.admin_client.credentials(HTTP_AUTHORIZATION=f'Bearer {admin_token.access_token}')

    def test_public_streak_hides_due_today(self):
        from datetime import date
        from unittest.mock import patch
        from apps.users.streak import record_watch
        from apps.users.profile import public_payload
        record_watch(self.user, 120, on=date(2026, 9, 21))
        with patch('apps.users.streak.timezone.localdate', return_value=date(2026, 9, 22)):
            owner = public_payload(self.user, owner=True)
            other = public_payload(self.user, owner=False)
        self.assertFalse(owner['streak']['today'])
        self.assertEqual(owner['streak']['current'], 1)
        self.assertTrue(other['streak']['today'])
        self.assertEqual(other['streak']['current'], 1)

    def test_ban_blocks_api_and_allows_me_and_appeal(self):
        banned = self.admin_client.patch(
            f'/uz/api/dashboard/users/{self.user.pk}/',
            {'ban': {'reason': 'Haqorat', 'allow_appeal': True}},
            format='json',
        )
        self.assertEqual(banned.status_code, 200, banned.content)
        self.assertTrue(banned.json()['banned'])
        me = self.client.get('/uz/api/auth/me/')
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()['banned']['reason'], 'Haqorat')
        lists = self.client.get('/uz/api/auth/lists/')
        self.assertEqual(lists.status_code, 403)
        self.assertEqual(lists.json()['code'], 'banned')
        no_appeal_ban = self.admin_client.patch(
            f'/uz/api/dashboard/users/{self.user.pk}/',
            {'ban': {'reason': 'Qattiq', 'allow_appeal': False}},
            format='json',
        )
        self.assertEqual(no_appeal_ban.status_code, 200)
        blocked = self.client.post('/uz/api/auth/ban/appeal/', {'body': 'Iltimos oching'}, format='json')
        self.assertEqual(blocked.status_code, 400)
        self.admin_client.patch(
            f'/uz/api/dashboard/users/{self.user.pk}/',
            {'ban': {'reason': 'Haqorat', 'allow_appeal': True}},
            format='json',
        )
        asked = self.client.post('/uz/api/auth/ban/appeal/', {'body': 'Iltimos oching'}, format='json')
        self.assertEqual(asked.status_code, 200, asked.content)
        appeals = self.admin_client.get('/uz/api/dashboard/appeals/')
        self.assertEqual(appeals.status_code, 200)
        rows = appeals.json()['results']
        self.assertEqual(rows[0]['username'], 'banned.one')
        self.assertEqual(rows[0]['user_id'], self.user.pk)
        accepted = self.admin_client.patch(
            f'/uz/api/dashboard/appeals/{rows[0]["id"]}/',
            {'accepted': True},
            format='json',
        )
        self.assertEqual(accepted.status_code, 200, accepted.content)
        lists = self.client.get('/uz/api/auth/lists/')
        self.assertEqual(lists.status_code, 200)

    def test_dashboard_opens_the_user_profile(self):
        got = self.admin_client.get(f'/uz/api/dashboard/users/{self.user.pk}/')
        self.assertEqual(got.status_code, 200, got.content)
        body = got.json()
        self.assertEqual(body['username'], 'banned.one')
        self.assertEqual(body['bio'], 'Salom')
        self.assertIn('reports', body)
        self.assertIn('locks', body)

    def test_locks_and_comment_mute_and_false_report(self):
        from apps.anime.models import Anime, Season
        from apps.anime.tests import _tiny_gif
        from apps.episode.models import Episode
        from apps.users.models import Notice
        locked = self.admin_client.patch(
            f'/uz/api/dashboard/users/{self.user.pk}/',
            {'locks': {'username': True, 'bio': True, 'comments': True, 'bio_keep': True}},
            format='json',
        )
        self.assertEqual(locked.status_code, 200, locked.content)
        name = self.client.patch('/uz/api/auth/me/', {'username': 'new.name'}, format='json')
        self.assertEqual(name.status_code, 400)
        bio = self.client.patch('/uz/api/auth/me/', {'bio': ''}, format='json')
        self.assertEqual(bio.status_code, 400)
        anime = Anime.objects.create(title='X', description='x', poster=_tiny_gif(), kind='anime')
        season = Season.objects.create(anime=anime, number=1, release_date=2026)
        episode = Episode.objects.create(season=season, number=1, title='1')
        comment = self.client.post(f'/uz/api/auth/episodes/{episode.pk}/comments/', {'body': 'salom'}, format='json')
        self.assertEqual(comment.status_code, 400)
        cleared = self.admin_client.patch(
            f'/uz/api/dashboard/users/{self.user.pk}/',
            {'clear': 'bio'},
            format='json',
        )
        self.assertEqual(cleared.status_code, 200)
        self.assertTrue(Notice.objects.filter(user=self.user, kind='moderation').exists())
        self.admin_client.patch(f'/uz/api/dashboard/users/{self.user.pk}/', {'warn_reporter': True}, format='json')
        self.admin_client.patch(f'/uz/api/dashboard/users/{self.user.pk}/', {'warn_reporter': True}, format='json')
        other = CustomUser.objects.create_user(username='other.one', email='o@example.com', password='Secret123!')
        filed = self.client.post(
            f'/uz/api/auth/u/{other.username}/report/',
            {'kind': 'bio', 'reason': 'spam'},
            format='json',
        )
        self.assertEqual(filed.status_code, 400)


