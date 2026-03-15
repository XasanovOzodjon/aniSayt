from django.apps import AppConfig


class EpisodeConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'episode'

    def ready(self):
        import episode.signals
        import episode.translation