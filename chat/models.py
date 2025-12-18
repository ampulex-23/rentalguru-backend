import json
from datetime import datetime, timedelta, time, date
from decimal import Decimal
import pytz
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models, transaction

from RentalGuru import settings
from influencer.models import PromoCode, UsedPromoCode


class RequestRent(models.Model):
    """ Заявки на аренду """
    STATUS_CHOICES = (
        ('accept', 'Принять'),
        ('denied', 'Отказать'),
        ('unknown', 'Не рассмотрено'),
        ('paid', 'Оплачено')
    )
    status = models.CharField(max_length=8, default='unknown', choices=STATUS_CHOICES, verbose_name='Статус')
    denied_reason = models.TextField(null=True, blank=True, verbose_name='Причина отказа', max_length=300)

    organizer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                  related_name='request_rent_organized_trips', verbose_name='Арендатор')

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, limit_choices_to={
        'model__in': ('auto', 'bike', 'ship', 'helicopter', 'specialtechnic')}, verbose_name='Тип транспорта')
    object_id = models.PositiveIntegerField(verbose_name='id транспорта')
    vehicle = GenericForeignKey('content_type', 'object_id')

    start_time = models.TimeField(null=True, blank=True, verbose_name='Время начала аренды')
    end_time = models.TimeField(null=True, blank=True, verbose_name='Время окончания аренды')
    start_date = models.DateField(verbose_name='Начало аренды', null=True, blank=True)
    end_date = models.DateField(verbose_name='Конец аренды', null=True, blank=True)
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Итоговая стоимость', default=0.00)
    deposit_cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Депозит', default=0.00)
    delivery_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00,
                                        verbose_name='Стоимость доставки')
    delivery = models.BooleanField(default=False, verbose_name='Доставка')
    on_request = models.BooleanField(null=True, blank=True, verbose_name='Заявка по запросу')
    is_deleted = models.BooleanField(default=False, verbose_name='Удалена')
    promocode = models.ForeignKey(PromoCode, on_delete=models.SET_NULL, blank=True, null=True,
                                  verbose_name="Активный промокод", related_name='request_rents')
    bonus = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True,
                                verbose_name="Использованные бонусные рубли")

    @property
    def owner(self):
        return self.vehicle.owner

    @property
    def rental_days(self):
        """
        Подсчитывает количество дней аренды с учётом времени.
        
        Логика:
        - 10 дек 18:00 → 11 дек 18:00 = 1 день (ровно 24 часа)
        - 10 дек 18:00 → 11 дек 18:01 = 2 дня (больше 24 часов - округляем вверх)
        - 10 дек 18:00 → 12 дек 18:00 = 2 дня (ровно 48 часов)
        - 10 дек 18:00 → 12 дек 18:01 = 3 дня (больше 48 часов)
        """
        if self.start_date and self.end_date:
            import math
            
            # Определяем время начала и окончания
            start_time = self.start_time if self.start_time else time(0, 0)
            end_time = self.end_time if self.end_time else time(0, 0)
            
            # Создаём полные datetime объекты
            start_datetime = datetime.combine(self.start_date, start_time)
            end_datetime = datetime.combine(self.end_date, end_time)
            
            # Вычисляем разницу в секундах
            delta = end_datetime - start_datetime
            total_seconds = delta.total_seconds()
            
            if total_seconds <= 0:
                return 1  # Минимум 1 день
            
            # Вычисляем количество полных 24-часовых периодов
            total_hours = total_seconds / 3600
            
            # Для почасовой аренды (меньше 24 часов в пределах одного дня)
            if total_hours < 24 and self.start_date == self.end_date:
                # Возвращаем дробное значение для почасового тарифа
                return max(total_hours / 24, 0.01)
            
            # Для дневной аренды: округляем вверх до целых дней
            # Если ровно N*24 часа - это N дней
            # Если больше N*24 часа хоть на секунду - это N+1 дней
            days = total_hours / 24
            
            # Проверяем, есть ли "хвост" сверх целых дней
            if days == int(days):
                return max(1, int(days))
            else:
                return max(1, math.ceil(days))
        return 0

    def create_chat(self):
        """Создание чата при подаче заявки или подтверждении аренды."""
        if not Chat.objects.filter(request_rent=self).exists():
            chat = Chat.objects.create(request_rent=self)
            chat.participants.add(self.organizer, self.vehicle.owner)
            chat.save()
            amount = self.calculate_amount()

            message_content = json.dumps({
                "status": self.status,
                "organizer_id": self.organizer.id,
                "vehicle_id": self.object_id,
                "vehicle_type": str(self.content_type),
                "start_date": str(self.start_date),
                "end_date": str(self.end_date),
                "start_time": str(self.start_time),
                "end_time": str(self.end_time),
                "total_cost": float(self.total_cost),
                "deposit_cost": float(self.deposit_cost),
                "delivery_cost": float(self.delivery_cost),
                "delivery": self.delivery,
                "amount": round(float(amount), 2),
                "on_request": self.on_request
            }, ensure_ascii=False)

            Message.objects.create(
                chat=chat,
                sender=self.organizer,
                content=message_content
            )

    def calculate_rent_price(self):
        """Подсчитывает итоговую стоимость аренды с поддержкой почасовой оплаты."""
        from vehicle.models import RentPrice
        from datetime import datetime

        # Если указано время аренды в пределах одного дня
        if self.start_time and self.end_time and self.start_date and self.end_date and self.start_date == self.end_date:
            start_datetime = datetime.combine(self.start_date, self.start_time)
            end_datetime = datetime.combine(self.end_date, self.end_time)

            if end_datetime <= start_datetime:
                raise ValueError("Время окончания должно быть больше времени начала.")

            total_duration = end_datetime - start_datetime
            total_hours = total_duration.total_seconds() / 3600

            # Если аренда >= 8 часов, пытаемся использовать дневной тариф
            if total_hours >= 8:
                daily_price = RentPrice.objects.filter(vehicle=self.vehicle, name='day').first()
                if daily_price:
                    # Есть дневной тариф - используем его (выгоднее для клиента)
                    total_cost = float(daily_price.total)
                    
                    if self.delivery:
                        total_cost += float(self.vehicle.price_delivery)
                    
                    return total_cost
                else:
                    # Нет дневного тарифа - ищем почасовой
                    hourly_price = RentPrice.objects.filter(vehicle=self.vehicle, name='hour').first()
                    if hourly_price:
                        total_cost = total_hours * float(hourly_price.total)
                        
                        if self.delivery:
                            total_cost += float(self.vehicle.price_delivery)
                        
                        return total_cost
                    else:
                        raise ValueError("Для аренды >= 8 часов требуется дневной или почасовой тариф.")
            else:
                # Меньше 8 часов - только почасовой тариф
                hourly_price = RentPrice.objects.filter(vehicle=self.vehicle, name='hour').first()
                if hourly_price:
                    total_cost = total_hours * float(hourly_price.total)

                    if self.delivery:
                        total_cost += float(self.vehicle.price_delivery)

                    return total_cost
                else:
                    raise ValueError("Для почасовой аренды (< 8 часов) требуется почасовой тариф.")

        # Иначе используем оригинальную логику для дневных тарифов
        rental_days = self.rental_days
        if rental_days <= 0:
            raise ValueError("Количество дней аренды должно быть положительным.")

        period_priorities = [
            ('year', 365),
            ('month', 30),
            ('week', 7),
            ('day', 1),
        ]

        suitable_periods = [(period, days) for period, days in period_priorities if rental_days >= days]

        if not suitable_periods:
            raise ValueError("Не найден подходящий период аренды для текущего количества дней.")

        for period, period_days in suitable_periods:
            rent_price = RentPrice.objects.filter(vehicle=self.vehicle, name=period).first()
            if rent_price:
                break
        else:
            raise ValueError("Не найдена цена аренды для указанного транспортного средства.")

        total_cost = (rental_days / period_days) * float(rent_price.total)

        if self.delivery:
            total_cost += float(self.vehicle.price_delivery)

        return total_cost


    def clean(self):
        super().clean()

    def save(self, *args, **kwargs):
        if not self.pk:
            if self.vehicle and not self.deposit_cost:
                self.deposit_cost = self.vehicle.price_deposit
            self.delivery_cost = self.vehicle.price_delivery if self.delivery else 0.00
            # Рассчитываем итоговую стоимость при создании
            self.total_cost = self.calculate_rent_price()
            
            # Определяем on_request на основе того, попадают ли даты в обычный availability
            from vehicle.models import Availability
            from chat.utils import is_period_contained
            import logging
            logger = logging.getLogger(__name__)
            
            # Проверяем, попадают ли выбранные даты в availability с on_request=False
            if self.start_date and self.end_date:
                regular_availabilities = list(Availability.objects.filter(
                    vehicle=self.vehicle, 
                    on_request=False
                ).values('start_date', 'end_date'))
                
                if regular_availabilities:
                    # Преобразуем даты в строки для is_period_contained
                    for avail in regular_availabilities:
                        avail['start_date'] = avail['start_date'].strftime('%Y-%m-%d')
                        avail['end_date'] = avail['end_date'].strftime('%Y-%m-%d')
                    
                    sub_period = {
                        'start_date': self.start_date.strftime('%Y-%m-%d'),
                        'end_date': self.end_date.strftime('%Y-%m-%d')
                    }
                    
                    # Если даты попадают в обычный availability - это обычная заявка
                    if is_period_contained(regular_availabilities, sub_period):
                        self.on_request = False
                    else:
                        self.on_request = True
                else:
                    # Нет обычных availability - заявка по запросу
                    self.on_request = True
            else:
                # Нет дат - заявка по запросу
                self.on_request = True
            
            logger.info(f'RequestRent save: vehicle={self.vehicle}, vehicle_id={self.object_id}, on_request={self.on_request}')

            # Сохраняем для получения pk
            super(RequestRent, self).save(*args, **kwargs)
            
            logger.info(f'RequestRent saved with pk={self.pk}, on_request={self.on_request}')
            
            # Для обычных поездок (не по запросу) создаём платёж сразу
            # Для поездок по запросу - ждём подтверждения арендодателя
            if not self.on_request:
                logger.info(f'Creating payment for RequestRent pk={self.pk}')
                with transaction.atomic():
                    self.create_payment()
                logger.info(f'Payment created for RequestRent pk={self.pk}')
            return  # Выходим после первого сохранения

        else:
            original = RequestRent.objects.get(pk=self.pk)
            # Для поездок по запросу: платёж создаётся при подтверждении
            if self.on_request and original.status != 'accept' and self.status == 'accept':
                super(RequestRent, self).save(*args, **kwargs)
                with transaction.atomic():
                    self.create_payment()
                return  # Выходим, чтобы избежать двойного сохранения

        super(RequestRent, self).save(*args, **kwargs)

    def create_payment(self):
        """Создание платежа через Тиньков API"""
        from payment.models import Payment

        # Рассчитываем комиссию (сумму к оплате)
        commission_amount = self.calculate_amount()
        discount_amount = 0

        # Обработка промокода - скидка применяется к комиссии
        if self.promocode:
            discount_amount = commission_amount * Decimal(self.promocode.total) / Decimal(100)
            commission_amount -= discount_amount

            # Отмечаем промокод как использованный
            used_promo = UsedPromoCode.objects.filter(
                user=self.organizer,
                promo_code=self.promocode
            ).first()

            if used_promo:
                if used_promo.used:
                    # Промокод уже был использован - это не должно происходить
                    raise ValueError("Промокод уже был использован ранее")
                else:
                    # Отмечаем как использованный
                    used_promo.used = True
                    used_promo.save()
            else:
                # Если записи нет (что странно, но возможно), создаем новую
                UsedPromoCode.objects.create(
                    user=self.organizer,
                    promo_code=self.promocode,
                    used=True
                )

        # Обработка бонусов - вычитаются из итоговой суммы к оплате
        final_amount = commission_amount
        if self.bonus:
            renter = self.organizer.renter
            bonus_to_use = min(Decimal(self.bonus), final_amount)  # Не можем использовать больше, чем сумма к оплате

            if renter.bonus_account < bonus_to_use:
                raise ValueError("Недостаточно бонусов на счете")

            renter.bonus_account -= bonus_to_use
            final_amount -= bonus_to_use
            renter.save()

        influencer = getattr(self.organizer.renter, 'influencer', None)

        # Создание записи о платеже
        Payment.objects.create(
            request_rent=self,
            amount=final_amount,
            deposite=self.deposit_cost,
            delivery=self.delivery_cost,
            promo_code=self.promocode,
            discount_amount=discount_amount,
            influencer=influencer
        )

    def calculate_amount(self):
        """ Расчет стоимости суммы к оплате (комиссия от стоимости аренды без доставки) """
        commission = self.vehicle.owner.lessor.commission
        rent_cost = Decimal(self.total_cost) - Decimal(self.delivery_cost or 0)
        return rent_cost * commission / Decimal(100)

    def __str__(self):
        return f'Заявка на аренду №-{self.pk}'

    class Meta:
        verbose_name = 'Заявка на аренду'
        verbose_name_plural = 'Заявки на аренду'


