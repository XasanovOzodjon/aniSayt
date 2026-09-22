import os
import shutil
from pathlib import Path

from django.conf import settings
from django.db.models import Count

from apps.episode.models import Episode, Video

DEMO_NAME = 'demo.mp4'
MEDIA_REL = f'demo/{DEMO_NAME}'


def candidate_paths():
    home = Path.home()
    roots = [
        home / 'Downloads' / DEMO_NAME,
        home / 'Download' / DEMO_NAME,
        Path(settings.BASE_DIR) / 'download' / DEMO_NAME,
        Path(settings.MEDIA_ROOT) / MEDIA_REL,
    ]
    extra = os.environ.get('ANIMEE_DEMO_MP4')
    if extra:
        roots.insert(0, Path(extra))
    return roots


def find_demo_mp4():
    for path in candidate_paths():
        if path.is_file() and _looks_like_mp4(path):
            return path
    return None


def _looks_like_mp4(path: Path) -> bool:
    if path.stat().st_size < 64 * 1024:
        return False
    head = path.read_bytes()[:12]
    return b'ftyp' in head


def ensure_media_copy(src: Path) -> str:
    dest_dir = Path(settings.MEDIA_ROOT) / 'demo'
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / DEMO_NAME
    if not dest.exists() or dest.stat().st_size != src.stat().st_size:
        shutil.copy2(src, dest)
    return f'/media/{MEDIA_REL}'


def attach_demo_to_episodes(src=None):
    src = Path(src) if src else find_demo_mp4()
    if not src:
        return 0, ''
    url = ensure_media_copy(src)
    missing = (
        Episode.objects.annotate(n=Count('videos'))
        .filter(n=0)
        .iterator()
    )
    created = 0
    batch = []
    for episode in missing:
        batch.append(Video(episode=episode, language='uz', hls_path=url))
        if len(batch) >= 200:
            Video.objects.bulk_create(batch)
            created += len(batch)
            batch = []
    if batch:
        Video.objects.bulk_create(batch)
        created += len(batch)
    return created, url
