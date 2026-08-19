from django.test import TestCase

from exams.models import ExamTaskTopic
from users.task_classification import get_task_classification
from users.task_topics import OGE_MATH_TASK_TOPICS, topic_for_task


THEMATIC_BLOCKS = {
    "Строение вещества",
    "Химические реакции",
    "Основы неорганической химии",
    "Основы органической химии",
    "Типы расчётных задач",
    "Экспериментальные основы химии",
    "Химия и жизнь",
}

EXPECTED_DISPLAY = {
    1: "Строение атома. Электронная конфигурация",
    2: "Периодический закон и свойства элементов",
    3: "Степень окисления",
    4: "Химическая связь и кристаллические решётки",
    5: "Классификация неорганических веществ",
    6: "Электролиты. Реакции ионного обмена",
    7: "Химические свойства неорганических веществ (вещество – реагенты)",
    8: "Химические свойства неорганических веществ (исходные вещества – продукты)",
    9: "Генетическая связь неорганических веществ",
    10: "Классификация и номенклатура органических веществ",
    11: "Теория строения Бутлерова. Изомерия и гомология",
    12: "Химические свойства углеводородов и кислородсодержащих соединений",
    13: "Азотсодержащие соединения, белки и углеводы",
    14: "Реакции углеводородов и галогенпроизводных",
    15: "Реакции кислородсодержащих органических соединений",
    16: "Цепочка превращений органических веществ",
    17: "Классификация химических реакций",
    18: "Скорость химических реакций",
    19: "Окислительно-восстановительные реакции",
    20: "Электролиз растворов и расплавов солей",
    21: "Гидролиз солей",
    22: "Химическое равновесие. Принцип Ле Шателье",
    23: "Химическое равновесие. Расчёты по уравнению реакции",
    24: "Качественные реакции. Идентификация веществ",
    25: "Химия и жизнь",
    26: "Массовая доля растворённого вещества",
    27: "Расчёты по термохимическим уравнениям",
    28: "Расчёты: примеси и выход продукта реакции",
    29: "ОВР и реакции ионного обмена",
    30: "ОВР и реакции ионного обмена",
    31: "Генетическая связь неорганических веществ",
    32: "Цепочка превращений органических веществ",
    33: "Расчётные задачи высокого уровня сложности",
    34: "Комбинированные расчёты по уравнениям реакций",
}

EXPECTED_BLOCKS = {
    1: "Строение вещества",
    2: "Строение вещества",
    3: "Строение вещества",
    4: "Строение вещества",
    5: "Основы неорганической химии",
    6: "Химические реакции",
    7: "Основы неорганической химии",
    8: "Основы неорганической химии",
    9: "Основы неорганической химии",
    10: "Основы органической химии",
    11: "Основы органической химии",
    12: "Основы органической химии",
    13: "Основы органической химии",
    14: "Основы органической химии",
    15: "Основы органической химии",
    16: "Основы органической химии",
    17: "Химические реакции",
    18: "Химические реакции",
    19: "Химические реакции",
    20: "Химические реакции",
    21: "Химические реакции",
    22: "Химические реакции",
    23: "Химические реакции",
    24: "Экспериментальные основы химии",
    25: "Химия и жизнь",
    26: "Типы расчётных задач",
    27: "Типы расчётных задач",
    28: "Типы расчётных задач",
    29: "Химические реакции",
    30: "Химические реакции",
    31: "Основы неорганической химии",
    32: "Основы органической химии",
    33: "Типы расчётных задач",
    34: "Типы расчётных задач",
}