class Chat(models.Model):
    request_rent = models.OneToOneField(RequestRent, null=True, on_delete=models.SET_NULL, verbose_name='Заявка на аренду', related_name='chat')
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, verbose_name='Участники')

    class Meta:
        verbose_name = 'Чат'
        verbose_name_plural = 'Чаты'

    def __str__(self):
        return f'chat_id_{self.pk}'


def file_chat_upload_to(instance, filename):
    return f'media/files/chat/{instance.chat}/{filename}'


class Trip(models.Model):
    """ Поездки """
    STATUS_CHOICES = (
        ('current', 'Текущая поездка'),
        ('started', 'В процессе'),
        ('finished', 'Завершить'),
        ('canceled', 'Отменить')
    )
    status = models.CharField(max_length=8, default='started', choices=STATUS_CHOICES, verbose_name='Статус')
    organizer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                  related_name='trip_organized_trips', verbose_name='Арендатор')

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, limit_choices_to={
        'model__in': ('auto', 'bike', 'ship', 'helicopter', 'specialtechnic')}, verbose_name='Тип транспорта')
    object_id = models.PositiveIntegerField(verbose_name='id транспорта')
    vehicle = GenericForeignKey('content_type', 'object_id')

    start_time = models.TimeField(null=True, blank=True, verbose_name='Время начала аренды')
    end_time = models.TimeField(null=True, blank=True, verbose_name='Время окончания аренды')

    chat = models.OneToOneField(Chat, on_delete=models.SET_NULL, null=True, blank=True)

    start_date = models.DateField(verbose_name='Начало поездки')
    end_date = models.DateField(verbose_name='Конец поездки')
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Стоимость аренды', default=0.00)

    @property
    def owner(self):
        return self.vehicle.owner

    def save(self, *args, **kwargs):
        if self.pk:
            previous_trip = Trip.objects.get(pk=self.pk)
        else:
            previous_trip = None

        super(Trip, self).save(*args, **kwargs)

        if previous_trip and previous_trip.status != 'finished' and self.status == 'finished':
            self.vehicle.count_trip += 1
            self.vehicle.save(update_fields=['count_trip'])
            self.owner.lessor.count_trip += 1
            self.owner.lessor.save(update_fields=['count_trip'])

    def get_time_until_start(self):
        """
        Вычисляет, сколько осталось времени до начала аренды.
        """
        if not isinstance(self.start_date, date):
            return None

        start_time = self.start_time if isinstance(self.start_time, time) else time(0, 0)
        start_datetime = datetime.combine(self.start_date, start_time)
        timezone = pytz.UTC
        start_datetime = timezone.localize(start_datetime)
        now = datetime.now(timezone)
        time_until = start_datetime - now
        return max(time_until, timedelta(0))

    def __str__(self):
        return f'Поездка id-{self.pk}'

    class Meta:
        verbose_name = 'Поездка'
        verbose_name_plural = 'Поездки'


