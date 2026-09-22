from botocore.exceptions import ClientError
from django.conf import settings
from django.core.management.base import BaseCommand

from apps.main import object_storage as store


class Command(BaseCommand):
    help = 'Probe S3 credentials without printing secrets.'

    def handle(self, *args, **options):
        bucket = store.bucket_name()
        region = store.region_name()
        has_keys = bool(settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY)
        self.stdout.write(f'bucket={bucket or "-"} region={region} keys={has_keys}')
        if not bucket or not has_keys:
            self.stderr.write('S3 yoqilmagan')
            return
        store.reset_client()
        client = store._client()
        try:
            client.head_bucket(Bucket=bucket)
        except ClientError as exc:
            code = (exc.response.get('Error') or {}).get('Code', 'Error')
            self.stderr.write(f'head_bucket={code}')
            return
        self.stdout.write('head_bucket=ok')
        key = '_animee/health.txt'
        client.put_object(Bucket=bucket, Key=key, Body=b'ok', ContentType='text/plain')
        got = client.get_object(Bucket=bucket, Key=key)['Body'].read()
        client.delete_object(Bucket=bucket, Key=key)
        if got != b'ok':
            self.stderr.write('get_object mismatch')
            return
        self.stdout.write('put_get_delete=ok')
        try:
            store.ensure_browser_cors()
            self.stdout.write('cors=ok')
        except ClientError as exc:
            self.stderr.write(f'cors={(exc.response.get("Error") or {}).get("Code", type(exc).__name__)}')
        self.stdout.write(self.style.SUCCESS('s3 ready'))