EXPECTED_CONTENT_NAMES = {
    1: "Строение вещества. Современная модель строения атома. Электронная конфигурация атома",
    2: "Периодическая система химических элементов Д.И. Менделеева. Периодический закон. Закономерности изменения свойств элементов",
    3: "Валентность. Электроотрицательность. Степень окисления",
    4: "Виды химической связи и механизмы её образования. Типы кристаллических решёток",
    5: "Классификация неорганических соединений. Номенклатура неорганических веществ",
    6: "Электролитическая диссоциация. Реакции ионного обмена",
    7: "Химические свойства важнейших металлов и неметаллов и их соединений",
    8: "Химические свойства важнейших металлов и неметаллов и их соединений",
    9: "Генетическая связь неорганических веществ, принадлежащих к различным классам",
    10: "Представление о классификации органических веществ. Номенклатура органических соединений",
    11: "Теория химического строения А.М. Бутлерова. Изомерия и гомология. Функциональная группа",
    12: "Химические свойства углеводородов и кислородсодержащих органических соединений",
    13: "Углеводы. Амины. Аминокислоты и белки",
    14: "Химические свойства углеводородов и галогенпроизводных. Механизмы реакций. Правила Марковникова и Зайцева",
    15: "Характерные химические свойства спиртов, фенола, альдегидов, карбоновых кислот, сложных эфиров",
    16: "Генетическая связь между классами органических соединений",
    17: "Химическая реакция. Классификация химических реакций в неорганической и органической химии",
    18: "Скорость реакции, её зависимость от различных факторов",
    19: "Окислительно-восстановительные реакции. Методы электронного баланса",
    20: "Электролиз растворов и расплавов солей",
    21: "Гидролиз солей. Ионное произведение воды. Водородный показатель (pH) раствора",
    22: "Обратимые реакции. Химическое равновесие. Принцип Ле Шателье",
    23: "Обратимые реакции. Химическое равновесие. Расчёты по уравнению реакции",
    24: "",
    25: "",
    26: "Способы выражения концентрации растворов: массовая доля. Расчёты с использованием понятия «массовая доля»",
    27: "Тепловые эффекты химических реакций. Термохимические уравнения. Расчёты теплового эффекта реакции",
    28: "Расчёты массы продукта при примесях. Расчёты массовой доли выхода продукта реакции от теоретически возможного",
    29: "Окислительно-восстановительные реакции. Реакции ионного обмена",
    30: "Окислительно-восстановительные реакции. Реакции ионного обмена",
    31: "Генетическая связь неорганических веществ, принадлежащих к различным классам",
    32: "Генетическая связь между классами органических соединений",
    33: "Типы расчётных задач",
    34: "Типы расчётных задач",
}

EXPECTED_CODES = {
    1: ["1.1"],
    2: ["1.2"],
    3: ["1.3"],
    4: ["1.4"],
    5: ["2.1"],
    6: ["1.9"],
    7: ["2.2", "2.3"],
    8: ["2.2", "2.3"],
    9: ["2.4"],
    10: ["3.3"],
    11: ["3.1", "3.2"],
    12: ["3.5–3.9", "3.10–3.14"],
    13: ["3.15", "3.16", "3.17"],
    14: ["3.4", "3.5–3.9"],
    15: ["3.10–3.14"],
    16: ["3.20"],
    17: ["1.5"],
    18: ["1.6"],
    19: ["1.12"],
    20: ["1.13"],
    21: ["1.10"],
    22: ["1.8"],
    23: ["1.8"],
    24: [],
    25: [],
    26: ["1.11", "5.7"],
    27: ["1.7", "5.2"],
    28: ["5.4", "5.5"],
    29: ["1.12", "1.9"],
    30: ["1.12", "1.9"],
    31: ["2.4"],
    32: ["3.20"],
    33: ["5"],
    34: ["5"],
}

EXPECTED_STATUS = {number: "partially_verified" for number in range(1, 35)}
EXPECTED_STATUS[24] = "needs_review"
EXPECTED_STATUS[25] = "needs_review"

MULTI_CODE_TASKS = {7, 8, 11, 12, 13, 14, 26, 27, 28, 29, 30}


