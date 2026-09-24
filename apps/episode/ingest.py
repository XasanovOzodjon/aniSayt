import ipaddress
import logging
import mimetypes
import os
import shutil
import socket
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from django.conf import settings
from django.core.cache import cache
from django.core.files import File

from apps.main import object_storage as store

logger = logging.getLogger(__name__)

MAX_DOWNLOAD_BYTES = 4 * 1024 * 1024 * 1024
CHUNK = 1024 * 1024
UPLOAD_CHUNK = 4 * 1024 * 1024
MAX_UPLOAD_CHUNK = 8 * 1024 * 1024
TIMEOUT = 1200
USER_AGENT = (
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
    'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
)


class IngestError(ValueError):
    def __init__(self, message):
        super().__init__(message)
        self.message = message


def is_playlist_url(url: str) -> bool:
    path = urlparse(url or '').path.lower()
    return path.endswith('.m3u8') or path.endswith('.m3u')


def _host_is_public(host: str):
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        raise IngestError('Havola ochilmadi') from exc
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            raise IngestError('Bu havoladan yuklab bo‘lmaydi')


def validate_source_url(url: str) -> str:
    url = (url or '').strip()
    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname:
        raise IngestError('Faqat http yoki https video havolasi')
    if is_playlist_url(url):
        raise IngestError('HLS havolasini yozmang. Video fayl yoki video havolasini yuboring')
    _host_is_public(parsed.hostname)
    return url


class _SafeRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_source_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def filename_from_url(url: str) -> str:
    name = os.path.basename(urlparse(url).path) or 'video.mp4'
    name = name.split('?')[0][:80]
    if '.' not in name:
        name = f'{name}.mp4'
    lower = name.lower()
    if lower.endswith(('.m3u8', '.m3u')):
        raise IngestError('HLS havolasini yozmang. Video fayl yoki video havolasini yuboring')
    return name


PROGRESS_TTL = 6 * 3600


def scratch_dir():
    """Disk-backed temp for Masters/HLS. /tmp is often a small RAM disk on EC2."""
    raw = (
        getattr(settings, 'INGEST_SCRATCH', '')
        or os.environ.get('INGEST_SCRATCH', '')
        or tempfile.gettempdir()
    )
    path = Path(raw)
    path.mkdir(parents=True, exist_ok=True)
    return str(path)


def pending_upload_path(pk) -> str:
    return os.path.join(scratch_dir(), f'upload-{int(pk)}.mp4')


def set_progress(pk, pct, stage=''):
    if not pk:
        return
    cache.set(
        f'video-progress:{pk}',
        {'progress': int(max(0, min(100, pct))), 'stage': stage or ''},
        PROGRESS_TTL,
    )


def get_progress(pk):
    if not pk:
        return {}
    data = cache.get(f'video-progress:{pk}')
    return data if isinstance(data, dict) else {}


def _bind_key(video, key):
    video.video.name = key


def download_source(url: str, on_progress=None) -> tuple[str, str]:
    url = validate_source_url(url)
    name = filename_from_url(url)
    parsed = urlparse(url)
    request = Request(url, headers={
        'User-Agent': USER_AGENT,
        'Referer': f'{parsed.scheme}://{parsed.hostname}/',
        'Accept': '*/*',
    })
    opener = build_opener(_SafeRedirect)
    try:
        resp = opener.open(request, timeout=TIMEOUT)
    except Exception as exc:
        raise IngestError('Videoni yuklab bo‘lmadi') from exc
    try:
        length = resp.headers.get('Content-Length')
        total = int(length) if length else 0
        if total > MAX_DOWNLOAD_BYTES:
            raise IngestError('Video juda katta')
        ctype = (resp.headers.get('Content-Type') or '').lower()
        if 'mpegurl' in ctype or 'x-mpegurl' in ctype:
            raise IngestError('HLS havolasini yozmang. Video fayl yoki video havolasini yuboring')
        if store.s3_enabled():
            key = store.master_key(name)
            store.upload_fileobj(
                resp,
                key,
                content_type='video/mp4',
                size=total or None,
                on_progress=on_progress,
            )
            return key, name
        tmp = tempfile.NamedTemporaryFile(
            delete=False,
            suffix=os.path.splitext(name)[1] or '.mp4',
            dir=scratch_dir(),
        )
        written = 0
        with open(tmp.name, 'wb') as out:
            while True:
                chunk = resp.read(CHUNK)
                if not chunk:
                    break
                written += len(chunk)
                if written > MAX_DOWNLOAD_BYTES:
                    raise IngestError('Video juda katta')
                out.write(chunk)
                if on_progress:
                    on_progress(written, total or written)
        if written < 1024:
            os.unlink(tmp.name)
            raise IngestError('Havolada video topilmadi')
        return tmp.name, name
    except IngestError:
        raise
    except Exception as exc:
        raise IngestError('Videoni yuklab bo‘lmadi') from exc
    finally:
        try:
            resp.close()
        except Exception:
            pass


