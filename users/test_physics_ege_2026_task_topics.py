from django.test import TestCase

from exams.models import ExamTaskTopic
from users.task_classification import get_task_classification
from users.task_topics import (
    OGE_MATH_TASK_TOPICS,
    is_expanded_answer_task,
    part2_start_task,
    topic_for_task,
)


THEMATIC_BLOCKS = {
    "Механика",
    "Молекулярная физика и термодинамика",
    "Электродинамика",
    "Квантовая физика",
    "Методы научного познания",
    "Интегрированное содержание",
}

EXPECTED_DISPLAY = {
    1: "Кинематика: равномерное и равноускоренное движение",
    2: "Динамика: законы Ньютона, тяготение, упругость и трение",
    3: "Законы сохранения в механике",
    4: "Статика, гидростатика, колебания и волны",
    5: "Анализ механических процессов",
    6: "Механика: соответствие и изменение величин",
    7: "МКТ идеального газа",
    8: "Термодинамика и тепловые машины",
    9: "Анализ процессов молекулярной физики и термодинамики",
    10: "Молекулярная физика и термодинамика: соответствие и изменение величин",
    11: "Электростатика и законы постоянного тока",
    12: "Магнитное поле и электромагнитная индукция",
    13: "Электромагнитные колебания и геометрическая оптика",
    14: "Анализ процессов электродинамики",
    15: "Электродинамика: соответствие и изменение величин",
    16: "Физика атома и атомного ядра",
    17: "Квантовая физика: соответствие и применение законов",
    18: "Интегрированное содержание всех разделов курса",
    19: "Показания измерительных приборов",
    20: "Планирование эксперимента",
    21: "Качественная задача: молекулярная физика и электродинамика",
    22: "Расчётная задача по механике",
    23: "Расчётная задача: молекулярная физика или электродинамика",
    24: "Расчётная задача высокого уровня: молекулярная физика и термодинамика",
    25: "Расчётная задача высокого уровня: геометрическая оптика",
    26: "Расчётная задача высокого уровня по механике с обоснованием модели",
}

EXPECTED_BLOCKS = {
    1: "Механика",
    2: "Механика",
    3: "Механика",
    4: "Механика",
    5: "Механика",
    6: "Механика",
    7: "Молекулярная физика и термодинамика",
    8: "Молекулярная физика и термодинамика",
    9: "Молекулярная физика и термодинамика",
    10: "Молекулярная физика и термодинамика",
    11: "Электродинамика",
    12: "Электродинамика",
    13: "Электродинамика",
    14: "Электродинамика",
    15: "Электродинамика",
    16: "Квантовая физика",
    17: "Квантовая физика",
    18: "Интегрированное содержание",
    19: "Методы научного познания",
    20: "Методы научного познания",
    21: "Интегрированное содержание",
    22: "Механика",
    23: "Интегрированное содержание",
    24: "Молекулярная физика и термодинамика",
    25: "Электродинамика",
    26: "Механика",
}

EXPECTED_CONTENT_NAMES = {
    1: "Равномерное прямолинейное движение. Равноускоренное прямолинейное движение",
    2: "Второй закон Ньютона. Закон всемирного тяготения. Закон Гука. Сила трения",
    3: "Импульс материальной точки. Закон сохранения импульса. Работа силы. Кинетическая и потенциальная энергия. Закон изменения и сохранения механической энергии",
    4: "Момент силы. Условие равновесия твёрдого тела. Давление в жидкости. Закон Архимеда. Математический и пружинный маятники. Механические волны. Звук",
    5: "Механика",
    6: "Механика",
    7: "Связь температуры газа со средней кинетической энергией поступательного теплового движения молекул. Уравнение p = nkT. Модель идеального газа. Изопроцессы",
    8: "Количество теплоты. Изменение агрегатных состояний вещества. Элементарная работа в термодинамике. Первый закон термодинамики. КПД тепловых машин. Цикл Карно",
    9: "Молекулярная физика. Термодинамика",
    10: "Молекулярная физика. Термодинамика",
    11: "Закон Кулона. Сила тока. Закон Ома для участка цепи. Работа электрического тока. Закон Джоуля – Ленца. Мощность электрического тока",
    12: "Сила Ампера. Сила Лоренца. Закон электромагнитной индукции Фарадея. Индуктивность. Энергия магнитного поля катушки с током",
    13: "Свободные электромагнитные колебания в идеальном колебательном контуре. Формула Томсона. Законы отражения света. Изображение в плоском зеркале. Формула тонкой линзы",
    14: "Электродинамика",
    15: "Электродинамика",
    16: "Планетарная модель атома. Нуклонная модель ядра. Радиоактивность. Закон радиоактивного распада. Ядерные реакции",
    17: "Квантовая физика",
    18: "Механика. Молекулярная физика и термодинамика. Электродинамика. Квантовая физика",
    19: "Методы научного познания. Измерительные приборы",
    20: "Методы научного познания. Проведение опытов",
    21: "Молекулярная физика. Термодинамика. Электродинамика",
    22: "Механика",
    23: "Молекулярная физика. Термодинамика. Электродинамика",
    24: "Молекулярная физика. Термодинамика",
    25: "Электродинамика",
    26: "Кинематика. Динамика. Статика. Законы сохранения в механике",
}

