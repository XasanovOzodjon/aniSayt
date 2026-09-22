from django.urls import path

from .views import PartyCreateView, PartyDetailView, PartyPreviewView

urlpatterns = [
    path('party/', PartyCreateView.as_view(), name='party_create'),
    path('party/<str:code>/preview/', PartyPreviewView.as_view(), name='party_preview'),
    path('party/<str:code>/', PartyDetailView.as_view(), name='party_detail'),
]
