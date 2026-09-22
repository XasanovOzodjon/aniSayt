from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0009_profile_banner'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='show_watching',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='customuser',
            name='status_line',
            field=models.CharField(blank=True, max_length=80),
        ),
    ]
