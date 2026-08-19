from django.test import TestCase

from exams.models import ExamTaskTopic
from users.task_classification import get_task_classification
from users.task_topics import OGE_MATH_TASK_TOPICS, topic_for_task


THEMATIC_BLOCKS = {
    "Числа и вычисления",
    "Уравнения и неравенства",
    "Функции и графики",
    "Начала математического анализа",
    "Множества и логика",
    "Вероятность и статистика",
    "Геометрия",
}

EXPECTED_DISPLAY = {
    1: "Планиметрия",
    2: "Векторы",
    3: "Стереометрия",
    4: "Вероятность и статистика",
    5: "Вероятность и статистика",
    6: "Уравнения",
    7: "Преобразования выражений",
    8: "Производная и первообразная",
    9: "Уравнения и неравенства",
    10: "Текстовые задачи",
    11: "Функции и графики",
    12: "Исследование функций",
    13: "Уравнения",
    14: "Стереометрия",
    15: "Неравенства",
    16: "Текстовые задачи из области управления личными и семейными финансами",
    17: "Планиметрия",
    18: "Уравнения, неравенства и системы с параметром",
    19: "Числа и вычисления",
}

EXPECTED_BLOCKS = {
    1: "Геометрия",
    2: "Геометрия",
    3: "Геометрия",
    4: "Вероятность и статистика",
    5: "Вероятность и статистика",
    6: "Уравнения и неравенства",
    7: "Числа и вычисления",
    8: "Начала математического анализа",
    9: "Уравнения и неравенства",
    10: "Уравнения и неравенства",
    11: "Функции и графики",
    12: "Начала математического анализа",
    13: "Уравнения и неравенства",
    14: "Геометрия",
    15: "Уравнения и неравенства",
    16: "Уравнения и неравенства",
    17: "Геометрия",
    18: "Уравнения и неравенства",
    19: "Числа и вычисления",
}

EXPECTED_CONTENT_NAMES = {
    1: "Геометрия",
    2: "Геометрия",
    3: "Геометрия",
    4: "Вероятность и статистика",
    5: "Вероятность и статистика",
    6: "Уравнения и неравенства",
    7: "Числа и вычисления",
    8: "Функции и графики. Начала математического анализа",
    9: "Уравнения и неравенства",
    10: "Уравнения и неравенства",
    11: "Функции и графики",
    12: "Начала математического анализа",
    13: "Уравнения и неравенства",
    14: "Геометрия",
    15: "Уравнения и неравенства",
    16: "Числа и вычисления. Уравнения и неравенства. Функции и графики",
    17: "Геометрия",
    18: "Уравнения и неравенства. Функции и графики. Начала математического анализа",
    19: "Числа и вычисления. Уравнения и неравенства. Множества и логика",
}

EXPECTED_CODES = {
    1: ["7"],
    2: ["7"],
    3: ["7"],
    4: ["6"],
    5: ["6"],
    6: ["2"],
    7: ["1"],
    8: ["3", "4"],
    9: ["2"],
    10: ["2"],
    11: ["3"],
    12: ["4"],
    13: ["2"],
    14: ["7"],
    15: ["2"],
    16: ["1–3"],
    17: ["7"],
    18: ["2–4"],
    19: ["1", "2", "5"],
}

EXPECTED_STATUS = {number: "verified" for number in range(1, 20)}
EXPECTED_STATUS[4] = "partially_verified"


