"""Управленческие рекомендации (проблемно-ориентированный анализ ФИОКО)."""

from __future__ import annotations

from apps.vpr.fioko_2026.schemas import (
    FiokoGroupsAnalysis,
    FiokoJournalAnalysis,
    FiokoManagementRecommendation,
    FiokoMarksStats,
    FiokoPrimaryDistribution,
    FiokoSkillDeficit,
    FiokoTaskRow,
)


def build_management_recommendations(
    *,
    tasks: list[FiokoTaskRow],
    skill_deficits: list[FiokoSkillDeficit],
    journal: FiokoJournalAnalysis,
    distribution: FiokoPrimaryDistribution,
    marks: FiokoMarksStats,
    groups: FiokoGroupsAnalysis,
    subject: str,
    parallel: int,
) -> list[FiokoManagementRecommendation]:
    """
    РЕЗУЛЬТАТ → ДЕФИЦИТ → ВОЗМОЖНАЯ ПРИЧИНА → РЕШЕНИЕ.

    possible_causes не выдаются за доказанный факт.
    """
    out: list[FiokoManagementRecommendation] = []
    subj = subject or "предмет"
    klass = f"{parallel} класс" if parallel else "класс"

    red_tasks = [t for t in tasks if t.fioko_level_status == "insufficient"]
    if red_tasks:
        codes = ", ".join(t.task_code for t in red_tasks[:8])
        skills = sorted({t.checked_skill for t in red_tasks if t.checked_skill})
        topics = sorted({t.topic for t in red_tasks if t.topic})
        evidence = (
            f"{subj}, {klass}: задания с недостаточным уровнем выполнения "
            f"({codes}"
            + (f"; умения: {', '.join(skills[:5])}" if skills else "")
            + (f"; темы: {', '.join(topics[:5])}" if topics else "")
            + ")."
        )
        out.append(
            FiokoManagementRecommendation(
                problem=f"Недостаточный уровень выполнения отдельных заданий ВПР ({subj}, {klass})",
                evidence=evidence,
                possible_causes=[
                    "Возможные пробелы в освоении проверяемых умений (требует проверки)",
                    "Возможное несоответствие календарно-тематического планирования и проверяемых элементов",
                    "Возможные особенности контингента / условий обучения (контекстные факторы)",
                ],
                action=(
                    "Скорректировать образовательные маршруты по проблемным темам/умениям; "
                    "включить задания формата ВПР в текущий контроль; "
                    "организовать адресную методическую помощь."
                ),
                responsible="Администрация ОО / ШМО / учитель-предметник",
                deadline="в течение текущей четверти/триместра",
                control_metric="доля заданий с недостаточным уровнем выполнения (ФИОКО) по предмету/классу",
                expected_result="снижение доли заданий с недостаточным уровнем выполнения",
                audience="smo",
            )
        )
        out.append(
            FiokoManagementRecommendation(
                problem=f"Зона, требующая методического анализа по {subj} ({klass})",
                evidence=evidence,
                possible_causes=[
                    "Требуется методический разбор критериев оценивания и типичных затруднений"
                ],
                action=(
                    "Провести тематическое заседание ШМО с разбором заданий и умений; "
                    "взаимное посещение уроков с фокусом на проблемную тему."
                ),
                responsible="Руководитель ШМО / учитель-предметник",
                deadline="1–2 методических цикла",
                control_metric="динамика процента выполнения по заданиям недостаточного уровня",
                expected_result="устойчивое закрепление умений на достаточном уровне",
                audience="teacher",
            )
        )

    for sd in skill_deficits:
        if not sd.system_deficit:
            continue
        out.append(
            FiokoManagementRecommendation(
                problem=f"Системный дефицит умения: {sd.skill}",
                evidence=(
                    f"Большинство связанных заданий отмечены как недостаточный уровень выполнения "
                    f"({len(sd.red_tasks)}/{len(sd.linked_tasks)}; доля={sd.red_share}%)."
                ),
                possible_causes=[
                    "Возможный системный пробел в формировании умения (не доказанный факт)",
                    "Возможная недостаточная представленность умения в рабочих программах",
                ],
                action=(
                    "Скорректировать индивидуальные образовательные маршруты и планы "
                    "повышения квалификации педагогов в соответствии с выявленной проблемой."
                ),
                responsible="Администрация / ШМО",
                deadline="до следующей оценочной процедуры",
                control_metric=f"статус выполнения заданий умения «{sd.skill}»",
                expected_result="снижение доли заданий недостаточного уровня по умению",
                audience="admin",
            )
        )

    if journal.status == "OK" and journal.gap_ge_2_count:
        out.append(
            FiokoManagementRecommendation(
                problem="Существенные расхождения отметок ВПР и журнала (≥2 балла)",
                evidence=f"{journal.gap_ge_2_count} случаев; {journal.wording}",
                possible_causes=[
                    "Возможное завышение/занижение текущего оценивания (требует проверки)",
                    "Возможные различия в критериях текущего контроля и ВПР",
                ],
                action=(
                    "Провести анализ случаев с расхождением ≥2 балла; "
                    "тематический семинар по объективности ВСОКО; "
                    "при необходимости — перекрёстная проверка."
                ),
                responsible="Администрация ОО / ШМО",
                deadline="в течение месяца после анализа",
                control_metric="доля пар с расхождением отметок ≥2 балла",
                expected_result="снижение существенных расхождений при сохранении корректных формулировок",
                audience="admin",
            )
        )

    if distribution.possible_objectivity_marker:
        out.append(
            FiokoManagementRecommendation(
                problem="Возможный маркер нарушения объективности (пики на границах отметок)",
                evidence=distribution.wording or "Выраженные пики на границах перехода отметок.",
                possible_causes=[
                    "Возможные нарушения процедуры проведения/проверки (не доказано)",
                    "Возможное округление/корректировка первичных баллов около границ",
                ],
                action=(
                    "Дополнительно проанализировать проведение и проверку работ; "
                    "сверить с рекомендациями по переводу баллов для данного предмета/класса; "
                    "усилить меры объективности."
                ),
                responsible="Ответственный организатор ВПР / администрация",
                deadline="до следующей процедуры ВПР",
                control_metric="наличие аномальных пиков на границах отметок",
                expected_result="отсутствие выраженных аномальных пиков при повторном анализе",
                audience="admin",
            )
        )

    if marks.mark_2_dynamics_status == "negative":
        out.append(
            FiokoManagementRecommendation(
                problem="Отрицательная динамика доли отметок «2» (≥10 п.п.)",
                evidence=(
                    f"изменение доли «2»: {marks.mark_2_dynamics_pp} п.п.; "
                    f"текущий={marks.mark_2_percent}%; прошлый={marks.previous_year_mark_2_percent}%."
                ),
                possible_causes=[
                    "Возможное снижение качества подготовки (требует контекстного анализа)",
                    "Возможные изменения контингента / условий обучения",
                ],
                action=(
                    "Создать рабочую группу для выявления причин снижения результатов; "
                    "сравнить классы параллели; усилить методическую поддержку."
                ),
                responsible="Администрация ОО",
                deadline="текущий учебный период",
                control_metric="доля отметок «2» и её динамика (п.п.)",
                expected_result="снижение доли отметок «2» (положительная динамика)",
                audience="admin",
            )
        )

    if groups.anomaly_crossings:
        out.append(
            FiokoManagementRecommendation(
                problem="Аномальные пересечения выполнения заданий группами участников",
                evidence=groups.anomaly_wording
                or f"Обнаружено пересечений: {len(groups.anomaly_crossings)}.",
                possible_causes=[
                    "Ситуация требует детального изучения; автоматический вывод о причине не делается"
                ],
                action=(
                    "Провести детальный разбор аномальных заданий по группам отметок; "
                    "проверить условия объективности проведения ВПР."
                ),
                responsible="Администрация / ШМО / организатор ВПР",
                deadline="в ходе текущего анализа ВПР",
                control_metric="число аномальных пересечений групп",
                expected_result="объяснённые причины аномалий и план корректирующих мер",
                audience="admin",
            )
        )

    if marks.mark_2_percent is not None and marks.mark_2_percent >= 30:
        out.append(
            FiokoManagementRecommendation(
                problem=f"Высокая доля отметок «2» по {subj} ({klass})",
                evidence=f"доля отметок «2» = {marks.mark_2_percent}%",
                possible_causes=[
                    "Возможные индивидуальные и групповые дефициты подготовки",
                ],
                action=(
                    "Дифференциация образовательного процесса; "
                    "индивидуальные/групповые маршруты; "
                    "при необходимости — работа с родителями по пропускам (если подтверждены)."
                ),
                responsible="Классный руководитель / учитель / администрация",
                deadline="текущая четверть",
                control_metric="доля отметок «2»",
                expected_result="снижение доли неудовлетворительных отметок",
                audience="students",
            )
        )

    return out
