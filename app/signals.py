from django.db.models.signals import pre_delete, post_save
from django.dispatch import receiver

from app.models import User, RenterDocuments


@receiver(pre_delete, sender=User)
def delete_user_vehicles(sender, instance, **kwargs):
    """
    Удаляет все транспортные средства пользователя ДО его удаления
    """
    if hasattr(instance, 'lessor'):
        from vehicle.models import Vehicle
        Vehicle.objects.filter(owner=instance).delete()


@receiver(post_save, sender=RenterDocuments)
def update_renter_verification(sender, instance, **kwargs):
    """
    Автоматически обновляет renter.verification когда ОБА документа (паспорт И права) верифицированы.
    Если хотя бы один документ не верифицирован или отсутствует - verification = False.
    """
    renter = instance.renter
    
    # Получаем все документы арендатора
    documents = RenterDocuments.objects.filter(renter=renter)
    
    # Проверяем наличие верифицированного паспорта
    has_approved_passport = documents.filter(title='passport', status='approved').exists()
    
    # Проверяем наличие верифицированных прав
    has_approved_license = documents.filter(title='license', status='approved').exists()
    
    # Верификация = True только если ОБА документа верифицированы
    new_verification_status = has_approved_passport and has_approved_license
    
    # Обновляем только если статус изменился
    if renter.verification != new_verification_status:
        renter.verification = new_verification_status
        renter.save(update_fields=['verification'])