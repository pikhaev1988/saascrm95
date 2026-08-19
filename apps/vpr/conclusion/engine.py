"""
Движок экспертной интерпретации результатов ВПР (ФИОКО).

Вход: analytics, deficits (уже рассчитанные).
Выход: структурированное аналитическое заключение.

Формирует официальную аналитическую записку по правилам интерпретации.
Не перечисляет показатели вкладки «Обзор», не даёт рекомендаций, не использует ИИ.
"""

from __future__ import annotations

from apps.vpr.analytics.result import VprAnalyticsResult, VprTaskAnalytics
from apps.vpr.conclusion.result import VprConclusionResult, VprConclusionSection
from apps.vpr.conclusion.rules import (
    DEFICIT_SCALE_INTERPRETATION,
    MASTERY_LABELS,
    QUALITY_INTERPRETATION,
    SKEW_INTERPRETATION,
    SPREAD_INTERPRETATION,
    InterpretationContext,
    classify_deficit_scale,
    classify_mastery,
    classify_skew,
    classify_spread,
)
from apps.vpr.deficits.result import VprDeficitResult

STRONG_LEVELS = frozenset({"high", "sufficient"})
WEAK_LEVELS = frozenset({"problem", "critical"})
PROBLEM_PRIORITIES = frozenset({"Critical", "High"})
PLACEHOLDER_TOPICS = frozenset({"", "Без темы в справочнике"})
PLACEHOLDER_SKILLS = frozenset({"", "Без умения в справочнике"})


