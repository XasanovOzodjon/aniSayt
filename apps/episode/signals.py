import os
import subprocess
import sys

from django.conf import settings
from django.db import close_old_connections, transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from .ingest import convert_to_hls, ingest_video, scratch_dir
from .models import Video


def _run_ingest(pk):
    close_old_connections()
    try:
        ingest_video(pk)
    finally:
        close_old_connections()


def _spawn_ingest(pk):
    """Own process, not a Daphne thread — SIGTERM on the web app must not abort S3/HLS."""
    log_dir = scratch_dir()
    log_path = os.path.join(log_dir, f'ingest-{pk}.log')
    log = open(log_path, 'ab')
    subprocess.Popen(
        [sys.executable, os.path.join(settings.BASE_DIR, 'apps', 'episode', 'run_ingest.py'), str(pk)],
        cwd=str(settings.BASE_DIR),
        stdin=subprocess.DEVNULL,
        stdout=log,
        stderr=log,
        start_new_session=True,
        close_fds=True,
        env={**os.environ, 'DJANGO_SETTINGS_MODULE': 'core.settings'},
    )


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
    transaction.on_commit(lambda: _spawn_ingest(pk))