def attach_file(video, uploaded=None, source_url='', on_progress=None):
    if uploaded:
        name = getattr(uploaded, 'name', '') or ''
        if name.lower().endswith(('.m3u8', '.m3u')):
            raise IngestError('HLS fayl emas — video yuklang')
        if store.s3_enabled():
            key = store.master_key(name)
            store.upload_fileobj(
                uploaded,
                key,
                content_type=getattr(uploaded, 'content_type', '') or 'video/mp4',
                size=getattr(uploaded, 'size', None),
                on_progress=on_progress,
            )
            _bind_key(video, key)
            return
        video.video = uploaded
        return
    if source_url:
        path, name = download_source(source_url, on_progress=on_progress)
        if store.s3_enabled():
            _bind_key(video, path)
            return
        try:
            with open(path, 'rb') as fh:
                video.video.save(name, File(fh), save=False)
        finally:
            if os.path.isfile(path):
                os.unlink(path)
        return
    raise IngestError('Video fayl yoki internetdagi video havolasi kerak')


@contextmanager
def local_source_path(fieldfile):
    if not fieldfile:
        yield None
        return
    try:
        path = fieldfile.path
        if path and os.path.isfile(path):
            yield path
            return
    except (NotImplementedError, ValueError):
        pass
    suffix = os.path.splitext(getattr(fieldfile, 'name', '') or '')[1] or '.mp4'
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix, dir=scratch_dir())
    try:
        fieldfile.open('rb')
        for chunk in fieldfile.chunks():
            tmp.write(chunk)
        fieldfile.close()
        tmp.close()
        yield tmp.name
    finally:
        if os.path.isfile(tmp.name):
            os.unlink(tmp.name)


def _upload_hls_dir(video_id, output_dir):
    for name in os.listdir(output_dir):
        path = os.path.join(output_dir, name)
        if not os.path.isfile(path):
            continue
        ctype, _ = mimetypes.guess_type(name)
        if name.endswith('.m3u8'):
            ctype = 'application/vnd.apple.mpegurl'
        elif name.endswith('.ts'):
            ctype = 'video/mp2t'
        store.upload_file(path, store.hls_key(video_id, name), ctype or '')


