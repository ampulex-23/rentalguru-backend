from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0027_currency_multicurrency'),
        ('franchise', '0010_franchisedocuments'),
    ]

    operations = [
        migrations.AddField(
            model_name='city',
            name='country',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='Страна'),
        ),
        migrations.AddField(
            model_name='city',
            name='currency',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='cities', to='app.currency', verbose_name='Валюта'),
        ),
    ]
