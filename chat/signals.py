import json

from django.db.models.signals import post_save
from django.dispatch import receiver

from RentalGuru.settings import HOST_URL
from chat.models import RequestRent, Trip, Chat, Message
from notification.models import Notification


@receiver(post_save, sender=RequestRent)
def handle_request_rent_post_save(sender, instance, created, **kwargs):
    """Обработчик для создания чата и связанных записей поездок."""
    if created and instance.vehicle:
        # Для заявок по запросу: создаём чат и уведомляем арендодателя
        if instance.on_request and instance.status == 'unknown':
            instance.create_chat()

            chat = Chat.objects.get(request_rent=instance)

            Notification.objects.create(
                user=instance.vehicle.owner,
                content=f"Поступил запрос аренды на {instance.vehicle}",
                url=f"wss://{HOST_URL.split('//')[1]}/ws/chat/{chat.pk}/"
            )
        # Для обычных заявок: создаём чат и Trip со статусом 'started' сразу
        elif not instance.on_request:
            instance.create_chat()
            
            chat = Chat.objects.filter(request_rent=instance).first()
            if chat:
                # Создаём Trip со статусом 'started' чтобы пользователь мог продолжить оплату
                Trip.objects.create(
                    organizer=instance.organizer,
                    content_type=instance.content_type,
                    object_id=instance.object_id,
                    start_date=instance.start_date,
                    end_date=instance.end_date,
                    start_time=instance.start_time,
                    end_time=instance.end_time,
                    total_cost=instance.total_cost,
                    chat=chat,
                    status='started'  # Ожидает оплату
                )

    # Для заявок по запросу: при accept создаём чат и Trip
    # Для обычных заявок: Trip создаётся после оплаты (в payment/views.py)
    if instance.status == 'accept' and instance.on_request:
        instance.create_chat()

        chat = Chat.objects.get(request_rent=instance)

        # Создаем Trip со статусом 'started' (В процессе) при accept
        # НЕ проверяем оплату - она будет позже!
        if not Trip.objects.filter(
            object_id=instance.object_id,
            start_date=instance.start_date,
            end_date=instance.end_date,
            status__in=['current', 'started']
        ).exists():
            Trip.objects.create(
                organizer=instance.organizer,
                content_type=instance.content_type,
                object_id=instance.object_id,
                start_date=instance.start_date,
                end_date=instance.end_date,
                start_time=instance.start_time,
                end_time=instance.end_time,
                total_cost=instance.total_cost,
                chat=chat,
                status='started'  # Статус "В процессе" - ждем оплату
            )
