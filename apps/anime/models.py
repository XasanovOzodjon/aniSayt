from django.db import models


class Genre(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, max_length=100, blank=True, null=True)

    def __str__(self):
        return self.name


class Anime(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    poster = models.ImageField(upload_to="anime/posters/")
    genres = models.ManyToManyField(Genre)

    def __str__(self):
        return self.title


class Season(models.Model):
    anime = models.ForeignKey(Anime, on_delete=models.CASCADE, related_name="seasons")
    number = models.IntegerField()
    release_date = models.IntegerField(default=2000)

    class Meta:
        unique_together = ["anime", "number"]

    def __str__(self):
        return f"{self.anime.title} Season {self.number}"
