import threading

from django.conf import settings
from django.db import close_old_connections, transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from .ingest import convert_to_hls, ingest_video
from .models import Video


def _run_ingest(pk):
    close_old_connections()
    try:
        ingest_video(pk)
    finally:
        close_old_connections()


@receiver(post_save, sender=Video)
def convert_master(sender, instance, created, **kwargs):
    if not created:
        return
    if not instance.video and not instance.source_url:
        return
    if settings.TESTING:
        if instance.video:
            convert_to_hls(instance)
        return
    pk = instance.pk
    transaction.on_commit(
        lambda: threading.Thread(target=_run_ingest, args=(pk,), daemon=True).start()
    )