class Message(models.Model):
    chat = models.ForeignKey(Chat, related_name='messages', on_delete=models.CASCADE, verbose_name='Чат')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='Отправитель')
    content = models.TextField(verbose_name='Сообщение')
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name='Время')
    file = models.FileField(upload_to=file_chat_upload_to, blank=True, null=True, verbose_name='Файл')
    deleted = models.BooleanField(default=False, verbose_name='Удалено')
    is_read = models.BooleanField(default=False, verbose_name='Прочитано')
    language = models.CharField(max_length=10, default='ru')

    class Meta:
        verbose_name = 'Сообщение'
        verbose_name_plural = 'Сообщения'

    def __str__(self):
        return self.content


class TopicSupport(models.Model):
    name = models.CharField(null=False, verbose_name='Тема')
    count = models.IntegerField(default=0, verbose_name='Количество')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Тема чата с техподдержкой'
        verbose_name_plural = 'Темы чатов с техподдержкой'
        ordering = ['-count']


class ChatSupport(models.Model):
    creator = models.OneToOneField(settings.AUTH_USER_MODEL, related_name='created_chats', on_delete=models.CASCADE,
                                   verbose_name='Создатель')

    class Meta:
        verbose_name = 'Чат с техподдержкой'
        verbose_name_plural = 'Чаты с техподдержкой'

    def __str__(self):
        return f'support_chat_id_{self.pk}'


