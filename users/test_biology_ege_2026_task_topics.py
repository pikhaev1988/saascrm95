from django.test import TestCase

from exams.models import ExamTaskTopic
from users.task_classification import get_task_classification
from users.task_topics import OGE_MATH_TASK_TOPICS, topic_for_task


THEMATIC_BLOCKS = {
    "Биология как наука",
    "Клетка как биологическая система",
    "Организм как биологическая система",
    "Многообразие органического мира",
    "Организм человека и его здоровье",
    "Эволюция живой природы",
    "Экосистемы и биосфера",
}

EXPECTED_DISPLAY = {
    1: "Биология как наука. Уровни организации живого",
    2: "Прогнозирование результатов биологического эксперимента",
    3: "Генетическая информация в клетке. Хромосомный набор",
    4: "Моногибридное и анализирующее скрещивание. Анализ родословных",
    5: "Клетка и организм. Анализ рисунка или схемы",
    6: "Клетка и организм. Установление соответствия",
    7: "Клетка, организм, селекция и биотехнология",
    8: "Клетка, организм, селекция и биотехнология",
    9: "Многообразие организмов. Анализ рисунка или схемы",
    10: "Многообразие организмов. Установление соответствия",
    11: "Многообразие организмов. Множественный выбор",
    12: "Систематические категории и их соподчинённость",
    13: "Организм человека. Анализ рисунка или схемы",
    14: "Организм человека. Установление соответствия",
    15: "Организм человека. Множественный выбор",
    16: "Организм человека. Установление последовательности",
    17: "Эволюция живой природы",
    18: "Экосистемы и биосфера",
    19: "Эволюция, происхождение человека, экосистемы",
    20: "Общебиологические закономерности. Человек и его здоровье",
    21: "Анализ табличных и графических данных",
    22: "Анализ биологического эксперимента",
    23: "Выводы и прогнозы по результатам эксперимента",
    24: "Изображение биологического объекта",
    25: "Человек и многообразие организмов",
    26: "Общая биология в новой ситуации",
    27: "Задачи по цитологии и эволюции",
    28: "Задачи по генетике",
}

EXPECTED_BLOCKS = {
    1: "Биология как наука",
    2: "Биология как наука",
    3: "Клетка как биологическая система",
    4: "Организм как биологическая система",
    5: "Клетка как биологическая система",
    6: "Клетка как биологическая система",
    7: "Организм как биологическая система",
    8: "Организм как биологическая система",
    9: "Многообразие органического мира",
    10: "Многообразие органического мира",
    11: "Многообразие органического мира",
    12: "Многообразие органического мира",
    13: "Организм человека и его здоровье",
    14: "Организм человека и его здоровье",
    15: "Организм человека и его здоровье",
    16: "Организм человека и его здоровье",
    17: "Эволюция живой природы",
    18: "Экосистемы и биосфера",
    19: "Эволюция живой природы",
    20: "Организм человека и его здоровье",
    21: "Биология как наука",
    22: "Биология как наука",
    23: "Биология как наука",
    24: "Многообразие органического мира",
    25: "Многообразие органического мира",
    26: "Эволюция живой природы",
    27: "Клетка как биологическая система",
    28: "Организм как биологическая система",
}

EXPECTED_CONTENT_NAMES = {
    1: "Биология как наука. Живые системы и их изучение",
    2: "Биология как наука. Живые системы и их изучение",
    3: "Клетка как биологическая система",
    4: "Организм как биологическая система",
    5: "Клетка как биологическая система. Организм как биологическая система",
    6: "Клетка как биологическая система. Организм как биологическая система",
    7: "Клетка как биологическая система. Организм как биологическая система. Селекция. Биотехнология",
    8: "Клетка как биологическая система. Организм как биологическая система. Селекция. Биотехнология",
    9: "Система и многообразие органического мира",
    10: "Система и многообразие органического мира",
    11: "Система и многообразие органического мира",
    12: "Система и многообразие органического мира",
    13: "Организм человека и его здоровье",
    14: "Организм человека и его здоровье",
    15: "Организм человека и его здоровье",
    16: "Организм человека и его здоровье",
    17: "Теория эволюции. Развитие жизни на Земле",
    18: "Экосистемы и присущие им закономерности",
    19: "Теория эволюции. Развитие жизни на Земле. Экосистемы и присущие им закономерности",
    20: "Общебиологические закономерности. Организм человека и его здоровье",
    21: "Биология как наука. Живые системы и их изучение",
    22: "Все проверяемые разделы кодификатора",
    23: "Все проверяемые разделы кодификатора",
    24: "Все разделы кодификатора, кроме «Биология как наука. Живые системы и их изучение»",
    25: "Клетка как биологическая система. Система и многообразие органического мира. Организм человека и его здоровье",
    26: "Организм как биологическая система. Теория эволюции. Развитие жизни на Земле. Экосистемы и присущие им закономерности",
    27: "Клетка как биологическая система. Организм как биологическая система. Теория эволюции. Развитие жизни на Земле",
    28: "Клетка как биологическая система. Организм как биологическая система",
}

