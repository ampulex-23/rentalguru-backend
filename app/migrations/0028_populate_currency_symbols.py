from django.db import migrations


CURRENCY_SYMBOLS = {
    'RUB': '₽',
    'USD': '$',
    'EUR': '€',
    'GBP': '£',
    'JPY': '¥',
    'CNY': '¥',
    'KRW': '₩',
    'INR': '₹',
    'THB': '฿',
    'AED': 'د.إ',
    'TRY': '₺',
    'UAH': '₴',
    'KZT': '₸',
    'BRL': 'R$',
    'PLN': 'zł',
    'CHF': 'Fr',
    'SEK': 'kr',
    'NOK': 'kr',
    'DKK': 'kr',
    'CZK': 'Kč',
    'HUF': 'Ft',
    'RON': 'lei',
    'BGN': 'лв',
    'HRK': 'kn',
    'RSD': 'дин',
    'GEL': '₾',
    'AMD': '֏',
    'AZN': '₼',
    'BYN': 'Br',
    'MDL': 'L',
    'KGS': 'с',
    'TJS': 'с.',
    'UZS': 'сўм',
    'TMT': 'm',
    'CAD': 'C$',
    'AUD': 'A$',
    'NZD': 'NZ$',
    'SGD': 'S$',
    'HKD': 'HK$',
    'IDR': 'Rp',
    'VND': '₫',
    'EGP': 'E£',
    'QAR': 'ر.ق',
    'ZAR': 'R',
    'XDR': 'SDR',
}


def populate_symbols(apps, schema_editor):
    Currency = apps.get_model('app', 'Currency')
    for currency in Currency.objects.all():
        if currency.code in CURRENCY_SYMBOLS:
            currency.symbol = CURRENCY_SYMBOLS[currency.code]
            currency.save(update_fields=['symbol'])


def reverse_populate(apps, schema_editor):
    Currency = apps.get_model('app', 'Currency')
    Currency.objects.all().update(symbol='')


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0027_currency_multicurrency'),
    ]

    operations = [
        migrations.RunPython(populate_symbols, reverse_populate),
    ]
