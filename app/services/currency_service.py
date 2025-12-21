import logging
import requests
from decimal import Decimal
from django.utils import timezone

logger = logging.getLogger(__name__)


class CurrencyService:
    """
    Сервис для работы с курсами валют.
    Использует ExchangeRate-API v6 для получения курсов.
    """
    
    API_KEY = 'a56426f592a64e93b501a72d'
    API_URL = f'https://v6.exchangerate-api.com/v6/{API_KEY}/latest/RUB'
    
    @classmethod
    def update_rates(cls):
        """
        Обновить курсы всех валют к RUB.
        Возвращает True при успехе, False при ошибке.
        """
        from app.models import Currency
        
        try:
            response = requests.get(cls.API_URL, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('result') != 'success':
                logger.error(f'ExchangeRate-API error: {data}')
                return False
            
            rates = data.get('conversion_rates', {})
            
            updated_count = 0
            for currency in Currency.objects.all():
                if currency.code == 'RUB':
                    currency.rate_to_rub = Decimal('1.000000')
                    currency.save(update_fields=['rate_to_rub', 'updated_at'])
                    updated_count += 1
                elif currency.code in rates:
                    # API возвращает курс RUB к другим валютам
                    # Нам нужен курс валюты к RUB (обратный)
                    rate_rub_to_currency = Decimal(str(rates[currency.code]))
                    if rate_rub_to_currency > 0:
                        # rate_to_rub = сколько рублей за 1 единицу валюты
                        rate_to_rub = Decimal('1') / rate_rub_to_currency
                        currency.rate_to_rub = round(rate_to_rub, 6)
                        currency.save(update_fields=['rate_to_rub', 'updated_at'])
                        updated_count += 1
            
            logger.info(f'Currency rates updated successfully. Updated {updated_count} currencies.')
            return True
            
        except requests.RequestException as e:
            logger.error(f'Error fetching currency rates: {e}')
            return False
        except Exception as e:
            logger.error(f'Error updating currency rates: {e}')
            return False
    
    @classmethod
    def convert(cls, amount, from_currency, to_currency):
        """
        Конвертировать сумму из одной валюты в другую.
        
        Args:
            amount: Сумма для конвертации
            from_currency: Исходная валюта (объект Currency)
            to_currency: Целевая валюта (объект Currency)
        
        Returns:
            Decimal: Сконвертированная сумма, округлённая до 2 знаков
        """
        if from_currency is None or to_currency is None:
            return Decimal(str(amount))
        
        if from_currency.code == to_currency.code:
            return Decimal(str(amount))
        
        # Конвертация через RUB как базовую валюту
        # amount_in_rub = amount * from_currency.rate_to_rub
        # result = amount_in_rub / to_currency.rate_to_rub
        amount_decimal = Decimal(str(amount))
        amount_in_rub = amount_decimal * from_currency.rate_to_rub
        
        if to_currency.rate_to_rub == 0:
            return amount_decimal
        
        result = amount_in_rub / to_currency.rate_to_rub
        return round(result, 2)
    
    @classmethod
    def convert_to_rub(cls, amount, from_currency):
        """
        Конвертировать сумму в рубли.
        
        Args:
            amount: Сумма для конвертации
            from_currency: Исходная валюта (объект Currency)
        
        Returns:
            Decimal: Сумма в рублях, округлённая до 2 знаков
        """
        if from_currency is None:
            return Decimal(str(amount))
        
        if from_currency.code == 'RUB':
            return Decimal(str(amount))
        
        amount_decimal = Decimal(str(amount))
        result = amount_decimal * from_currency.rate_to_rub
        return round(result, 2)
