from django.conf import settings
from django.templatetags.static import static

HOME_TITLE = 'Animee.uz — Eng sara Kinolar, Animelar'
HOME_DESCRIPTION = (
    'Animee.uz — eng sara kinolar, animelar, dramalar va seriallar. '
    'Onlayn tomosha qiling.'
)

HUBS = (
    {
        'slug': '',
        'kind': '',
        'path': '/catalog/',
        'label': 'Katalog',
        'title': 'Katalog — Animee.uz',
    },
    {
        'slug': 'anime',
        'kind': 'anime',
        'path': '/catalog/anime/',
        'label': 'Animelar',
        'title': 'Animelar — Animee.uz',
    },
    {
        'slug': 'drama',
        'kind': 'drama',
        'path': '/catalog/drama/',
        'label': 'Dramalar',
        'title': 'Dramalar — Animee.uz',
    },
    {
        'slug': 'kino',
        'kind': 'film',
        'path': '/catalog/kino/',
        'label': 'Kinolar',
        'title': 'Kinolar — Animee.uz',
    },
    {
        'slug': 'serial',
        'kind': 'serial',
        'path': '/catalog/serial/',
        'label': 'Seriallar',
        'title': 'Seriallar — Animee.uz',
    },
)
HUB_BY_SLUG = {row['slug']: row for row in HUBS}


def site_origin():
    return (settings.SITE_URL or 'https://animee.uz').rstrip('/')


def hub_for(slug):
    if slug is None or slug == '':
        return HUB_BY_SLUG['']
    return HUB_BY_SLUG.get(slug)


def website_json_ld():
    origin = site_origin()
    return {
        '@context': 'https://schema.org',
        '@type': 'WebSite',
        'name': 'Animee.uz',
        'url': f'{origin}/',
        'potentialAction': {
            '@type': 'SearchAction',
            'target': f'{origin}/catalog/?q={{search_term_string}}',
            'query-input': 'required name=search_term_string',
        },
    }


def nav_json_ld():
    origin = site_origin()
    return {
        '@context': 'https://schema.org',
        '@type': 'ItemList',
        'itemListElement': [
            {
                '@type': 'SiteNavigationElement',
                'position': index,
                'name': row['label'],
                'url': f'{origin}{row["path"]}',
            }
            for index, row in enumerate(HUBS, 1)
        ],
    }


def page_ctx(request, title, description=None, canonical_path=None, extra_json=None):
    import json

    origin = site_origin()
    path = canonical_path or request.path
    payload = [website_json_ld()]
    if extra_json:
        payload.extend(extra_json if isinstance(extra_json, list) else [extra_json])
    image = origin + static('img/player-poster.jpg')
    return {
        'seo_title': title,
        'seo_description': description or HOME_DESCRIPTION,
        'seo_canonical': origin + path,
        'seo_image': image,
        'seo_json_ld': json.dumps(payload, ensure_ascii=False),
    }
