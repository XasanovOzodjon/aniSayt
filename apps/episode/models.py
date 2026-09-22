import os
import shutil
from django.db import models
from django.conf import settings


class Episode(models.Model):
    season = models.ForeignKey(
        "anime.Season",
        on_delete=models.CASCADE,
        related_name="episodes"
    )
    number = models.IntegerField()
    title = models.CharField(max_length=255)
    thumbnail = models.ImageField(
        upload_to="episodes/thumbs/",
        blank=True,
        null=True
    )

    class Meta:
        ordering = ["number"]
        unique_together = ["season", "number"]  # Bir seasonda ikki xil episode bo'lmasin

    def __str__(self):
        return f"{self.season.anime.title} S{self.season.number} E{self.number}"


class Video(models.Model):
    episode = models.ForeignKey(
        Episode,
        on_delete=models.CASCADE,
        related_name="videos"
    )
    language = models.CharField(max_length=50)
    translated_by = models.CharField(max_length=120, blank=True)
    video = models.FileField(upload_to="episodes/videos/", blank=True, null=True)
    source_url = models.CharField(max_length=1000, blank=True)
    hls_path = models.CharField(max_length=255, blank=True)
    ingest_error = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.episode} ({self.language})"

    def delete(self, *args, **kwargs):
        vid_id = self.pk
        if self.video:
            self.video.delete(save=False)
        from apps.main import object_storage as store
        if store.s3_enabled() and vid_id:
            store.delete_prefix(f'hls/{vid_id}/')
        else:
            hls_dir = os.path.join(settings.MEDIA_ROOT, "hls", str(vid_id))
            if os.path.isdir(hls_dir):
                shutil.rmtree(hls_dir)
        super().delete(*args, **kwargs)