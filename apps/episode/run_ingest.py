"""Run Master ingest in its own process so a Daphne restart does not kill the download."""
import os
import sys
from pathlib import Path

# `python apps/episode/run_ingest.py` puts this folder first on sys.path, so
# `import apps` would load episode/apps.py (AppConfig) instead of the package.
_SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = _SCRIPT_DIR.parents[1]
sys.path[:] = [p for p in sys.path if p and Path(p).resolve() != _SCRIPT_DIR]
sys.path.insert(0, str(ROOT))
_apps = sys.modules.get('apps')
if _apps is not None and not getattr(_apps, '__path__', None):
    sys.modules.pop('apps', None)


def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
    import django
    django.setup()
    from apps.episode.ingest import ingest_video
    ingest_video(int(sys.argv[1]))


if __name__ == '__main__':
    main()
