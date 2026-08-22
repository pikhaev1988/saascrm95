from django.contrib.auth import get_user_model
from django.core import mail
from django.test import Client, TestCase, override_settings

from users.support_mail import send_support_question


@override_settings(
    SUPPORT_EMAIL="support@analizgia.ru",
    DEFAULT_FROM_EMAIL="support@analizgia.ru",
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
class SupportMailTests(TestCase):
    def test_send_support_question(self):
        send_support_question("Тестовая тема", "Текст вопроса")
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, ["support@analizgia.ru"])
        self.assertIn("Тестовая тема", message.subject)
        self.assertIn("Текст вопроса", message.body)
        self.assertNotIn("Кабинет:", message.body)

    def test_send_support_question_with_sender(self):
        user = get_user_model().objects.create_user(username="school1", password="pass")
        send_support_question("Тема", "Вопрос", sender=user)
        self.assertIn("school1", mail.outbox[0].body)


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
class SupportQuestionViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = get_user_model().objects.create_user(
            username="hub_user",
            password="pass",
            role="school",
        )

    def test_post_sends_email(self):
        self.client.login(username="hub_user", password="pass")
        response = self.client.post(
            "/cabinet/support-ask/",
            {"topic": "Отчёты", "question": "Как скачать аналитику?"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Отчёты", mail.outbox[0].subject)

    def test_post_requires_auth(self):
        response = self.client.post(
            "/cabinet/support-ask/",
            {"topic": "X", "question": "Y"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/"))

    def test_post_validates_empty_fields(self):
        self.client.login(username="hub_user", password="pass")
        response = self.client.post("/cabinet/support-ask/", {"topic": "", "question": ""})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 0)
