from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('anime', '0005_profile_lists_and_kind'),
    ]

    operations = [
        migrations.AlterField(
            model_name='anime',
            name='kind',
            field=models.CharField(
                choices=[
                    ('anime', 'Anime'),
                    ('drama', 'Drama'),
                    ('film', 'Kino'),
                    ('serial', 'Serial'),
                ],
                db_index=True,
                default='anime',
                max_length=8,
            ),
        ),
    ]
