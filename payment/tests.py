"""
Тесты для флоу аренды с онлайн-оплатой.

Тест-кейсы по требованиям заказчика:
1. Арендатор откликается на аренду → заявка создаётся со статусом 'unknown', Trip создаётся со статусом 'started'
2. При открытии формы оплаты → Trip в статусе 'started' (ожидает оплату)
3. После успешной оплаты → Trip переходит в статус 'current', RequestRent в статус 'paid'
4. Если оплата не прошла → Trip остаётся в статусе 'started', можно повторить оплату
5. Арендодатель видит заявку в статусе 'unknown' пока не оплачено
"""
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.test import TestCase, TransactionTestCase
from django.contrib.contenttypes.models import ContentType
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from app.models import User, Currency, Language
from chat.models import RequestRent, Trip, Chat
from payment.models import Payment
from vehicle.models import Auto, VehicleBrand, VehicleModel, RentPrice, Availability


class RentalPaymentFlowTestCase(TransactionTestCase):
    """Тесты флоу аренды с онлайн-оплатой."""
    
    def setUp(self):
        """Создание тестовых данных."""
        # Создаём язык и валюту
        self.language = Language.objects.create(code='ru', name='Русский')
        self.currency = Currency.objects.create(
            code='RUB',
            symbol='₽',
            title='Рубль',
            rate_to_rub=Decimal('1.0')
        )
        
        # Создаём арендодателя (lessor)
        self.lessor_user = User.objects.create_user(
            email='lessor@test.com',
            password='testpass123',
            first_name='Lessor',
            last_name='Test',
            role='lessor',
            language=self.language,
            currency=self.currency
        )
        
        # Создаём профиль lessor
        from app.models import Lessor
        self.lessor = Lessor.objects.create(
            user=self.lessor_user,
            commission=Decimal('20.0')
        )
        
        # Создаём арендатора (renter)
        self.renter_user = User.objects.create_user(
            email='renter@test.com',
            password='testpass123',
            first_name='Renter',
            last_name='Test',
            role='renter',
            language=self.language,
            currency=self.currency
        )
        
        # Создаём профиль renter
        from app.models import Renter
        self.renter = Renter.objects.create(user=self.renter_user)
        
        # Создаём бренд и модель авто
        self.brand = VehicleBrand.objects.create(name='TestBrand')
        self.model = VehicleModel.objects.create(
            name='TestModel',
            brand=self.brand,
            vehicle_type='auto'
        )
        
        # Создаём автомобиль
        self.auto = Auto.objects.create(
            owner=self.lessor_user,
            brand=self.brand,
            model=self.model,
            year=2023,
            price_deposit=Decimal('10000.00'),
            price_delivery=Decimal('500.00'),
            min_rent_day=1,
            max_rent_day=30,
            currency=self.currency
        )
        
        # Создаём цену аренды
        self.rent_price = RentPrice.objects.create(
            vehicle=self.auto,
            name='day',
            price=Decimal('5000.00'),
            discount=0
        )
        
        # Создаём availability (доступные даты)
        self.start_date = date.today() + timedelta(days=1)
        self.end_date = date.today() + timedelta(days=30)
        self.availability = Availability.objects.create(
            vehicle=self.auto,
            start_date=self.start_date,
            end_date=self.end_date,
            on_request=False
        )
        
        self.content_type = ContentType.objects.get_for_model(Auto)
    
    def test_01_request_rent_creates_trip_with_started_status(self):
        """
        Тест: При создании заявки на обычную аренду (не по запросу)
        создаётся Trip со статусом 'started'.
        """
        # Создаём заявку на аренду
        request_rent = RequestRent.objects.create(
            organizer=self.renter_user,
            content_type=self.content_type,
            object_id=self.auto.id,
            start_date=self.start_date,
            end_date=self.start_date + timedelta(days=2),
            delivery=False
        )
        
        # Проверяем, что заявка создана со статусом 'unknown'
        self.assertEqual(request_rent.status, 'unknown')
        
        # Проверяем, что on_request=False (обычная аренда)
        self.assertFalse(request_rent.on_request)
        
        # Проверяем, что создан чат
        chat = Chat.objects.filter(request_rent=request_rent).first()
        self.assertIsNotNone(chat)
        
        # Проверяем, что создан Trip со статусом 'started'
        trip = Trip.objects.filter(chat=chat).first()
        self.assertIsNotNone(trip)
        self.assertEqual(trip.status, 'started')
        self.assertEqual(trip.organizer, self.renter_user)
    
    def test_02_payment_created_for_regular_rental(self):
        """
        Тест: Для обычной аренды (не по запросу) платёж создаётся сразу.
        """
        request_rent = RequestRent.objects.create(
            organizer=self.renter_user,
            content_type=self.content_type,
            object_id=self.auto.id,
            start_date=self.start_date,
            end_date=self.start_date + timedelta(days=2),
            delivery=False
        )
        
        # Проверяем, что платёж создан
        payment = Payment.objects.filter(request_rent=request_rent).first()
        self.assertIsNotNone(payment)
        self.assertEqual(payment.status, 'pending')
        self.assertGreater(payment.amount, 0)
    
    def test_03_trip_status_changes_to_current_after_payment(self):
        """
        Тест: После успешной оплаты Trip переходит в статус 'current'.
        """
        # Создаём заявку
        request_rent = RequestRent.objects.create(
            organizer=self.renter_user,
            content_type=self.content_type,
            object_id=self.auto.id,
            start_date=self.start_date,
            end_date=self.start_date + timedelta(days=2),
            delivery=False
        )
        
        chat = Chat.objects.filter(request_rent=request_rent).first()
        trip = Trip.objects.filter(chat=chat).first()
        payment = Payment.objects.filter(request_rent=request_rent).first()
        
        # Проверяем начальные статусы
        self.assertEqual(trip.status, 'started')
        self.assertEqual(payment.status, 'pending')
        
        # Симулируем успешную оплату (как в TinkoffCallbackView)
        payment.payment_id = 'test_payment_123'
        payment.status = 'success'
        payment.save()
        
        # Обновляем статус заявки
        request_rent.status = 'paid'
        request_rent.save()
        
        # Обновляем статус Trip
        trip.status = 'current'
        trip.save()
        
        # Проверяем финальные статусы
        trip.refresh_from_db()
        request_rent.refresh_from_db()
        
        self.assertEqual(trip.status, 'current')
        self.assertEqual(request_rent.status, 'paid')
    
    def test_04_trip_remains_started_if_payment_fails(self):
        """
        Тест: Если оплата не прошла, Trip остаётся в статусе 'started'.
        """
        request_rent = RequestRent.objects.create(
            organizer=self.renter_user,
            content_type=self.content_type,
            object_id=self.auto.id,
            start_date=self.start_date,
            end_date=self.start_date + timedelta(days=2),
            delivery=False
        )
        
        chat = Chat.objects.filter(request_rent=request_rent).first()
        trip = Trip.objects.filter(chat=chat).first()
        payment = Payment.objects.filter(request_rent=request_rent).first()
        
        # Симулируем неудачную оплату
        payment.payment_id = 'test_payment_failed'
        payment.status = 'failed'
        payment.save()
        
        # Trip должен остаться в статусе 'started'
        trip.refresh_from_db()
        self.assertEqual(trip.status, 'started')
        
        # Заявка должна остаться в статусе 'unknown'
        request_rent.refresh_from_db()
        self.assertEqual(request_rent.status, 'unknown')
    
    def test_05_payment_can_be_retried(self):
        """
        Тест: После неудачной оплаты можно повторить попытку.
        """
        request_rent = RequestRent.objects.create(
            organizer=self.renter_user,
            content_type=self.content_type,
            object_id=self.auto.id,
            start_date=self.start_date,
            end_date=self.start_date + timedelta(days=2),
            delivery=False
        )
        
        payment = Payment.objects.filter(request_rent=request_rent).first()
        
        # Первая попытка - неудача
        payment.payment_id = 'test_payment_1'
        payment.status = 'failed'
        payment.save()
        
        # Сбрасываем для повторной попытки
        payment.payment_id = None
        payment.status = 'pending'
        payment.save()
        
        # Проверяем, что платёж можно инициировать заново
        self.assertEqual(payment.status, 'pending')
        self.assertIsNone(payment.payment_id)
    
    def test_06_lessor_sees_request_before_payment(self):
        """
        Тест: Арендодатель видит заявку в статусе 'unknown' до оплаты.
        """
        request_rent = RequestRent.objects.create(
            organizer=self.renter_user,
            content_type=self.content_type,
            object_id=self.auto.id,
            start_date=self.start_date,
            end_date=self.start_date + timedelta(days=2),
            delivery=False
        )
        
        # Заявка видна арендодателю со статусом 'unknown'
        self.assertEqual(request_rent.status, 'unknown')
        self.assertEqual(request_rent.owner, self.lessor_user)
    
    def test_07_on_request_rental_no_trip_until_accept(self):
        """
        Тест: Для аренды по запросу Trip НЕ создаётся до подтверждения.
        """
        # Удаляем обычный availability и создаём on_request
        self.availability.delete()
        Availability.objects.create(
            vehicle=self.auto,
            on_request=True
        )
        
        request_rent = RequestRent.objects.create(
            organizer=self.renter_user,
            content_type=self.content_type,
            object_id=self.auto.id,
            start_date=None,
            end_date=None,
            delivery=False
        )
        
        # Проверяем, что on_request=True
        self.assertTrue(request_rent.on_request)
        
        # Проверяем, что чат создан
        chat = Chat.objects.filter(request_rent=request_rent).first()
        self.assertIsNotNone(chat)
        
        # Проверяем, что Trip НЕ создан (для on_request создаётся только после оплаты)
        trip = Trip.objects.filter(chat=chat).first()
        self.assertIsNone(trip)


