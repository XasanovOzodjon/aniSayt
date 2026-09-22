from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.anime.models import Anime
from apps.anime.paths import kind_prefix

from .models import UserList
from .profile import avatar_url, dashboard_flags


class AnimeeTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        data['username'] = self.user.username
        data['email'] = self.user.email or ''
        data['photo'] = avatar_url(self.user)
        data['bio'] = self.user.bio or ''
        data['preferred_audio'] = self.user.preferred_audio or 'uz'
        data['preferred_subs'] = self.user.preferred_subs or 'uz'
        data['autoplay_next'] = bool(self.user.autoplay_next)
        data['public_profile'] = bool(self.user.public_profile)
        data['telegram_linked'] = bool(self.user.telegram_id)
        data.update(dashboard_flags(self.user))
        return data


class RegistarSerializer(serializers.Serializer):
    username = serializers.CharField(required=True, min_length=3, max_length=30)
    password = serializers.CharField(style={'input_type': 'password'}, write_only=True, required=True, validators=[validate_password])
    conform_password = serializers.CharField(style={'input_type': 'password'}, write_only=True, required=True)
    email = serializers.EmailField(required=True)

    def validate(self, data):
        if data['password'] != data['conform_password']:
            raise serializers.ValidationError(
                "Password and Confirm Password do not match"
            )

        data.pop('conform_password')
        return data


class EmailCheckSerializer(serializers.Serializer):
    uid = serializers.CharField()
    pincode = serializers.IntegerField()


class ProfileUpdateSerializer(serializers.Serializer):
    username = serializers.CharField(required=False, allow_blank=False)
    first_name = serializers.CharField(required=False, allow_blank=True, max_length=80)
    status_line = serializers.CharField(required=False, allow_blank=True, max_length=80)
    show_watching = serializers.BooleanField(required=False)
    bio = serializers.CharField(required=False, allow_blank=True, max_length=280)
    photo = serializers.CharField(required=False, allow_blank=True)
    preferred_audio = serializers.ChoiceField(choices=['uz', 'ru'], required=False)
    preferred_subs = serializers.ChoiceField(choices=['uz', 'ru', 'off'], required=False)
    autoplay_next = serializers.BooleanField(required=False)
    public_profile = serializers.BooleanField(required=False)
    notify_telegram = serializers.BooleanField(required=False)
    notify_new_season = serializers.BooleanField(required=False)
    notify_new_episode = serializers.BooleanField(required=False)


class ListWriteSerializer(serializers.Serializer):
    anime = serializers.IntegerField()
    status = serializers.ChoiceField(choices=['watching', 'completed', 'planned', 'dropped', 'favorite'])
    score = serializers.IntegerField(required=False, allow_null=True, min_value=1, max_value=10)


class ListAnimeSerializer(serializers.ModelSerializer):
    path = serializers.SerializerMethodField()

    class Meta:
        model = Anime
        fields = ['id', 'title', 'poster', 'kind', 'slug', 'path']

    def get_path(self, obj):
        if obj.slug:
            return f'/{kind_prefix(obj.kind)}/{obj.slug}/'
        return f'/detail/?id={obj.id}'


class UserListSerializer(serializers.ModelSerializer):
    anime = ListAnimeSerializer(read_only=True)

    class Meta:
        model = UserList
        fields = ['id', 'status', 'score', 'updated_at', 'anime']


class GetUIDSerializer(serializers.Serializer):
    unicID = serializers.CharField(max_length=255)
