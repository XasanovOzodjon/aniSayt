from modeltranslation.translator import register, TranslationOptions
from .models import Anime, Genre

@register(Anime)
class AnimeTranslationOptions(TranslationOptions):
    fields = ('title', 'description',)

@register(Genre)
class GenreTranslationOptions(TranslationOptions):
    fields = ('name',)
