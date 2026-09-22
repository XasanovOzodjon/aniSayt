from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('episode', '0005_video_optional_file'),
        ('users', '0006_is_moderator'),
    ]

    operations = [
        migrations.CreateModel(
            name='Progress',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('position', models.FloatField(default=0)),
                ('duration', models.FloatField(default=0)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('episode', models.ForeignKey(
                    on_delete=models.deletion.CASCADE,
                    related_name='progress',
                    to='episode.episode',
                )),
                ('user', models.ForeignKey(
                    on_delete=models.deletion.CASCADE,
                    related_name='progress',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
        ),
        migrations.AddConstraint(
            model_name='progress',
            constraint=models.UniqueConstraint(fields=('user', 'episode'), name='uniq_user_episode_progress'),
        ),
    ]
