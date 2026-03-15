from modeltranslation.translator import register, TranslationOptions
from .models import Person


@register(Person)
class PersonTranslationOptions(TranslationOptions):
    fields = ('bio',)