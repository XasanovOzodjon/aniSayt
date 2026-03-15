import os
import subprocess

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings

from .models import Video


@receiver(post_save, sender=Video)
def convert_to_hls(sender, instance, created, **kwargs):

    if not created:
        return

    video_path = instance.video.path

    output_dir = os.path.join(settings.MEDIA_ROOT, "hls", str(instance.id))
    os.makedirs(output_dir, exist_ok=True)

    output_file = os.path.join(output_dir, "master.m3u8")

    cmd = [
        "ffmpeg",
        "-i", video_path,
        "-preset", "fast",
        "-g", "48",
        "-sc_threshold", "0",
        "-map", "0:v",
        "-map", "0:a",
        "-f", "hls",
        "-hls_time", "6",
        "-hls_playlist_type", "vod",
        output_file
    ]

    subprocess.run(cmd)

    instance.hls_path = f"/media/hls/{instance.id}/master.m3u8"
    instance.save(update_fields=["hls_path"])