"""Тесты Rule Engine экспертной интерпретации ФИОКО 2.0."""

from __future__ import annotations

from types import SimpleNamespace

from django.test import SimpleTestCase

from apps.vpr.expert_analysis import build_expert_analysis
from apps.vpr.expert_analysis.competences import competences_for_subject, normalize_subject
from apps.vpr.expert_analysis.cognitive import analyze_cognitive
from apps.vpr.expert_analysis.subject_models import get_subject_model


def _task(code, pct, topic="", skill="", section="", difficulty="Базовый"):
    return {
        "task_code": code,
        "completion_percent": pct,
        "topic": topic,
        "checked_skill": skill,
        "program_section": section,
        "difficulty": difficulty,
        "priority": "High" if pct < 50 else "Low",
        "status": "RISK" if pct < 50 else "NORMAL",
    }


def _topic(name, pct):
    return SimpleNamespace(topic=name, avg_completion_percent=pct, mastery_level=None)


def _skill(name, pct):
    return SimpleNamespace(checked_skill=name, avg_completion_percent=pct, mastery_level=None)


def _analysis(subject="Математика", **kwargs):
    base = SimpleNamespace(
        subject=subject,
        parallel=4,
        academic_year=2026,
        summary=SimpleNamespace(
            knowledge_quality_percent=55.0,
            absolute_achievement_percent=80.0,
            avg_primary_score=12.0,
            max_primary_score=20.0,
            median_primary_score=11.0,
            cv_primary_score_percent=28.0,
            avg_mark_vpr=3.5,
            avg_mark_journal=4.0,
            sou_percent=60.0,
        ),
        task_rows=[
            _task("1", 90, "Дроби", "Выполнять арифметические действия", "Числа и вычисления", "Базовый"),
            _task("2", 85, "Натуральные числа", "Выполнять арифметические действия", "Числа и вычисления", "Базовый"),
            _task("3", 35, "Решение текстовых задач", "Решать текстовые задачи", "Текстовые задачи", "Повышенный"),
            _task("4", 40, "Задачи на величины", "Решать задачи на скорость", "Текстовые задачи", "Повышенный"),
            _task("5", 30, "Комплексная задача", "Решать комплексные задачи", "Текстовые задачи", "Повышенный"),
            _task("6", 70, "Наглядная геометрия", "Вычислять периметр", "Геометрия", "Базовый"),
        ],
        topic_rows=[
            _topic("Дроби", 90),
            _topic("Решение текстовых задач", 35),
            _topic("Задачи на величины", 40),
            _topic("Наглядная геометрия", 70),
        ],
        skill_rows=[
            _skill("Выполнять арифметические действия с натуральными числами", 88),
            _skill("Решать текстовые задачи арифметическим способом", 35),
            _skill("Решать задачи на скорость, время, расстояние", 40),
        ],
        topic_analysis=SimpleNamespace(mass_deficits=["Решение текстовых задач"], local_deficits=[]),
        participant_groups=SimpleNamespace(
            groups={
                "high": SimpleNamespace(count=3, percent=15),
                "medium": SimpleNamespace(count=12, percent=60),
                "risk": SimpleNamespace(count=5, percent=25),
            }
        ),
        causes=SimpleNamespace(
            summary=SimpleNamespace(
                dominant_cause_type="тематический",
                dominant_scale="массовый",
                causes_count=3,
                significant_deficits_count=2,
            ),
            patterns=[],
            topics=[],
            skills=[],
            tasks=[],
        ),
    )
    for key, value in kwargs.items():
        setattr(base, key, value)
    return base


