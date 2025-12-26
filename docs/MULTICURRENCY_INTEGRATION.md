# Интеграция мультивалютности в мобильное приложение

## 1. Получение списка валют

```
GET /app/currencies/
```

**Ответ:**
```json
[
  {"id": 1, "code": "RUB", "symbol": "₽", "title": "Рубль"},
  {"id": 2, "code": "USD", "symbol": "$", "title": "Доллар"},
  {"id": 3, "code": "BYN", "symbol": "Br", "title": "Белорусский рубль"}
]
```

---

## 2. Валюта пользователя

**Получить профиль:**
```
GET /app/users/me/
```

**Ответ содержит:**
```json
{
  "currency": {"id": 1, "code": "RUB", "symbol": "₽", "title": "Рубль"}
}
```

**Изменить валюту пользователя:**
```
PATCH /app/users/me/
Content-Type: application/json

{"currency_id": 2}
```

---

## 3. Конвертация цен при получении транспорта

При запросе списка транспорта передай параметр `?currency=XXX`:

```
GET /vehicle/all_vehicles/?currency=BYN
GET /vehicle/auto/?currency=USD
```

**Ответ:**
```json
{
  "currency": {"code": "RUB", "symbol": "₽"},
  "user_currency": {"code": "BYN", "symbol": "Br"},
  "rent_prices": [
    {
      "name": "day",
      "price": "5000.00",
      "total": "5000.00",
      "price_converted": "150.00",
      "total_converted": "150.00"
    }
  ]
}
```

| Поле | Описание |
|------|----------|
| `currency` | Валюта транспорта (в которой указана цена) |
| `user_currency` | Валюта пользователя (для отображения) |
| `price` / `total` | Цена в валюте транспорта |
| `price_converted` / `total_converted` | Цена в валюте пользователя (null если валюты совпадают) |

---

## 4. Валюта транспорта

**При создании транспорта:**
```
POST /vehicle/auto/
{
  "currency_id": 1,
  ...
}
```

Если `currency_id` не передан — берётся валюта из профиля владельца.

**При редактировании:**
```
PATCH /vehicle/auto/{id}/
{
  "currency_id": 2
}
```

---

## 5. Логика отображения цен

```dart
// Псевдокод для Flutter
String displayPrice(RentPrice price, Currency userCurrency) {
  if (price.totalConverted != null) {
    // Показываем конвертированную цену
    return '${price.totalConverted} ${userCurrency.symbol}';
  }
  // Валюты совпадают — показываем оригинал
  return '${price.total} ${vehicleCurrency.symbol}';
}
```

---

## 6. Рекомендации

1. **Храни валюту пользователя локально** — бери из `/app/users/me/` при старте
2. **Передавай `?currency=XXX`** во всех запросах списков транспорта
3. **Показывай обе цены** если они разные: `5000 ₽ (~150 Br)`
4. **Обновляй курсы** — курсы обновляются на бэке, просто делай новые запросы

---

## 7. Эндпоинты с поддержкой конвертации

| Эндпоинт | Параметр |
|----------|----------|
| `/vehicle/all_vehicles/` | `?currency=XXX` |
| `/vehicle/auto/` | `?currency=XXX` |
| `/vehicle/bike/` | `?currency=XXX` |
| `/vehicle/ship/` | `?currency=XXX` |
| `/vehicle/helicopter/` | `?currency=XXX` |
| `/vehicle/special_technic/` | `?currency=XXX` |