class ChemistryEge2026TaskTopicsTests(TestCase):
    def test_all_tasks_1_34_have_classification(self):
        for number in range(1, 35):
            with self.subTest(task=number):
                classification = get_task_classification(
                    "Химия", number, exam_type="ege", year=2026
                )
                theme = classification["theme"]
                display_name = theme["display_name"]
                block = theme["block"]

                self.assertEqual(classification["subject"], "chemistry")
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
                self.assertIsInstance(classification["school_program"]["grades"], list)
                self.assertIsInstance(classification["school_program"]["items"], list)
                self.assertIsInstance(classification["line_scope"], str)
                self.assertEqual(
                    classification["verification"]["status"],
                    EXPECTED_STATUS[number],
                )
                self.assertEqual(classification["verification"]["source"], "FIPI")
                self.assertEqual(classification["verification"]["year"], 2026)
                self.assertTrue(classification["verification"]["note"])
                self.assertEqual(
                    topic_for_task("Химия", number, "ege"),
                    display_name,
                )

    def test_part_and_task_format(self):
        for number in range(1, 29):
            classification = get_task_classification("Химия", number, "ege", 2026)
            self.assertEqual(classification["kim"]["part"], 1, number)
            self.assertEqual(classification["task_format"], "Задание с кратким ответом")
            self.assertIn("краткий ответ", classification["kim"]["answer_type"])
        for number in range(29, 35):
            classification = get_task_classification("Химия", number, "ege", 2026)
            self.assertEqual(classification["kim"]["part"], 2, number)
            self.assertEqual(
                classification["task_format"], "Задание с развёрнутым ответом"
            )
            self.assertEqual(classification["kim"]["answer_type"], "развёрнутый ответ")

    def test_multiple_content_codes_use_existing_array(self):
        for number in MULTI_CODE_TASKS:
            with self.subTest(task=number):
                classification = get_task_classification("Химия", number, "ege", 2026)
                self.assertGreaterEqual(len(classification["fipi"]["content_codes"]), 2)
                self.assertTrue(classification["line_scope"])

    def test_entities_are_separated(self):
        classification = get_task_classification("Химия", 23, "ege", 2026)
        self.assertEqual(classification["theme"]["block"], "Химические реакции")
        self.assertEqual(
            classification["theme"]["display_name"],
            "Химическое равновесие. Расчёты по уравнению реакции",
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

    def test_tasks_24_and_25_are_needs_review(self):
        for number in (24, 25):
            classification = get_task_classification("Химия", number, "ege", 2026)
            self.assertEqual(classification["verification"]["status"], "needs_review")
            self.assertEqual(classification["fipi"]["content_codes"], [])
            self.assertEqual(classification["fipi"]["content_name"], "")
            self.assertTrue(classification["verification"]["note"])
            self.assertEqual(
                topic_for_task("Химия", number, "ege"),
                EXPECTED_DISPLAY[number],
            )

    def test_no_invented_fipi_codes_on_review_lines(self):
        for number in (24, 25):
            classification = get_task_classification("Химия", number, "ege", 2026)
            for code in classification["fipi"]["content_codes"]:
                self.assertFalse(str(code).startswith("CHEM"))
                self.assertNotIn("custom", str(code).lower())

    def test_calculation_lines_use_existing_fields(self):
        task26 = get_task_classification("Химия", 26, "ege", 2026)
        self.assertEqual(task26["theme"]["block"], "Типы расчётных задач")
        self.assertIn("1.11", task26["fipi"]["content_codes"])
        self.assertIn("5.7", task26["fipi"]["content_codes"])
        task33 = get_task_classification("Химия", 33, "ege", 2026)
        self.assertEqual(task33["kim"]["part"], 2)
        self.assertEqual(task33["fipi"]["content_codes"], ["5"])
        self.assertNotEqual(task33["theme"]["display_name"], task33["task_format"])

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

    def test_math_profile_catalog_still_works(self):
        topic = topic_for_task("Математика профильная", 1, "ege")
        self.assertEqual(topic, "Планиметрия")
        classification = get_task_classification(
            "Математика профильная", 4, "ege", 2026
        )
        self.assertEqual(classification["subject"], "math_profile")
        self.assertEqual(classification["verification"]["status"], "partially_verified")

    def test_oge_math_still_uses_oge_topics(self):
        self.assertEqual(topic_for_task("Математика", 1, "oge"), OGE_MATH_TASK_TOPICS[1])
        self.assertEqual(topic_for_task("Математика", 5, "oge"), OGE_MATH_TASK_TOPICS[5])
        oge = get_task_classification("Математика", 1, "oge", 2026)
        self.assertNotEqual(oge["verification"]["source"], "FIPI")

    def test_math_basic_does_not_use_chemistry_catalog(self):
        chemistry = topic_for_task("Химия", 1, "ege")
        basic = topic_for_task("Математика базовая", 1, "ege")
        self.assertEqual(chemistry, EXPECTED_DISPLAY[1])
        self.assertNotEqual(basic, chemistry)
        classification = get_task_classification("Математика базовая", 1, "ege", 2026)
        self.assertEqual(classification["subject"], "math_basic")
        self.assertNotEqual(classification["verification"]["source"], "FIPI")

    def test_oge_chemistry_does_not_use_ege_catalog(self):
        ege_topic = topic_for_task("Химия", 1, "ege")
        oge_topic = topic_for_task("Химия", 1, "oge")
        self.assertEqual(ege_topic, EXPECTED_DISPLAY[1])
        self.assertNotEqual(oge_topic, ege_topic)
        oge_classification = get_task_classification("Химия", 1, "oge", 2026)
        self.assertEqual(oge_classification["verification"]["status"], "needs_review")
        self.assertNotEqual(oge_classification["verification"]["source"], "FIPI")

    def test_manual_override_is_not_auto_verified(self):
        ExamTaskTopic.objects.create(
            exam_type="ege",
            subject_key="chemistry",
            task_number=1,
            topic="Ручная тема строения атома",
            grade_range=[11],
        )
        self.assertEqual(
            topic_for_task("Химия", 1, "ege"),
            "Ручная тема строения атома",
        )
        classification = get_task_classification("Химия", 1, "ege", 2026)
        self.assertEqual(
            classification["theme"]["display_name"],
            "Ручная тема строения атома",
        )
        self.assertEqual(classification["verification"]["status"], "needs_review")
        self.assertEqual(classification["verification"]["source"], "manual_override")
        self.assertEqual(classification["fipi"]["content_codes"], ["1.1"])
        self.assertEqual(classification["theme"]["block"], "Строение вещества")
