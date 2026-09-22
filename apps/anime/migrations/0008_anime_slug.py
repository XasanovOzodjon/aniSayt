from django.db import migrations, models
from django.utils.text import slugify


def fill_slugs(apps, schema_editor):
    Anime = apps.get_model('anime', 'Anime')
    used = set()
    for anime in Anime.objects.order_by('id'):
        base = slugify(anime.title or '', allow_unicode=True) or f'title-{anime.pk}'
        base = base[:80].strip('-') or f'title-{anime.pk}'
        slug = base
        n = 2
        while slug in used:
            slug = f'{base[:70]}-{n}'
            n += 1
        used.add(slug)
        anime.slug = slug
        anime.save(update_fields=['slug'])


class Migration(migrations.Migration):

    dependencies = [
        ('anime', '0007_age_rating'),
    ]

    operations = [
        migrations.AddField(
            model_name='anime',
            name='slug',
            field=models.SlugField(allow_unicode=True, blank=True, db_index=False, max_length=100, null=True),
        ),
        migrations.RunPython(fill_slugs, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='anime',
            name='slug',
            field=models.SlugField(allow_unicode=True, blank=True, max_length=100, unique=True),
        ),
    ]