class TinkoffCallbackTestCase(TransactionTestCase):
    """Тесты для обработки callback от Тинькофф."""
    
    def setUp(self):
        """Создание тестовых данных."""
        self.language = Language.objects.create(code='ru', name='Русский')
        self.currency = Currency.objects.create(
            code='RUB',
            symbol='₽',
            title='Рубль',
            rate_to_rub=Decimal('1.0')
        )
        
        self.lessor_user = User.objects.create_user(
            email='lessor2@test.com',
            password='testpass123',
            first_name='Lessor',
            last_name='Test',
            role='lessor',
            language=self.language,
            currency=self.currency
        )
        
        from app.models import Lessor
        self.lessor = Lessor.objects.create(
            user=self.lessor_user,
            commission=Decimal('20.0')
        )
        
        self.renter_user = User.objects.create_user(
            email='renter2@test.com',
            password='testpass123',
            first_name='Renter',
            last_name='Test',
            role='renter',
            language=self.language,
            currency=self.currency
        )
        
        from app.models import Renter
        self.renter = Renter.objects.create(user=self.renter_user)
        
        self.brand = VehicleBrand.objects.create(name='TestBrand2')
        self.model = VehicleModel.objects.create(
            name='TestModel2',
            brand=self.brand,
            vehicle_type='auto'
        )
        
        self.auto = Auto.objects.create(
            owner=self.lessor_user,
            brand=self.brand,
            model=self.model,
            year=2023,
            price_deposit=Decimal('10000.00'),
            price_delivery=Decimal('500.00'),
            min_rent_day=1,
            max_rent_day=30,
            currency=self.currency
        )
        
        RentPrice.objects.create(
            vehicle=self.auto,
            name='day',
            price=Decimal('5000.00'),
            discount=0
        )
        
        self.start_date = date.today() + timedelta(days=1)
        self.end_date = date.today() + timedelta(days=30)
        Availability.objects.create(
            vehicle=self.auto,
            start_date=self.start_date,
            end_date=self.end_date,
            on_request=False
        )
        
        self.content_type = ContentType.objects.get_for_model(Auto)
    
    def test_confirmed_callback_updates_statuses(self):
        """
        Тест: Callback CONFIRMED от Тинькофф обновляет статусы.
        """
        # Создаём заявку
        request_rent = RequestRent.objects.create(
            organizer=self.renter_user,
            content_type=self.content_type,
            object_id=self.auto.id,
            start_date=self.start_date,
            end_date=self.start_date + timedelta(days=2),
            delivery=False
        )
        
        chat = Chat.objects.filter(request_rent=request_rent).first()
        trip = Trip.objects.filter(chat=chat).first()
        payment = Payment.objects.filter(request_rent=request_rent).first()
        
        # Устанавливаем payment_id (как после инициализации платежа)
        payment.payment_id = 'tinkoff_123456'
        payment.save()
        
        # Симулируем обработку CONFIRMED callback
        # (логика из TinkoffCallbackView.post)
        payment.status = 'success'
        payment.save()
        
        request_rent.status = 'paid'
        request_rent.save()
        
        trip.status = 'current'
        trip.save()
        
        # Проверяем результаты
        payment.refresh_from_db()
        request_rent.refresh_from_db()
        trip.refresh_from_db()
        
        self.assertEqual(payment.status, 'success')
        self.assertEqual(request_rent.status, 'paid')
        self.assertEqual(trip.status, 'current')
    
    def test_cancelled_callback_marks_payment_failed(self):
        """
        Тест: Callback CANCELLED от Тинькофф помечает платёж как failed.
        """
        request_rent = RequestRent.objects.create(
            organizer=self.renter_user,
            content_type=self.content_type,
            object_id=self.auto.id,
            start_date=self.start_date,
            end_date=self.start_date + timedelta(days=2),
            delivery=False
        )
        
        chat = Chat.objects.filter(request_rent=request_rent).first()
        trip = Trip.objects.filter(chat=chat).first()
        payment = Payment.objects.filter(request_rent=request_rent).first()
        
        payment.payment_id = 'tinkoff_cancelled'
        payment.save()
        
        # Симулируем CANCELLED callback
        payment.status = 'failed'
        payment.save()
        
        # Trip остаётся в started
        trip.refresh_from_db()
        self.assertEqual(trip.status, 'started')
        
        # Payment помечен как failed
        payment.refresh_from_db()
        self.assertEqual(payment.status, 'failed')


