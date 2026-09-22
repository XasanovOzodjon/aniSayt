from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0008_comments_likes'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='banner',
            field=models.ImageField(blank=True, null=True, upload_to='users/banners/'),
        ),
    ]
