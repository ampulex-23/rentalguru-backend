from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'RentalGuru.settings')

app = Celery('RentalGuru')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'update-currency-rates-hourly': {
        'task': 'app.task.update_currency_rates',
        'schedule': 3600,  # каждый час
    },
}
