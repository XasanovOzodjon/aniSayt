from django.contrib import admin
from .models import Person
from modeltranslation.admin import TranslationAdmin

class PersonAdmin(TranslationAdmin):
    list_display = ("id", "fullname", "anime__title")
    search_fields = ("fullname", "anime__title")
    fieldsets = (
        (None, {
            'fields': ('fullname', 'anime', 'bio', 'photo')
        }),
    )
admin.site.register(Person, PersonAdmin)
