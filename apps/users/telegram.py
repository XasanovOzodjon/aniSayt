import json
import re
from uuid import uuid4

from django.conf import settings
from django.contrib.auth import get_user_model
from redis import Redis

from .auth_services import GoogleAuthService, create_user, get_tokens_for_user
from .profile import ProfileError, public_payload

CustomUser = get_user_model()


def _redis():
    return Redis(host='localhost', port=6379, db=0)


def bot_username():
    return getattr(settings, 'TELEGRAM_BOT_USERNAME', '') or 'animeediabot'


def start_url(unic_id: str) -> str:
    return f'https://t.me/{bot_username()}?start={unic_id}'


def begin_login():
    unic_id = str(uuid4())
    client = _redis()
    client.set(unic_id, json.dumps({'purpose': 'login'}), ex=900)
    client.close()
    return unic_id, start_url(unic_id)


def begin_link(user):
    unic_id = str(uuid4())
    client = _redis()
    client.set(unic_id, json.dumps({'purpose': 'link', 'user_id': user.pk}), ex=900)
    client.close()
    return unic_id, start_url(unic_id)


def attach_telegram(user, telegram_id, username='', photo_url=''):
    taken = CustomUser.objects.filter(telegram_id=telegram_id).exclude(pk=user.pk).first()
    if taken:
        raise ProfileError('Bu Telegram boshqa hisobga ulangan')
    user.telegram_id = telegram_id
    if username:
        user.telegram_username = str(username).lstrip('@')[:64]
    if photo_url and not user.photo and not user.photo_url:
        user.photo_url = photo_url[:500]
    user.save()
    return user


def unlink_telegram(user):
    user.telegram_id = None
    user.telegram_username = ''
    user.save(update_fields=['telegram_id', 'telegram_username'])
    return user


def _handle_from_telegram(username, telegram_id):
    raw = re.sub(r'[^A-Za-z0-9._-]', '', (username or '').lstrip('@'))[:30]
    return raw or f'id{telegram_id}'[:30]


def complete_bot_start(unic_id, telegram_user: dict) -> str:
    """Apply a /start payload from the bot. Returns the Uzbek reply text."""
    client = _redis()
    raw = client.get(str(unic_id))
    if not raw:
        client.close()
        return 'Havola eskirgan. Saytdan qayta urinib ko‘ring.'
    text = raw.decode() if isinstance(raw, bytes) else raw
    try:
        session = json.loads(text) if text and text != 'empty' else {'purpose': 'login'}
    except json.JSONDecodeError:
        session = {'purpose': 'login'}

    telegram_id = int(telegram_user['telegram_id'])
    username = telegram_user.get('username') or ''
    photo_url = telegram_user.get('photo_url') or ''

    if session.get('purpose') == 'link':
        user = CustomUser.objects.filter(pk=session.get('user_id')).first()
        if not user:
            client.set(str(unic_id), json.dumps({'purpose': 'link', 'status': 'error', 'message': 'Hisob topilmadi'}), ex=900)
            client.close()
            return 'Hisob topilmadi. Saytdan qayta urinib ko‘ring.'
        try:
            attach_telegram(user, telegram_id, username, photo_url)
        except ProfileError as exc:
            client.set(str(unic_id), json.dumps({'purpose': 'link', 'status': 'error', 'message': exc.message}), ex=900)
            client.close()
            return exc.message
        client.set(
            str(unic_id),
            json.dumps({
                'purpose': 'link',
                'status': 'linked',
                'telegram_id': telegram_id,
                'telegram_username': username,
            }),
            ex=900,
        )
        client.close()
        return 'Telegram ulandi. Saytga qayting — yangi sezonlar shu yerga keladi.'

    user = CustomUser.objects.filter(telegram_id=telegram_id).first()
    if not user:
        email = f'tg{telegram_id}@telegram.animee.local'
        user = create_user({
            'username': GoogleAuthService.unique_username(_handle_from_telegram(username, telegram_id)),
            'email': email,
            'telegram_id': telegram_id,
            'telegram_username': (username or '')[:64],
            'first_name': telegram_user.get('first_name') or '',
            'last_name': telegram_user.get('last_name') or '',
            'photo_url': (photo_url or '')[:500],
        })
    elif username and user.telegram_username != username:
        user.telegram_username = username[:64]
        user.save(update_fields=['telegram_username'])

    tokens = get_tokens_for_user(user)
    tokens.update(public_payload(user, owner=True))
    tokens['purpose'] = 'login'
    tokens['status'] = 'ok'
    client.set(str(unic_id), json.dumps(tokens), ex=900)
    client.close()
    return 'Kirish tasdiqlandi. Saytga qayting.'


def poll_session(unic_id: str) -> dict:
    client = _redis()
    raw = client.get(str(unic_id))
    client.close()
    if not raw:
        return {'status': 'expired'}
    text = raw.decode() if isinstance(raw, bytes) else raw
    if text == 'empty':
        return {'status': 'pending'}
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {'status': 'pending'}
    if data.get('purpose') == 'link' and data.get('status') not in ('linked', 'error'):
        return {'status': 'pending'}
    if data.get('status') == 'linked':
        return data
    if data.get('status') == 'error':
        return data
    if data.get('access'):
        data['status'] = 'ok'
        return data
    return {'status': 'pending'}
