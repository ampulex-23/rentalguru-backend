from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0028_alter_user_options'),
    ]

    operations = [
        migrations.AddField(
            model_name='lessor',
            name='director_name',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='ФИО директора'),
        ),
        migrations.AddField(
            model_name='lessor',
            name='company_name',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='Название компании'),
        ),
        migrations.AddField(
            model_name='lessor',
            name='country',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='Страна'),
        ),
        migrations.AddField(
            model_name='lessor',
            name='city',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='Город'),
        ),
        migrations.AddField(
            model_name='lessor',
            name='address',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='Адрес'),
        ),
        migrations.AddField(
            model_name='lessor',
            name='account_number',
            field=models.CharField(blank=True, max_length=50, null=True, verbose_name='Расчетный счет'),
        ),
        migrations.AddField(
            model_name='lessor',
            name='account_owner',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='ФИО владельца счета'),
        ),
        migrations.AddField(
            model_name='lessor',
            name='phone_1',
            field=models.CharField(blank=True, max_length=20, null=True, verbose_name='Телефон 1'),
        ),
        migrations.AddField(
            model_name='lessor',
            name='phone_2',
            field=models.CharField(blank=True, max_length=20, null=True, verbose_name='Телефон 2'),
        ),
        migrations.AddField(
            model_name='lessor',
            name='email_1',
            field=models.EmailField(blank=True, max_length=254, null=True, verbose_name='Email 1'),
        ),
        migrations.AddField(
            model_name='lessor',
            name='email_2',
            field=models.EmailField(blank=True, max_length=254, null=True, verbose_name='Email 2'),
        ),
    ]
