"""S3 object storage for Masters and HLS. Local disk until AWS env is set."""

from functools import lru_cache
from urllib.parse import quote

from django.conf import settings


def s3_enabled() -> bool:
    if getattr(settings, 'TESTING', False):
        return False
    if not getattr(settings, 'AWS_S3_READY', False):
        return False
    return bool(
        (getattr(settings, 'AWS_STORAGE_BUCKET_NAME', '') or '').strip()
        and (getattr(settings, 'AWS_ACCESS_KEY_ID', '') or '').strip()
        and (getattr(settings, 'AWS_SECRET_ACCESS_KEY', '') or '').strip()
    )


def bucket_name() -> str:
    return (getattr(settings, 'AWS_STORAGE_BUCKET_NAME', '') or '').strip()


def region_name() -> str:
    return (getattr(settings, 'AWS_S3_REGION_NAME', '') or 'eu-central-1').strip()


def public_file_url(field_or_name) -> str:
    """Browser URL. Always Django /media/ so S3 signatures/CORS never hit the client."""
    if not field_or_name:
        return ''
    name = field_or_name if isinstance(field_or_name, str) else getattr(field_or_name, 'name', '') or ''
    name = str(name).replace('\\', '/').lstrip('/')
    if not name:
        return ''
    return f'/media/{name}'


@lru_cache(maxsize=1)
def _client():
    import boto3
    from botocore.config import Config

    region = region_name()
    return boto3.client(
        's3',
        region_name=region,
        endpoint_url=f'https://s3.{region}.amazonaws.com',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        config=Config(signature_version='s3v4', s3={'addressing_style': 'virtual'}),
    )


def reset_client():
    _client.cache_clear()


def signed_url(key: str, expires=None) -> str:
    seconds = int(expires or getattr(settings, 'AWS_QUERYSTRING_EXPIRE', 6 * 3600))
    return _client().generate_presigned_url(
        'get_object',
        Params={'Bucket': bucket_name(), 'Key': key},
        ExpiresIn=seconds,
    )


def master_key(filename: str) -> str:
    import os
    import uuid

    base = os.path.basename(filename or 'video.mp4') or 'video.mp4'
    base = base.replace(' ', '-')[:80]
    return f'episodes/videos/{uuid.uuid4().hex}_{base}'


def _iter_chunks(source, chunk=1024 * 1024):
    if hasattr(source, 'chunks'):
        yield from source.chunks(chunk)
        return
    read = getattr(source, 'read', None)
    if not read:
        raise TypeError('stream has no read')
    while True:
        data = read(chunk)
        if not data:
            break
        yield data


def upload_fileobj(source, key, content_type='', size=None, on_progress=None):
    """Stream a file-like object straight to S3. No full local copy."""
    client = _client()
    bucket = bucket_name()
    extra = {
        'ContentType': content_type or 'video/mp4',
        'CacheControl': 'public, max-age=86400',
    }
    min_part = 8 * 1024 * 1024
    buf = bytearray()
    sent = 0
    total = int(size or 0)
    chunks = _iter_chunks(source)

    def ping():
        if on_progress:
            on_progress(sent, total or sent)

    for piece in chunks:
        buf.extend(piece)
        if len(buf) >= min_part:
            break
    else:
        body = bytes(buf)
        client.put_object(Bucket=bucket, Key=key, Body=body, **extra)
        sent = len(body)
        ping()
        return key

    mpu = client.create_multipart_upload(Bucket=bucket, Key=key, **extra)
    upload_id = mpu['UploadId']
    parts = []
    part_no = 1
    try:
        def flush(force=False):
            nonlocal buf, part_no, sent
            while buf and (force or len(buf) >= min_part):
                take = len(buf) if force else min_part
                if not force:
                    take = min(take, len(buf))
                    if take < min_part:
                        break
                body = bytes(buf[:take])
                del buf[:take]
                resp = client.upload_part(
                    Bucket=bucket,
                    Key=key,
                    PartNumber=part_no,
                    UploadId=upload_id,
                    Body=body,
                )
                parts.append({'ETag': resp['ETag'], 'PartNumber': part_no})
                part_no += 1
                sent += len(body)
                ping()
                if force:
                    break

        flush(force=True)
        for piece in chunks:
            buf.extend(piece)
            flush(force=False)
        flush(force=True)
        client.complete_multipart_upload(
            Bucket=bucket,
            Key=key,
            UploadId=upload_id,
            MultipartUpload={'Parts': parts},
        )
    except Exception:
        client.abort_multipart_upload(Bucket=bucket, Key=key, UploadId=upload_id)
        raise
    return key


def upload_file(local_path: str, key: str, content_type=''):
    extra = {}
    if content_type:
        extra['ContentType'] = content_type
    extra['CacheControl'] = 'public, max-age=86400'
    _client().upload_file(local_path, bucket_name(), key, ExtraArgs=extra or None)


def delete_prefix(prefix: str):
    if not prefix or not s3_enabled():
        return
    client = _client()
    bucket = bucket_name()
    token = None
    while True:
        kwargs = {'Bucket': bucket, 'Prefix': prefix}
        if token:
            kwargs['ContinuationToken'] = token
        listing = client.list_objects_v2(**kwargs)
        objects = [{'Key': obj['Key']} for obj in listing.get('Contents') or []]
        if objects:
            client.delete_objects(Bucket=bucket, Delete={'Objects': objects})
        if not listing.get('IsTruncated'):
            break
        token = listing.get('NextContinuationToken')


def object_exists(key: str) -> bool:
    from botocore.exceptions import ClientError

    try:
        _client().head_object(Bucket=bucket_name(), Key=key)
        return True
    except ClientError:
        return False


def ensure_browser_cors():
    _client().put_bucket_cors(
        Bucket=bucket_name(),
        CORSConfiguration={
            'CORSRules': [
                {
                    'AllowedHeaders': ['*'],
                    'AllowedMethods': ['GET', 'HEAD'],
                    'AllowedOrigins': ['*'],
                    'ExposeHeaders': [
                        'Accept-Ranges',
                        'Content-Length',
                        'Content-Range',
                        'Content-Type',
                        'ETag',
                    ],
                    'MaxAgeSeconds': 3600,
                }
            ]
        },
    )


def rewrite_playlist(body: str, folder: str, signer) -> str:
    """Turn relative HLS URIs into signed absolute URLs. `signer(key) -> url`."""
    prefix = folder.strip('/')
    out = []
    for line in body.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith('#'):
            name = stripped.split('?')[0].lstrip('/')
            key = f'{prefix}/{name}' if prefix else name
            out.append(signer(key))
        else:
            out.append(line)
    return '\n'.join(out) + ('\n' if body.endswith('\n') or body else '')


def hls_key(video_id, filename='master.m3u8') -> str:
    return f'hls/{video_id}/{filename}'


def media_hls_url(video_id) -> str:
    return f'/media/hls/{video_id}/master.m3u8'


def quote_key(key: str) -> str:
    return quote(key, safe='/')


class ProxiedS3Storage:
    """S3 writes; browsers always fetch through Django /media/."""

    def __new__(cls, **kwargs):
        from storages.backends.s3boto3 import S3Boto3Storage

        class Impl(S3Boto3Storage):
            def url(self, name, parameters=None, expire=None, http_method=None):
                return public_file_url(name)

        return Impl(**kwargs)