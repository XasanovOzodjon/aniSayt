from django.db import models


class SiteSettings(models.Model):
    player_poster = models.ImageField(upload_to='site/', blank=True)

    class Meta:
        verbose_name = 'Site settings'
        verbose_name_plural = 'Site settings'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def __str__(self):
        return 'Site settings'
