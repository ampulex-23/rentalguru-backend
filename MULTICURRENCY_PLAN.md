# План реализации мультивалютности

## Обзор

Арендодатель устанавливает цену в валюте страны размещения. Клиент видит цену в оригинальной валюте по умолчанию, но может переключить на свою валюту для просмотра.

---

## Этап 1: Модели (Backend)

### 1.1 Расширить модель Currency

**Файл:** `app/models.py`

```python
class Currency(models.Model):
    code = models.CharField(max_length=3, unique=True)  # RUB, THB, USD, AED
    title = models.CharField(max_length=255, null=True)  # Российский рубль
    symbol = models.CharField(max_length=5, default='')  # ₽, ฿, $, د.إ
    rate_to_usd = models.DecimalField(max_digits=18, decimal_places=6, default=1)  # курс к USD
    updated_at = models.DateTimeField(auto_now=True)
```

### 1.2 Добавить currency в Vehicle

**Файл:** `vehicle/models.py`

```python
class Vehicle(models.Model):
    # ... существующие поля ...
    currency = models.ForeignKey(
        'app.Currency', 
        on_delete=models.SET_DEFAULT,
        default=1,  # RUB по умолчанию
        verbose_name='Валюта'
    )
```

### 1.3 Миграции

```bash
python manage.py makemigrations app --name add_currency_rate_fields
python manage.py makemigrations vehicle --name add_vehicle_currency
python manage.py migrate
```

---

## Этап 2: Сервис обновления курсов (Backend)

### 2.1 Создать сервис для получения курсов

**Файл:** `app/services/currency_service.py`

```python
import requests
from decimal import Decimal
from django.utils import timezone
from app.models import Currency

class CurrencyService:
    # Бесплатный API: https://api.exchangerate-api.com/v4/latest/USD
    API_URL = 'https://api.exchangerate-api.com/v4/latest/USD'
    
    @classmethod
    def update_rates(cls):
        """Обновить курсы всех валют"""
        try:
            response = requests.get(cls.API_URL, timeout=10)
            data = response.json()
            rates = data.get('rates', {})
            
            for currency in Currency.objects.all():
                if currency.code in rates:
                    currency.rate_to_usd = Decimal(str(rates[currency.code]))
                    currency.save(update_fields=['rate_to_usd', 'updated_at'])
            
            return True
        except Exception as e:
            print(f'Error updating currency rates: {e}')
            return False
    
    @classmethod
    def convert(cls, amount, from_currency, to_currency):
        """Конвертировать сумму из одной валюты в другую"""
        if from_currency.code == to_currency.code:
            return amount
        
        # Конвертация через USD как базовую валюту
        amount_in_usd = Decimal(str(amount)) / from_currency.rate_to_usd
        return round(amount_in_usd * to_currency.rate_to_usd, 2)
```

### 2.2 Celery task для обновления курсов

**Файл:** `app/tasks.py`

```python
from celery import shared_task
from app.services.currency_service import CurrencyService

@shared_task
def update_currency_rates():
    """Обновление курсов валют (запускать раз в час)"""
    CurrencyService.update_rates()
```

**Файл:** `RentalGuru/celery.py` (добавить в beat_schedule)

```python
CELERY_BEAT_SCHEDULE = {
    'update-currency-rates': {
        'task': 'app.tasks.update_currency_rates',
        'schedule': 3600,  # каждый час
    },
}
```

---

## Этап 3: API (Backend)

### 3.1 Сериализатор для Currency

**Файл:** `app/serializers.py`

```python
class CurrencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Currency
        fields = ['id', 'code', 'title', 'symbol', 'rate_to_usd', 'updated_at']
```

### 3.2 Добавить конвертацию в Vehicle сериализаторы

**Файл:** `vehicle/serializers/base.py`

```python
class RentPriceSerializer(serializers.ModelSerializer):
    price_converted = serializers.SerializerMethodField()
    
    class Meta:
        model = RentPrice
        fields = ['name', 'price', 'discount', 'total', 'price_converted', 'total_converted']
        read_only_fields = ['total', 'price_converted', 'total_converted']
    
    def get_price_converted(self, obj):
        request = self.context.get('request')
        target_currency = self._get_target_currency(request)
        if not target_currency or target_currency == obj.vehicle.currency:
            return None
        return CurrencyService.convert(obj.price, obj.vehicle.currency, target_currency)
    
    def get_total_converted(self, obj):
        request = self.context.get('request')
        target_currency = self._get_target_currency(request)
        if not target_currency or target_currency == obj.vehicle.currency:
            return None
        return CurrencyService.convert(obj.total, obj.vehicle.currency, target_currency)
    
    def _get_target_currency(self, request):
        if not request:
            return None
        currency_code = request.query_params.get('currency')
        if currency_code:
            return Currency.objects.filter(code=currency_code).first()
        if request.user.is_authenticated:
            return request.user.currency
        return None
```

