from .models import CustomUser
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import AuthenticationFailed

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

