from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0005_notice_read_and_news'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='is_moderator',
            field=models.BooleanField(default=False),
        ),
    ]
