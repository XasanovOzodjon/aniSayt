from django.test import TestCase
from rest_framework.test import APIClient

from apps.anime.models import Anime
from apps.anime.tests import _tiny_gif
from apps.users.models import CustomUser


class UserSearchTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.visible = CustomUser.objects.create_user(
            username='sakura.fan',
            email='sakura@example.com',
            password='Secret123!',
            first_name='Sakura',
            public_profile=True,
        )
        CustomUser.objects.create_user(
            username='hidden.user',
            email='hidden@example.com',
            password='Secret123!',
            first_name='Sakura',
            public_profile=False,
        )
        Anime.objects.create(title='Sakura Server', description='x', poster=_tiny_gif(), kind='anime')

    def test_guest_finds_public_users_not_private_or_titles(self):
        listed = self.client.get('/uz/api/search/users/?q=sakura')
        self.assertEqual(listed.status_code, 200, listed.content)
        names = [row['username'] for row in listed.json()['results']]
        self.assertEqual(names, ['sakura.fan'])
        self.assertNotIn('hidden.user', names)
        self.assertFalse(any('title' in row for row in listed.json()['results']))

    def test_short_query_is_empty(self):
        listed = self.client.get('/uz/api/search/users/?q=s')
        self.assertEqual(listed.json()['results'], [])


class CatalogKindSearchTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        Anime.objects.create(title='Neon Qish', description='x', poster=_tiny_gif(), kind='anime')
        Anime.objects.create(title='Neon Film', description='x', poster=_tiny_gif(), kind='film')

    def test_kind_filter_keeps_titles_apart(self):
        films = self.client.get('/uz/api/anime/?search=Neon&kind=film')
        data = films.json()
        titles = [row['title'] for row in (data['results'] if isinstance(data, dict) else data)]
        self.assertEqual(titles, ['Neon Film'])
        mixed = self.client.get('/uz/api/anime/?search=Neon')
        mixed_data = mixed.json()
        all_titles = [row['title'] for row in (mixed_data['results'] if isinstance(mixed_data, dict) else mixed_data)]
        self.assertCountEqual(all_titles, ['Neon Qish', 'Neon Film'])
        combined = self.client.get('/uz/api/search/?q=Neon')
        self.assertEqual(combined.status_code, 200, combined.content)
        payload = combined.json()
        self.assertIn('animes', payload)
        self.assertNotIn('users', payload)
        self.assertNotIn('results', payload)