EXPECTED_CODES = {
    1: ["1.1.5", "1.1.6"],
    2: ["1.2.4", "1.2.6", "1.2.7", "1.2.8"],
    3: ["1.4.1", "1.4.3", "1.4.4", "1.4.6", "1.4.7", "1.4.8"],
    4: ["1.3.1", "1.3.3", "1.3.5", "1.3.6", "1.5.2", "1.5.4", "1.5.5"],
    5: ["1"],
    6: ["1"],
    7: ["2.1.8", "2.1.9", "2.1.10", "2.1.12"],
    8: ["2.2.4", "2.2.5", "2.2.6", "2.2.7", "2.2.9", "2.2.10"],
    9: ["2"],
    10: ["2"],
    11: ["3.1.2", "3.2.1", "3.2.3", "3.2.8", "3.2.9"],
    12: ["3.3.3", "3.3.4", "3.4.3", "3.4.6", "3.4.7"],
    13: ["3.5.1", "3.6.2", "3.6.3", "3.6.7"],
    14: ["3"],
    15: ["3"],
    16: ["4.2.1", "4.3.1", "4.3.2", "4.3.3", "4.3.4"],
    17: ["4"],
    18: ["1", "2", "3", "4"],
    19: ["1", "2", "3"],
    20: ["1", "2", "3", "4"],
    21: ["2", "3"],
    22: ["1"],
    23: ["2", "3"],
    24: ["2"],
    25: ["3"],
    26: ["1.1", "1.2", "1.3", "1.4"],
}

EXPECTED_STATUS = {
    **{n: "verified" for n in range(1, 21)},
    21: "partially_verified",
    22: "partially_verified",
    23: "partially_verified",
    24: "verified",
    25: "partially_verified",
    26: "verified",
}

MULTI_SECTION_TASKS = {4, 13, 18, 19, 20, 21, 23, 26}

ENRICHED_LEGACY_TOPICS = {
    1: "Кинематика",
    3: "Работа и мощность",
    7: "Механические колебания и волны",
    8: "Звуковые волны и их свойства",
    9: "Электростатика и закон Кулона",
    18: "Термодинамика и тепловые процессы",
    20: "Современная физика: теория относительности",
    21: "Механика жидкости и газа",
    25: "Оптика: интерференция и дифракция",
    26: "Ядерные реакции и радиоактивность",
}

NUMERIC_SHORT = {1, 2, 3, 4, 7, 8, 11, 12, 13, 16, 19}
DIGIT_SHORT = {5, 6, 9, 10, 14, 15, 17, 18, 20}


