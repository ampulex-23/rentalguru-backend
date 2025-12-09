# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notification', '0002_alter_notification_url'),
    ]

    operations = [
        migrations.AddField(
            model_name='fcmtoken',
            name='device_type',
            field=models.CharField(
                choices=[('web', 'Web Browser'), ('android', 'Android'), ('ios', 'iOS')],
                default='web',
                max_length=10,
                verbose_name='Тип устройства'
            ),
        ),
        migrations.AddField(
            model_name='fcmtoken',
            name='is_active',
            field=models.BooleanField(default=True, verbose_name='Активен'),
        ),
    ]
