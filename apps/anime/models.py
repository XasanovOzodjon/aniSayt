from django.db import models


class Genre(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, max_length=100, blank=True, null=True)

    def __str__(self):
        return self.name


class Anime(models.Model):
    class Kind(models.TextChoices):
        ANIME = 'anime', 'Anime'
        DRAMA = 'drama', 'Drama'
        FILM = 'film', 'Kino'
        SERIAL = 'serial', 'Serial'

    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, max_length=100, blank=True, allow_unicode=True)
    description = models.TextField()
    poster = models.ImageField(upload_to="anime/posters/")
    genres = models.ManyToManyField(Genre)
    kind = models.CharField(max_length=8, choices=Kind.choices, default=Kind.ANIME, db_index=True)
    age_rating = models.CharField(
        max_length=4,
        choices=[
            ('0+', '0+'),
            ('6+', '6+'),
            ('12+', '12+'),
            ('16+', '16+'),
            ('18+', '18+'),
        ],
        default='16+',
        db_index=True,
    )
    next_title = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='previous_titles',
    )

    def is_seasonal(self):
        return self.kind != self.Kind.FILM

    def save(self, *args, **kwargs):
        if not self.slug:
            from .paths import unique_slug
            self.slug = unique_slug(self.title, exclude_pk=self.pk)
        super().save(*args, **kwargs)

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
