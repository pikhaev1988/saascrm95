from django.test import TestCase

from exams.models import ExamTaskTopic
from users.task_classification import get_task_classification
from users.task_topics import topic_for_task


THEMATIC_BLOCKS = {
    "Текст",
    "Лексика",
    "Стилистика и культура речи",
    "Орфоэпия",
    "Грамматические нормы",
    "Морфология",
    "Синтаксис",
    "Орфография",
    "Пунктуация",
    "Изобразительно-выразительные средства",
    "Создание собственного текста",
}

FORBIDDEN_AS_BLOCK = {
    "анализ текста",
    "работа с информацией",
    "аргументация",
    "построение ответа",
}

EXPECTED_DISPLAY = {
    1: "Логико-смысловые отношения между предложениями в тексте",
    2: "Лексикология и фразеология как разделы лингвистики. Лексический анализ слова",
    3: "Функциональная стилистика. Культура речи",
    4: "Нормы ударения в современном литературном русском языке",
    5: "Основные лексические нормы современного русского литературного языка. Паронимы и их употребление",
    6: "Основные лексические нормы современного русского литературного языка. Лексическая сочетаемость. Тавтология. Плеоназм",
    7: "Грамматические нормы",
    8: "Основные синтаксические нормы современного русского литературного языка",
    9: "Правописание гласных и согласных в корне",
    10: "Употребление ъ и ь (в том числе разделительных). Правописание приставок. Буквы ы — и после приставок",
    11: "Правописание суффиксов (кроме суффиксов причастий, деепричастий)",
    12: "Правописание личных окончаний глаголов и суффиксов причастий, деепричастий",
    13: "Правописание не и ни",
    14: "Слитное, дефисное и раздельное написание слов разных частей речи",
    15: "Правописание -н- и -нн- в словах различных частей речи",
    16: "Знаки препинания в предложениях с однородными членами. Знаки препинания в сложном предложении",
    17: "Знаки препинания при обособлении",
    18: "Знаки препинания в предложениях с вводными конструкциями, обращениями, междометиями",
    19: "Знаки препинания в сложном предложении",
    20: "Знаки препинания в сложном предложении с разными видами связи",
    21: "Пунктуационный анализ предложения",
    22: "Основные изобразительно-выразительные средства русского языка",
    23: "Информационно-смысловая переработка прочитанного текста",
    24: "Информативность текста. Виды информации в тексте",
    25: "Лексикология и фразеология как разделы лингвистики. Лексический анализ слова",
    26: "Логико-смысловые отношения между предложениями в тексте",
    27: "Сочинение-рассуждение на основе прочитанного текста",
}

EXPECTED_BLOCKS = {
    1: "Текст",
    2: "Лексика",
    3: "Стилистика и культура речи",
    4: "Орфоэпия",
    5: "Лексика",
    6: "Лексика",
    7: "Грамматические нормы",
    8: "Синтаксис",
    9: "Орфография",
    10: "Орфография",
    11: "Орфография",
    12: "Орфография",
    13: "Орфография",
    14: "Орфография",
    15: "Орфография",
    16: "Пунктуация",
    17: "Пунктуация",
    18: "Пунктуация",
    19: "Пунктуация",
    20: "Пунктуация",
    21: "Пунктуация",
    22: "Изобразительно-выразительные средства",
    23: "Текст",
    24: "Текст",
    25: "Лексика",
    26: "Текст",
    27: "Создание собственного текста",
}

EXPECTED_CONTENT_NAMES = {
    1: "Логико-смысловые отношения между предложениями в тексте",
    2: "Лексикология и фразеология как разделы лингвистики. Лексический анализ слова",
    7: "Основные морфологические нормы современного русского литературного языка",
    21: "Пунктуационный анализ предложения",
    25: "Лексикология и фразеология как разделы лингвистики. Лексический анализ слова",
    26: "Логико-смысловые отношения между предложениями в тексте",
    27: "Информационно-смысловая переработка прочитанного текста. Отзыв. Рецензия",
}

EXPECTED_STATUS = {number: "verified" for number in range(1, 28)}
EXPECTED_STATUS[7] = "partially_verified"


