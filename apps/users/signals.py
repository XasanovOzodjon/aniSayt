from apps.anime.models import Season
from django.db.models.signals import post_save
from django.dispatch import receiver

from .notices import notify_new_season


@receiver(post_save, sender=Season)
def season_created(sender, instance, created, **kwargs):
    if created:
        notify_new_season(instance)
