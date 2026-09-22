import mimetypes
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.main import object_storage as store


class Command(BaseCommand):
    help = 'Upload local media/ files to S3 so every player can stream from the bucket.'

    def handle(self, *args, **options):
        if not store.s3_enabled():
            self.stderr.write('S3 yoqilmagan. .env da bucket va kalitlarni tekshiring.')
            return
        root = Path(settings.MEDIA_ROOT)
        if not root.is_dir():
            self.stderr.write(f'{root} yo‘q')
            return
        uploaded = 0
        skipped = 0
        for path in root.rglob('*'):
            if not path.is_file() or path.name.startswith('.'):
                continue
            rel = path.relative_to(root).as_posix()
            ctype = mimetypes.guess_type(path.name)[0] or ''
            try:
                store.upload_file(str(path), rel, ctype)
                uploaded += 1
            except Exception as exc:
                skipped += 1
                self.stderr.write(f'xato {rel}: {type(exc).__name__}')
        self.stdout.write(self.style.SUCCESS(
            f'S3 {store.bucket_name()} · {uploaded} fayl · {skipped} xato'
        ))