class RussianEge2026TaskTopicsTests(TestCase):
    def test_all_tasks_1_27_have_classification(self):
        for number in range(1, 28):
            with self.subTest(task=number):
                classification = get_task_classification(
                    "Русский язык", number, exam_type="ege", year=2026
                )
                theme = classification["theme"]
                display_name = theme["display_name"]
                block = theme["block"]

                self.assertEqual(classification["subject"], "russian")
                self.assertEqual(classification["exam_type"], "ege")
                self.assertEqual(classification["year"], 2026)
                self.assertEqual(classification["task"], number)
                self.assertEqual(classification["kim"]["line"], number)
                self.assertIn(classification["kim"]["part"], (1, 2))
                self.assertTrue(display_name)
                self.assertNotIn("Содержание задания №", display_name)
                self.assertEqual(display_name, EXPECTED_DISPLAY[number])
                self.assertEqual(block, EXPECTED_BLOCKS[number])
                self.assertIn(block, THEMATIC_BLOCKS)
                self.assertNotIn(block.lower(), FORBIDDEN_AS_BLOCK)
                self.assertTrue(classification["fipi"]["content_codes"])
                self.assertTrue(classification["fipi"]["content_name"])
                self.assertEqual(classification["fipi"]["source_document"], "FIPI")
                self.assertEqual(classification["fipi"]["year"], 2026)
                self.assertIsInstance(classification["skills"], list)
                self.assertTrue(classification["skills"])
                self.assertTrue(classification["task_format"])
                self.assertTrue(classification["school_program"]["grades"])
                self.assertIn(
                    classification["verification"]["status"],
                    {"verified", "partially_verified", "needs_review"},
                )
                self.assertEqual(
                    classification["verification"]["status"],
                    EXPECTED_STATUS[number],
                )
                self.assertEqual(classification["verification"]["source"], "FIPI")
                self.assertEqual(classification["verification"]["year"], 2026)
                self.assertEqual(
                    topic_for_task("Русский язык", number, "ege"),
                    display_name,
                )

    def test_part2_is_only_task_27(self):
        for number in range(1, 27):
            classification = get_task_classification("Русский язык", number, "ege", 2026)
            self.assertEqual(classification["kim"]["part"], 1, number)
            self.assertEqual(classification["task_format"], "Задание с кратким ответом")
        classification = get_task_classification("Русский язык", 27, "ege", 2026)
        self.assertEqual(classification["kim"]["part"], 2)

    def test_theme_is_not_replaced_by_skill(self):
        classification = get_task_classification("Русский язык", 9, "ege", 2026)
        self.assertEqual(classification["theme"]["block"], "Орфография")
        self.assertIn("применение орфографических норм", classification["skills"])
        self.assertNotEqual(classification["theme"]["block"], classification["skills"][0])

    def test_task_7_is_not_morphology_only(self):
        classification = get_task_classification("Русский язык", 7, "ege", 2026)
        self.assertEqual(
            classification["fipi"]["content_name"],
            EXPECTED_CONTENT_NAMES[7],
        )
        self.assertEqual(classification["fipi"]["content_codes"], ["3.5.2–3.5.6"])
        self.assertNotEqual(classification["theme"]["block"], "Морфология")
        self.assertEqual(classification["theme"]["block"], "Грамматические нормы")
        self.assertEqual(classification["theme"]["display_name"], "Грамматические нормы")
        self.assertIn("исправление грамматической ошибки", classification["skills"])
        self.assertNotEqual(
            classification["fipi"]["content_name"],
            classification["theme"]["display_name"],
        )
        self.assertEqual(classification["verification"]["status"], "partially_verified")
        self.assertTrue(classification["verification"]["note"])

    def test_task_21_skill_is_not_content_name(self):
        classification = get_task_classification("Русский язык", 21, "ege", 2026)
        self.assertEqual(classification["fipi"]["content_name"], EXPECTED_CONTENT_NAMES[21])
        self.assertEqual(classification["theme"]["block"], "Пунктуация")
        self.assertNotEqual(
            classification["skills"][0],
            classification["fipi"]["content_name"],
        )
        self.assertEqual(classification["skills"], ["проводить пунктуационный анализ"])

    def test_task_25_keeps_code_331_not_336(self):
        classification = get_task_classification("Русский язык", 25, "ege", 2026)
        self.assertEqual(classification["fipi"]["content_codes"], ["3.3.1"])
        self.assertNotIn("3.3.6", classification["fipi"]["content_codes"])
        self.assertEqual(classification["fipi"]["content_name"], EXPECTED_CONTENT_NAMES[25])
        task2 = get_task_classification("Русский язык", 2, "ege", 2026)
        self.assertEqual(classification["fipi"]["content_name"], task2["fipi"]["content_name"])
        self.assertEqual(classification["fipi"]["content_codes"], task2["fipi"]["content_codes"])

    def test_task_26_shares_content_with_task_1(self):
        task1 = get_task_classification("Русский язык", 1, "ege", 2026)
        task26 = get_task_classification("Русский язык", 26, "ege", 2026)
        self.assertEqual(task1["fipi"]["content_codes"], ["1.2"])
        self.assertEqual(task26["fipi"]["content_codes"], ["1.2"])
        self.assertEqual(task1["fipi"]["content_name"], EXPECTED_CONTENT_NAMES[1])
        self.assertEqual(task26["fipi"]["content_name"], EXPECTED_CONTENT_NAMES[26])
        self.assertEqual(task1["fipi"]["content_name"], task26["fipi"]["content_name"])

    def test_task_27_splits_content_and_format(self):
        classification = get_task_classification("Русский язык", 27, "ege", 2026)
        self.assertEqual(classification["fipi"]["content_name"], EXPECTED_CONTENT_NAMES[27])
        self.assertIn("Отзыв. Рецензия", classification["fipi"]["content_name"])
        self.assertEqual(
            classification["task_format"],
            "Сочинение-рассуждение на основе прочитанного текста",
        )
        self.assertNotEqual(
            classification["fipi"]["content_name"],
            classification["task_format"],
        )
        self.assertEqual(
            classification["theme"]["display_name"],
            classification["task_format"],
        )
        self.assertEqual(classification["theme"]["block"], "Создание собственного текста")
        self.assertIn(
            "создание собственного высказывания на основе прочитанного текста",
            classification["skills"],
        )
        self.assertNotEqual(classification["theme"]["block"], classification["task_format"])
        self.assertNotEqual(classification["fipi"]["content_name"], classification["skills"][0])

    def test_oge_russian_does_not_use_ege_catalog(self):
        ege_topic = topic_for_task("Русский язык", 1, "ege")
        oge_topic = topic_for_task("Русский язык", 1, "oge")
        self.assertEqual(ege_topic, EXPECTED_DISPLAY[1])
        self.assertNotEqual(oge_topic, ege_topic)
        self.assertNotIn("Содержание задания №", oge_topic)
        oge_classification = get_task_classification("Русский язык", 1, "oge", 2026)
        self.assertEqual(oge_classification["verification"]["status"], "needs_review")
        self.assertNotEqual(oge_classification["verification"]["source"], "FIPI")

    def test_other_ege_subject_is_not_rewritten(self):
        topic = topic_for_task("Математика профильная", 1, "ege")
        self.assertNotEqual(topic, EXPECTED_DISPLAY[1])
        self.assertNotIn("Содержание задания №", topic)
        classification = get_task_classification("Математика профильная", 1, "ege", 2026)
        self.assertEqual(classification["subject"], "math_profile")
        self.assertNotEqual(classification["fipi"]["content_name"], EXPECTED_CONTENT_NAMES[1])

    def test_manual_override_is_not_auto_verified(self):
        ExamTaskTopic.objects.create(
            exam_type="ege",
            subject_key="russian",
            task_number=4,
            topic="Ручная тема орфоэпии",
            grade_range=[10],
        )
        self.assertEqual(topic_for_task("Русский язык", 4, "ege"), "Ручная тема орфоэпии")
        classification = get_task_classification("Русский язык", 4, "ege", 2026)
        self.assertEqual(classification["theme"]["display_name"], "Ручная тема орфоэпии")
        self.assertEqual(classification["verification"]["status"], "needs_review")
        self.assertEqual(classification["verification"]["source"], "manual_override")
        self.assertEqual(classification["theme"]["block"], "Орфоэпия")
        self.assertEqual(classification["fipi"]["content_codes"], ["3.2.3"])
