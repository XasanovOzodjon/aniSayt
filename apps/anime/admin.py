from django.contrib import admin
from .models import Anime, Genre, Season
from modeltranslation.admin import TranslationAdmin


class AnimeAdmin(TranslationAdmin):
    list_display = ("id", "title", "description")
    search_fields = ("title", "description")
    list_filter = ("genres",)
    fieldsets = (
        (None, {
            'fields': ('title', 'description', 'poster')
        }),
        ('Genres', {
            'fields': ('genres',)
        }),
    )
    filter_horizontal = ("genres",)


class GenreAdmin(TranslationAdmin):
    list_display = ("id", "name")
    search_fields = ("slug",)
    ordering = ("id",)


class SeasonAdmin(admin.ModelAdmin):
    list_display = ("id", "anime", "number", "release_date")
    search_fields = ("anime__title",)
    list_filter = ("anime",)


admin.site.register(Anime, AnimeAdmin)
admin.site.register(Genre, GenreAdmin)
admin.site.register(Season, SeasonAdmin)
