import json
import threading
import time

from django.conf import settings
from redis import Redis

from .services import MAX_MEMBERS

TTL = 6 * 60 * 60
_lock = threading.Lock()
_MEM = {}


def reset():
    with _lock:
        _MEM.clear()
    client = _redis()
    if client is None:
        return
    try:
        keys = client.keys('party:*:members')
        if keys:
            client.delete(*keys)
    except Exception:
        pass
    finally:
        try:
            client.close()
        except Exception:
            pass


def _redis():
    url = (getattr(settings, 'REDIS_URL', '') or '').strip()
    if not url:
        return None
    return Redis.from_url(url, decode_responses=True)


def _key(code):
    return f'party:{code}:members'


def _public(member: dict) -> dict:
    row = dict(member or {})
    row.pop('_ch', None)
    return row


def _mem_bucket(code):
    now = time.time()
    bucket = _MEM.setdefault(code, {})
    dead = [uid for uid, row in list(bucket.items()) if row['exp'] < now]
    for uid in dead:
        del bucket[uid]
    return bucket


def remember(code, member: dict):
    payload = json.dumps(member)
    client = _redis()
    if client is not None:
        try:
            client.hset(_key(code), str(member['id']), payload)
            client.expire(_key(code), TTL)
        finally:
            client.close()
        return
    with _lock:
        bucket = _mem_bucket(code)
        bucket[str(member['id'])] = {'raw': payload, 'exp': time.time() + TTL}


def forget(code, user_id, channel_name=None):
    uid = str(user_id)
    client = _redis()
    if client is not None:
        try:
            raw = client.hget(_key(code), uid)
            if raw and channel_name:
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    data = {}
                if data.get('_ch') and data['_ch'] != channel_name:
                    return
            client.hdel(_key(code), uid)
        finally:
            client.close()
        return
    with _lock:
        bucket = _mem_bucket(code)
        row = bucket.get(uid)
        if row and channel_name:
            try:
                data = json.loads(row['raw'])
            except json.JSONDecodeError:
                data = {}
            if data.get('_ch') and data['_ch'] != channel_name:
                return
        bucket.pop(uid, None)
        if not bucket:
            _MEM.pop(code, None)


def members(code) -> list:
    rows = []
    client = _redis()
    if client is not None:
        try:
            values = client.hvals(_key(code))
        finally:
            client.close()
        raw_list = values or []
    else:
        with _lock:
            raw_list = [row['raw'] for row in _mem_bucket(code).values()]
    for raw in raw_list:
        try:
            rows.append(_public(json.loads(raw)))
        except json.JSONDecodeError:
            continue
    return rows


def count(code) -> int:
    client = _redis()
    if client is not None:
        try:
            return int(client.hlen(_key(code)) or 0)
        finally:
            client.close()
    with _lock:
        return len(_mem_bucket(code))


def set_camera(code, user_id, on: bool):
    uid = str(user_id)
    client = _redis()
    if client is not None:
        try:
            raw = client.hget(_key(code), uid)
            if raw:
                data = json.loads(raw)
                data['camera'] = bool(on)
                client.hset(_key(code), uid, json.dumps(data))
        finally:
            client.close()
        return
    with _lock:
        bucket = _mem_bucket(code)
        row = bucket.get(uid)
        if not row:
            return
        data = json.loads(row['raw'])
        data['camera'] = bool(on)
        row['raw'] = json.dumps(data)


def has_user(code, user_id) -> bool:
    uid = str(user_id)
    client = _redis()
    if client is not None:
        try:
            return bool(client.hexists(_key(code), uid))
        finally:
            client.close()
    with _lock:
        return uid in _mem_bucket(code)


def is_full(code, user_id) -> bool:
    if has_user(code, user_id):
        return False
    return count(code) >= MAX_MEMBERS
