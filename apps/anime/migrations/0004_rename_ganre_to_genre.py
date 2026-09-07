from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('anime', '0003_rename_discription_anime_description_and_more'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='Ganre',
            new_name='Genre',
        ),
        migrations.RenameField(
            model_name='anime',
            old_name='ganres',
            new_name='genres',
        ),
    ]
