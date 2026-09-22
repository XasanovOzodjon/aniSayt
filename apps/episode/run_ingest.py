"""Run Master ingest in its own process so a Daphne restart does not kill the download."""
import os
import sys


def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
    import django
    django.setup()
    from apps.episode.ingest import ingest_video
    ingest_video(int(sys.argv[1]))


if __name__ == '__main__':
    main()
