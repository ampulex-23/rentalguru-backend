from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0027_currency_multicurrency'),
        ('vehicle', '0033_increase_price_deposit_max_digits'),
    ]

    operations = [
        migrations.AddField(
            model_name='vehicle',
            name='currency',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='vehicles', to='app.currency', verbose_name='Валюта'),
        ),
    ]
