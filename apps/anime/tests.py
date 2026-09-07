from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase

from apps.anime.models import Anime, Genre


def _tiny_gif():
    return SimpleUploadedFile(
        "poster.gif",
        (
            b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!"
            b"\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01"
            b"\x00\x00\x02\x02D\x01\x00;"
        ),
        content_type="image/gif",
    )


class GenreApiTests(APITestCase):
    def test_guest_can_list_genres(self):
        Genre.objects.create(name="Action", slug="action")

        response = self.client.get("/uz/api/genres/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["name"], "Action")

    def test_guest_can_retrieve_a_genre(self):
        genre = Genre.objects.create(name="Comedy", slug="comedy")

        response = self.client.get(f"/uz/api/genres/{genre.pk}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["name"], "Comedy")

    def test_guest_can_filter_anime_by_genre(self):
        action = Genre.objects.create(name="Action", slug="action")
        comedy = Genre.objects.create(name="Comedy", slug="comedy")
        naruto = Anime.objects.create(
            title="Naruto",
            description="n",
            poster=_tiny_gif(),
        )
        other = Anime.objects.create(
            title="Comedy Show",
            description="c",
            poster=_tiny_gif(),
        )
        naruto.genres.add(action)
        other.genres.add(comedy)

        response = self.client.get("/uz/api/anime/", {"genres": action.pk})

        self.assertEqual(response.status_code, 200)
        titles = [row["title"] for row in response.json()]
        self.assertEqual(titles, ["Naruto"])
        self.assertEqual(response.json()[0]["genres"][0]["name"], "Action")

    def test_legacy_ganres_url_redirects_to_genres(self):
        response = self.client.get("/uz/api/ganres/", follow=False)

        self.assertIn(response.status_code, (301, 302))
        self.assertIn("/uz/api/genres/", response["Location"])
