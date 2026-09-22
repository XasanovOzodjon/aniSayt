import ipaddress
import mimetypes
import os
import shutil
import socket
import subprocess
import tempfile
from contextlib import contextmanager
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from django.conf import settings
from django.core.files import File

from apps.main import object_storage as store

MAX_DOWNLOAD_BYTES = 4 * 1024 * 1024 * 1024
CHUNK = 1024 * 1024
TIMEOUT = 180
USER_AGENT = 'Animee/1.0'


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


def download_source(url: str) -> tuple[str, str]:
    url = validate_source_url(url)
    name = filename_from_url(url)
    request = Request(url, headers={'User-Agent': USER_AGENT})
    opener = build_opener(_SafeRedirect)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(name)[1] or '.mp4')
    written = 0
    try:
        with opener.open(request, timeout=TIMEOUT) as resp, open(tmp.name, 'wb') as out:
            length = resp.headers.get('Content-Length')
            if length and int(length) > MAX_DOWNLOAD_BYTES:
                raise IngestError('Video juda katta')
            ctype = (resp.headers.get('Content-Type') or '').lower()
            if 'mpegurl' in ctype or 'x-mpegurl' in ctype:
                raise IngestError('HLS havolasini yozmang. Video fayl yoki video havolasini yuboring')
            while True:
                chunk = resp.read(CHUNK)
                if not chunk:
                    break
                written += len(chunk)
                if written > MAX_DOWNLOAD_BYTES:
                    raise IngestError('Video juda katta')
                out.write(chunk)
    except IngestError:
        os.unlink(tmp.name)
        raise
    except Exception as exc:
        os.unlink(tmp.name)
        raise IngestError('Videoni yuklab bo‘lmadi') from exc
    if written < 1024:
        os.unlink(tmp.name)
        raise IngestError('Havolada video topilmadi')
    return tmp.name, name


def attach_file(video, uploaded=None, source_url=''):
    if uploaded:
        name = getattr(uploaded, 'name', '') or ''
        if name.lower().endswith(('.m3u8', '.m3u')):
            raise IngestError('HLS fayl emas — video yuklang')
        video.video = uploaded
        return
    if source_url:
        path, name = download_source(source_url)
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
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
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
        output_dir = tempfile.mkdtemp(prefix=f'animee-hls-{instance.id}-')
        try:
            output_file = os.path.join(output_dir, 'master.m3u8')
            cmd = [
                'ffmpeg', '-y', '-i', video_path,
                '-preset', 'veryfast',
                '-g', '48',
                '-keyint_min', '48',
                '-sc_threshold', '0',
                '-force_key_frames', 'expr:gte(t,n_forced*4)',
                '-map', '0:v',
                '-map', '0:a?',
                '-c:a', 'aac',
                '-ac', '2',
                '-f', 'hls',
                '-hls_time', '4',
                '-hls_list_size', '0',
                '-hls_flags', 'independent_segments',
                '-hls_playlist_type', 'vod',
                output_file,
            ]
            try:
                result = subprocess.run(cmd, capture_output=True, timeout=3600)
                ok = result.returncode == 0 and os.path.isfile(output_file)
            except (OSError, subprocess.TimeoutExpired):
                ok = False
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