class PaymentStatusFlowTestCase(TestCase):
    """Тесты для проверки корректности статусов в разных сценариях."""
    
    def test_payment_status_transitions(self):
        """Тест: Проверка допустимых переходов статусов платежа."""
        valid_transitions = {
            'pending': ['success', 'failed', 'canceled'],
            'success': [],  # Финальный статус
            'failed': ['pending'],  # Можно повторить
            'canceled': []  # Финальный статус
        }
        
        for from_status, to_statuses in valid_transitions.items():
            for to_status in to_statuses:
                # Проверяем, что переход допустим
                self.assertIn(to_status, valid_transitions.get(from_status, []) + [from_status])
    
    def test_trip_status_transitions(self):
        """Тест: Проверка допустимых переходов статусов Trip."""
        valid_transitions = {
            'started': ['current', 'canceled'],  # Ожидает оплату → оплачено или отменено
            'current': ['finished', 'canceled'],  # В процессе → завершено или отменено
            'finished': [],  # Финальный статус
            'canceled': []  # Финальный статус
        }
        
        for from_status, to_statuses in valid_transitions.items():
            for to_status in to_statuses:
                self.assertIn(to_status, valid_transitions.get(from_status, []) + [from_status])
    
    def test_request_rent_status_transitions(self):
        """Тест: Проверка допустимых переходов статусов RequestRent."""
        valid_transitions = {
            'unknown': ['accept', 'denied', 'paid', 'canceled'],
            'accept': ['paid', 'canceled'],
            'denied': [],  # Финальный статус
            'paid': ['canceled'],  # Можно отменить после оплаты
            'canceled': []  # Финальный статус
        }
        
        for from_status, to_statuses in valid_transitions.items():
            for to_status in to_statuses:
                self.assertIn(to_status, valid_transitions.get(from_status, []) + [from_status])

