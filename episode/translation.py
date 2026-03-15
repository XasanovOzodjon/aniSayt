from modeltranslation.translator import register, TranslationOptions
from .models import Episode


@register(Episode)
class EpisodeTranslationOptions(TranslationOptions):
    fields = ('title',)
    
    