def convert_to_hls(instance):
    if not instance.video:
        return
    with local_source_path(instance.video) as video_path:
        if not video_path:
            return
        output_dir = tempfile.mkdtemp(prefix=f'animee-hls-{instance.id}-', dir=scratch_dir())
        try:
            output_file = os.path.join(output_dir, 'master.m3u8')
            hls_tail = [
                '-map', '0:v',
                '-map', '0:a?',
                '-f', 'hls',
                '-hls_time', '4',
                '-hls_list_size', '0',
                '-hls_flags', 'independent_segments',
                '-hls_playlist_type', 'vod',
                output_file,
            ]
            copy_cmd = [
                'ffmpeg', '-y', '-threads', '1', '-i', video_path,
                '-c:v', 'copy', '-c:a', 'aac', '-ac', '2',
                *hls_tail,
            ]
            transcode_cmd = [
                'ffmpeg', '-y', '-threads', '1', '-i', video_path,
                '-preset', 'veryfast',
                '-threads', '1',
                '-g', '48',
                '-keyint_min', '48',
                '-sc_threshold', '0',
                '-force_key_frames', 'expr:gte(t,n_forced*4)',
                '-c:a', 'aac',
                '-ac', '2',
                *hls_tail,
            ]

            def run_ffmpeg(cmd):
                try:
                    result = subprocess.run(cmd, capture_output=True, timeout=3600)
                    return result.returncode == 0 and os.path.isfile(output_file)
                except (OSError, subprocess.TimeoutExpired):
                    return False

            def clear_out():
                for name in os.listdir(output_dir):
                    path = os.path.join(output_dir, name)
                    if os.path.isfile(path):
                        os.unlink(path)

            ok = run_ffmpeg(copy_cmd)
            if not ok:
                clear_out()
                ok = run_ffmpeg(transcode_cmd)
            if ok and store.s3_enabled():
                _upload_hls_dir(instance.id, output_dir)
                instance.hls_path = store.media_hls_url(instance.id)
            elif ok:
                dest = os.path.join(settings.MEDIA_ROOT, 'hls', str(instance.id))
                if os.path.isdir(dest):
                    shutil.rmtree(dest)
                shutil.copytree(output_dir, dest)
                instance.hls_path = f'/media/hls/{instance.id}/master.m3u8'
            else:
                instance.hls_path = instance.video.url
            instance.save(update_fields=['hls_path'])
        finally:
            shutil.rmtree(output_dir, ignore_errors=True)


def ingest_video(pk):
    from .models import Video

    video = Video.objects.filter(pk=pk).first()
    if not video:
        return

    def on_progress(done, total):
        if total:
            set_progress(pk, 1 + int((done / total) * 84), 's3')
        else:
            set_progress(pk, min(85, 1 + done // (4 * 1024 * 1024)), 's3')

    try:
        set_progress(pk, 1, 'start')
        pending = pending_upload_path(pk)
        if (not video.video) and os.path.isfile(pending) and os.path.getsize(pending) > 0:
            name = cache.get(f'video-upload-name:{pk}') or os.path.basename(pending)
            with open(pending, 'rb') as fh:
                wrapped = File(fh, name=name)
                wrapped.size = os.path.getsize(pending)
                attach_file(video, uploaded=wrapped, on_progress=on_progress)
                video.ingest_error = ''
                video.save(update_fields=['video', 'ingest_error'])
            try:
                os.unlink(pending)
            except OSError:
                pass
        if video.source_url and not video.video:
            attach_file(video, source_url=video.source_url, on_progress=on_progress)
            video.ingest_error = ''
            video.save(update_fields=['video', 'ingest_error'])
        if video.video:
            set_progress(pk, 90, 'hls')
            convert_to_hls(video)
            Video.objects.filter(pk=pk).update(ingest_error='')
            set_progress(pk, 100, 'ready')
        else:
            Video.objects.filter(pk=pk).update(ingest_error='Video fayl topilmadi')
            set_progress(pk, 0, 'error')
    except IngestError as exc:
        Video.objects.filter(pk=pk).update(ingest_error=exc.message[:255])
        set_progress(pk, 0, 'error')
    except OSError:
        logger.exception('ingest disk error pk=%s', pk)
        Video.objects.filter(pk=pk).update(ingest_error='Videoni HLS qilib bo‘lmadi')
        set_progress(pk, 0, 'error')
    except Exception:
        logger.exception('ingest failed pk=%s', pk)
        row = Video.objects.filter(pk=pk).first()
        msg = (
            'Videoni HLS qilib bo‘lmadi'
            if row and row.video
            else 'Videoni yuklab bo‘lmadi'
        )
        Video.objects.filter(pk=pk).update(ingest_error=msg)
        set_progress(pk, 0, 'error')
