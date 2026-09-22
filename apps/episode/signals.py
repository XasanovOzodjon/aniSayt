from django.db.models.signals import post_save
from django.dispatch import receiver

from .ingest import convert_to_hls
from .models import Video


@receiver(post_save, sender=Video)
def convert_master(sender, instance, created, **kwargs):
    if not created:
        return
    if not instance.video:
        return
    convert_to_hls(instance)
