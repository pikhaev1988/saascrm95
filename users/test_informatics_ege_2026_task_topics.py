from django.test import TestCase

from exams.models import ExamTaskTopic
from users.task_classification import get_task_classification
from users.task_topics import (
    OGE_MATH_TASK_TOPICS,
    is_expanded_answer_task,
    part2_start_task,
    topic_for_task,
)


EXPECTED_BOUNDARY = 26
PART2_TASKS = {26, 27}

EXPECTED_DISPLAY = {
    1: "Информационные модели: схемы, таблицы, графики",
    2: "Логические выражения и таблицы истинности",
    3: "Поиск и выборка в реляционной базе данных",
    4: "Кодирование и декодирование сообщений (условие Фано)",
    5: "Формальное исполнение линейного алгоритма",
    6: "Результаты работы алгоритма исполнителя",
    7: "Объём графической и звуковой информации",
    8: "Измерение количества информации",
    9: "Обработка числовых данных в электронных таблицах",
    10: "Информационный поиск в текстовом процессоре",
    11: "Подсчёт информационного объёма сообщения",
    12: "Исполнение алгоритма для конкретного исполнителя",
    13: "IP-адресация и маска подсети",
    14: "Позиционные системы счисления",
    15: "Законы математической логики",
    16: "Вычисление рекуррентных выражений",
    17: "Программа обработки числовой последовательности",
    18: "Электронные таблицы для обработки целочисленных данных",
    19: "Анализ алгоритма логической игры",
    20: "Выигрышная стратегия игры",
    21: "Дерево игры и выигрышная стратегия",
    22: "Математическая модель и параллельные вычисления",
    23: "Анализ хода исполнения алгоритма",
    24: "Программа обработки символьной информации",
    25: "Программа обработки целочисленной информации",
    26: "Обработка целочисленной информации с сортировкой",
    27: "Полный цикл анализа данных",
}

EXPECTED_CODES = {
    1: ["2.10"],
    2: ["2.7"],
    3: ["4.5"],
    4: ["2.1"],
    5: ["3.3"],
    6: ["3.3"],
    7: ["2.6"],
    8: ["2.2"],
    9: ["4.2"],
    10: ["4.6"],
    11: ["2.2"],
    12: ["3.3"],
    13: ["1.2"],
    14: ["2.3"],
    15: ["2.7"],
    16: ["3.7"],
    17: ["3.10"],
    18: ["4.5"],
    19: ["2.15"],
    20: ["2.15"],
    21: ["2.15"],
    22: ["1.1"],
    23: ["3.3"],
    24: ["3.9"],
    25: ["3.4"],
    26: ["3.10"],
    27: ["4.1"],
}


class InformaticsEge2026TaskTopicsTests(TestCase):
    def test_all_tasks_1_27_have_classification(self):
        for number in range(1, 28):
            with self.subTest(task=number):
                c = get_task_classification("Информатика", number, "ege", 2026)
                self.assertEqual(c["subject"], "informatics")
                self.assertEqual(c["exam_type"], "ege")
                self.assertEqual(c["year"], 2026)
                self.assertEqual(c["task"], number)
                self.assertEqual(c["kim"]["line"], number)
                self.assertEqual(c["theme"]["display_name"], EXPECTED_DISPLAY[number])
                self.assertEqual(c["fipi"]["content_codes"], EXPECTED_CODES[number])
                self.assertTrue(c["kim"]["answer_type"])
                self.assertTrue(c["fipi"]["content_name"])
                self.assertTrue(c["theme"]["block"])
                self.assertTrue(c["skills"])
                self.assertTrue(c["task_format"])
                self.assertIsInstance(c["school_program"]["grades"], list)
                self.assertIsInstance(c["school_program"]["items"], list)
                self.assertTrue(c["school_program"]["grades"])
                self.assertTrue(c["school_program"]["items"])
                self.assertEqual(
                    topic_for_task("Информатика", number, "ege"),
                    EXPECTED_DISPLAY[number],
                )

    def test_kim_part_boundary(self):
        for number in range(1, EXPECTED_BOUNDARY):
            c = get_task_classification("Информатика", number, "ege", 2026)
            self.assertEqual(c["kim"]["part"], 1, number)
        for number in PART2_TASKS:
            c = get_task_classification("Информатика", number, "ege", 2026)
            self.assertEqual(c["kim"]["part"], 2, number)
        self.assertEqual(part2_start_task("ege", "informatics"), EXPECTED_BOUNDARY)
        self.assertFalse(
            is_expanded_answer_task("ege", "informatics", EXPECTED_BOUNDARY - 1)
        )
        self.assertTrue(is_expanded_answer_task("ege", "informatics", EXPECTED_BOUNDARY))

    def test_answer_type_is_short_for_all_tasks(self):
        for number in range(1, 28):
            answer_type = get_task_classification(
                "Информатика", number, "ege", 2026
            )["kim"]["answer_type"]
            self.assertIn("краткий ответ", answer_type)

    def test_manual_override_keeps_priority(self):
        ExamTaskTopic.objects.create(
            exam_type="ege",
            subject_key="informatics",
            task_number=1,
            topic="Ручная тема по моделированию",
            grade_range=[11],
        )
        self.assertEqual(
            topic_for_task("Информатика", 1, "ege"),
            "Ручная тема по моделированию",
        )
        c = get_task_classification("Информатика", 1, "ege", 2026)
        self.assertEqual(c["theme"]["display_name"], "Ручная тема по моделированию")
        self.assertEqual(c["verification"]["status"], "needs_review")
        self.assertEqual(c["verification"]["source"], "manual_override")

    def test_isolation_other_subjects_and_oge(self):
        self.assertEqual(part2_start_task("ege", "russian"), 27)
        self.assertEqual(part2_start_task("ege", "math_profile"), 13)
        self.assertEqual(part2_start_task("ege", "chemistry"), 29)
        self.assertEqual(part2_start_task("ege", "biology"), 22)
        self.assertEqual(part2_start_task("ege", "physics"), 21)
        self.assertEqual(topic_for_task("Математика", 1, "oge"), OGE_MATH_TASK_TOPICS[1])