class MathProfileEge2026TaskTopicsTests(TestCase):
    def test_all_tasks_1_19_have_classification(self):
        for number in range(1, 20):
            with self.subTest(task=number):
                classification = get_task_classification(
                    "Математика профильная", number, exam_type="ege", year=2026
                )
                theme = classification["theme"]
                display_name = theme["display_name"]
                block = theme["block"]

                self.assertEqual(classification["subject"], "math_profile")
                self.assertEqual(classification["exam_type"], "ege")
                self.assertEqual(classification["year"], 2026)
                self.assertEqual(classification["task"], number)
                self.assertEqual(classification["kim"]["line"], number)
                self.assertIn(classification["kim"]["part"], (1, 2))
                self.assertTrue(classification["kim"]["answer_type"])
                self.assertEqual(display_name, EXPECTED_DISPLAY[number])
                self.assertEqual(block, EXPECTED_BLOCKS[number])
                self.assertIn(block, THEMATIC_BLOCKS)
                self.assertEqual(
                    classification["fipi"]["content_codes"], EXPECTED_CODES[number]
                )
                self.assertEqual(
                    classification["fipi"]["content_name"],
                    EXPECTED_CONTENT_NAMES[number],
                )
                self.assertEqual(classification["fipi"]["source_document"], "FIPI")
                self.assertEqual(classification["fipi"]["year"], 2026)
                self.assertIsInstance(classification["skills"], list)
                self.assertTrue(classification["skills"])
                self.assertNotEqual(classification["skills"][0], display_name)
                self.assertTrue(classification["task_format"])
                self.assertTrue(classification["school_program"]["grades"])
                self.assertTrue(classification["school_program"]["items"])
                self.assertEqual(
                    classification["verification"]["status"],
                    EXPECTED_STATUS[number],
                )
                self.assertEqual(classification["verification"]["source"], "FIPI")
                self.assertEqual(
                    topic_for_task("Математика профильная", number, "ege"),
                    display_name,
                )

    def test_part_and_task_format(self):
        for number in range(1, 13):
            classification = get_task_classification(
                "Математика профильная", number, "ege", 2026
            )
            self.assertEqual(classification["kim"]["part"], 1, number)
            self.assertEqual(classification["task_format"], "Задание с кратким ответом")
            self.assertIn("краткий ответ", classification["kim"]["answer_type"])
        for number in range(13, 20):
            classification = get_task_classification(
                "Математика профильная", number, "ege", 2026
            )
            self.assertEqual(classification["kim"]["part"], 2, number)
            self.assertEqual(
                classification["task_format"], "Задание с развёрнутым ответом"
            )
            self.assertIn("развёрнутый ответ", classification["kim"]["answer_type"])

    def test_entities_are_separated(self):
        classification = get_task_classification(
            "Математика профильная", 12, "ege", 2026
        )
        self.assertEqual(classification["fipi"]["content_name"], "Начала математического анализа")
        self.assertEqual(classification["theme"]["block"], "Начала математического анализа")
        self.assertEqual(classification["theme"]["display_name"], "Исследование функций")
        self.assertNotEqual(
            classification["theme"]["display_name"],
            classification["skills"][0],
        )
        self.assertNotEqual(
            classification["task_format"],
            classification["theme"]["display_name"],
        )

    def test_multiple_content_codes_are_kept(self):
        task8 = get_task_classification("Математика профильная", 8, "ege", 2026)
        self.assertEqual(task8["fipi"]["content_codes"], ["3", "4"])
        self.assertTrue(task8["line_scope"])
        task16 = get_task_classification("Математика профильная", 16, "ege", 2026)
        self.assertEqual(task16["fipi"]["content_codes"], ["1–3"])
        task18 = get_task_classification("Математика профильная", 18, "ege", 2026)
        self.assertEqual(task18["fipi"]["content_codes"], ["2–4"])
        task19 = get_task_classification("Математика профильная", 19, "ege", 2026)
        self.assertEqual(task19["fipi"]["content_codes"], ["1", "2", "5"])
        self.assertIn("Множества и логика", task19["fipi"]["content_name"])

    def test_geometry_lines_share_content_code_but_not_display(self):
        task1 = get_task_classification("Математика профильная", 1, "ege", 2026)
        task2 = get_task_classification("Математика профильная", 2, "ege", 2026)
        task3 = get_task_classification("Математика профильная", 3, "ege", 2026)
        self.assertEqual(task1["fipi"]["content_codes"], ["7"])
        self.assertEqual(task2["fipi"]["content_codes"], ["7"])
        self.assertEqual(task3["fipi"]["content_codes"], ["7"])
        self.assertEqual(task1["theme"]["display_name"], "Планиметрия")
        self.assertEqual(task2["theme"]["display_name"], "Векторы")
        self.assertEqual(task3["theme"]["display_name"], "Стереометрия")

    def test_probability_lines_share_content(self):
        task4 = get_task_classification("Математика профильная", 4, "ege", 2026)
        task5 = get_task_classification("Математика профильная", 5, "ege", 2026)
        self.assertEqual(task4["fipi"]["content_codes"], ["6"])
        self.assertEqual(task5["fipi"]["content_codes"], ["6"])
        self.assertEqual(task4["fipi"]["content_name"], task5["fipi"]["content_name"])
        self.assertNotEqual(task4["skills"], task5["skills"])

    def test_russian_catalog_still_works(self):
        topic = topic_for_task("Русский язык", 21, "ege")
        self.assertEqual(topic, "Пунктуационный анализ предложения")
        classification = get_task_classification("Русский язык", 7, "ege", 2026)
        self.assertEqual(classification["subject"], "russian")
        self.assertEqual(classification["verification"]["status"], "partially_verified")
        self.assertEqual(
            classification["fipi"]["content_name"],
            "Основные морфологические нормы современного русского литературного языка",
        )

    def test_oge_math_still_uses_oge_topics(self):
        self.assertEqual(topic_for_task("Математика", 1, "oge"), OGE_MATH_TASK_TOPICS[1])
        self.assertEqual(topic_for_task("Математика", 5, "oge"), OGE_MATH_TASK_TOPICS[5])
        oge = get_task_classification("Математика", 1, "oge", 2026)
        self.assertNotEqual(oge["verification"]["source"], "FIPI")

    def test_math_basic_does_not_use_math_profile_catalog(self):
        profile = topic_for_task("Математика профильная", 1, "ege")
        basic = topic_for_task("Математика базовая", 1, "ege")
        self.assertEqual(profile, EXPECTED_DISPLAY[1])
        self.assertNotEqual(basic, profile)
        classification = get_task_classification("Математика базовая", 1, "ege", 2026)
        self.assertEqual(classification["subject"], "math_basic")
        self.assertNotEqual(classification["verification"]["source"], "FIPI")

    def test_manual_override_is_not_auto_verified(self):
        ExamTaskTopic.objects.create(
            exam_type="ege",
            subject_key="math_profile",
            task_number=1,
            topic="Ручная тема планиметрии",
            grade_range=[10],
        )
        self.assertEqual(
            topic_for_task("Математика профильная", 1, "ege"),
            "Ручная тема планиметрии",
        )
        classification = get_task_classification(
            "Математика профильная", 1, "ege", 2026
        )
        self.assertEqual(classification["theme"]["display_name"], "Ручная тема планиметрии")
        self.assertEqual(classification["verification"]["status"], "needs_review")
        self.assertEqual(classification["verification"]["source"], "manual_override")
        self.assertEqual(classification["fipi"]["content_codes"], ["7"])