class PhysicsEge2026TaskTopicsTests(TestCase):
    def test_all_tasks_1_26_have_classification(self):
        for number in range(1, 27):
            with self.subTest(task=number):
                classification = get_task_classification(
                    "Физика", number, exam_type="ege", year=2026
                )
                theme = classification["theme"]
                display_name = theme["display_name"]
                block = theme["block"]

                self.assertEqual(classification["subject"], "physics")
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
                self.assertTrue(classification["school_program"]["grades"])
                self.assertIsInstance(classification["school_program"]["items"], list)
                self.assertTrue(classification["school_program"]["items"])
                self.assertIsInstance(classification["line_scope"], str)
                self.assertEqual(
                    classification["verification"]["status"],
                    EXPECTED_STATUS[number],
                )
                self.assertEqual(classification["verification"]["source"], "FIPI")
                self.assertEqual(classification["verification"]["year"], 2026)
                self.assertTrue(classification["verification"]["note"])
                self.assertEqual(
                    topic_for_task("Физика", number, "ege"),
                    display_name,
                )
                self.assertNotIn("п. 119.", display_name)
                self.assertNotIn("openai", display_name.lower())

    def test_part_and_answer_types(self):
        for number in range(1, 21):
            classification = get_task_classification("Физика", number, "ege", 2026)
            self.assertEqual(classification["kim"]["part"], 1, number)
            self.assertIn("краткий ответ", classification["kim"]["answer_type"])
            self.assertNotIn("развёрнутый", classification["task_format"].lower(), number)
        for number in range(21, 27):
            classification = get_task_classification("Физика", number, "ege", 2026)
            self.assertEqual(classification["kim"]["part"], 2, number)
            self.assertEqual(classification["kim"]["answer_type"], "развёрнутый ответ")
            self.assertIn("развёрнут", classification["task_format"].lower())

        for number in NUMERIC_SHORT:
            classification = get_task_classification("Физика", number, "ege", 2026)
            self.assertIn("числа", classification["kim"]["answer_type"], number)
        for number in DIGIT_SHORT:
            classification = get_task_classification("Физика", number, "ege", 2026)
            self.assertIn("последовательности цифр", classification["kim"]["answer_type"], number)

    def test_multiple_content_codes_use_existing_array(self):
        for number in MULTI_SECTION_TASKS:
            with self.subTest(task=number):
                classification = get_task_classification("Физика", number, "ege", 2026)
                self.assertGreaterEqual(len(classification["fipi"]["content_codes"]), 2)
                self.assertTrue(classification["line_scope"])

    def test_no_invented_subcodes_beyond_spec_plan(self):
        allowed_prefixes = ("1", "2", "3", "4")
        for number in range(1, 27):
            classification = get_task_classification("Физика", number, "ege", 2026)
            for code in classification["fipi"]["content_codes"]:
                self.assertTrue(str(code).startswith(allowed_prefixes), code)
                self.assertNotIn("PHYS", str(code))
                self.assertRegex(str(code), r"^[1-4](\.\d+){0,2}$")

    def test_school_program_comes_from_spec_table_1(self):
        task1 = get_task_classification("Физика", 1, "ege", 2026)
        self.assertEqual(task1["school_program"]["grades"], [9, 10])
        self.assertTrue(any("115.6.2" in item for item in task1["school_program"]["items"]))
        self.assertTrue(any("153.5.1" in item for item in task1["school_program"]["items"]))
        task12 = get_task_classification("Физика", 12, "ege", 2026)
        self.assertEqual(task12["school_program"]["grades"], [11])
        self.assertTrue(any("115.7.1" in item for item in task12["school_program"]["items"]))

    def test_entities_are_separated(self):
        classification = get_task_classification("Физика", 21, "ege", 2026)
        self.assertEqual(classification["theme"]["block"], "Интегрированное содержание")
        self.assertEqual(
            classification["theme"]["display_name"],
            "Качественная задача: молекулярная физика и электродинамика",
        )
        self.assertNotEqual(
            classification["theme"]["display_name"],
            classification["skills"][0],
        )
        self.assertNotEqual(
            classification["task_format"],
            classification["theme"]["display_name"],
        )
        self.assertNotEqual(
            classification["fipi"]["content_name"],
            classification["theme"]["display_name"],
        )
        self.assertIn("качествен", classification["task_format"].lower())

    def test_calculation_and_experiment_formats(self):
        meter = get_task_classification("Физика", 19, "ege", 2026)
        plan = get_task_classification("Физика", 20, "ege", 2026)
        qualitative = get_task_classification("Физика", 21, "ege", 2026)
        calc = get_task_classification("Физика", 22, "ege", 2026)
        optics = get_task_classification("Физика", 25, "ege", 2026)
        model = get_task_classification("Физика", 26, "ege", 2026)
        self.assertIn("прибор", meter["task_format"].lower())
        self.assertIn("эксперимент", plan["task_format"].lower())
        self.assertIn("качествен", qualitative["task_format"].lower())
        self.assertIn("расчётн", calc["task_format"].lower())
        self.assertIn("оптик", optics["theme"]["display_name"].lower())
        self.assertIn("обоснован", model["task_format"].lower())
        self.assertEqual(meter["kim"]["part"], 1)
        self.assertEqual(plan["kim"]["part"], 1)
        self.assertEqual(qualitative["kim"]["part"], 2)

    def test_old_enriched_topic_is_not_used(self):
        for number, old_topic in ENRICHED_LEGACY_TOPICS.items():
            topic = topic_for_task("Физика", number, "ege")
            self.assertEqual(topic, EXPECTED_DISPLAY[number], number)
            self.assertNotEqual(topic, old_topic, number)
        self.assertNotEqual(topic_for_task("Физика", 7, "ege"), "Механические колебания и волны")
        self.assertNotEqual(topic_for_task("Физика", 12, "ege"), "Магнитное поле и его свойства")

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

    def test_chemistry_catalog_still_works(self):
        topic = topic_for_task("Химия", 1, "ege")
        self.assertEqual(topic, "Строение атома. Электронная конфигурация")
        classification = get_task_classification("Химия", 24, "ege", 2026)
        self.assertEqual(classification["subject"], "chemistry")
        self.assertEqual(classification["verification"]["status"], "needs_review")

    def test_biology_catalog_still_works(self):
        topic = topic_for_task("Биология", 1, "ege")
        self.assertEqual(topic, "Биология как наука. Уровни организации живого")
        classification = get_task_classification("Биология", 22, "ege", 2026)
        self.assertEqual(classification["subject"], "biology")
        self.assertEqual(classification["kim"]["part"], 2)

    def test_oge_math_still_uses_oge_topics(self):
        self.assertEqual(topic_for_task("Математика", 1, "oge"), OGE_MATH_TASK_TOPICS[1])
        self.assertEqual(topic_for_task("Математика", 5, "oge"), OGE_MATH_TASK_TOPICS[5])
        oge = get_task_classification("Математика", 1, "oge", 2026)
        self.assertNotEqual(oge["verification"]["source"], "FIPI")

    def test_math_basic_does_not_use_physics_catalog(self):
        physics = topic_for_task("Физика", 1, "ege")
        basic = topic_for_task("Математика базовая", 1, "ege")
        self.assertEqual(physics, EXPECTED_DISPLAY[1])
        self.assertNotEqual(basic, physics)
        classification = get_task_classification("Математика базовая", 1, "ege", 2026)
        self.assertEqual(classification["subject"], "math_basic")
        self.assertNotEqual(classification["verification"]["source"], "FIPI")

    def test_oge_physics_does_not_use_ege_catalog(self):
        ege_topic = topic_for_task("Физика", 1, "ege")
        oge_topic = topic_for_task("Физика", 1, "oge")
        self.assertEqual(ege_topic, EXPECTED_DISPLAY[1])
        self.assertNotEqual(oge_topic, ege_topic)
        oge_classification = get_task_classification("Физика", 1, "oge", 2026)
        self.assertEqual(oge_classification["verification"]["status"], "needs_review")
        self.assertNotEqual(oge_classification["verification"]["source"], "FIPI")

    def test_manual_override_is_not_auto_verified(self):
        ExamTaskTopic.objects.create(
            exam_type="ege",
            subject_key="physics",
            task_number=1,
            topic="Ручная тема кинематики",
            grade_range=[11],
        )
        self.assertEqual(topic_for_task("Физика", 1, "ege"), "Ручная тема кинематики")
        classification = get_task_classification("Физика", 1, "ege", 2026)
        self.assertEqual(
            classification["theme"]["display_name"],
            "Ручная тема кинематики",
        )
        self.assertEqual(classification["verification"]["status"], "needs_review")
        self.assertEqual(classification["verification"]["source"], "manual_override")
        self.assertEqual(classification["fipi"]["content_codes"], ["1.1.5", "1.1.6"])
        self.assertEqual(classification["theme"]["block"], "Механика")


