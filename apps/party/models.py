from django.conf import settings
from django.db import models


class WatchParty(models.Model):
    class Control(models.TextChoices):
        HOST = 'host', 'Faqat host'
        SHARED = 'shared', 'Hammaga'

    code = models.CharField(max_length=12, unique=True, db_index=True)
    episode = models.ForeignKey(
        'episode.Episode',
        on_delete=models.CASCADE,
        related_name='watch_parties',
    )
    host = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='hosted_parties',
    )
    control = models.CharField(max_length=8, choices=Control.choices, default=Control.SHARED)
    want_playing = models.BooleanField(default=False)
    playing = models.BooleanField(default=False)
    position = models.FloatField(default=0)
    clock = models.DateTimeField(auto_now_add=True)
    buffering = models.JSONField(default=list, blank=True)
    require_camera = models.BooleanField(default=False)
    require_mic = models.BooleanField(default=False)
    closed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.code


class PartyMessage(models.Model):
    party = models.ForeignKey(WatchParty, on_delete=models.CASCADE, related_name='messages')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='party_messages',
    )
    body = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.party.code} · {self.user_id}'
