from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0012_profile_report'),
    ]

    operations = [
        migrations.AlterField(
            model_name='notice',
            name='kind',
            field=models.CharField(
                choices=[
                    ('new_season', 'Yangi sezon'),
                    ('new_episode', 'Yangi qism'),
                    ('news', 'Yangilik'),
                    ('moderation', 'Moderatsiya'),
                ],
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name='profilereport',
            name='reason',
            field=models.CharField(default='other', max_length=20),
        ),
        migrations.CreateModel(
            name='UserModeration',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('banned_at', models.DateTimeField(blank=True, null=True)),
                ('banned_until', models.DateTimeField(blank=True, null=True)),
                ('ban_reason', models.CharField(blank=True, max_length=400)),
                ('ban_allow_appeal', models.BooleanField(default=True)),
                ('report_strikes', models.PositiveSmallIntegerField(default=0)),
                ('report_mute_until', models.DateTimeField(blank=True, null=True)),
                ('lock_username', models.BooleanField(default=False)),
                ('lock_photo', models.BooleanField(default=False)),
                ('keep_photo', models.BooleanField(default=False)),
                ('lock_banner', models.BooleanField(default=False)),
                ('keep_banner', models.BooleanField(default=False)),
                ('lock_bio', models.BooleanField(default=False)),
                ('keep_bio', models.BooleanField(default=False)),
                ('lock_comments', models.BooleanField(default=False)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='moderation', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='UnbanRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('body', models.CharField(max_length=800)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('resolved_at', models.DateTimeField(blank=True, null=True)),
                ('accepted', models.BooleanField(blank=True, null=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='unban_requests', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddConstraint(
            model_name='unbanrequest',
            constraint=models.UniqueConstraint(condition=models.Q(('resolved_at__isnull', True)), fields=('user',), name='uniq_open_unban_request'),
        ),
    ]
