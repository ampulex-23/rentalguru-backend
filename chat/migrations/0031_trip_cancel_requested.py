from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0030_add_canceled_status_to_request_rent'),
    ]

    operations = [
        migrations.AddField(
            model_name='trip',
            name='cancel_requested',
            field=models.BooleanField(default=False, verbose_name='Запрос на отмену'),
        ),
    ]
