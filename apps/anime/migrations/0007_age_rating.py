from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('anime', '0006_kind_serial'),
    ]

    operations = [
        migrations.AddField(
            model_name='anime',
            name='age_rating',
            field=models.CharField(
                choices=[
                    ('0+', '0+'),
                    ('6+', '6+'),
                    ('12+', '12+'),
                    ('16+', '16+'),
                    ('18+', '18+'),
                ],
                db_index=True,
                default='16+',
                max_length=4,
            ),
        ),
    ]
