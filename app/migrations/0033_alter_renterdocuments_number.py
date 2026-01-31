# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0030_add_lessor_withdraw_request'),
    ]

    operations = [
        migrations.AlterField(
            model_name='renterdocuments',
            name='number',
            field=models.CharField(max_length=50, verbose_name='Номер'),
        ),
    ]
