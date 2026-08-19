import logging

from celery import shared_task
from django.utils import timezone

from uploads.models import UploadSession
from uploads.parsers import parse_ege, parse_oge

logger = logging.getLogger(__name__)


@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={"max_retries": 2, "countdown": 5})
def process_upload(self, upload_session_id):
    session = UploadSession.objects.get(pk=upload_session_id)
    session.status = "processing"
    session.error_message = ""
    session.save(update_fields=["status", "error_message"])
    try:
        if session.exam_type == "ege":
            parse_ege(session.file.path)
        else:
            parse_oge(session.file.path)
        session.status = "done"
        session.processed_at = timezone.now()
        session.save(update_fields=["status", "processed_at"])
    except Exception as exc:
        logger.exception("Upload processing failed: %s", exc)
        session.status = "failed"
        session.error_message = str(exc)
        session.save(update_fields=["status", "error_message"])
        raise
