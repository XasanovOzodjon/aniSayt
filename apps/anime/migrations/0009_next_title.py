from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('anime', '0008_anime_slug'),
    ]

    operations = [
        migrations.AddField(
            model_name='anime',
            name='next_title',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='previous_titles',
                to='anime.anime',
            ),
        ),
    ]
