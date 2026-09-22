import mimetypes
import re
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404, HttpResponse
from django.utils._os import safe_join
from django.utils.http import http_date

RANGE_RE = re.compile(r'bytes=(\d*)-(\d*)')
HLS_SEGMENT = ('.ts', '.m4s', '.mp4', '.aac', '.vtt')
HLS_PLAYLIST = ('.m3u8', '.m3u')


class MediaFileResponse(FileResponse):
    block_size = 256 * 1024


class _LimitedFile:
    def __init__(self, fh, remaining):
        self._fh = fh
        self._remaining = remaining
        self.name = getattr(fh, 'name', '')

    def read(self, size=-1):
        if self._remaining <= 0:
            return b''
        if size is None or size < 0:
            size = self._remaining
        data = self._fh.read(min(size, self._remaining))
        self._remaining -= len(data)
        return data

    def close(self):
        self._fh.close()

    def tell(self):
        return self._fh.tell()

    def seek(self, *args, **kwargs):
        return self._fh.seek(*args, **kwargs)

    def seekable(self):
        return False


def _parse_range(header, size):
    match = RANGE_RE.fullmatch((header or '').strip())
    if not match or size <= 0:
        return None
    start_s, end_s = match.group(1), match.group(2)
    if start_s == '' and end_s == '':
        return None
    if start_s == '':
        suffix = int(end_s)
        if suffix <= 0:
            return None
        start = max(0, size - suffix)
        return start, size - 1
    start = int(start_s)
    end = int(end_s) if end_s else size - 1
    if start >= size or end < start:
        return None
    return start, min(end, size - 1)


def _cache_for(name: str):
    lower = name.lower()
    if lower.endswith(HLS_PLAYLIST):
        return 'public, max-age=30'
    if lower.endswith(HLS_SEGMENT):
        return 'public, max-age=86400, immutable'
    if lower.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg')):
        return 'public, max-age=86400'
    return 'public, max-age=3600'


def _with_independent_segments(body: str) -> str:
    if '#EXT-X-INDEPENDENT-SEGMENTS' in body:
        return body
    if body.lstrip().startswith('#EXTM3U'):
        return body.replace('#EXTM3U', '#EXTM3U\n#EXT-X-INDEPENDENT-SEGMENTS', 1)
    return body


def serve_media(request, path):
    fullpath = Path(safe_join(str(settings.MEDIA_ROOT), path))
    if fullpath.is_file():
        return _serve_local(request, fullpath)
    from apps.main import object_storage as store
    if store.s3_enabled():
        return _serve_s3(request, path)
    raise Http404()


def _serve_s3(request, path):
    from botocore.exceptions import ClientError
    from django.http import StreamingHttpResponse

    from apps.main import object_storage as store

    key = path.lstrip('/')
    name = Path(key).name.lower()
    kwargs = {'Bucket': store.bucket_name(), 'Key': key}
    rng = request.META.get('HTTP_RANGE')
    if rng and not name.endswith(('.m3u8', '.m3u')):
        kwargs['Range'] = rng
    try:
        obj = store._client().get_object(**kwargs)
    except ClientError as exc:
        raise Http404() from exc
    content_type = obj.get('ContentType') or mimetypes.guess_type(name)[0]
    if name.endswith(('.m3u8', '.m3u')):
        body = _with_independent_segments(obj['Body'].read().decode('utf-8', errors='replace'))
        response = HttpResponse(body, content_type='application/vnd.apple.mpegurl')
        response['Cache-Control'] = _cache_for(name)
        return response
    status = 206 if obj.get('ContentRange') else 200
    response = StreamingHttpResponse(
        obj['Body'].iter_chunks(256 * 1024),
        content_type=content_type or 'application/octet-stream',
        status=status,
    )
    if obj.get('ContentLength') is not None:
        response['Content-Length'] = str(obj['ContentLength'])
    if obj.get('ContentRange'):
        response['Content-Range'] = obj['ContentRange']
    response['Accept-Ranges'] = 'bytes'
    response['Cache-Control'] = _cache_for(name)
    return response


def _serve_local(request, fullpath: Path):
    stat = fullpath.stat()
    size = stat.st_size
    content_type, encoding = mimetypes.guess_type(str(fullpath))
    content_type = content_type or 'application/octet-stream'
    parsed = _parse_range(request.META.get('HTTP_RANGE', ''), size)
    if request.META.get('HTTP_RANGE') and parsed is None:
        response = HttpResponse(status=416)
        response['Content-Range'] = f'bytes */{size}'
        return response
    if parsed:
        start, end = parsed
        length = end - start + 1
        fh = fullpath.open('rb')
        fh.seek(start)
        response = MediaFileResponse(
            _LimitedFile(fh, length),
            content_type=content_type,
            status=206,
        )
        response['Content-Range'] = f'bytes {start}-{end}/{size}'
        response['Content-Length'] = str(length)
    elif fullpath.suffix.lower() in HLS_PLAYLIST:
        body = _with_independent_segments(fullpath.read_text(encoding='utf-8', errors='replace'))
        response = HttpResponse(body, content_type='application/vnd.apple.mpegurl')
        response['Content-Length'] = str(len(body.encode('utf-8')))
    else:
        response = MediaFileResponse(fullpath.open('rb'), content_type=content_type)
        response['Content-Length'] = str(size)
    response['Accept-Ranges'] = 'bytes'
    response['Last-Modified'] = http_date(stat.st_mtime)
    response['Cache-Control'] = _cache_for(fullpath.name)
    if encoding and fullpath.suffix.lower() not in HLS_PLAYLIST:
        response['Content-Encoding'] = encoding
    response['Content-Disposition'] = f'inline; filename="{fullpath.name}"'
    return response
