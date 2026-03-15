from django.apps import AppConfig


class EpisodeConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.episode'

    def ready(self):
        import apps.episode.signals
        import apps.episode.translation