class ExpertAnalysisV2Tests(SimpleTestCase):
    def test_subject_models_unique(self):
        math_m = get_subject_model("Математика")
        rus_m = get_subject_model("Русский язык")
        hist_m = get_subject_model("История")
        self.assertNotEqual(math_m.overview_openers[0], rus_m.overview_openers[0])
        self.assertNotEqual(rus_m.systemic_chain, hist_m.systemic_chain)
        self.assertIn("картографическая", " ".join(get_subject_model("География").competence_lines))

    def test_cognitive_meta(self):
        code, label, _paras, meta = analyze_cognitive(_analysis())
        self.assertIn(code, {"advanced_deficit", "advanced_gap", "both_levels"})
        self.assertIsNotNone(meta["basic_avg"])
        self.assertIsNotNone(meta["advanced_avg"])
        self.assertTrue(label)

    def test_no_task_number_listing(self):
        report = build_expert_analysis(_analysis(), protocol=None)
        blob = " ".join(
            report.tasks_analysis
            + report.overview
            + report.problems
            + report.topics_analysis
        )
        self.assertNotIn("Задание №", blob)
        self.assertNotIn("задание №", blob.lower())
        self.assertNotIn("№1", blob)
        self.assertNotIn("№2", blob)

    def test_texts_differ_by_subject(self):
        math_report = build_expert_analysis(_analysis("Математика"), protocol=None)
        rus = _analysis("Русский язык")
        rus.task_rows = [
            _task("1", 80, "Списывание текста", "Соблюдать нормы", "Орфография и письмо", "Базовый"),
            _task("2", 40, "Смысловой анализ текста", "Проводить смысловой анализ", "Развитие речи", "Повышенный"),
            _task("3", 35, "Работа с текстом", "Перерабатывать информацию", "Развитие речи", "Базовый"),
            _task("4", 38, "Лексика", "Объяснять значение", "Лексика", "Базовый"),
        ]
        rus.topic_rows = [
            _topic("Списывание текста", 80),
            _topic("Смысловой анализ текста", 40),
            _topic("Работа с текстом", 35),
        ]
        rus.skill_rows = [
            _skill("Соблюдать нормы современного русского литературного языка", 80),
            _skill("Проводить смысловой анализ текста", 40),
        ]
        rus_report = build_expert_analysis(rus, protocol=None)

        self.assertNotEqual(math_report.overview[0], rus_report.overview[0])
        self.assertNotEqual(math_report.final_conclusion[0], rus_report.final_conclusion[0])
        self.assertTrue(any("математи" in p.lower() or "вычисл" in p.lower() or "модель" in p.lower() for p in math_report.overview + math_report.competences_analysis))
        self.assertTrue(any("язык" in p.lower() or "текст" in p.lower() or "орфограф" in p.lower() or "читатель" in p.lower() for p in rus_report.overview + rus_report.competences_analysis))
        self.assertTrue(math_report.cause_chains)
        self.assertTrue(rus_report.cause_chains)
        # Цепочки — не пустые шаги
        self.assertGreaterEqual(len(math_report.cause_chains[0].steps), 3)

    def test_history_spatial_chain_language(self):
        hist = _analysis("История")
        hist.task_rows = [
            _task("1", 85, "События", "Знать события", "История России", "Базовый"),
            _task("2", 30, "Карта", "Работать с картой", "Историческая карта", "Базовый"),
            _task("3", 28, "Источник", "Анализировать источник", "Источники", "Повышенный"),
            _task("4", 32, "Памятники", "Анализировать культуру", "Культура", "Повышенный"),
        ]
        hist.topic_rows = [
            _topic("Историческая карта", 30),
            _topic("Источники", 28),
            _topic("Культура", 32),
        ]
        hist.skill_rows = [
            _skill("Работать с исторической картой", 30),
            _skill("Анализировать исторический источник", 28),
        ]
        report = build_expert_analysis(hist, protocol=None)
        blob = " ".join(report.overview + report.problems + report.patterns_analysis + report.causes_analysis)
        self.assertTrue(
            any(x in blob.lower() for x in ("карт", "простран", "источник", "историческ"))
        )

    def test_normalize_and_competences(self):
        self.assertEqual(normalize_subject("Английский язык"), "английский язык")
        names = " ".join(c.name for c in competences_for_subject("Математика"))
        self.assertIn("вычислительная", names)
        lit = " ".join(c.name for c in competences_for_subject("Литературное чтение"))
        self.assertIn("авторской", lit)
