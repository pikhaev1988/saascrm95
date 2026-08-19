"""
Аналитическая справка ВПР по методологии ФИОКО
(«Рекомендации по проведению анализа результатов ВПР на уровне ОО»).

Только формирование текста и структуры справки.
Движки, модели, расчёты и API не изменяются.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass, field
from typing import Any

from apps.vpr.conclusion.rules import classify_mastery, classify_skew
from apps.vpr.expert_analysis import build_expert_analysis
from apps.vpr.services.catalog_lookup import lookup_task_catalog

PLACEHOLDER_TOPICS = frozenset({"", "Без темы в справочнике"})
PLACEHOLDER_SKILLS = frozenset({"", "Без умения в справочнике"})


# ---------------------------------------------------------------------------
# DTO
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class KpiItem:
    label: str
    value: str
    tone: str = "neutral"
    hint: str = ""


@dataclass(slots=True)
class AnalyticCycle:
    """Обязательный цикл ФИОКО после статистических показателей."""

    interpretation: list[str] = field(default_factory=list)
    causes: list[str] = field(default_factory=list)
    org_decisions: list[str] = field(default_factory=list)
    method_decisions: list[str] = field(default_factory=list)
    expected_effect: list[str] = field(default_factory=list)


@dataclass(slots=True)
class MarkRow:
    mark: str
    count: int
    percent: float


@dataclass(slots=True)
class ScoreRow:
    score: str
    count: int
    percent: float


@dataclass(slots=True)
class TaskPerformanceRow:
    """Количество детей, решивших задание правильно / неправильно / частично."""

    task_code: str
    topic: str = ""
    skill: str = ""
    completion_percent: float | None = None
    correct_count: int = 0
    incorrect_count: int = 0
    partial_count: int = 0
    answers_count: int = 0
    priority: str = ""
    priority_label: str = ""


@dataclass(slots=True)
class GroupInsight:
    key: str
    title: str
    count: int
    percent: float
    characteristic: str
    actions: list[str] = field(default_factory=list)
    tone: str = "neutral"
    sample_names: list[str] = field(default_factory=list)


@dataclass(slots=True)
class PlannedResultRow:
    result: str
    status: str
    status_label: str
    average_percent: float | None
    tasks_count: int
    explanation: str
    subject_actions: str = ""
    meta_actions: str = ""
    content_adjustments: str = ""
    tone: str = "neutral"


@dataclass(slots=True)
class GroupTaskInsight:
    title: str
    explanation: str
    evidence: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ContentLineInsight:
    name: str
    mastery_level: str
    mastery_label: str
    average_percent: float | None
    typical_errors: list[str] = field(default_factory=list)
    probable_causes: list[str] = field(default_factory=list)
    method_changes: list[str] = field(default_factory=list)
    tone: str = "neutral"


@dataclass(slots=True)
class DeficitInsight:
    name: str
    kind: str
    priority: str
    average_percent: float | None
    impact_results: str
    impact_quality: str
    impact_program: str
    management_decisions: list[str] = field(default_factory=list)
    tone: str = "neutral"


@dataclass(slots=True)
class IomBlock:
    group: str
    focus: str
    actions: list[str] = field(default_factory=list)


@dataclass(slots=True)
class PlanRow:
    action: str
    executor: str
    deadline: str
    expected_result: str
    efficiency_indicator: str


@dataclass(slots=True)
class SubjectReport:
    """Справка ВПР — 16 разделов по алгоритму анализа ФИОКО."""

    subject: str = ""
    parallel: int | None = None
    academic_year: int | None = None
    school_name: str = ""
    quality_level: str = ""
    quality_tone: str = "neutral"

    # 1. Паспорт анализа
    passport: list[KpiItem] = field(default_factory=list)
    passport_assessment: list[str] = field(default_factory=list)

    # 2. Индивидуальные результаты
    individual_groups: list[GroupInsight] = field(default_factory=list)
    individual_cycle: AnalyticCycle = field(default_factory=AnalyticCycle)
    iom_blocks: list[IomBlock] = field(default_factory=list)
    gifted_actions: list[str] = field(default_factory=list)
    parent_support_actions: list[str] = field(default_factory=list)
    attendance_control: list[str] = field(default_factory=list)

    # 3. Статистика отметок
    marks_rows: list[MarkRow] = field(default_factory=list)
    marks_cycle: AnalyticCycle = field(default_factory=AnalyticCycle)

    # 4. Объективность (ВПР ↔ журнал)
    objectivity_rows: list[dict[str, str]] = field(default_factory=list)
    objectivity_risk: str = ""
    objectivity_cycle: AnalyticCycle = field(default_factory=AnalyticCycle)

    # 5. Первичные баллы
    scores_rows: list[ScoreRow] = field(default_factory=list)
    scores_cycle: AnalyticCycle = field(default_factory=AnalyticCycle)

    # 6. Выполнение заданий → темы → линии
    content_pipeline: list[str] = field(default_factory=list)
    task_performance_rows: list[TaskPerformanceRow] = field(default_factory=list)
    content_lines: list[ContentLineInsight] = field(default_factory=list)
    content_cycle: AnalyticCycle = field(default_factory=AnalyticCycle)

    # 7. Планируемые результаты
    planned_results: list[PlannedResultRow] = field(default_factory=list)
    planned_cycle: AnalyticCycle = field(default_factory=AnalyticCycle)

    # 8. Группы участников
    group_task_insights: list[GroupTaskInsight] = field(default_factory=list)
    group_task_cycle: AnalyticCycle = field(default_factory=AnalyticCycle)

    # 9. Образовательные дефициты
    deficit_items: list[DeficitInsight] = field(default_factory=list)
    deficits_cycle: AnalyticCycle = field(default_factory=AnalyticCycle)

    # 10. Работа администрации
    admin_director: list[str] = field(default_factory=list)
    admin_deputy: list[str] = field(default_factory=list)
    admin_cycle: AnalyticCycle = field(default_factory=AnalyticCycle)

    # 11. Школьные МО
    smo_actions: list[str] = field(default_factory=list)
    smo_cycle: AnalyticCycle = field(default_factory=AnalyticCycle)

    # 12. Работа с педагогами
    teacher_deficits: list[str] = field(default_factory=list)
    teacher_actions: list[str] = field(default_factory=list)
    teachers_cycle: AnalyticCycle = field(default_factory=AnalyticCycle)

    # 13. Работа с родителями
    parent_actions: list[str] = field(default_factory=list)
    parents_cycle: AnalyticCycle = field(default_factory=AnalyticCycle)

    # 14. Методические рекомендации
    method_recommendations: list[str] = field(default_factory=list)
    method_cycle: AnalyticCycle = field(default_factory=AnalyticCycle)

    # 15. План мероприятий
    action_plan: list[PlanRow] = field(default_factory=list)

    # 16. Итоговое заключение
    final_conclusion: list[str] = field(default_factory=list)

    # Совместимость со старыми обращениями / тестами
    @property
    def individual_analysis(self) -> list[str]:
        return self.individual_cycle.interpretation

    @property
    def individual_actions(self) -> list[str]:
        return self.individual_cycle.org_decisions + self.individual_cycle.method_decisions

    @property
    def marks_analysis(self) -> list[str]:
        return self.marks_cycle.interpretation

    @property
    def marks_actions(self) -> list[str]:
        return self.marks_cycle.org_decisions

    @property
    def objectivity_analysis(self) -> list[str]:
        return self.objectivity_cycle.interpretation

    @property
    def objectivity_actions(self) -> list[str]:
        return self.objectivity_cycle.org_decisions

    @property
    def scores_analysis(self) -> list[str]:
        return self.scores_cycle.interpretation

    @property
    def deficits_summary(self) -> list[str]:
        return [d.impact_results for d in self.deficit_items[:5]] or self.deficits_cycle.interpretation

    @property
    def planned_analysis(self) -> list[str]:
        return self.planned_cycle.interpretation

    @property
    def group_task_analysis(self) -> list[str]:
        return self.group_task_cycle.interpretation

    @property
    def expert_interpretation(self) -> list[str]:
        return self.deficits_cycle.interpretation or self.content_cycle.interpretation

    @property
    def cause_chains(self) -> list[dict[str, Any]]:
        return [{"summary": c, "steps": []} for c in self.deficits_cycle.causes[:5]]

    @property
    def management_by_role(self) -> list[Any]:
        from types import SimpleNamespace

        return [
            SimpleNamespace(role="Директор", actions=self.admin_director),
            SimpleNamespace(role="Заместитель директора", actions=self.admin_deputy),
            SimpleNamespace(role="Школьное методическое объединение", actions=self.smo_actions),
            SimpleNamespace(role="Педагоги", actions=self.teacher_actions),
            SimpleNamespace(role="Родители", actions=self.parent_actions),
        ]

    @property
    def methodical_actions(self) -> list[str]:
        return self.method_recommendations

    @property
    def strengths(self) -> list[str]:
        return [g.characteristic for g in self.individual_groups if g.key == "high"] or self.passport_assessment[:3]

    @property
    def problems(self) -> list[str]:
        return [d.impact_results for d in self.deficit_items[:5]] or self.deficits_cycle.causes[:5]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fmt(value: Any, suffix: str = "") -> str | None:
    if value is None or value == "":
        return None
    if isinstance(value, float):
        text = f"{value:.2f}".rstrip("0").rstrip(".")
        return f"{text}{suffix}"
    return f"{value}{suffix}"


def _tone(band: str | None) -> str:
    return {
        "high": "success",
        "sufficient": "success",
        "acceptable": "warn",
        "problem": "danger",
        "critical": "danger",
        "achieved": "success",
        "partial": "warn",
        "not_achieved": "danger",
    }.get(band or "", "neutral")


def _prep_index(summary) -> float | None:
    if summary is None:
        return None
    parts: list[float] = []
    for value in (
        summary.knowledge_quality_percent,
        summary.absolute_achievement_percent,
        getattr(summary, "sou_percent", None),
    ):
        if value is not None:
            parts.append(float(value))
    if summary.avg_mark_vpr is not None:
        parts.append(float(summary.avg_mark_vpr) / 5.0 * 100.0)
    if summary.avg_primary_score is not None and summary.max_primary_score:
        parts.append(float(summary.avg_primary_score) / float(summary.max_primary_score) * 100.0)
    if not parts:
        return None
    return round(sum(parts) / len(parts), 1)


def _cycle(
    interpretation: list[str] | None = None,
    causes: list[str] | None = None,
    org: list[str] | None = None,
    method: list[str] | None = None,
    effect: list[str] | None = None,
) -> AnalyticCycle:
    return AnalyticCycle(
        interpretation=list(interpretation or []),
        causes=list(causes or []),
        org_decisions=list(org or []),
        method_decisions=list(method or []),
        expected_effect=list(effect or []),
    )


def _mastery_label(band: str | None) -> str:
    return {
        "high": "высокий уровень освоения",
        "sufficient": "достаточный уровень освоения",
        "acceptable": "приемлемый (частичный) уровень освоения",
        "problem": "проблемный уровень освоения",
        "critical": "критический уровень освоения",
    }.get(band or "", "уровень освоения не определён")


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------


def build_fioko_report(analysis, protocol) -> SubjectReport:
    """Собрать справку строго в последовательности 16 разделов ФИОКО."""
    summary = analysis.summary
    subject = str(analysis.subject or protocol.subject or "—")
    parallel = analysis.parallel or protocol.parallel
    year = analysis.academic_year or protocol.academic_year
    expert = build_expert_analysis(analysis, protocol)
    school_name = (
        analysis.organization_name
        or getattr(protocol, "organization_name", None)
        or getattr(getattr(protocol, "school", None), "name", None)
        or ""
    )

    avg_share = None
    if summary and summary.avg_primary_score is not None and summary.max_primary_score:
        avg_share = float(summary.avg_primary_score) / float(summary.max_primary_score) * 100.0
    prep = classify_mastery(avg_share) or classify_mastery(
        summary.knowledge_quality_percent if summary else None
    )

    report = SubjectReport(
        subject=subject,
        parallel=parallel,
        academic_year=year,
        school_name=str(school_name or ""),
        quality_level=expert.profile_label or "профиль подготовки определён по данным ВПР",
        quality_tone=_tone(prep),
    )

    report.passport, report.passport_assessment = _section1_passport(
        analysis, protocol, summary, expert, school_name
    )
    (
        report.individual_groups,
        report.individual_cycle,
        report.iom_blocks,
        report.gifted_actions,
        report.parent_support_actions,
        report.attendance_control,
    ) = _section2_individuals(analysis, expert)
    report.marks_rows, report.marks_cycle = _section3_marks(analysis, expert)
    report.objectivity_rows, report.objectivity_risk, report.objectivity_cycle = (
        _section4_objectivity(analysis)
    )
    report.scores_rows, report.scores_cycle = _section5_scores(analysis)
    (
        report.content_pipeline,
        report.task_performance_rows,
        report.content_lines,
        report.content_cycle,
    ) = _section6_content(analysis, expert)
    report.planned_results, report.planned_cycle = _section7_planned(
        analysis, subject, parallel, year
    )
    report.group_task_insights, report.group_task_cycle = _section8_group_tasks(
        analysis, protocol
    )
    report.deficit_items, report.deficits_cycle = _section9_deficits(analysis, expert)
    (
        report.admin_director,
        report.admin_deputy,
        report.admin_cycle,
    ) = _section10_admin(report, analysis)
    report.smo_actions, report.smo_cycle = _section11_smo(report, analysis)
    (
        report.teacher_deficits,
        report.teacher_actions,
        report.teachers_cycle,
    ) = _section12_teachers(report, expert, subject)
    report.parent_actions, report.parents_cycle = _section13_parents(report)
    report.method_recommendations, report.method_cycle = _section14_methodical(
        report, analysis, expert, subject
    )
    report.action_plan = _section15_plan(report)
    report.final_conclusion = _section16_final(report, expert, subject, parallel)
    return report


# ---------------------------------------------------------------------------
# Раздел 1. Паспорт анализа
# ---------------------------------------------------------------------------


def _section1_passport(analysis, protocol, summary, expert, school_name):
    exam_date = "—"
    if getattr(protocol, "exam_date", None):
        exam_date = protocol.exam_date.strftime("%d.%m.%Y")
    prep = _prep_index(summary)
    subjects = str(analysis.subject or protocol.subject or "—")
    grades = str(analysis.parallel or protocol.parallel or "—")
    participants = _fmt(getattr(summary, "participants_count", None) if summary else None) or "—"

    passport = [
        KpiItem("ОО", str(school_name or analysis.organization_name or "—")),
        KpiItem("Учебный год", str(analysis.academic_year or protocol.academic_year or "—")),
        KpiItem("Предметы", subjects),
        KpiItem("Классы", grades),
        KpiItem("Участники", participants),
        KpiItem("Протокол", str(getattr(protocol, "id", None) or getattr(protocol, "pk", "—"))),
        KpiItem("Дата проведения", exam_date),
        KpiItem("Максимальный первичный балл", _fmt(getattr(summary, "max_primary_score", None) if summary else None) or "—"),
        KpiItem("Средний первичный балл", _fmt(getattr(summary, "avg_primary_score", None) if summary else None) or "—"),
        KpiItem("Средняя отметка ВПР", _fmt(getattr(summary, "avg_mark_vpr", None) if summary else None) or "—"),
        KpiItem(
            "Средняя отметка по журналу",
            _fmt(getattr(summary, "avg_mark_journal", None) if summary else None) or "—",
        ),
        KpiItem(
            "Качество знаний (образовательные результаты «4»–«5»)",
            _fmt(getattr(summary, "knowledge_quality_percent", None) if summary else None, "%") or "—",
            tone=_tone(classify_mastery(getattr(summary, "knowledge_quality_percent", None) if summary else None)),
        ),
        KpiItem(
            "Абсолютная успеваемость",
            _fmt(getattr(summary, "absolute_achievement_percent", None) if summary else None, "%") or "—",
            tone=_tone(
                classify_mastery(getattr(summary, "absolute_achievement_percent", None) if summary else None)
            ),
        ),
        KpiItem(
            "СОУ",
            _fmt(getattr(summary, "sou_percent", None) if summary else None, "%") or "—",
            tone=_tone(classify_mastery(getattr(summary, "sou_percent", None) if summary else None)),
        ),
        KpiItem(
            "Индекс подготовки",
            _fmt(prep) or "—",
            tone=_tone(classify_mastery(prep)),
            hint="Сводный показатель качества образования по данным ВПР",
        ),
    ]

    assessment = [
        "Экспертная оценка общего состояния качества образования по результатам ВПР "
        f"для параллели {grades} класса по предмету «{subjects}»."
    ]
    if expert.profile_label:
        assessment.append(
            f"Профиль образовательных результатов: «{expert.profile_label}». "
            "Данный профиль отражает реальное состояние предметной подготовки "
            "и служит основанием для организационно-управленческих решений."
        )
    if expert.overview:
        assessment.append(expert.overview[0])
    quality = getattr(summary, "knowledge_quality_percent", None) if summary else None
    absolute = getattr(summary, "absolute_achievement_percent", None) if summary else None
    if quality is not None and absolute is not None:
        if float(quality) >= 50 and float(absolute) >= 85:
            assessment.append(
                "Качество образования в целом соответствует устойчивому уровню: "
                "предметные результаты обеспечивают выполнение базовых требований "
                "и формируют ресурс для повышения образовательных достижений."
            )
        elif float(absolute) < 70 or float(quality) < 30:
            assessment.append(
                "Качество образования требует первоочередного управленческого внимания: "
                "образовательные результаты ограничены, имеются признаки системных "
                "затруднений в освоении планируемых результатов."
            )
        else:
            assessment.append(
                "Качество образования находится на рабочем уровне: базовые образовательные "
                "результаты достигаются большей частью участников, однако устойчивость "
                "повышенного уровня и объективность оценивания требуют усиления ВСОКО."
            )
    return passport, assessment


# ---------------------------------------------------------------------------
# Раздел 2. Анализ индивидуальных результатов
# ---------------------------------------------------------------------------


def _section2_individuals(analysis, expert):
    groups_profile = getattr(analysis, "participant_groups", None)
    students = list(getattr(getattr(analysis, "analytics", None), "students", None) or [])
    by_code = {s.participant_code: s for s in students if getattr(s, "participant_code", None)}
    insights: list[GroupInsight] = []
    gmap = getattr(groups_profile, "groups", None) or {} if groups_profile else {}

    defs = [
        (
            "risk",
            "Группа риска",
            "danger",
            "Обучающиеся с низким уровнем выполнения работы; требуют индивидуального "
            "образовательного маршрута и усиленного сопровождения.",
            [
                "индивидуальный образовательный маршрут",
                "дополнительные занятия по ключевым образовательным дефицитам",
                "сопровождение классным руководителем и учителем-предметником",
            ],
        ),
        (
            "medium",
            "Группа стабильных результатов",
            "warn",
            "Обучающиеся со стабильным базовым уровнем образовательных результатов; "
            "имеют потенциал перехода к повышенному уровню.",
            [
                "закрепление базовых предметных результатов",
                "тематические консультации по дефицитным содержательным линиям",
            ],
        ),
        (
            "high",
            "Группа высокого уровня",
            "success",
            "Обучающиеся с высоким уровнем выполнения работы и устойчивыми "
            "предметными результатами.",
            [
                "олимпиадная и проектная траектория",
                "задания повышенной сложности",
                "тьюторская поддержка одноклассников",
            ],
        ),
    ]

    for key, title, tone, characteristic, actions in defs:
        bucket = gmap.get(key)
        if bucket is None:
            continue
        codes = list(getattr(bucket, "participant_codes", None) or [])
        names = []
        for code in codes[:5]:
            st = by_code.get(code)
            if st and getattr(st, "full_name", None):
                names.append(st.full_name)
        insights.append(
            GroupInsight(
                key=key,
                title=title,
                count=int(getattr(bucket, "count", 0) or 0),
                percent=float(getattr(bucket, "percent", 0) or 0),
                characteristic=characteristic,
                actions=actions,
                tone=tone,
                sample_names=names,
            )
        )

    decline = []
    potential = []
    for st in students:
        vpr = getattr(st, "mark_vpr", None)
        journal = getattr(st, "mark_journal", None)
        name = getattr(st, "full_name", None) or getattr(st, "participant_code", "")
        if vpr is not None and journal is not None and journal - vpr >= 2:
            decline.append(name)
        if vpr is not None and vpr >= 4 and (getattr(st, "completion_percent", None) or 0) >= 70:
            potential.append(name)

    if potential or any(g.key == "medium" and g.count for g in insights):
        insights.append(
            GroupInsight(
                key="potential",
                title="Обучающиеся с положительным потенциалом",
                count=len(potential) or next((g.count for g in insights if g.key == "medium"), 0),
                percent=0.0,
                characteristic=(
                    "Обучающиеся, демонстрирующие устойчивые или растущие образовательные "
                    "результаты и способные при адресной поддержке выйти на повышенный уровень."
                ),
                actions=[
                    "индивидуальные задания на применение знаний в новой ситуации",
                    "включение в проекты и взаимообучение",
                ],
                tone="success",
                sample_names=potential[:5],
            )
        )

    interpretation = [
        "Анализ индивидуальных результатов выполнен в логике рекомендаций ФИОКО: "
        "выделены группа риска, группа стабильных результатов, группа высокого уровня "
        "и обучающиеся с положительным потенциалом."
    ]
    for g in insights:
        if g.key == "potential" and g.percent == 0 and g.sample_names:
            interpretation.append(
                f"{g.title}: {', '.join(g.sample_names)}"
                f"{'…' if len(potential) > 5 else ''}. {g.characteristic}"
            )
        else:
            interpretation.append(f"{g.title}: {g.count} чел. ({g.percent}%). {g.characteristic}")
    if decline:
        interpretation.append(
            "Выявлена подгруппа с признаками риска по расхождению журнальной и внешней оценки "
            f"({', '.join(decline[:5])}{'…' if len(decline) > 5 else ''})."
        )
    if expert.profile_explanation:
        interpretation.append(expert.profile_explanation[0])

    risk_count = next((g.count for g in insights if g.key == "risk"), 0)
    causes = [
        "Неравномерность сформированности предметных и метапредметных результатов "
        "внутри параллели.",
        "Различия в индивидуальных образовательных траекториях и степени освоения "
        "планируемых результатов.",
    ]
    if risk_count:
        causes.append(
            "Наличие обучающихся группы риска указывает на недостаточную адресность "
            "текущего сопровождения и необходимость индивидуальных образовательных маршрутов."
        )
    if decline:
        causes.append(
            "Расхождение отметок ВПР и журнала у части обучающихся может отражать "
            "проблемы объективности оценивания либо снижение готовности к внешней оценке."
        )

    org = [
        "Утвердить списки обучающихся группы риска, стабильной группы, высокого уровня "
        "и группы положительного потенциала.",
        "Назначить ответственных за индивидуальное сопровождение (учитель-предметник, "
        "классный руководитель).",
        "Включить контроль реализации индивидуальных образовательных маршрутов "
        "во внутришкольный контроль.",
    ]
    method = [
        "Разработать индивидуальные образовательные маршруты для группы риска.",
        "Организовать дифференцированные консультации по образовательным дефицитам.",
        "Сформировать банк заданий для групп различного уровня подготовки.",
    ]
    effect = [
        "Снижение доли обучающихся группы риска и рост доли устойчивых образовательных "
        "результатов при повторных внутренних мониторингах.",
        "Повышение адресности методического сопровождения и вовлечённости родителей.",
    ]

    iom = [
        IomBlock(
            group="Группа риска",
            focus="Ликвидация ключевых образовательных дефицитов и достижение базового уровня "
            "предметных результатов",
            actions=[
                "диагностика недостигнутых планируемых результатов",
                "еженедельные дополнительные занятия и консультации",
                "индивидуальный трек заданий по слабым содержательным линиям",
                "мониторинг динамики раз в 2–3 недели",
                "совместное сопровождение с родителями",
            ],
        ),
        IomBlock(
            group="Группа стабильных результатов",
            focus="Закрепление базового уровня и переход к повышенным образовательным результатам",
            actions=[
                "отработка применения знаний в новой ситуации",
                "работа по частично достигнутым планируемым результатам",
                "включение в групповые проекты и взаимообучение",
            ],
        ),
        IomBlock(
            group="Группа высокого уровня / положительный потенциал",
            focus="Развитие повышенного уровня и поддержка одарённых детей",
            actions=[
                "задания повышенной сложности и нестандартные сюжеты",
                "олимпиадная и проектная траектория",
                "роль консультантов для одноклассников",
            ],
        ),
    ]
    gifted = [
        "Сформировать олимпиадную / проектную группу по предмету.",
        "Включить задания повышенного уровня в текущий контроль и внеурочную деятельность.",
        "Обеспечить методическое сопровождение работы с одарёнными детьми на уровне МО.",
    ]
    parents = [
        "Провести индивидуальные консультации с родителями обучающихся группы риска.",
        "Информировать родителей о результатах ВПР и индивидуальных образовательных маршрутах.",
        "Дать рекомендации по домашнему сопровождению освоения дефицитных тем.",
    ]
    attendance: list[str] = []
    if risk_count or decline:
        attendance = [
            "Организовать контроль посещаемости дополнительных занятий и консультаций "
            "для обучающихся группы риска.",
            "Фиксировать причины пропусков и оперативно информировать администрацию "
            "и родителей при признаках риска.",
        ]

    return insights, _cycle(interpretation, causes, org, method, effect), iom, gifted, parents, attendance


# ---------------------------------------------------------------------------
# Раздел 3. Анализ статистики отметок
# ---------------------------------------------------------------------------


def _section3_marks(analysis, expert):
    marks = getattr(getattr(analysis, "analytics", None), "marks", None)
    vpr = getattr(marks, "vpr", None) or {}
    percents = getattr(marks, "vpr_percents", None) or {}
    rows: list[MarkRow] = []
    total = sum(int(v) for v in vpr.values()) or 0
    for mark in ("5", "4", "3", "2"):
        count = int(vpr.get(mark, 0) or 0)
        pct = float(percents.get(mark, 0) or 0)
        if not pct and total:
            pct = round(100.0 * count / total, 1)
        rows.append(MarkRow(mark=mark, count=count, percent=pct))

    share2 = next((r.percent for r in rows if r.mark == "2"), 0.0)
    share45 = sum(r.percent for r in rows if r.mark in {"4", "5"})
    share3 = next((r.percent for r in rows if r.mark == "3"), 0.0)

    interpretation = [
        "Распределение отметок ВПР отражает структуру образовательных достижений "
        "и используется для управленческой оценки качества образования."
    ]
    if share45 >= 60:
        interpretation.append(
            f"Доля отметок «4» и «5» составляет {share45:.1f}% — повышенный уровень "
            "достигнут значительной частью участников; тенденция благоприятная."
        )
    elif share45 >= 40:
        interpretation.append(
            f"Доля отметок «4» и «5» ({share45:.1f}%) соответствует умеренному качеству "
            "знаний: положительный контур есть, но устойчивый рост качества не обеспечен."
        )
    else:
        interpretation.append(
            f"Доля отметок «4» и «5» ({share45:.1f}%) недостаточна: выявлены признаки "
            "ухудшения / ограничения качества образовательных результатов."
        )
    if share2 >= 15:
        interpretation.append(
            f"Доля отметок «2» ({share2:.1f}%) формирует выраженную группу риска "
            "и указывает на признаки системной проблемы подготовки."
        )
    elif share2 > 0:
        interpretation.append(
            f"Отметки «2» ({share2:.1f}%) присутствуют локально и задают зону "
            "индивидуального сопровождения."
        )
    if share3 >= 40:
        interpretation.append(
            f"Высокая доля «3» ({share3:.1f}%) свидетельствует о преобладании базового "
            "уровня без устойчивого перехода к повышенным образовательным результатам."
        )
    if expert.profile_label:
        interpretation.append(f"Структура отметок согласуется с профилем «{expert.profile_label}».")

    causes = [
        "Недостаточная отработка планируемых результатов повышенного уровня.",
        "Неравномерность освоения содержательных линий программы.",
    ]
    if share2 >= 15 or share45 < 40:
        causes.append(
            "Системные затруднения в формировании предметных результатов у части класса "
            "и/или недостаточная дифференциация обучения."
        )

    org = [
        "Рассмотреть структуру отметок на совещании при директоре / заместителе директора по УВР.",
        "Принять решения методического совета по корректировке системы оценки качества образования.",
        "Поручить школьным методическим объединениям анализ причин преобладания базового уровня.",
        "Внести предложения по корректировке ВСОКО с учётом результатов ВПР.",
    ]
    method = [
        "Скорректировать формы текущего контроля с ориентацией на критерии ВПР.",
        "Усилить дифференцированную работу с обучающимися, имеющими отметки «2» и «3».",
    ]
    effect = [
        "Рост доли отметок «4» и «5» и снижение доли неудовлетворительных результатов "
        "при внутренних мониторингах качества образования.",
        "Согласованность решений администрации, методического совета и ШМО в рамках ВСОКО.",
    ]
    return rows, _cycle(interpretation, causes, org, method, effect)


# ---------------------------------------------------------------------------
# Раздел 4. Сравнение отметок ВПР и журнала
# ---------------------------------------------------------------------------


def _section4_objectivity(analysis):
    obj = getattr(analysis, "objectivity", None)
    if obj is None or not getattr(obj, "compared_count", 0):
        return (
            [],
            "не определён",
            _cycle(
                [
                    "Сопоставление отметок ВПР и журнала ограничено: недостаточно парных данных "
                    "для устойчивого вывода об объективности оценивания."
                ],
                [
                    "Неполнота журнальных отметок либо отсутствие сопоставимых данных "
                    "по части участников."
                ],
                [
                    "Обеспечить полноту журнальных отметок для последующего анализа объективности.",
                    "Включить проверку соответствия текущего оценивания и внешней оценки в план ВСОКО.",
                ],
                [
                    "Провести методический семинар по критериальному оцениванию.",
                ],
                [
                    "Повышение готовности школы к анализу объективности оценивания "
                    "на следующих процедурах ВПР.",
                ],
            ),
        )

    cmp_ = obj.journal_comparison or {}
    pct = obj.journal_comparison_percents or {}
    rows = [
        {"label": "Совпадение отметок", "value": f"{cmp_.get('equal', 0)} ({pct.get('equal', 0)}%)"},
        {"label": "Завышение (ВПР ниже журнала)", "value": f"{cmp_.get('lower', 0)} ({pct.get('lower', 0)}%)"},
        {"label": "Занижение (ВПР выше журнала)", "value": f"{cmp_.get('higher', 0)} ({pct.get('higher', 0)}%)"},
        {"label": "Сравнено пар отметок", "value": str(obj.compared_count)},
    ]
    risk_map = {"low": "низкий", "medium": "средний", "high": "высокий"}
    risk = risk_map.get(obj.risk_level, obj.risk_level or "не определён")
    lower_pct = float(pct.get("lower", 0) or 0)
    higher_pct = float(pct.get("higher", 0) or 0)
    equal_pct = float(pct.get("equal", 0) or 0)

    interpretation = [
        f"Сопоставление отметок ВПР и журнала выполнено по {obj.compared_count} обучающимся. "
        f"Степень объективности оценивания: риск необъективности — {risk}."
    ]
    if equal_pct >= 60:
        interpretation.append(
            f"Совпадение отметок ({equal_pct:.1f}%) преобладает — внутренняя оценка "
            "в целом согласована с внешней, что поддерживает стабильность ВСОКО."
        )
    if lower_pct >= 20:
        interpretation.append(
            f"В {lower_pct:.1f}% случаев выявлено завышение текущих отметок "
            "(отметка ВПР ниже журнальной)."
        )
    if higher_pct >= 20:
        interpretation.append(
            f"В {higher_pct:.1f}% случаев выявлено занижение текущих отметок "
            "(отметка ВПР выше журнальной)."
        )
    if obj.risk_level == "high":
        interpretation.append(
            "Высокий риск необъективности требует реакции в логике ФИОКО: "
            "корректировка локальных актов, внутренняя экспертиза и методические мероприятия."
        )

    causes = []
    if lower_pct >= 20:
        causes.append(
            "Возможное завышение текущих отметок либо недостаточная готовность обучающихся "
            "к внешней оценке."
        )
    if higher_pct >= 20:
        causes.append(
            "Возможное занижение текущих отметок или нестабильность внутреннего контроля."
        )
    if not causes:
        causes.append(
            "Расхождения носят локальный характер; системных признаков необъективности "
            "не выявлено либо они выражены слабо."
        )

    org = [
        "Скорректировать локальные акты по оцениванию с учётом расхождений ВПР и журнала.",
        "Провести внутреннюю экспертизу объективности отметок по предмету.",
        "Организовать перекрёстную проверку работ и взаимопроверку педагогов.",
        "Включить мероприятия по повышению объективности оценивания в план ВСОКО.",
    ]
    method = [
        "Провести методические семинары по критериальному оцениванию.",
        "Обеспечить обучение экспертов / педагогов по объективному оцениванию.",
        "Сформировать банк эталонных работ и критериев оценивания.",
    ]
    effect = [
        "Снижение доли расхождений отметок ВПР и журнала при последующих процедурах.",
        "Повышение доверия к внутренней системе оценивания и устойчивости ВСОКО.",
    ]
    return rows, risk, _cycle(interpretation, causes, org, method, effect)


# ---------------------------------------------------------------------------
# Раздел 5. Распределение первичных баллов
# ---------------------------------------------------------------------------


def _section5_scores(analysis):
    scores = getattr(getattr(analysis, "analytics", None), "scores", None)
    counts = getattr(scores, "counts", None) or {}
    percents = getattr(scores, "percents", None) or {}
    rows: list[ScoreRow] = []
    items = []
    for key in sorted(counts.keys(), key=lambda x: int(x) if str(x).isdigit() else 0):
        c = int(counts.get(key, 0) or 0)
        p = float(percents.get(key, 0) or 0)
        rows.append(ScoreRow(score=str(key), count=c, percent=p))
        items.append((int(key) if str(key).isdigit() else 0, c, p))

    summary = analysis.summary
    interpretation = [
        "Распределение первичных баллов анализируется на предмет аномалий, разрывов, "
        "концентрации у границ отметок и возможных признаков необъективности процедуры ВПР."
    ]
    causes: list[str] = []
    if not items:
        interpretation.append("Данных распределения первичных баллов недостаточно.")
        return rows, _cycle(
            interpretation,
            ["Недостаточно данных для устойчивого анализа распределения."],
            ["Обеспечить полноту фиксации первичных баллов в протоколах."],
            ["Повторить анализ после уточнения данных."],
            ["Корректность последующего анализа объективности процедуры ВПР."],
        )

    peak = max(items, key=lambda x: x[1])
    interpretation.append(
        f"Наиболее выраженный пик — первичный балл {peak[0]} ({peak[1]} чел., {peak[2]:.1f}%)."
    )
    present = [s for s, c, _ in items if c > 0]
    if len(present) >= 2:
        gaps = [(a, b) for a, b in zip(present, present[1:]) if b - a >= 3]
        if gaps:
            interpretation.append(
                "Обнаружены разрывы в распределении "
                f"({', '.join(f'{a}…{b}' for a, b in gaps[:3])})."
            )
            causes.append(
                "Разрывы могут отражать неоднородность подготовки либо особенности "
                "шкалы перевода баллов в отметки."
            )

    skew = classify_skew(
        summary.avg_primary_score if summary else None,
        summary.median_primary_score if summary else None,
    )
    if skew == "low_tail":
        interpretation.append(
            "Распределение смещено к более низким баллам: нижний полюс усиливает "
            "неоднородность образовательных результатов."
        )
        causes.append("Концентрация результатов в нижней части шкалы указывает на массовые затруднения.")
    elif skew == "high_tail":
        interpretation.append(
            "Распределение смещено к более высоким баллам; анализ группы риска сохраняет актуальность."
        )

    cv = getattr(summary, "cv_primary_score_percent", None) if summary else None
    if cv is not None and float(cv) >= 30:
        interpretation.append(
            f"Высокая неравномерность подготовки (CV {cv}%) усиливает управленческий риск "
            "двухполюсной структуры класса."
        )
        causes.append("Выраженная дифференциация образовательных результатов внутри параллели.")

    anomaly_flag = False
    if peak[2] >= 25 and summary and summary.max_primary_score:
        if peak[0] >= 0.85 * float(summary.max_primary_score):
            interpretation.append(
                "Выраженный пик у высоких первичных баллов требует сопоставления "
                "с заданиями повышенной сложности и журнальными отметками: "
                "при расхождении возможен признак необъективности."
            )
            causes.append("Возможные признаки необъективности процедуры либо аномальной концентрации баллов.")
            anomaly_flag = True

    if not causes:
        causes.append(
            "Структура распределения в целом соответствует неоднородности подготовки класса."
        )

    org = [
        "Обеспечить объективность процедуры проведения и проверки ВПР.",
        "При выявлении аномалий инициировать внутреннюю экспертизу результатов.",
    ]
    if anomaly_flag:
        org.append("Провести перекрёстную проверку работ с пиковыми первичными баллами.")
    method = [
        "Обсудить на МО шкалу перевода баллов и типичные ошибки при проверке.",
        "Усилить подготовку экспертов / проверяющих по критериям оценивания.",
    ]
    effect = [
        "Снижение аномалий распределения и повышение доверия к результатам ВПР.",
        "Укрепление объективности оценивания в рамках ВСОКО.",
    ]
    return rows, _cycle(interpretation, causes, org, method, effect)


# ---------------------------------------------------------------------------
# Раздел 6. Анализ выполнения заданий
# ---------------------------------------------------------------------------


def _section6_content(analysis, expert):
    pipeline = [
        "Согласно методологии ФИОКО анализ содержания идёт последовательно: "
        "задания → темы → содержательные линии → образовательные дефициты.",
    ]
    if expert.tasks_analysis:
        pipeline.append("1. Анализ выполнения заданий. " + expert.tasks_analysis[0])
        if len(expert.tasks_analysis) > 1:
            pipeline.append(expert.tasks_analysis[1])
    if expert.topics_analysis:
        pipeline.append("2. Объединение заданий в темы. " + expert.topics_analysis[0])
    if expert.structure_analysis:
        pipeline.append(
            "3. Объединение тем в содержательные линии. " + expert.structure_analysis[0]
        )
    if expert.patterns_analysis:
        pipeline.append(expert.patterns_analysis[0])

    task_performance_rows: list[TaskPerformanceRow] = []
    for row in analysis.task_rows or []:
        code = str(row.get("task_code") or "").strip()
        if not code:
            continue
        correct = int(row.get("correct_count") or row.get("full_count") or 0)
        answers = int(row.get("answers_count") or row.get("total") or 0)
        incorrect = int(row.get("incorrect_count") if row.get("incorrect_count") is not None else max(0, answers - correct))
        if "minus" in row and row.get("minus") is not None:
            incorrect = int(row.get("minus") or 0)
        partial = int(row.get("partial_count") or 0)
        pct = row.get("success_rate")
        if pct is None:
            pct = row.get("completion_percent")
        if pct is None and answers:
            pct = round(100.0 * correct / answers, 1)
        task_performance_rows.append(
            TaskPerformanceRow(
                task_code=code,
                topic=(row.get("topic") or "").strip(),
                skill=(row.get("checked_skill") or "").strip(),
                completion_percent=round(float(pct), 1) if pct is not None else None,
                correct_count=correct,
                incorrect_count=incorrect,
                partial_count=partial,
                answers_count=answers,
                priority=str(row.get("priority") or ""),
                priority_label=str(row.get("priority_label") or row.get("priority") or ""),
            )
        )
    task_performance_rows.sort(key=lambda item: (item.task_code.zfill(4), item.task_code))

    if task_performance_rows:
        total_correct = sum(r.correct_count for r in task_performance_rows)
        total_incorrect = sum(r.incorrect_count for r in task_performance_rows)
        pipeline.append(
            "По протоколу зафиксировано выполнение заданий участниками: "
            f"верно (полный балл) — {total_correct} ответов, "
            f"ошибок — {total_incorrect} ответов "
            f"по {len(task_performance_rows)} заданиям."
        )

    lines: list[ContentLineInsight] = []
    topic_rows = list(analysis.topic_rows or [])
    for row in topic_rows[:12]:
        topic = (getattr(row, "topic", None) or "").strip()
        if not topic or topic in PLACEHOLDER_TOPICS:
            continue
        pct = getattr(row, "avg_completion_percent", None)
        band = classify_mastery(float(pct) if pct is not None else None)
        problem = int(getattr(row, "problem_tasks_count", 0) or 0)
        critical = int(getattr(row, "critical_tasks_count", 0) or 0)
        typical = []
        if critical:
            typical.append(f"критические задания: {critical}")
        if problem:
            typical.append(f"проблемные задания: {problem}")
        if not typical:
            typical.append("типичные ошибки определяются по заданиям с низким выполнением")
        causes = []
        if band in {"problem", "critical"}:
            causes.append("Недостаточная отработка темы в текущем контроле и на уроках.")
            causes.append("Слабая сформированность связанных предметных действий.")
        elif band == "acceptable":
            causes.append("Нестабильное применение знаний в новой ситуации.")
        else:
            causes.append("Содержательная линия освоена на достаточном уровне.")
        methods = []
        if band in {"problem", "critical", "acceptable"}:
            methods.append("Изменить методику: усилить практику решения типовых и вариативных заданий.")
            methods.append("Включить элементы темы в систематический текущий контроль.")
        else:
            methods.append("Сохранить успешные приёмы и использовать линию как опору для переноса.")
        lines.append(
            ContentLineInsight(
                name=topic,
                mastery_level=band or "unknown",
                mastery_label=_mastery_label(band),
                average_percent=round(float(pct), 1) if pct is not None else None,
                typical_errors=typical,
                probable_causes=causes,
                method_changes=methods,
                tone=_tone(band),
            )
        )

    weak = [ln for ln in lines if ln.mastery_level in {"problem", "critical"}]
    interpretation = list(pipeline[:1])
    if task_performance_rows:
        weak_tasks = [
            r
            for r in task_performance_rows
            if r.completion_percent is not None and float(r.completion_percent) < 50
        ]
        interpretation.append(
            f"По заданиям протокола: {len(task_performance_rows)} заданий; "
            f"с успешностью ниже 50%: {len(weak_tasks)}."
        )
    if lines:
        interpretation.append(
            f"Выделено содержательных линий (тем) для анализа: {len(lines)}; "
            f"с проблемным / критическим уровнем освоения: {len(weak)}."
        )
    if expert.topics_analysis:
        interpretation.append(expert.topics_analysis[0])

    causes = [
        "Образовательные дефициты формируются на стыке слабых тем и недостаточно "
        "сформированных предметных действий.",
        "Низкая доля полных правильных ответов по отдельным заданиям отражает "
        "локальные и массовые дефициты предметных умений.",
    ]
    if expert.causes_analysis:
        causes.append(expert.causes_analysis[0])
    if weak:
        causes.append(
            "Наибольшее влияние оказывают линии: " + "; ".join(ln.name[:60] for ln in weak[:4]) + "."
        )

    org = [
        "Зафиксировать перечень приоритетных содержательных линий в плане устранения дефицитов.",
        "Включить контроль освоения дефицитных линий во внутришкольный контроль.",
        "Зафиксировать в плане ВСОКО задания с наибольшим числом неверных ответов.",
    ]
    method = [
        "Скорректировать методику преподавания по линиям с низким уровнем освоения.",
        "Объединить задания в тематические блоки для целенаправленной отработки.",
        "Провести разбор типичных ошибок по заданиям с максимальным числом неверных ответов.",
    ]
    effect = [
        "Повышение уровня освоения проблемных содержательных линий и снижение "
        "масштаба образовательных дефицитов.",
        "Рост доли обучающихся, выполняющих задания на полный балл.",
    ]
    return pipeline, task_performance_rows, lines, _cycle(interpretation, causes, org, method, effect)


# ---------------------------------------------------------------------------
# Раздел 7. Планируемые результаты
# ---------------------------------------------------------------------------


def _section7_planned(analysis, subject, parallel, year):
    rows_out: list[PlannedResultRow] = []
    buckets: dict[str, list[float]] = defaultdict(list)
    for row in analysis.task_rows or []:
        code = row.get("task_code")
        pct = row.get("completion_percent")
        if code is None or pct is None:
            continue
        try:
            if parallel is None or year is None:
                info = None
            else:
                info = lookup_task_catalog(
                    subject=subject,
                    parallel=int(parallel),
                    academic_year=int(year),
                    task_code=str(code),
                )
        except Exception:
            info = None
        fgos = ""
        if info is not None:
            fgos = (getattr(info, "fgos_result", None) or "").strip()
        if not fgos:
            fgos = (row.get("checked_skill") or row.get("topic") or "").strip()
        if not fgos or fgos in PLACEHOLDER_SKILLS | PLACEHOLDER_TOPICS:
            continue
        buckets[fgos].append(float(pct))

    for result, values in buckets.items():
        avg = sum(values) / len(values)
        band = classify_mastery(avg)
        if band in {"high", "sufficient"}:
            status, label = "achieved", "достигнут"
            expl = (
                "Планируемый результат в целом достигнут: знания, умения и способы "
                "действий проявляются устойчиво."
            )
            subject_act = "Закрепить сформированные предметные действия на материале повышенной сложности."
            meta_act = "Использовать результат как опору для развития регулятивных и познавательных УУД."
            content = "Сохранить акцент в рабочей программе; расширить вариативные задания."
        elif band == "acceptable":
            status, label = "partial", "частично достигнут"
            expl = (
                "Планируемый результат достигнут частично: способы действий "
                "применяются нестабильно."
            )
            subject_act = "Доформировать предметные действия через систему тренировочных и диагностических заданий."
            meta_act = "Развить УУД: планирование решения, самоконтроль, перенос способа действия."
            content = "Скорректировать элементы содержания в КТП и усилить текущий контроль."
        else:
            status, label = "not_achieved", "не достигнут"
            expl = (
                "Планируемый результат не достигнут: не сформированы ключевые "
                "знания, умения и способы действий."
            )
            subject_act = "Сфокусировать обучение на не сформированных предметных действиях."
            meta_act = "Целенаправленно развивать базовые познавательные и регулятивные УУД."
            content = "Внести изменения в рабочую программу, КТП и систему контроля."
        rows_out.append(
            PlannedResultRow(
                result=result,
                status=status,
                status_label=label,
                average_percent=round(avg, 1),
                tasks_count=len(values),
                explanation=expl,
                subject_actions=subject_act,
                meta_actions=meta_act,
                content_adjustments=content,
                tone=_tone(status),
            )
        )

    order = {"not_achieved": 0, "partial": 1, "achieved": 2}
    rows_out.sort(key=lambda r: (order.get(r.status, 9), r.average_percent or 0))
    rows_out = rows_out[:20]

    not_ok = [r for r in rows_out if r.status == "not_achieved"]
    partial = [r for r in rows_out if r.status == "partial"]
    ok = [r for r in rows_out if r.status == "achieved"]

    interpretation = [
        "Ключевой раздел анализа ФИОКО — достижение планируемых результатов. "
        "Каждый результат оценивается как достигнутый, частично достигнутый или не достигнутый."
    ]
    if not_ok:
        interpretation.append(
            "Не достигнуты планируемые результаты, связанные с: "
            + "; ".join(r.result[:80] for r in not_ok[:4])
            + "."
        )
    if partial:
        interpretation.append(
            "Частично достигнуты: " + "; ".join(r.result[:80] for r in partial[:4]) + "."
        )
    if ok:
        interpretation.append(
            "Достигнуты и могут служить опорой: " + "; ".join(r.result[:80] for r in ok[:3]) + "."
        )
    if not rows_out:
        interpretation.append(
            "Сопоставление с формулировками планируемых результатов каталога ограничено."
        )

    causes = [
        "Недостаточная согласованность рабочей программы, КТП и системы текущего контроля "
        "с планируемыми результатами, проверяемыми ВПР.",
    ]
    if not_ok:
        causes.append(
            "Не сформированы отдельные предметные действия и связанные с ними "
            "универсальные учебные действия."
        )

    org = [
        "Утвердить изменения рабочих программ по итогам анализа планируемых результатов.",
        "Скорректировать календарно-тематическое планирование.",
        "Изменить систему контроля с включением заданий формата ВПР.",
    ]
    method = [
        "Сфокусировать уроки на недостигнутых и частично достигнутых планируемых результатах.",
        "Встроить развитие УУД в предметную деятельность.",
    ]
    effect = [
        "Рост доли достигнутых планируемых результатов при внутренних диагностиках.",
        "Согласованность рабочих программ, КТП и системы контроля с требованиями ФГОС и ВПР.",
    ]
    return rows_out, _cycle(interpretation, causes, org, method, effect)


# ---------------------------------------------------------------------------
# Раздел 8. Группы участников
# ---------------------------------------------------------------------------


def _section8_group_tasks(analysis, protocol):
    insights: list[GroupTaskInsight] = []
    groups_profile = getattr(analysis, "participant_groups", None)
    gmap = getattr(groups_profile, "groups", None) or {} if groups_profile else {}
    code_to_group = {}
    for key in ("high", "medium", "risk"):
        bucket = gmap.get(key)
        if not bucket:
            continue
        for code in getattr(bucket, "participant_codes", None) or []:
            code_to_group[code] = key

    task_group_vals: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    task_meta: dict[str, str] = {}
    try:
        qs = protocol.student_results.prefetch_related("task_scores__task").all()
        for student in qs:
            g = code_to_group.get(student.participant_code)
            if not g:
                continue
            for ts in student.task_scores.all():
                task = ts.task
                if task is None or not task.max_score:
                    continue
                code = str(task.code or task.number or task.pk)
                pct = 100.0 * float(ts.score or 0) / float(task.max_score)
                task_group_vals[code][g].append(pct)
                task_meta.setdefault(code, f"задание {code}")
    except Exception:
        task_group_vals = {}

    accessible = []
    barrier = []
    differentiates = []
    systemic = []

    if task_group_vals:
        for code, gvals in task_group_vals.items():
            avgs = {g: (sum(v) / len(v) if v else None) for g, v in gvals.items()}
            present = [a for a in avgs.values() if a is not None]
            if not present:
                continue
            if all(a >= 70 for a in present):
                accessible.append(code)
            if all(a < 50 for a in present):
                systemic.append(code)
                barrier.append(code)
            high_avg = avgs.get("high")
            risk_avg = avgs.get("risk")
            med_avg = avgs.get("medium")
            if high_avg is not None and risk_avg is not None and high_avg - risk_avg >= 25:
                differentiates.append((code, high_avg, risk_avg))
            if med_avg is not None and risk_avg is not None and med_avg - risk_avg >= 20:
                if code not in barrier:
                    barrier.append(code)

    if not task_group_vals:
        weak = [
            r
            for r in (analysis.task_rows or [])
            if r.get("completion_percent") is not None and float(r["completion_percent"]) < 50
        ]
        if weak:
            insights.append(
                GroupTaskInsight(
                    title="Задания, вызывающие массовые затруднения",
                    explanation=(
                        "Ряд заданий выполняется слабо большинством обучающихся — "
                        "системная проблема подготовки."
                    ),
                    evidence=[f"№{r.get('task_code')}" for r in weak[:5]],
                )
            )
    else:
        if accessible:
            insights.append(
                GroupTaskInsight(
                    title="Задания, доступные всем группам",
                    explanation="Высокое выполнение во всех группах — опорные элементы содержания.",
                    evidence=[task_meta.get(c, c) for c in accessible[:6]],
                )
            )
        if barrier or systemic:
            insights.append(
                GroupTaskInsight(
                    title="Барьерные задания / массовые затруднения",
                    explanation=(
                        "Низкое выполнение у слабых и/или у всех групп указывает на "
                        "барьерные элементы содержания."
                    ),
                    evidence=[task_meta.get(c, c) for c in (systemic or barrier)[:6]],
                )
            )
        if differentiates:
            differentiates.sort(key=lambda x: x[1] - x[2], reverse=True)
            insights.append(
                GroupTaskInsight(
                    title="Задания, отличающие сильных обучающихся",
                    explanation=(
                        "Наибольший разрыв между сильной группой и группой риска: "
                        "задания дифференцируют уровень подготовки."
                    ),
                    evidence=[
                        f"{task_meta.get(c, c)} (сильные {h:.0f}% / риск {r:.0f}%)"
                        for c, h, r in differentiates[:6]
                    ],
                )
            )

    interpretation = [
        "Сравнение выполнения заданий группами участников (сильные, средние, слабые / группа риска) "
        "проведено в логике ФИОКО."
    ]
    for ins in insights:
        interpretation.append(f"{ins.title}: {ins.explanation}")
    if not insights:
        interpretation.append("Выраженных контрастов между группами по заданиям не выявлено.")

    causes = [
        "Различия в уровне освоения планируемых результатов между группами участников.",
    ]
    if systemic or barrier:
        causes.append(
            "Наличие барьерных заданий отражает общие образовательные дефициты класса."
        )
    if differentiates:
        causes.append(
            "Дифференцирующие задания требуют усиления работы со средними и слабыми "
            "обучающимися по соответствующим содержательным линиям."
        )

    org = [
        "Учесть результаты группового анализа при формировании индивидуальных образовательных маршрутов.",
        "Включить барьерные задания в план внутришкольного контроля и методической работы.",
    ]
    method = [
        "Отработать барьерные задания на уроках и консультациях с дифференциацией по группам.",
        "Использовать задания, отличающие сильных, для развития повышенной подготовки.",
    ]
    effect = [
        "Сокращение разрыва между группами по барьерным заданиям и рост доступности "
        "базовых элементов содержания для группы риска.",
    ]
    return insights, _cycle(interpretation, causes, org, method, effect)


# ---------------------------------------------------------------------------
# Раздел 9. Образовательные дефициты
# ---------------------------------------------------------------------------


def _section9_deficits(analysis, expert):
    items: list[DeficitInsight] = []
    deficits = getattr(analysis, "deficits", None)
    topic_list = list(getattr(deficits, "topics", None) or analysis.topic_rows or [])
    skill_list = list(getattr(deficits, "skills", None) or analysis.skill_rows or [])

    def _add(name, kind, priority, pct, band):
        if not name or name in PLACEHOLDER_TOPICS | PLACEHOLDER_SKILLS:
            return
        if priority not in {"Critical", "High", "Medium"} and band not in {
            "problem",
            "critical",
            "acceptable",
        }:
            return
        if band in {"critical", "problem"} or priority in {"Critical", "High"}:
            impact_r = (
                f"Дефицит «{name}» существенно снижает образовательные результаты "
                "по связанным заданиям ВПР."
            )
            impact_q = "Ограничивает качество знаний и долю повышенных отметок."
            impact_p = (
                "Затрудняет дальнейшее освоение программы по связанным темам и разделам."
            )
            decisions = [
                "Включить дефицит в приоритетный перечень устранения.",
                "Назначить контроль заместителю директора и руководителю МО.",
            ]
            tone = "danger"
        else:
            impact_r = f"Дефицит «{name}» оказывает умеренное влияние на результаты ВПР."
            impact_q = "Сдерживает рост качества знаний при переходе к повышенному уровню."
            impact_p = "При отсутствии коррекции может закрепиться как устойчивый пробел."
            decisions = [
                "Учесть в тематическом планировании и текущем контроле.",
            ]
            tone = "warn"
        items.append(
            DeficitInsight(
                name=name,
                kind=kind,
                priority=str(priority or band or "—"),
                average_percent=round(float(pct), 1) if pct is not None else None,
                impact_results=impact_r,
                impact_quality=impact_q,
                impact_program=impact_p,
                management_decisions=decisions,
                tone=tone,
            )
        )

    for row in topic_list:
        name = (getattr(row, "topic", None) or "").strip()
        pct = getattr(row, "avg_completion_percent", None)
        priority = getattr(row, "priority", None) or ""
        band = classify_mastery(float(pct) if pct is not None else None)
        _add(name, "тема / содержательная линия", priority, pct, band)

    for row in skill_list:
        name = (getattr(row, "checked_skill", None) or "").strip()
        pct = getattr(row, "avg_completion_percent", None)
        priority = getattr(row, "priority", None) or ""
        band = classify_mastery(float(pct) if pct is not None else None)
        _add(name, "умение / предметное действие", priority, pct, band)

    items = items[:15]
    if not items and expert.deficits_analysis:
        for text in expert.deficits_analysis[:5]:
            items.append(
                DeficitInsight(
                    name=text[:120],
                    kind="образовательный дефицит",
                    priority="—",
                    average_percent=None,
                    impact_results=text,
                    impact_quality="Влияет на качество предметной подготовки.",
                    impact_program="Требует учёта при освоении последующих разделов программы.",
                    management_decisions=["Включить в план устранения образовательных дефицитов."],
                    tone="warn",
                )
            )

    interpretation = [
        "Система образовательных дефицитов сохранена; для каждого дефицита определены "
        "влияние на результаты, качество знаний, дальнейшее освоение программы "
        "и необходимые управленческие решения."
    ]
    if expert.deficits_analysis:
        interpretation.extend(expert.deficits_analysis[:2])
    summary = getattr(analysis, "deficit_summary", None)
    if summary is not None:
        interpretation.append(
            f"Сводка: критических заданий — {getattr(summary, 'tasks_critical', 0)}, "
            f"проблемных — {getattr(summary, 'tasks_problem', 0)}, "
            f"тем в зоне риска — {getattr(summary, 'topics_at_risk', 0)}, "
            f"обучающихся в группе риска — {getattr(summary, 'students_at_risk', 0)}."
        )

    causes = list(expert.causes_analysis[:3]) if expert.causes_analysis else [
        "Образовательные дефициты обусловлены сочетанием предметных, метапредметных "
        "и организационных факторов."
    ]
    for chain in (expert.cause_chains or [])[:2]:
        if chain.summary:
            causes.append(chain.summary)

    org = [
        "Утвердить приоритетный перечень образовательных дефицитов на уровне администрации.",
        "Включить мониторинг устранения дефицитов во внутришкольный контроль.",
    ]
    for d in items[:3]:
        org.extend(d.management_decisions[:1])

    method = [
        "Разработать методические мероприятия по каждому приоритетному дефициту.",
        "Скорректировать рабочие программы и текущий контроль.",
    ]
    effect = [
        "Снижение числа критических и проблемных дефицитов, рост качества знаний "
        "и устойчивости освоения программы.",
    ]
    return items, _cycle(interpretation, causes, org, method, effect)


# ---------------------------------------------------------------------------
# Раздел 10. Работа администрации
# ---------------------------------------------------------------------------


def _section10_admin(report: SubjectReport, analysis):
    director = [
        "Рассмотреть результаты ВПР на совещании при директоре.",
        "Скорректировать программу развития ОО с учётом выявленных образовательных дефицитов.",
        "Внести изменения в локальные акты и процедуры ВСОКО.",
        "Утвердить план мероприятий и обеспечить контроль его реализации.",
    ]
    if report.objectivity_risk == "высокий":
        director.append(
            "Инициировать комплекс мер по повышению объективности оценивания."
        )

    deputy = [
        "Организовать внутришкольный контроль по итогам ВПР.",
        "Провести анализ календарно-тематического планирования.",
        "Обеспечить контроль рабочих программ на предмет устранения дефицитов.",
        "Организовать мониторинг устранения образовательных дефицитов.",
        "Координировать работу ШМО, педагогов и классных руководителей.",
    ]

    interpretation = [
        "Организационно-управленческие решения администрации формируются на основе "
        "полного цикла анализа ФИОКО и ориентированы на повышение качества образования."
    ]
    causes = [
        "Без управленческого контура результаты анализа не переходят в устойчивые "
        "изменения образовательной деятельности.",
    ]
    if report.deficit_items:
        causes.append(
            "Наличие приоритетных образовательных дефицитов требует контроля реализации "
            "мероприятий на уровне директора и заместителя директора."
        )
    org = director + deputy[:2]
    method = [
        "Обеспечить методическое сопровождение реализации управленческих решений "
        "через ШМО и заместителя директора.",
    ]
    effect = [
        "Исполнение плана мероприятий, корректировка ВСОКО и программы развития, "
        "снижение образовательных дефицитов.",
    ]
    return director, deputy, _cycle(interpretation, causes, org, method, effect)


# ---------------------------------------------------------------------------
# Раздел 11. Работа ШМО
# ---------------------------------------------------------------------------


def _section11_smo(report: SubjectReport, analysis):
    weak_topics = [ln.name for ln in report.content_lines if ln.mastery_level in {"problem", "critical"}][:4]
    actions = [
        "Провести заседание ШМО по анализу причин результатов ВПР.",
        "Организовать открытые уроки по дефицитным содержательным линиям.",
        "Обеспечить взаимопосещение уроков с фокусом на проблемные планируемые результаты.",
        "Разработать банк заданий по барьерным и дефицитным темам.",
        "Скорректировать рабочие программы по итогам анализа.",
        "Обсудить результаты ВПР и практику критериального оценивания.",
    ]
    if weak_topics:
        actions.insert(
            1,
            "Сфокусировать методическую работу на темах: " + ", ".join(weak_topics) + ".",
        )

    interpretation = [
        "Школьные методические объединения обеспечивают методическое сопровождение "
        "устранения образовательных дефицитов и корректировку преподавания."
    ]
    causes = [
        "Дефициты и барьерные задания требуют коллективного методического разбора "
        "и обмена эталонными подходами."
    ]
    org = [
        "Включить обсуждение результатов ВПР в план работы ШМО.",
        "Назначить ответственных за банк заданий и взаимопосещение.",
    ]
    method = actions[:5]
    effect = [
        "Повышение методической согласованности педагогов и снижение дефицитов "
        "по приоритетным содержательным линиям.",
    ]
    return actions, _cycle(interpretation, causes, org, method, effect)


# ---------------------------------------------------------------------------
# Раздел 12. Работа с педагогами
# ---------------------------------------------------------------------------


def _section12_teachers(report: SubjectReport, expert, subject):
    deficits = [
        "Профессиональные дефициты в области критериального оценивания и объективности.",
        "Недостаточная отработка методики формирования планируемых результатов "
        "повышенного уровня.",
    ]
    if expert.cognitive_code in {"advanced_deficit", "advanced_gap"}:
        deficits.append(
            "Дефицит методик обучения применению знаний в новой ситуации."
        )
    if expert.cognitive_code == "basic_deficit":
        deficits.append(
            "Дефицит устойчивых приёмов отработки обязательного минимума содержания."
        )
    if report.objectivity_risk in {"высокий", "средний"}:
        deficits.append(
            "Профессиональный дефицит в обеспечении объективности текущего оценивания."
        )

    actions = [
        f"Семинар по анализу результатов ВПР («{subject}») и планируемых результатов.",
        "Мастер-класс по работе с барьерными заданиями и дифференцированным обучением.",
        "Курсы повышения квалификации / модули по критериальному оцениванию.",
        "Вебинары ФИОКО / региональные вебинары по анализу ВПР.",
        "Индивидуальные консультации заместителя директора / руководителя МО.",
        "Наставничество для педагогов с устойчивыми дефицитами в результатах класса.",
    ]

    interpretation = [
        "Профессиональные дефициты педагогов определены по итогам анализа образовательных "
        "результатов, объективности оценивания и содержательных линий."
    ]
    causes = list(deficits[:3])
    org = [
        "Утвердить план методического сопровождения педагогов по итогам ВПР.",
        "Закрепить наставнические пары при наличии устойчивых профессиональных дефицитов.",
    ]
    method = actions[:5]
    effect = [
        "Снижение профессиональных дефицитов педагогов и рост качества преподавания "
        "по приоритетным направлениям.",
    ]
    return deficits, actions, _cycle(interpretation, causes, org, method, effect)


# ---------------------------------------------------------------------------
# Раздел 13. Работа с родителями
# ---------------------------------------------------------------------------


def _section13_parents(report: SubjectReport):
    actions = list(report.parent_support_actions) or [
        "Информирование родителей о результатах ВПР и качестве образовательных результатов.",
    ]
    actions.extend(
        [
            "Провести индивидуальные консультации по сопровождению обучающихся группы риска.",
            "Организовать совместные мероприятия (родительские собрания / консультации) "
            "по итогам ВПР.",
            "Предоставить рекомендации по домашнему сопровождению освоения дефицитных тем.",
        ]
    )
    # unique preserve order
    seen = set()
    actions = [a for a in actions if not (a in seen or seen.add(a))]

    interpretation = [
        "Работа с родителями является обязательным элементом индивидуального сопровождения "
        "и повышения качества образования."
    ]
    causes = [
        "Без включения родителей сопровождение группы риска и контроль выполнения "
        "индивидуальных маршрутов недостаточно устойчивы."
    ]
    if report.attendance_control:
        causes.append(
            "Признаки риска требуют совместного контроля посещаемости и учебной дисциплины."
        )
    org = [
        "Включить работу с родителями в план мероприятий по итогам ВПР.",
        "Назначить классных руководителей ответственными за информирование и консультации.",
    ]
    method = [
        "Подготовить памятки для родителей по сопровождению освоения дефицитных тем.",
    ]
    effect = [
        "Повышение вовлечённости родителей и устойчивость индивидуальных образовательных маршрутов.",
    ]
    return actions, _cycle(interpretation, causes, org, method, effect)


# ---------------------------------------------------------------------------
# Раздел 14. Методические рекомендации
# ---------------------------------------------------------------------------


def _section14_methodical(report: SubjectReport, analysis, expert, subject):
    recs: list[str] = [
        f"По предмету «{subject}» скорректировать методику преподавания с опорой на "
        "недостигнутые планируемые результаты и образовательные дефициты."
    ]
    weak_topics = [ln.name for ln in report.content_lines if ln.mastery_level in {"problem", "critical"}]
    if weak_topics:
        recs.append("Повторить и закрепить темы: " + "; ".join(weak_topics[:5]) + ".")
    not_achieved = [r.result for r in report.planned_results if r.status == "not_achieved"]
    if not_achieved:
        recs.append(
            "Сфокусировать повторение на планируемых результатах: "
            + "; ".join(x[:70] for x in not_achieved[:3])
            + "."
        )
    recs.extend(
        [
            "Изменить формы работы: усилить практику, дифференцированные задания, "
            "разбор эталонных решений.",
            "Использовать технологии обучения: проблемное обучение, формирующее оценивание, "
            "взаимообучение.",
            "Скорректировать виды контроля: включить задания формата ВПР в текущий "
            "и тематический контроль.",
            "Включить барьерные задания в банк текущего контроля и тренировочных работ.",
        ]
    )
    if expert.cognitive_code in {"advanced_deficit", "advanced_gap"}:
        recs.append("Усилить задания на применение знаний в новой ситуации.")
    if expert.cognitive_code == "basic_deficit":
        recs.append("Отработать обязательный минимум содержания до устойчивого навыка.")
    rec_actions = list(getattr(getattr(analysis, "recommendations", None), "actions", None) or [])
    recs.extend(rec_actions[:3])

    seen = set()
    out = []
    for a in recs:
        if a and a not in seen:
            seen.add(a)
            out.append(a)

    interpretation = [
        "Методические рекомендации сформированы по каждому приоритетному направлению "
        "предметной подготовки и ориентированы на изменение практики обучения."
    ]
    causes = [
        "Сохранение прежних форм работы и контроля не обеспечивает устранение "
        "выявленных образовательных дефицитов."
    ]
    org = [
        "Утвердить перечень методических изменений на уровне ШМО и заместителя директора.",
    ]
    method = out[:8]
    effect = [
        "Повышение уровня освоения планируемых результатов и качества предметной подготовки.",
    ]
    return out[:12], _cycle(interpretation, causes, org, method, effect)


# ---------------------------------------------------------------------------
# Раздел 15. План мероприятий
# ---------------------------------------------------------------------------


def _section15_plan(report: SubjectReport) -> list[PlanRow]:
    rows: list[PlanRow] = [
        PlanRow(
            action="Рассмотрение результатов ВПР и утверждение плана мероприятий",
            executor="Директор / заместитель директора",
            deadline="В течение 10 рабочих дней",
            expected_result="Утверждённый план и ответственные",
            efficiency_indicator="Наличие приказа / протокола совещания",
        ),
        PlanRow(
            action="Корректировка ВСОКО и локальных актов по оцениванию",
            executor="Директор, заместитель директора",
            deadline="В течение месяца",
            expected_result="Обновлённые процедуры объективности оценивания",
            efficiency_indicator="Снижение риска необъективности при следующем срезе",
        ),
        PlanRow(
            action="Внутришкольный контроль рабочих программ и КТП",
            executor="Заместитель директора",
            deadline="В течение 3–4 недель",
            expected_result="Скорректированные РП и КТП",
            efficiency_indicator="Доля РП с внесёнными изменениями по дефицитам",
        ),
        PlanRow(
            action="Заседание ШМО: анализ причин, банк заданий, взаимопосещение",
            executor="Руководитель ШМО",
            deadline="В течение 2 недель",
            expected_result="План методической работы и банк заданий",
            efficiency_indicator="Количество открытых уроков / взаимопосещений",
        ),
        PlanRow(
            action="Реализация индивидуальных образовательных маршрутов группы риска",
            executor="Учитель-предметник, классный руководитель",
            deadline="В течение четверти / полугодия",
            expected_result="Динамика результатов группы риска",
            efficiency_indicator="Снижение доли обучающихся группы риска",
        ),
        PlanRow(
            action="Мероприятия для одарённых детей и группы высокого уровня",
            executor="Учитель-предметник, руководитель ШМО",
            deadline="В течение четверти",
            expected_result="Олимпиадная / проектная активность",
            efficiency_indicator="Участие и результативность в олимпиадах / проектах",
        ),
        PlanRow(
            action="Методическое сопровождение педагогов (семинары, наставничество)",
            executor="Заместитель директора, руководитель ШМО",
            deadline="В течение полугодия",
            expected_result="Снижение профессиональных дефицитов",
            efficiency_indicator="Выполнение плана ПК / семинаров",
        ),
        PlanRow(
            action="Работа с родителями: информирование и консультации",
            executor="Классный руководитель, учитель-предметник",
            deadline="В течение месяца",
            expected_result="Вовлечённость родителей в сопровождение",
            efficiency_indicator="Охват консультациями семей группы риска",
        ),
        PlanRow(
            action="Мониторинг устранения образовательных дефицитов",
            executor="Заместитель директора",
            deadline="Ежемесячно / раз в четверть",
            expected_result="Позитивная динамика по приоритетным дефицитам",
            efficiency_indicator="Рост % выполнения по дефицитным линиям",
        ),
    ]
    if report.objectivity_risk == "высокий":
        rows.insert(
            2,
            PlanRow(
                action="Внутренняя экспертиза и перекрёстная проверка объективности оценивания",
                executor="Администрация, ШМО",
                deadline="В течение 2–3 недель",
                expected_result="Снижение расхождений ВПР и журнала",
                efficiency_indicator="Доля совпадения отметок",
            ),
        )
    if report.attendance_control:
        rows.append(
            PlanRow(
                action="Контроль посещаемости дополнительных занятий группы риска",
                executor="Классный руководитель, заместитель директора",
                deadline="Еженедельно",
                expected_result="Стабильная посещаемость консультаций",
                efficiency_indicator="Доля посещённых занятий",
            )
        )
    return rows


# ---------------------------------------------------------------------------
# Раздел 16. Итоговое экспертное заключение
# ---------------------------------------------------------------------------


def _section16_final(report: SubjectReport, expert, subject, parallel) -> list[str]:
    texts = [
        (
            f"Итоговое экспертное заключение по результатам ВПР («{subject}», {parallel} класс) "
            "сформировано как аналитическая записка для принятия управленческих решений "
            "и не повторяет статистические показатели."
        ),
        f"Общий уровень качества подготовки характеризуется профилем «{report.quality_level}».",
    ]

    systemic = []
    if report.deficit_items:
        systemic.append(
            "образовательные дефициты по приоритетным содержательным линиям и умениям"
        )
    if report.objectivity_risk == "высокий":
        systemic.append("риск необъективности оценивания")
    share_risk = next((g for g in report.individual_groups if g.key == "risk"), None)
    if share_risk and share_risk.percent >= 15:
        systemic.append("значимая доля обучающихся группы риска")
    if systemic:
        texts.append("Системные проблемы: " + "; ".join(systemic) + ".")
    else:
        texts.append(
            "Системные проблемы выражены умеренно; основной фокус — закрепление качества "
            "и адресная поддержка отдельных групп обучающихся."
        )

    if report.deficits_cycle.causes:
        texts.append("Основные причины: " + report.deficits_cycle.causes[0])
    elif report.marks_cycle.causes:
        texts.append("Основные причины: " + report.marks_cycle.causes[0])

    priorities = []
    not_achieved = [r.result for r in report.planned_results if r.status == "not_achieved"]
    if not_achieved:
        priorities.append("достижение невыполненных планируемых результатов")
    if report.objectivity_risk in {"высокий", "средний"}:
        priorities.append("повышение объективности оценивания и усиление ВСОКО")
    if share_risk and share_risk.count:
        priorities.append("индивидуальные образовательные маршруты группы риска")
    if report.deficit_items:
        priorities.append("устранение приоритетных образовательных дефицитов")
    if priorities:
        texts.append(
            "Направления первоочередного вмешательства: " + "; ".join(priorities[:4]) + "."
        )

    texts.append(
        "Наиболее эффективные управленческие решения: рассмотрение результатов на уровне "
        "директора, корректировка программы развития и ВСОКО, внутришкольный контроль "
        "рабочих программ и КТП, мониторинг устранения дефицитов."
    )
    texts.append(
        "Образовательная деятельность школы должна быть скорректирована через изменение "
        "рабочих программ и календарно-тематического планирования, дифференциацию обучения, "
        "методическое сопровождение педагогов, работу с родителями и реализацию плана мероприятий."
    )
    if report.method_recommendations:
        texts.append("Методический приоритет: " + report.method_recommendations[0])
    if expert.final_conclusion:
        # берём качественные формулировки без «сырой» статистики
        for line in expert.final_conclusion:
            low = line.lower()
            if any(x in low for x in ("% ", "процент", "баллов", "отметок «")):
                continue
            texts.append(line)
            break

    seen = set()
    out = []
    for t in texts:
        if t and t not in seen:
            seen.add(t)
            out.append(t)
    return out[:14]
