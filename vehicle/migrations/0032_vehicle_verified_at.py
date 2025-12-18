from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vehicle', '0031_vehicle_created_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='vehicle',
            name='verified_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Дата верификации'),
        ),
    ]
