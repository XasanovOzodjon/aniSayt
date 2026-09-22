from django.contrib import admin

from .models import PartyMessage, WatchParty


@admin.register(WatchParty)
class WatchPartyAdmin(admin.ModelAdmin):
    list_display = ('code', 'episode', 'host', 'control', 'playing', 'closed_at', 'created_at')
    search_fields = ('code', 'host__username')
    list_filter = ('control',)


@admin.register(PartyMessage)
class PartyMessageAdmin(admin.ModelAdmin):
    list_display = ('party', 'user', 'body', 'created_at')
    search_fields = ('body', 'user__username', 'party__code')
