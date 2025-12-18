from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vehicle', '0032_vehicle_verified_at'),
    ]

    operations = [
        migrations.AlterField(
            model_name='vehicle',
            name='price_deposit',
            field=models.DecimalField(decimal_places=2, max_digits=15, verbose_name='депозит'),
        ),
    ]
