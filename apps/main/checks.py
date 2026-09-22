from django.conf import settings
from django.core.checks import Error, Tags, register


@register(Tags.security, deploy=True)
def production_ready(app_configs, **kwargs):
    if settings.DEBUG or getattr(settings, 'TESTING', False):
        return []
    errors = []
    if len(settings.SECRET_KEY or '') < 50:
        errors.append(Error('SECRET_KEY kamida 50 belgi bo‘lsin.', id='animee.E001'))
    if not (settings.REDIS_URL or '').strip():
        errors.append(Error('REDIS_URL productionda majburiy.', id='animee.E002'))
    hosts = [str(h).strip() for h in (settings.ALLOWED_HOSTS or []) if str(h).strip()]
    if not hosts or hosts == ['*']:
        errors.append(Error('ALLOWED_HOSTS ni aniqlang.', id='animee.E003'))
    site = (settings.SITE_URL or '').rstrip('/')
    if not site.startswith('https://'):
        errors.append(Error('SITE_URL https bo‘lsin.', id='animee.E004'))
    redirect = settings.GOOGLE_REDIRECT_URL or ''
    if 'localhost' in redirect or '127.0.0.1' in redirect:
        errors.append(Error('GOOGLE_REDIRECT_URL production domenini ko‘rsatsin.', id='animee.E005'))
    return errors
