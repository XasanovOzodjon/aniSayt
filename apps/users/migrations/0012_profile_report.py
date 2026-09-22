from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0011_watch_streak'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProfileReport',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('kind', models.CharField(choices=[('photo', 'Profil rasmi'), ('banner', 'Banner'), ('nick', 'Nick'), ('bio', 'Tavsif')], max_length=12)),
                ('note', models.CharField(blank=True, max_length=400)),
                ('snapshot', models.CharField(blank=True, max_length=500)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('resolved_at', models.DateTimeField(blank=True, null=True)),
                ('reporter', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='profile_reports_sent', to='users.customuser')),
                ('target', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='profile_reports', to='users.customuser')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddConstraint(
            model_name='profilereport',
            constraint=models.UniqueConstraint(condition=models.Q(('resolved_at__isnull', True)), fields=('reporter', 'target', 'kind'), name='uniq_open_profile_report'),
        ),
    ]
