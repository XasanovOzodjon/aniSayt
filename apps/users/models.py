from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    telegram_id = models.BigIntegerField(unique=True, null=True, blank=True)
    telegram_username = models.CharField(max_length=64, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    photo = models.ImageField(upload_to='users/avatars/', blank=True, null=True)
    photo_url = models.URLField(max_length=500, blank=True, null=True)
    banner = models.ImageField(upload_to='users/banners/', blank=True, null=True)
    bio = models.CharField(max_length=280, blank=True)
    status_line = models.CharField(max_length=80, blank=True)
    show_watching = models.BooleanField(default=True)
    preferred_audio = models.CharField(
        max_length=2,
        choices=[('uz', 'UZ'), ('ru', 'RU')],
        default='uz',
    )
    preferred_subs = models.CharField(
        max_length=4,
        choices=[('uz', 'UZ'), ('ru', 'RU'), ('off', 'Off')],
        default='uz',
    )
    autoplay_next = models.BooleanField(default=True)
    public_profile = models.BooleanField(default=True)
    notify_telegram = models.BooleanField(default=True)
    notify_new_season = models.BooleanField(default=True)
    notify_new_episode = models.BooleanField(default=True)
    is_moderator = models.BooleanField(default=False)
    streak_count = models.PositiveIntegerField(default=0)
    streak_best = models.PositiveIntegerField(default=0)
    streak_days = models.PositiveIntegerField(default=0)
    streak_started_on = models.DateField(null=True, blank=True)
    streak_last_on = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.username


class UserList(models.Model):
    class Status(models.TextChoices):
        WATCHING = 'watching', 'Ko‘ryapman'
        COMPLETED = 'completed', 'Ko‘rib bo‘ldim'
        PLANNED = 'planned', 'Reja'
        DROPPED = 'dropped', 'Tashladim'
        FAVORITE = 'favorite', 'Sevimli'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='title_lists',
    )
    anime = models.ForeignKey(
        'anime.Anime',
        on_delete=models.CASCADE,
        related_name='user_lists',
    )
    status = models.CharField(max_length=16, choices=Status.choices)
    score = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'anime'], name='uniq_user_anime_list'),
        ]

    def __str__(self):
        return f'{self.user} · {self.anime_id} · {self.status}'


class Notice(models.Model):
    class Kind(models.TextChoices):
        NEW_SEASON = 'new_season', 'Yangi sezon'
        NEW_EPISODE = 'new_episode', 'Yangi qism'
        NEWS = 'news', 'Yangilik'
        MODERATION = 'moderation', 'Moderatsiya'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notices',
    )
    anime = models.ForeignKey(
        'anime.Anime',
        on_delete=models.CASCADE,
        related_name='notices',
        null=True,
        blank=True,
    )
    kind = models.CharField(max_length=16, choices=Kind.choices)
    title = models.CharField(max_length=200)
    body = models.TextField()
    sent_telegram = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user} · {self.kind}'


class Progress(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='progress',
    )
    episode = models.ForeignKey(
        'episode.Episode',
        on_delete=models.CASCADE,
        related_name='progress',
    )
    position = models.FloatField(default=0)
    duration = models.FloatField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'episode'], name='uniq_user_episode_progress'),
        ]


class Comment(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='comments',
    )
    episode = models.ForeignKey(
        'episode.Episode',
        on_delete=models.CASCADE,
        related_name='comments',
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        related_name='replies',
        null=True,
        blank=True,
    )
    body = models.TextField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user} · {self.episode_id}'


class CommentLike(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='comment_likes',
    )
    comment = models.ForeignKey(
        Comment,
        on_delete=models.CASCADE,
        related_name='likes',
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'comment'], name='uniq_user_comment_like'),
        ]


class EpisodeLike(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='episode_likes',
    )
    episode = models.ForeignKey(
        'episode.Episode',
        on_delete=models.CASCADE,
        related_name='likes',
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'episode'], name='uniq_user_episode_like'),
        ]

    def __str__(self):
        return f'{self.user} · {self.episode_id}'


class ProfileReport(models.Model):
    class Kind(models.TextChoices):
        PHOTO = 'photo', 'Profil rasmi'
        BANNER = 'banner', 'Banner'
        NICK = 'nick', 'Nick'
        BIO = 'bio', 'Tavsif'

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile_reports_sent',
    )
    target = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile_reports',
    )
    kind = models.CharField(max_length=12, choices=Kind.choices)
    reason = models.CharField(max_length=20, default='other')
    note = models.CharField(max_length=400, blank=True)
    snapshot = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['reporter', 'target', 'kind'],
                condition=models.Q(resolved_at__isnull=True),
                name='uniq_open_profile_report',
            ),
        ]

    def __str__(self):
        return f'{self.reporter} → {self.target} · {self.kind}'


class UserModeration(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='moderation',
    )
    banned_at = models.DateTimeField(null=True, blank=True)
    banned_until = models.DateTimeField(null=True, blank=True)
    ban_reason = models.CharField(max_length=400, blank=True)
    ban_allow_appeal = models.BooleanField(default=True)
    report_strikes = models.PositiveSmallIntegerField(default=0)
    report_mute_until = models.DateTimeField(null=True, blank=True)
    lock_username = models.BooleanField(default=False)
    lock_photo = models.BooleanField(default=False)
    keep_photo = models.BooleanField(default=False)
    lock_banner = models.BooleanField(default=False)
    keep_banner = models.BooleanField(default=False)
    lock_bio = models.BooleanField(default=False)
    keep_bio = models.BooleanField(default=False)
    lock_comments = models.BooleanField(default=False)

    def __str__(self):
        return f'mod · {self.user}'


class UnbanRequest(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='unban_requests',
    )
    body = models.CharField(max_length=800)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    accepted = models.BooleanField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['user'],
                condition=models.Q(resolved_at__isnull=True),
                name='uniq_open_unban_request',
            ),
        ]

    def __str__(self):
        return f'unban · {self.user}'