### 3.3 Добавить currency в Vehicle сериализаторы

```python
class VehicleSerializer(serializers.ModelSerializer):
    currency = CurrencySerializer(read_only=True)
    currency_id = serializers.PrimaryKeyRelatedField(
        queryset=Currency.objects.all(),
        source='currency',
        write_only=True,
        required=False
    )
    user_currency = serializers.SerializerMethodField()
    
    def get_user_currency(self, obj):
        request = self.context.get('request')
        currency_code = request.query_params.get('currency') if request else None
        if currency_code:
            currency = Currency.objects.filter(code=currency_code).first()
            if currency:
                return CurrencySerializer(currency).data
        if request and request.user.is_authenticated and request.user.currency:
            return CurrencySerializer(request.user.currency).data
        return None
```

### 3.4 Endpoint для получения курсов

**Файл:** `app/views.py`

```python
class CurrencyListView(ListAPIView):
    queryset = Currency.objects.all()
    serializer_class = CurrencySerializer
    permission_classes = [AllowAny]
```

---

## Этап 4: Заполнение данных

### 4.1 Начальные валюты

```python
# management command или миграция
currencies = [
    {'code': 'RUB', 'title': 'Российский рубль', 'symbol': '₽'},
    {'code': 'USD', 'title': 'Доллар США', 'symbol': '$'},
    {'code': 'EUR', 'title': 'Евро', 'symbol': '€'},
    {'code': 'THB', 'title': 'Тайский бат', 'symbol': '฿'},
    {'code': 'AED', 'title': 'Дирхам ОАЭ', 'symbol': 'د.إ'},
    {'code': 'TRY', 'title': 'Турецкая лира', 'symbol': '₺'},
]
```

### 4.2 Установить валюту для существующих Vehicle

```python
# Все существующие транспорты → RUB (или определить по городу)
Vehicle.objects.filter(currency__isnull=True).update(currency_id=1)
```

---

## Этап 5: Frontend (Flutter)

### 5.1 API Response формат

```json
{
  "id": 142,
  "currency": {
    "code": "THB",
    "symbol": "฿",
    "title": "Тайский бат"
  },
  "user_currency": {
    "code": "RUB",
    "symbol": "₽"
  },
  "rent_prices": [
    {
      "name": "day",
      "price": "1000.00",
      "total": "1250.00",
      "price_converted": "2500.00",
      "total_converted": "3125.00"
    }
  ]
}
```

### 5.2 Отображение на Flutter

```
Цена: ฿1,000 / день
      ≈ ₽2,500
```

---

## Этап 6: Тестирование

- [ ] Создание транспорта с валютой
- [ ] Просмотр транспорта без конвертации (та же валюта)
- [ ] Просмотр транспорта с конвертацией (?currency=RUB)
- [ ] Обновление курсов через Celery
- [ ] Проверка расчёта комиссии (в оригинальной валюте)

---

## Оценка трудозатрат

| Этап | Backend | Frontend | Всего |
|------|---------|----------|-------|
| 1. Модели | 2ч | - | 2ч |
| 2. Сервис курсов | 3ч | - | 3ч |
| 3. API | 4ч | - | 4ч |
| 4. Данные | 1ч | - | 1ч |
| 5. Flutter | - | 4ч | 4ч |
| 6. Тестирование | 2ч | 2ч | 4ч |
| **Итого** | **12ч** | **6ч** | **18ч** |

---

## Вопросы для уточнения

1. **Какие валюты нужны?** RUB, USD, EUR, THB, AED, TRY — достаточно?
2. **Валюта по умолчанию для нового транспорта** — определять по городу арендодателя или выбирать вручную?
3. **Оплата** — всегда в оригинальной валюте транспорта или в валюте пользователя?
4. **Частота обновления курсов** — раз в час достаточно?
