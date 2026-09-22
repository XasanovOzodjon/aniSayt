from django.urls import path

from .consumers import PartyConsumer

websocket_urlpatterns = [
    path('ws/party/<str:code>/', PartyConsumer.as_asgi()),
]
