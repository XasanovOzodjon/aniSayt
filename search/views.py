from django.db.models import Q, FloatField
from django.db.models.functions import Greatest
from django.contrib.postgres.search import (
    TrigramSimilarity,
    TrigramWordSimilarity,
)
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from anime.models import Anime, Ganre
from person.models import Person
from .serializers import AnimeSearchSerializer, PersonSearchSerializer, CombinedSearchSerializer

# Minimal o'xshashlik chegarasi (0.0 - 1.0)
# 0.15 = biroz xato yozsa ham topadi
# 0.3  = aniqroq yozish kerak
SIMILARITY_THRESHOLD = 0.15


class AnimeSearchView(APIView):
    """
    Anime qidirish — trigram fuzzy search.
    Xato yozilsa ham topadi.

    GET /api/search/anime/?q=naruto
    GET /api/search/anime/?q=nruto        ← xato, lekin topadi
    GET /api/search/anime/?q=naruto&genre=action
    GET /api/search/anime/?genre=action   ← faqat janr filter
    """

    def get(self, request):
        q = request.query_params.get("q", "").strip()
        genre = request.query_params.get("genre", "").strip()

        if not q and not genre:
            return Response(
                {"detail": "Kamida 'q' yoki 'genre' parametri kerak."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        queryset = Anime.objects.prefetch_related("ganres")

        if q:
            queryset = (
                queryset
                .annotate(
                    similarity=Greatest(
                        TrigramSimilarity("title", q),
                        TrigramWordSimilarity(q, "title"),
                        output_field=FloatField(),
                    )
                )
                .filter(
                    Q(similarity__gte=SIMILARITY_THRESHOLD) |
                    Q(title__icontains=q)
                )
                .order_by("-similarity")
            )

        if genre:
            queryset = queryset.filter(ganres__name__icontains=genre).distinct()

        serializer = AnimeSearchSerializer(queryset, many=True, context={"request": request})
        return Response({
            "count": queryset.count(),
            "results": serializer.data,
        })


class PersonSearchView(APIView):
    """
    Personaj qidirish — trigram fuzzy search.
    Xato yozilsa ham topadi.

    GET /api/search/person/?q=naruto
    GET /api/search/person/?q=sakra       ← xato, lekin topadi
    GET /api/search/person/?q=sakura&anime_id=1
    """

    def get(self, request):
        q = request.query_params.get("q", "").strip()
        anime_id = request.query_params.get("anime_id", "").strip()

        if not q and not anime_id:
            return Response(
                {"detail": "Kamida 'q' yoki 'anime_id' parametri kerak."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        queryset = Person.objects.select_related("anime")

        if q:
            queryset = (
                queryset
                .annotate(
                    similarity=Greatest(
                        TrigramSimilarity("fullname", q),
                        TrigramWordSimilarity(q, "fullname"),
                        TrigramSimilarity("anime__title", q),
                        output_field=FloatField(),
                    )
                )
                .filter(
                    Q(similarity__gte=SIMILARITY_THRESHOLD) |
                    Q(fullname__icontains=q) |
                    Q(anime__title__icontains=q)
                )
                .order_by("-similarity")
            )

        if anime_id:
            if not anime_id.isdigit():
                return Response(
                    {"detail": "'anime_id' raqam bo'lishi kerak."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            queryset = queryset.filter(anime_id=int(anime_id))

        serializer = PersonSearchSerializer(queryset, many=True, context={"request": request})
        return Response({
            "count": queryset.count(),
            "results": serializer.data,
        })


class CombinedSearchView(APIView):
    """
    Bitta so'rov — anime + personaj, fuzzy search.

    GET /api/search/?q=naruto
    GET /api/search/?q=nruto       ← xato, lekin topadi
    GET /api/search/?q=naruto&genre=action
    """

    def get(self, request):
        q = request.query_params.get("q", "").strip()
        genre = request.query_params.get("genre", "").strip()

        if not q and not genre:
            return Response(
                {"detail": "Kamida 'q' parametri kerak."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # --- Anime ---
        anime_qs = Anime.objects.prefetch_related("ganres")
        if q:
            anime_qs = (
                anime_qs
                .annotate(
                    similarity=Greatest(
                        TrigramSimilarity("title", q),
                        TrigramWordSimilarity(q, "title"),
                        output_field=FloatField(),
                    )
                )
                .filter(
                    Q(similarity__gte=SIMILARITY_THRESHOLD) |
                    Q(title__icontains=q)
                )
                .order_by("-similarity")
            )
        if genre:
            anime_qs = anime_qs.filter(ganres__name__icontains=genre).distinct()

        # --- Person ---
        person_qs = Person.objects.select_related("anime")
        if q:
            person_qs = (
                person_qs
                .annotate(
                    similarity=Greatest(
                        TrigramSimilarity("fullname", q),
                        TrigramWordSimilarity(q, "fullname"),
                        TrigramSimilarity("anime__title", q),
                        output_field=FloatField(),
                    )
                )
                .filter(
                    Q(similarity__gte=SIMILARITY_THRESHOLD) |
                    Q(fullname__icontains=q) |
                    Q(anime__title__icontains=q)
                )
                .order_by("-similarity")
            )

        data = {
            "animes": anime_qs,
            "persons": person_qs,
        }

        serializer = CombinedSearchSerializer(data, context={"request": request})
        return Response(serializer.data)


class GenreListView(APIView):
    """
    Filter uchun barcha janrlar ro'yxati.
    GET /api/search/genres/
    """

    def get(self, request):
        genres = Ganre.objects.values("id", "name").order_by("name")
        return Response({"results": list(genres)})