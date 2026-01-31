# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0032_add_unique_together_renter_documents'),
    ]

    operations = [
        migrations.AlterField(
            model_name='renterdocuments',
            name='number',
            field=models.CharField(max_length=50, verbose_name='Номер'),
        ),
    ]