EXPECTED_CODES = {
    1: ["1"],
    2: ["1"],
    3: ["2"],
    4: ["3"],
    5: ["2", "3"],
    6: ["2", "3"],
    7: ["2", "3"],
    8: ["2", "3"],
    9: ["4"],
    10: ["4"],
    11: ["4"],
    12: ["4"],
    13: ["5"],
    14: ["5"],
    15: ["5"],
    16: ["5"],
    17: ["6"],
    18: ["7"],
    19: ["6", "7"],
    20: ["5"],
    21: ["1"],
    22: ["1", "2", "3", "4", "5", "6", "7"],
    23: ["1", "2", "3", "4", "5", "6", "7"],
    24: ["2", "3", "4", "5", "6", "7"],
    25: ["2", "4", "5"],
    26: ["3", "6", "7"],
    27: ["2", "3", "6"],
    28: ["2", "3"],
}

MULTI_SECTION_TASKS = {5, 6, 7, 8, 19, 22, 23, 24, 25, 26, 27, 28}

ENRICHED_LEGACY_MARKERS = (
    "п. 119.",
    "п. 120.",
    "п. 157.",
    "Общая биология и анатомия",
    "Генетика и экология",
    "Содержание задания №",
)


class BiologyEge2026TaskTopicsTests(TestCase):
    def test_all_tasks_1_28_have_classification(self):
        for number in range(1, 29):
            with self.subTest(task=number):
                classification = get_task_classification(
                    "Биология", number, exam_type="ege", year=2026
                )
                theme = classification["theme"]
                display_name = theme["display_name"]
                block = theme["block"]

                self.assertEqual(classification["subject"], "biology")
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
                self.assertNotEqual(classification["task_format"], display_name)
                self.assertIsInstance(classification["school_program"]["grades"], list)
                self.assertIsInstance(classification["school_program"]["items"], list)
                self.assertEqual(classification["school_program"]["grades"], [])
                self.assertEqual(classification["school_program"]["items"], [])
                self.assertIsInstance(classification["line_scope"], str)
                self.assertEqual(
                    classification["verification"]["status"], "partially_verified"
                )
                self.assertEqual(classification["verification"]["source"], "FIPI")
                self.assertEqual(classification["verification"]["year"], 2026)
                self.assertTrue(classification["verification"]["note"])
                self.assertEqual(
                    topic_for_task("Биология", number, "ege"),
                    display_name,
                )
                for marker in ENRICHED_LEGACY_MARKERS:
                    self.assertNotIn(marker, display_name)

    def test_part_and_answer_types(self):
        for number in range(1, 22):
            classification = get_task_classification("Биология", number, "ege", 2026)
            self.assertEqual(classification["kim"]["part"], 1, number)
            self.assertIn("краткий ответ", classification["kim"]["answer_type"])
            self.assertNotEqual(
                classification["task_format"],
                "Задание с развёрнутым ответом",
                number,
            )
        for number in range(22, 29):
            classification = get_task_classification("Биология", number, "ege", 2026)
            self.assertEqual(classification["kim"]["part"], 2, number)
            self.assertEqual(classification["kim"]["answer_type"], "развёрнутый ответ")
            self.assertEqual(
                classification["task_format"],
                "Задание с развёрнутым ответом",
            )

    def test_multiple_content_codes_use_existing_array(self):
        for number in MULTI_SECTION_TASKS:
            with self.subTest(task=number):
                classification = get_task_classification("Биология", number, "ege", 2026)
                self.assertGreaterEqual(len(classification["fipi"]["content_codes"]), 2)
                self.assertTrue(classification["line_scope"])

    def test_no_invented_subcodes(self):
        for number in range(1, 29):
            classification = get_task_classification("Биология", number, "ege", 2026)
            for code in classification["fipi"]["content_codes"]:
                self.assertRegex(str(code), r"^[1-7]$")

    def test_different_short_answer_formats(self):
        table = get_task_classification("Биология", 1, "ege", 2026)
        choice = get_task_classification("Биология", 2, "ege", 2026)
        calc = get_task_classification("Биология", 3, "ege", 2026)
        match = get_task_classification("Биология", 6, "ege", 2026)
        sequence = get_task_classification("Биология", 12, "ege", 2026)
        graph = get_task_classification("Биология", 21, "ege", 2026)
        self.assertIn("таблиц", table["task_format"].lower())
        self.assertIn("выбор", choice["task_format"].lower())
        self.assertIn("задач", calc["task_format"].lower())
        self.assertIn("соответств", match["task_format"].lower())
        self.assertIn("последовательн", sequence["task_format"].lower())
        self.assertIn("графическ", graph["task_format"].lower())

    def test_extended_answer_lines(self):
        experiment = get_task_classification("Биология", 22, "ege", 2026)
        genetics = get_task_classification("Биология", 28, "ege", 2026)
        self.assertEqual(experiment["kim"]["part"], 2)
        self.assertEqual(genetics["kim"]["part"], 2)
        self.assertEqual(
            experiment["fipi"]["content_codes"],
            ["1", "2", "3", "4", "5", "6", "7"],
        )
        self.assertEqual(genetics["fipi"]["content_codes"], ["2", "3"])
        self.assertIn("нулев", experiment["skills"][0])
        self.assertIn("генетическ", genetics["skills"][0])

    def test_old_enriched_topic_is_not_used(self):
        topic = topic_for_task("Биология", 1, "ege")
        self.assertEqual(topic, EXPECTED_DISPLAY[1])
        self.assertNotIn("п. 119.", topic)
        self.assertNotIn("п. 157.", topic)
        self.assertNotEqual(topic, "Общая биология и анатомия")
        topic17 = topic_for_task("Биология", 17, "ege")
        self.assertEqual(topic17, EXPECTED_DISPLAY[17])
        self.assertNotEqual(topic17, "Эволюция и развитие жизни на Земле")

    def test_russian_catalog_still_works(self):
        topic = topic_for_task("Русский язык", 21, "ege")
        self.assertEqual(topic, "Пунктуационный анализ предложения")
        classification = get_task_classification("Русский язык", 7, "ege", 2026)
        self.assertEqual(classification["subject"], "russian")
        self.assertEqual(classification["verification"]["status"], "partially_verified")

    def test_math_profile_catalog_still_works(self):
        topic = topic_for_task("Математика профильная", 1, "ege")
        self.assertEqual(topic, "Планиметрия")
        classification = get_task_classification(
            "Математика профильная", 4, "ege", 2026
        )
        self.assertEqual(classification["subject"], "math_profile")
        self.assertEqual(classification["verification"]["status"], "partially_verified")

    def test_chemistry_catalog_still_works(self):
        topic = topic_for_task("Химия", 1, "ege")
        self.assertEqual(topic, "Строение атома. Электронная конфигурация")
        classification = get_task_classification("Химия", 24, "ege", 2026)
        self.assertEqual(classification["subject"], "chemistry")
        self.assertEqual(classification["verification"]["status"], "needs_review")

    def test_oge_math_still_uses_oge_topics(self):
        self.assertEqual(topic_for_task("Математика", 1, "oge"), OGE_MATH_TASK_TOPICS[1])
        self.assertEqual(topic_for_task("Математика", 5, "oge"), OGE_MATH_TASK_TOPICS[5])
        oge = get_task_classification("Математика", 1, "oge", 2026)
        self.assertNotEqual(oge["verification"]["source"], "FIPI")

    def test_math_basic_does_not_use_biology_or_profile_catalog(self):
        biology = topic_for_task("Биология", 1, "ege")
        profile = topic_for_task("Математика профильная", 1, "ege")
        basic = topic_for_task("Математика базовая", 1, "ege")
        self.assertEqual(biology, EXPECTED_DISPLAY[1])
        self.assertEqual(profile, "Планиметрия")
        self.assertNotEqual(basic, biology)
        self.assertNotEqual(basic, profile)
        classification = get_task_classification("Математика базовая", 1, "ege", 2026)
        self.assertEqual(classification["subject"], "math_basic")
        self.assertNotEqual(classification["verification"]["source"], "FIPI")

    def test_oge_biology_does_not_use_ege_catalog(self):
        ege_topic = topic_for_task("Биология", 1, "ege")
        oge_topic = topic_for_task("Биология", 1, "oge")
        self.assertEqual(ege_topic, EXPECTED_DISPLAY[1])
        self.assertNotEqual(oge_topic, ege_topic)
        oge_classification = get_task_classification("Биология", 1, "oge", 2026)
        self.assertEqual(oge_classification["verification"]["status"], "needs_review")
        self.assertNotEqual(oge_classification["verification"]["source"], "FIPI")

    def test_manual_override_is_not_auto_verified(self):
        ExamTaskTopic.objects.create(
            exam_type="ege",
            subject_key="biology",
            task_number=1,
            topic="Ручная тема клеточной теории",
            grade_range=[11],
        )
        self.assertEqual(
            topic_for_task("Биология", 1, "ege"),
            "Ручная тема клеточной теории",
        )
        classification = get_task_classification("Биология", 1, "ege", 2026)
        self.assertEqual(
            classification["theme"]["display_name"],
            "Ручная тема клеточной теории",
        )
        self.assertEqual(classification["verification"]["status"], "needs_review")
        self.assertEqual(classification["verification"]["source"], "manual_override")
        self.assertEqual(classification["fipi"]["content_codes"], ["1"])
        self.assertEqual(classification["theme"]["block"], "Биология как наука")
