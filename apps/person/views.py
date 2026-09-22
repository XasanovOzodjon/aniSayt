from .models import Person
from rest_framework.generics import ListAPIView, DestroyAPIView
from .serializers import PersonSerializer
from drf_spectacular.utils import extend_schema_view, extend_schema

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter


@extend_schema_view(
    get=extend_schema(tags=["Persons"]),
)
class PersonListView(ListAPIView):
    queryset = Person.objects.all()
    serializer_class = PersonSerializer
    
    filter_backends = [
        DjangoFilterBackend,
        OrderingFilter
    ]

    ordering_fields = [
        "rating",
    ]
    

@extend_schema_view(
    delete=extend_schema(tags=["Persons"]),
)
class PersonDetailView(DestroyAPIView):
    queryset = Person.objects.all()
    serializer_class = PersonSerializer

