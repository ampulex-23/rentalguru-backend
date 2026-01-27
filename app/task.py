from celery import shared_task
from django.core.mail import send_mail
from smsaero import SmsAero
from RentalGuru import settings


@shared_task
def send_email_password(user_name, user_email, password):
    send_mail(
        subject='Ваш пароль для доступа к Rental Guru',
        message=f'Здравствуйте, {user_name}!\n\nВаш пароль для доступа: {password}\nПожалуйста, измените его при первой возможности.',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user_email],
        fail_silently=False,
    )


@shared_task
def send_verification_email(email, code):
    send_mail(
        subject='Rental Guru - Код подтверждения',
        message=f'Здравствуйте!\n\nВаш код подтверждения для Rental Guru: {code}\n\nКод действителен 30 минут.\n\nЕсли вы не запрашивали код, проигнорируйте это письмо.\n\n--\nКоманда Rental Guru\nhttps://rentalguru.ru',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=False,
    )


@shared_task
def send_sms(phone_number, code):
    api = SmsAero("rentalguru.ru@yandex.ru", "softspace23")
    api.send(phone_number, f"Ваш код подтверждения: {code}")


@shared_task
def update_currency_rates():
    """
    Обновление курсов валют.
    Запускается по расписанию (раз в час).
    """
    from app.services.currency_service import CurrencyService
    return CurrencyService.update_rates()