class VprConclusionEngine:
    """
    Использование::

        analytics = VprAnalyticsEngine().analyze(protocol)
        deficits = VprDeficitEngine().analyze(analytics)
        conclusion = VprConclusionEngine().build(analytics, deficits)
    """

    def build(
        self,
        analytics: VprAnalyticsResult,
        deficits: VprDeficitResult,
    ) -> VprConclusionResult:
        ctx = self._context(analytics, deficits)
        return VprConclusionResult(
            protocol_id=analytics.protocol_id,
            subject=analytics.subject,
            parallel=analytics.parallel,
            academic_year=analytics.academic_year,
            overview=self._section_overview(ctx, analytics),
            statistics=self._section_statistics(ctx),
            strengths=self._section_quality(ctx),
            weaknesses=self._section_tasks(ctx, analytics, deficits),
            topics=self._section_topics(ctx),
            skills=self._section_skills(ctx),
            deficits=self._section_deficits(ctx, deficits),
            final_conclusion=self._section_final(ctx),
        )

    # ------------------------------------------------------------------ context

    def _context(
        self,
        analytics: VprAnalyticsResult,
        deficits: VprDeficitResult,
    ) -> InterpretationContext:
        s = analytics.summary
        avg_share = None
        if s.avg_primary_score is not None and s.max_primary_score:
            avg_share = float(s.avg_primary_score) / float(s.max_primary_score) * 100.0

        mastery = classify_mastery(avg_share) or classify_mastery(s.knowledge_quality_percent) or "acceptable"
        quality_band = classify_mastery(s.knowledge_quality_percent)
        absolute_band = classify_mastery(s.absolute_achievement_percent)
        spread = classify_spread(s.cv_primary_score_percent)
        skew = classify_skew(s.avg_primary_score, s.median_primary_score)

        mark2_share = self._mark_share(analytics, "2")
        mark45_share = self._combined_mark_share(analytics, ("4", "5"))

        task_total = len(deficits.tasks) or len(analytics.tasks) or 1
        strong_tasks = [
            t
            for t in deficits.tasks
            if t.mastery_level in STRONG_LEVELS
            or (t.completion_percent is not None and t.completion_percent >= 75)
        ]
        weak_tasks = [t for t in deficits.tasks if t.priority in PROBLEM_PRIORITIES]
        strong_share = len(strong_tasks) / task_total
        weak_share = len(weak_tasks) / task_total

        basic_strong, advanced_weak = self._difficulty_pattern(analytics.tasks, deficits)

        topics = [t for t in deficits.topics if (t.topic or "").strip() not in PLACEHOLDER_TOPICS]
        skills = [
            sk
            for sk in deficits.skills
            if (sk.checked_skill or "").strip() not in PLACEHOLDER_SKILLS
        ]
        strong_topics = tuple(
            t.topic
            for t in sorted(
                topics,
                key=lambda x: -(x.avg_completion_percent or -1),
            )
            if t.mastery_level in STRONG_LEVELS
            or (t.avg_completion_percent is not None and t.avg_completion_percent >= 75)
        )[:4]
        weak_topics = tuple(
            t.topic
            for t in sorted(
                topics,
                key=lambda x: (x.avg_completion_percent if x.avg_completion_percent is not None else 101),
            )
            if t.mastery_level in WEAK_LEVELS
            or t.risk in PROBLEM_PRIORITIES
            or (t.avg_completion_percent is not None and t.avg_completion_percent < 60)
        )[:4]
        strong_skills = tuple(
            sk.checked_skill
            for sk in sorted(
                skills,
                key=lambda x: -(x.avg_completion_percent or -1),
            )
            if sk.mastery_level in STRONG_LEVELS
            or (sk.avg_completion_percent is not None and sk.avg_completion_percent >= 75)
        )[:4]
        weak_skills = tuple(
            sk.checked_skill
            for sk in sorted(
                skills,
                key=lambda x: (x.avg_completion_percent if x.avg_completion_percent is not None else 101),
            )
            if sk.mastery_level in WEAK_LEVELS
            or sk.risk in PROBLEM_PRIORITIES
            or (sk.avg_completion_percent is not None and sk.avg_completion_percent < 60)
        )[:4]

        deficit_scale = classify_deficit_scale(
            weak_task_share=weak_share,
            topics_at_risk=deficits.summary.topics_at_risk,
            topics_total=len(deficits.topics),
            skills_at_risk=deficits.summary.skills_at_risk,
            skills_total=len(deficits.skills),
        )

        return InterpretationContext(
            mastery_band=mastery,
            quality_band=quality_band,
            absolute_band=absolute_band,
            avg_share=avg_share,
            spread_band=spread,
            skew=skew,
            mark2_share=mark2_share,
            mark45_share=mark45_share,
            strong_task_share=strong_share,
            weak_task_share=weak_share,
            basic_strong=basic_strong,
            advanced_weak=advanced_weak,
            deficit_scale=deficit_scale,
            strong_topics=strong_topics,
            weak_topics=weak_topics,
            strong_skills=strong_skills,
            weak_skills=weak_skills,
            subject=analytics.subject,
            parallel=analytics.parallel,
        )

    @staticmethod
    def _mark_share(analytics: VprAnalyticsResult, mark: str) -> float | None:
        counts = analytics.marks.vpr or {}
        total = sum(counts.values())
        if not total:
            return None
        return counts.get(mark, 0) / total

    @staticmethod
    def _combined_mark_share(analytics: VprAnalyticsResult, marks: tuple[str, ...]) -> float | None:
        counts = analytics.marks.vpr or {}
        total = sum(counts.values())
        if not total:
            return None
        return sum(counts.get(m, 0) for m in marks) / total

    @staticmethod
    def _difficulty_pattern(
        tasks: list[VprTaskAnalytics],
        deficits: VprDeficitResult,
    ) -> tuple[bool, bool]:
        by_code = {t.task_code: t for t in deficits.tasks}
        basic_ok = 0
        basic_total = 0
        advanced_weak = 0
        advanced_total = 0
        for task in tasks:
            diff = (task.difficulty or "").strip().lower()
            deficit = by_code.get(task.task_code)
            pct = task.completion_percent
            if pct is None and deficit is not None:
                pct = deficit.completion_percent
            if not diff:
                continue
            is_basic = any(token in diff for token in ("базов", "basic", "лёгк", "легк"))
            is_advanced = any(
                token in diff for token in ("повыш", "сложн", "высокий", "advanced", "трудн")
            )
            if is_basic:
                basic_total += 1
                if pct is not None and pct >= 75:
                    basic_ok += 1
            if is_advanced:
                advanced_total += 1
                if pct is not None and pct < 60:
                    advanced_weak += 1
        basic_strong = basic_total > 0 and (basic_ok / basic_total) >= 0.6
        advanced_is_weak = advanced_total > 0 and (advanced_weak / advanced_total) >= 0.5
        return basic_strong, advanced_is_weak

    # ------------------------------------------------------------------ sections

    def _section_overview(
        self,
        ctx: InterpretationContext,
        analytics: VprAnalyticsResult,
    ) -> VprConclusionSection:
        paragraphs: list[str] = []
        paragraphs.append(
            f"По результатам ВПР по предмету «{ctx.subject}» ({ctx.parallel} класс, "
            f"{analytics.academic_year} учебный год) общий уровень подготовки участников "
            f"соответствует {MASTERY_LABELS[ctx.mastery_band]}."
        )

        if ctx.mastery_band in {"high", "sufficient"}:
            paragraphs.append(
                "Преобладающая часть обучающихся демонстрирует устойчивое освоение "
                "базового программного содержания. Существенных признаков массового "
                "снижения качества подготовки по итогам работы не наблюдается."
            )
        elif ctx.mastery_band == "acceptable":
            paragraphs.append(
                "Подготовка участников в целом находится в допустимых границах, "
                "однако отдельные компоненты предметных результатов освоены неравномерно. "
                "Это отражается на общем профиле достижений."
            )
        elif ctx.mastery_band == "problem":
            paragraphs.append(
                "Средний результат участников соответствует уровню освоения "
                "образовательной программы ниже ожидаемого. Значительная часть обучающихся "
                "испытывает затруднения при выполнении отдельных типов заданий, "
                "что отражается на общем уровне подготовки."
            )
        else:
            paragraphs.append(
                "Полученные результаты указывают на выраженные затруднения значительной "
                "части участников при освоении программного содержания. Общий уровень "
                "подготовки требует особого внимания к характеру выявленных дефицитов."
            )

        if ctx.quality_band:
            paragraphs.append(QUALITY_INTERPRETATION[ctx.quality_band])

        if ctx.absolute_band in {"high", "sufficient"} and ctx.quality_band in {"problem", "critical"}:
            paragraphs.append(
                "При относительно высокой абсолютной успеваемости доля участников "
                "с повышенным уровнем подготовки остаётся ограниченной. Это свидетельствует "
                "о преобладании минимально достаточных достижений над глубоким освоением материала."
            )
        elif ctx.absolute_band in {"problem", "critical"}:
            paragraphs.append(
                "Существенная часть участников не достигла удовлетворительного уровня "
                "результативности, что усиливает значимость анализа предметных затруднений."
            )

        return VprConclusionSection(
            key="overview",
            title="Общая оценка результатов",
            paragraphs=paragraphs,
        )

    def _section_statistics(self, ctx: InterpretationContext) -> VprConclusionSection:
        paragraphs: list[str] = []

        paragraphs.append(
            f"Центральная характеристика результатов соответствует "
            f"{MASTERY_LABELS[ctx.mastery_band]}. В аналитическом смысле это отражает "
            f"типичный уровень выполнения работы большинством участников, а не единичные "
            f"экстремальные значения."
        )

        if ctx.skew != "unknown":
            paragraphs.append(SKEW_INTERPRETATION[ctx.skew])
            if ctx.skew == "symmetric":
                paragraphs.append(
                    "Медиана и среднее значение согласованы, что повышает устойчивость "
                    "общей оценки и снижает влияние случайных выбросов на интерпретацию."
                )
            elif ctx.skew == "low_tail":
                paragraphs.append(
                    "Наличие смещения в сторону более низких результатов указывает "
                    "на группу обучающихся с пониженной результативностью, влияющую "
                    "на общий профиль подготовки."
                )
            else:
                paragraphs.append(
                    "Наличие смещения в сторону более высоких результатов отражает "
                    "вклад группы участников с относительно успешной подготовкой."
                )

        if ctx.spread_band:
            paragraphs.append(SPREAD_INTERPRETATION[ctx.spread_band])
            if ctx.spread_band == "homogeneous":
                paragraphs.append(
                    "Низкая вариативность свидетельствует об устойчивости подготовки "
                    "в рамках обследуемой совокупности."
                )
            elif ctx.spread_band == "heterogeneous":
                paragraphs.append(
                    "Высокая вариативность означает, что общий средний результат "
                    "не в полной мере описывает положение отдельных групп обучающихся."
                )
            else:
                paragraphs.append(
                    "Умеренная вариативность допускает наличие различий в подготовке "
                    "при сохранении относительно устойчивого центра распределения."
                )

        return VprConclusionSection(
            key="statistics",
            title="Анализ статистических показателей",
            paragraphs=paragraphs,
        )

    def _section_quality(self, ctx: InterpretationContext) -> VprConclusionSection:
        paragraphs: list[str] = []

        if ctx.spread_band == "homogeneous":
            paragraphs.append(
                "Подготовка участников характеризуется относительной однородностью: "
                "существенных разрывов между основным массивом результатов не наблюдается."
            )
        elif ctx.spread_band == "heterogeneous":
            paragraphs.append(
                "Подготовка участников неоднородна: дифференциация результатов выражена "
                "достаточно отчётливо и указывает на наличие различных по уровню групп обучающихся."
            )
        else:
            paragraphs.append(
                "Подготовка участников умеренно дифференцирована: наряду с основной "
                "группой присутствуют различия в индивидуальных достижениях."
            )

        if ctx.mark2_share is not None:
            if ctx.mark2_share >= 0.2:
                paragraphs.append(
                    "По распределению отметок фиксируется заметная группа риска — "
                    "обучающиеся, не достигшие удовлетворительного уровня выполнения работы. "
                    "Это усиливает неоднородность образовательных результатов."
                )
            elif ctx.mark2_share > 0:
                paragraphs.append(
                    "Группа риска по итогам работы присутствует, однако её доля "
                    "не определяет общий характер распределения результатов."
                )
            else:
                paragraphs.append(
                    "Группа обучающихся, не достигших удовлетворительного уровня, "
                    "по итогам работы не сформирована."
                )

        if ctx.mark45_share is not None:
            if ctx.mark45_share >= 0.6:
                paragraphs.append(
                    "Значительная часть участников продемонстрировала повышенный "
                    "и высокий уровни выполнения, что поддерживает положительный профиль подготовки."
                )
            elif ctx.mark45_share < 0.35:
                paragraphs.append(
                    "Доля участников с повышенным уровнем выполнения ограничена, "
                    "вследствие чего общий профиль подготовки смещён к минимально достаточным результатам."
                )

        if ctx.skew == "low_tail" and ctx.spread_band in {"moderate", "heterogeneous"}:
            paragraphs.append(
                "Сочетание неоднородности и смещения распределения указывает на "
                "существенные различия между учащимися по уровню предметной подготовки."
            )
        elif ctx.spread_band == "homogeneous" and ctx.mastery_band in {"high", "sufficient"}:
            paragraphs.append(
                "Различия между учащимися не носят критического характера: "
                "основная часть участников находится в сходном диапазоне достижений."
            )

        return VprConclusionSection(
            key="strengths",
            title="Анализ качества подготовки",
            paragraphs=paragraphs,
        )

    def _section_tasks(
        self,
        ctx: InterpretationContext,
        analytics: VprAnalyticsResult,
        deficits: VprDeficitResult,
    ) -> VprConclusionSection:
        paragraphs: list[str] = []

        if ctx.basic_strong and ctx.advanced_weak:
            paragraphs.append(
                "Большинство участников успешно выполняет задания базового уровня. "
                "Значительные затруднения вызывают задания повышенного уровня сложности."
            )
        elif ctx.basic_strong:
            paragraphs.append(
                "Наиболее устойчивые результаты связаны с заданиями базового уровня. "
                "Это свидетельствует о сформированности опорных предметных действий "
                "у преобладающей части участников."
            )
        elif ctx.advanced_weak:
            paragraphs.append(
                "Наиболее сложными оказались задания, требующие применения умений "
                "повышенного уровня. Затруднения в этой группе заданий существенно "
                "влияют на общий профиль выполнения работы."
            )

        if (ctx.strong_task_share or 0) >= 0.5 and (ctx.weak_task_share or 0) < 0.2:
            paragraphs.append(
                "По совокупности заданий преобладает успешное выполнение. "
                "Локальные затруднения не формируют доминирующий паттерн ошибок."
            )
        elif (ctx.weak_task_share or 0) >= 0.4:
            paragraphs.append(
                "Затруднения проявляются в широком круге заданий и не ограничиваются "
                "единичными позициями. Это указывает на устойчивый характер проблем "
                "при выполнении проверяемых типов учебных действий."
            )
        elif (ctx.weak_task_share or 0) > 0:
            paragraphs.append(
                "Наряду с успешно выполненными позициями выделяется группа заданий "
                "с пониженным уровнем выполнения. Различие между этими группами "
                "формирует основной предметный профиль затруднений."
            )

        # закономерность по умениям/темам без перечисления номеров
        if ctx.weak_skills and len(ctx.weak_skills) >= 2:
            paragraphs.append(
                "Наиболее сложными оказались задания, требующие комплексного применения "
                "нескольких предметных умений, связанных с направлениями: "
                + self._join_names(ctx.weak_skills)
                + "."
            )
        elif ctx.weak_skills:
            paragraphs.append(
                "Наиболее выраженные затруднения сосредоточены в заданиях, направленных "
                f"на проверку умения «{ctx.weak_skills[0]}»."
            )

        if ctx.strong_skills and not paragraphs:
            paragraphs.append(
                "Успешность выполнения связана прежде всего с заданиями, "
                "проверяющими уже сформированные предметные умения."
            )

        if not paragraphs:
            paragraphs.append(
                "Устойчивых закономерностей выполнения заданий по уровню сложности "
                "и типу проверяемых умений на основании имеющихся данных не выделено."
            )

        return VprConclusionSection(
            key="weaknesses",
            title="Анализ выполнения заданий",
            paragraphs=paragraphs,
        )

    def _section_topics(self, ctx: InterpretationContext) -> VprConclusionSection:
        paragraphs: list[str] = []

        if ctx.strong_topics:
            paragraphs.append(
                "К разделам программы, освоенным на достаточном и высоком уровне, "
                f"относятся: {self._join_names(ctx.strong_topics)}. "
                "Устойчивое выполнение заданий по данным направлениям отражает "
                "сформированность соответствующих предметных результатов."
            )
        else:
            paragraphs.append(
                "Разделы программы с устойчиво высоким уровнем освоения "
                "по итогам работы явно не выделяются."
            )

        if ctx.weak_topics:
            paragraphs.append(
                "Дополнительного внимания требуют разделы: "
                f"{self._join_names(ctx.weak_topics)}. "
                "Именно по этим направлениям фиксируются наиболее выраженные "
                "затруднения участников."
            )
            paragraphs.append(
                "Значимость указанных разделов определяется их ролью в структуре "
                "предметных результатов: пробелы в их освоении ограничивают возможность "
                "успешного выполнения связанных типов заданий и снижают целостность подготовки."
            )
        else:
            paragraphs.append(
                "Тематических направлений с выраженными массовыми затруднениями "
                "не зафиксировано."
            )

        if ctx.strong_topics and ctx.weak_topics:
            paragraphs.append(
                "Сопоставление освоенных и проблемных разделов указывает на "
                "неравномерность освоения программы: успешность по одним темам "
                "не компенсирует затруднения по другим."
            )

        return VprConclusionSection(
            key="topics",
            title="Анализ тем",
            paragraphs=paragraphs,
        )

    def _section_skills(self, ctx: InterpretationContext) -> VprConclusionSection:
        paragraphs: list[str] = []

        if ctx.strong_skills:
            paragraphs.append(
                "Сформированными можно считать следующие предметные умения: "
                f"{self._join_names(ctx.strong_skills)}. "
                "Их проявление в результатах работы является относительно устойчивым."
            )
        else:
            paragraphs.append(
                "Предметные умения с устойчиво высоким уровнем сформированности "
                "по итогам работы не выделены."
            )

        if ctx.weak_skills:
            paragraphs.append(
                "Недостаточно сформированными являются умения: "
                f"{self._join_names(ctx.weak_skills)}."
            )
            if ctx.deficit_scale in {"mass", "systemic"}:
                paragraphs.append(
                    "У значительной части участников указанные умения проявляются "
                    "нестабильно либо фактически отсутствуют в ожидаемом объёме, "
                    "что подтверждается масштабом связанных образовательных дефицитов."
                )
            else:
                paragraphs.append(
                    "Недостаточная сформированность данных умений носит "
                    "ограниченный характер и проявляется в отдельной группе заданий."
                )
        else:
            paragraphs.append(
                "Умения с признаками недостаточной сформированности у значительной "
                "части участников не выявлены."
            )

        return VprConclusionSection(
            key="skills",
            title="Анализ проверяемых умений",
            paragraphs=paragraphs,
        )

    def _section_deficits(
        self,
        ctx: InterpretationContext,
        deficits: VprDeficitResult,
    ) -> VprConclusionSection:
        paragraphs: list[str] = [DEFICIT_SCALE_INTERPRETATION[ctx.deficit_scale]]

        if ctx.deficit_scale == "absent":
            paragraphs.append(
                "Масштаб проблемы минимален: профиль выполнения заданий "
                "не содержит устойчивых зон критических и высоких дефицитов."
            )
        elif ctx.deficit_scale == "local":
            paragraphs.append(
                "Масштаб проблемы ограничен. Затруднения связаны с отдельными "
                "элементами содержания и не определяют общий результат большинства участников."
            )
        elif ctx.deficit_scale == "mass":
            paragraphs.append(
                "Выявленные образовательные дефициты сосредоточены преимущественно "
                "в заданиях, направленных на проверку конкретных предметных умений. "
                "Это свидетельствует о системном характере затруднений в отдельных "
                "направлениях, а не о единичных ошибках."
            )
        else:
            paragraphs.append(
                "Масштаб проблемы является значительным: дефициты охватывают "
                "существенную долю проверяемых заданий и тематических направлений, "
                "формируя устойчивый негативный профиль подготовки."
            )

        if ctx.weak_topics:
            paragraphs.append(
                "По содержанию наиболее значимые дефициты связаны с разделами: "
                f"{self._join_names(ctx.weak_topics)}."
            )
        if ctx.weak_skills:
            paragraphs.append(
                "В части предметных умений дефициты концентрируются вокруг: "
                f"{self._join_names(ctx.weak_skills)}."
            )

        # характер: локальные vs массовые по доле приоритетов (уже посчитано DeficitEngine)
        critical = sum(1 for t in deficits.tasks if t.priority == "Critical")
        high = sum(1 for t in deficits.tasks if t.priority == "High")
        if critical and high:
            paragraphs.append(
                "В структуре дефицитов присутствуют как критические, так и высокие "
                "по приоритету зоны, что усиливает вывод о неоднородности освоения "
                "проверяемого содержания."
            )
        elif critical:
            paragraphs.append(
                "Доминируют дефициты критического приоритета, что отражает "
                "глубину затруднений по отдельным проверяемым позициям."
            )
        elif high:
            paragraphs.append(
                "Преобладают дефициты высокого приоритета, связанные с проблемными "
                "зонами освоения при сохранении выполнения части заданий на допустимом уровне."
            )

        return VprConclusionSection(
            key="deficits",
            title="Анализ образовательных дефицитов",
            paragraphs=paragraphs,
        )

    def _section_final(self, ctx: InterpretationContext) -> VprConclusionSection:
        paragraphs: list[str] = []

        if ctx.mastery_band in {"high", "sufficient"} and ctx.deficit_scale in {"absent", "local"}:
            paragraphs.append(
                "Полученные результаты характеризуются стабильным уровнем подготовки "
                "большинства участников."
            )
            paragraphs.append(
                "Существенных системных дефицитов не выявлено. Отдельные затруднения, "
                "если они фиксируются, носят ограниченный характер и не определяют "
                "общий профиль освоения программы."
            )
        elif ctx.mastery_band == "acceptable" and ctx.deficit_scale in {"local", "mass"}:
            paragraphs.append(
                "Результаты свидетельствуют о допустимом общем уровне подготовки "
                "при наличии неравномерности освоения отдельных предметных результатов."
            )
            paragraphs.append(
                "Основные затруднения локализованы в конкретных тематических направлениях "
                "и проверяемых умениях и не распространяются равномерно на всю работу."
            )
        else:
            paragraphs.append(
                "Результаты свидетельствуют о недостаточном уровне сформированности "
                "отдельных предметных результатов."
            )
            if ctx.deficit_scale in {"mass", "systemic"}:
                paragraphs.append("Основные затруднения носят системный характер.")
            else:
                paragraphs.append(
                    "Основные затруднения сосредоточены в отдельных компонентах "
                    "предметной подготовки."
                )

        if ctx.weak_topics or ctx.weak_skills:
            focus_parts: list[str] = []
            if ctx.weak_topics:
                focus_parts.append(
                    "тематическими разделами " + self._join_names(ctx.weak_topics)
                )
            if ctx.weak_skills:
                focus_parts.append(
                    "предметными умениями " + self._join_names(ctx.weak_skills)
                )
            paragraphs.append(
                "Наиболее выраженные проблемы связаны с "
                + " и ".join(focus_parts)
                + "."
            )
        elif ctx.mastery_band in {"high", "sufficient"}:
            paragraphs.append(
                "Сильные стороны подготовки связаны с устойчивым выполнением "
                "базового содержания и достаточной однородностью результатов."
            )

        if ctx.spread_band == "heterogeneous":
            paragraphs.append(
                "Дополнительным фактором общего профиля является выраженная "
                "дифференциация индивидуальных результатов участников."
            )

        return VprConclusionSection(
            key="final_conclusion",
            title="Итоговая аналитическая оценка",
            paragraphs=paragraphs,
        )

    @staticmethod
    def _join_names(names: tuple[str, ...] | list[str]) -> str:
        clean = [n.strip() for n in names if n and n.strip()]
        if not clean:
            return "—"
        if len(clean) == 1:
            return f"«{clean[0]}»"
        if len(clean) == 2:
            return f"«{clean[0]}» и «{clean[1]}»"
        return ", ".join(f"«{n}»" for n in clean[:-1]) + f" и «{clean[-1]}»"
