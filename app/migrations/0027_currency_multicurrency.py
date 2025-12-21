from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0024_currency_title_alter_lessor_commission'),
    ]

    operations = [
        migrations.AddField(
            model_name='currency',
            name='symbol',
            field=models.CharField(blank=True, default='', max_length=5, verbose_name='Символ'),
        ),
        migrations.AddField(
            model_name='currency',
            name='rate_to_rub',
            field=models.DecimalField(decimal_places=6, default=1, max_digits=18, verbose_name='Курс к RUB'),
        ),
        migrations.AddField(
            model_name='currency',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, verbose_name='Дата обновления курса'),
        ),
    ]
