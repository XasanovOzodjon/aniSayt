from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('episode', '0005_video_optional_file'),
    ]

    operations = [
        migrations.AddField(
            model_name='video',
            name='source_url',
            field=models.CharField(blank=True, max_length=1000),
        ),
        migrations.AddField(
            model_name='video',
            name='ingest_error',
            field=models.CharField(blank=True, max_length=255),
        ),
    ]
