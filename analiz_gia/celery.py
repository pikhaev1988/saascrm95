import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "analiz_gia.settings")

app = Celery("analiz_gia")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
