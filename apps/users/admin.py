from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CustomUser, Comment, Notice, Progress, ProfileReport, UnbanRequest, UserList, UserModeration


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Animee', {
            'fields': (
                'photo',
                'photo_url',
                'banner',
                'bio',
                'status_line',
                'show_watching',
                'preferred_audio',
                'preferred_subs',
                'autoplay_next',
                'public_profile',
                'telegram_id',
                'telegram_username',
                'phone_number',
                'notify_telegram',
                'notify_new_season',
                'notify_new_episode',
                'is_moderator',
                'streak_count',
                'streak_best',
                'streak_days',
                'streak_started_on',
                'streak_last_on',
            ),
        }),
    )
    list_display = ('username', 'email', 'is_staff', 'is_moderator', 'telegram_id', 'public_profile')
    search_fields = ('username', 'email', 'telegram_username')


@admin.register(UserList)
class UserListAdmin(admin.ModelAdmin):
    list_display = ('user', 'anime', 'status', 'score', 'updated_at')
    list_filter = ('status',)
    search_fields = ('user__username', 'anime__title')


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('user', 'episode', 'parent', 'created_at')
    search_fields = ('user__username', 'body')


@admin.register(Progress)
class ProgressAdmin(admin.ModelAdmin):
    list_display = ('user', 'episode', 'position', 'updated_at')
    search_fields = ('user__username', 'episode__title')


@admin.register(Notice)
class NoticeAdmin(admin.ModelAdmin):
    list_display = ('user', 'kind', 'title', 'read_at', 'sent_telegram', 'created_at')
    list_filter = ('kind', 'sent_telegram')
    search_fields = ('user__username', 'title')


@admin.register(ProfileReport)
class ProfileReportAdmin(admin.ModelAdmin):
    list_display = ('target', 'kind', 'reason', 'reporter', 'resolved_at', 'created_at')
    list_filter = ('kind', 'reason')
    search_fields = ('target__username', 'reporter__username', 'note')


@admin.register(UserModeration)
class UserModerationAdmin(admin.ModelAdmin):
    list_display = ('user', 'banned_at', 'ban_allow_appeal', 'lock_comments', 'report_strikes')
    search_fields = ('user__username',)


@admin.register(UnbanRequest)
class UnbanRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'accepted', 'resolved_at', 'created_at')
    search_fields = ('user__username', 'body')
