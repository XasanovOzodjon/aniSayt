import re

import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

CustomUser = get_user_model()


from apps.users.profile import is_username_taken


class GoogleAuthService:

    @staticmethod
    def generate_google_auth_url():
        url = (
            f'https://accounts.google.com/o/oauth2/v2/auth?'
            f'client_id={settings.GOOGLE_CLIENT_ID}&'
            f'redirect_uri={settings.GOOGLE_REDIRECT_URL}&'
            'scope=email%20profile&'
            'response_type=code'
        )
        return url

    @staticmethod
    def get_access_token(code: str):
        data = {
            'client_id': settings.GOOGLE_CLIENT_ID,
            'client_secret': settings.GOOGLE_CLIENT_SECRET,
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': settings.GOOGLE_REDIRECT_URL,
        }
        response = requests.post(settings.GOOGLE_TOKEN_URL, data=data)

        if response.status_code != 200:
            return False

        return response.json().get('access_token') or False

    @staticmethod
    def get_user_info(access_token: str):
        if not access_token:
            return False
        response = requests.get(
            settings.GOOGLE_USER_INFO_URL,
            headers={'Authorization': f'Bearer {access_token}'},
        )

        if response.status_code != 200:
            return False

        return response.json()

    @staticmethod
    def username_from_email(email: str) -> str:
        local = (email or '').split('@')[0].strip()
        local = re.sub(r'[^A-Za-z0-9._-]', '', local)
        return (local[:30] or 'user')

    @staticmethod
    def unique_username(base: str, exclude_pk=None) -> str:
        candidate = (base or 'user')[:30]
        if not is_username_taken(candidate, exclude_pk=exclude_pk):
            return candidate
        for i in range(2, 1000):
            suffix = f'_{i}'
            name = f'{candidate[:30 - len(suffix)]}{suffix}'
            if not is_username_taken(name, exclude_pk=exclude_pk):
                return name
        return f'user_{CustomUser.objects.count()}'

    @staticmethod
    def photo_from_google(user_info: dict) -> str:
        picture = (user_info or {}).get('picture') or ''
        if not picture.startswith('http'):
            return ''
        picture = picture.replace('=s96-c', '=s256-c').replace('=s96', '=s256')
        if len(picture) > 500:
            return ''
        return picture

    @staticmethod
    def get_user(user):
        email = ((user or {}).get('email') or '').strip()
        if not email:
            return None
        picture = GoogleAuthService.photo_from_google(user)
        userdata = CustomUser.objects.filter(email__iexact=email).first()
        if userdata:
            changed = False
            if picture and userdata.photo_url != picture:
                userdata.photo_url = picture
                changed = True
            if changed:
                userdata.save(update_fields=['photo_url'])
            return userdata

        userdata = CustomUser(
            username=GoogleAuthService.unique_username(
                GoogleAuthService.username_from_email(email)
            ),
            email=email,
            first_name=user.get('given_name', '') or '',
            last_name=user.get('family_name', '') or '',
            photo_url=picture,
        )
        userdata.set_unusable_password()
        userdata.save()
        return userdata

    @staticmethod
    def get_token(user):
        refresh = RefreshToken.for_user(user)
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }

    @staticmethod
    def login_by_google(code: str):
        access_token = GoogleAuthService.get_access_token(code)
        if not access_token:
            return None
        user_info = GoogleAuthService.get_user_info(access_token)
        if not user_info or not user_info.get('email'):
            return None
        user = GoogleAuthService.get_user(user_info)
        if not user:
            return None
        tokens = GoogleAuthService.get_token(user)
        tokens['user'] = user
        return tokens


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


def create_user(data):
    user = CustomUser.objects.create_user(**data)
    return user


def set_number(telegram_id, number):
    user = CustomUser.objects.filter(telegram_id=telegram_id).first()

    if user:
        user.phone_number = number
        user.save()
        return True
    return False