class IssueSupport(models.Model):
    chat = models.ForeignKey(ChatSupport, null=False, on_delete=models.CASCADE, related_name='issue_chat',
                             verbose_name='Чат техподдержки')
    topic = models.ForeignKey(TopicSupport, null=False, related_name='chat_support', on_delete=models.CASCADE,
                              verbose_name='Тема')
    description = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Время создания')

    class Meta:
        verbose_name = 'Обращение в техподдержку'
        verbose_name_plural = 'Обращения в техподдержку'

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)

        if is_new:
            from .tasks import send_issue_email
            send_issue_email.delay(self.id)


def file_support_chat_upload_to(instance, filename):
    return f'media/files/chat_support/{instance.chat}/{filename}'


class MessageSupport(models.Model):
    chat = models.ForeignKey(ChatSupport, related_name='message_support', on_delete=models.CASCADE, verbose_name='Чат')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='Отправитель')
    content = models.TextField(verbose_name='Сообщение')
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name='Время')
    file = models.FileField(upload_to=file_support_chat_upload_to, blank=True, null=True, verbose_name='Файл')
    deleted = models.BooleanField(default=False, verbose_name='Удалено')
    is_read = models.BooleanField(default=False, verbose_name='Прочитано')
    language = models.CharField(max_length=10, default='ru')

    class Meta:
        verbose_name = 'Сообщение чата техподдержки'
        verbose_name_plural = 'Сообщения чата техподдержки'

    def __str__(self):
        return self.content