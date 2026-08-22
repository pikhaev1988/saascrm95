import logging

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def send_support_question(topic: str, question: str, *, sender=None) -> None:
    """Send support question to SUPPORT_EMAIL. Form collects topic and question only."""
    support_to = getattr(settings, "SUPPORT_EMAIL", "support@analizgia.ru")
    subject = f"Вопрос по платформе Анализ ГИА: {topic[:120]}"
    body_lines = [
        f"Тема: {topic}",
        "",
        "Вопрос:",
        question,
    ]
    if sender is not None and getattr(sender, "is_authenticated", False):
        role = getattr(sender, "role", "") or "—"
        body_lines.extend(["", "---", f"Кабинет: {sender.username} (роль: {role})"])
    send_mail(
        subject=subject,
        message="\n".join(body_lines),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[support_to],
        fail_silently=False,
    )
    logger.info("Support question sent: topic=%r", topic[:80])
