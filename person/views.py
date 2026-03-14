from .models import Person
from rest_framework.generics import ListAPIView, DestroyAPIView
from .serializers import PersonSerializer

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import  OrderingFilter


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
    
class PersonDetailView(DestroyAPIView):
    queryset = Person.objects.all()
    serializer_class = PersonSerializer