PHYSICS_PART2_BOUNDARY = 21


class PhysicsEge2026PartBoundaryTests(TestCase):
    def test_part2_start_task_from_catalog(self):
        self.assertEqual(part2_start_task("ege", "physics"), PHYSICS_PART2_BOUNDARY)
        self.assertEqual(
            get_task_classification("Физика", PHYSICS_PART2_BOUNDARY - 1, "ege", 2026)[
                "kim"
            ]["part"],
            1,
        )
        self.assertEqual(
            get_task_classification("Физика", PHYSICS_PART2_BOUNDARY, "ege", 2026)[
                "kim"
            ]["part"],
            2,
        )

    def test_is_expanded_answer_task(self):
        self.assertFalse(is_expanded_answer_task("ege", "physics", 20))
        self.assertTrue(is_expanded_answer_task("ege", "physics", 21))

    def test_isolation_of_other_catalog_subjects(self):
        self.assertEqual(part2_start_task("ege", "russian"), 27)
        self.assertEqual(part2_start_task("ege", "math_profile"), 13)
        self.assertEqual(part2_start_task("ege", "chemistry"), 29)
        self.assertEqual(part2_start_task("ege", "biology"), 22)
        self.assertFalse(is_expanded_answer_task("ege", "russian", 26))
        self.assertTrue(is_expanded_answer_task("ege", "russian", 27))
        self.assertFalse(is_expanded_answer_task("ege", "math_profile", 12))
        self.assertTrue(is_expanded_answer_task("ege", "math_profile", 13))
        self.assertFalse(is_expanded_answer_task("ege", "chemistry", 28))
        self.assertTrue(is_expanded_answer_task("ege", "chemistry", 29))
        self.assertFalse(is_expanded_answer_task("ege", "biology", 21))
        self.assertTrue(is_expanded_answer_task("ege", "biology", 22))
