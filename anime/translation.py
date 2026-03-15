from modeltranslation.translator import register, TranslationOptions
from .models import Anime, Ganre

@register(Anime)
class AnimeTranslationOptions(TranslationOptions):
    fields = ('title', 'description',)
    
@register(Ganre)
class GanreTranslationOptions(TranslationOptions):
    fields = ('name',)