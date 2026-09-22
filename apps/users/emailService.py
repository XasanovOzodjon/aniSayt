import json
import uuid
from random import randint

import redis
from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.core.mail import send_mail
from django.utils import timezone


PIN_TTL_SECONDS = 15 * 60
PIN_TRIES = 5


def _redis():
    return redis.StrictRedis(host='localhost', port=6379, db=0)


def send_email(data):
    pincode = randint(100000, 999999)
    uid = str(uuid.uuid4())
    username = data['username']
    email = data['email']
    payload = {
        'username': username,
        'email': email,
        'password': make_password(data['password']),
        'pin_code': make_password(str(pincode)),
        'count_try': PIN_TRIES,
        'create_at': timezone.now().timestamp(),
    }
    redis_client = _redis()
    redis_client.set(uid, json.dumps(payload), ex=PIN_TTL_SECONDS)
    try:
        send_mail(
            subject='Animee — tasdiqlash kodi',
            message=(
                f'Assalomu alaykum, {username}!\n\n'
                f'Hisobni ochish uchun kod: {pincode}\n'
                f'Kod 15 daqiqa amal qiladi. Uni hech kimga bermang.\n\n'
                f'— Animee'
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
    except Exception:
        redis_client.delete(uid)
        raise
    return uid


def check_email_pincode(uid, pincode):
    redis_client = _redis()
    key = str(uid)
    redis_data = redis_client.get(key)
    if not redis_data:
        return 404

    data = json.loads(redis_data)
    created = float(data.get('create_at') or 0)
    tries = int(data.get('count_try') or 0)
    expired = timezone.now().timestamp() > created + PIN_TTL_SECONDS
    if tries <= 0 or expired:
        redis_client.delete(key)
        return 408

    if check_password(str(pincode), data.get('pin_code') or ''):
        redis_client.delete(key)
        return data

    data['count_try'] = tries - 1
    if data['count_try'] <= 0:
        redis_client.delete(key)
        return 408
    redis_client.set(key, json.dumps(data), ex=PIN_TTL_SECONDS)
    return 401
