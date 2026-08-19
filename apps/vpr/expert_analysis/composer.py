"""
Компоновщик экспертных текстов ФИОКО 2.0.

Собирает связный методический нарратив из уже рассчитанных данных
и предметной модели. Без перечисления заданий/тем списком.
"""

from __future__ import annotations

from collections import defaultdict

from apps.vpr.conclusion.rules import classify_mastery
from apps.vpr.expert_analysis.competences import PLACEHOLDER_SKILLS, PLACEHOLDER_TOPICS
from apps.vpr.expert_analysis.result import CauseChain, CompetenceInsight, PatternInsight
from apps.vpr.expert_analysis.subject_models import SubjectExpertModel, get_subject_model


def _join_names(names: list[str], *, limit: int = 3) -> str:
    cleaned = [n.strip() for n in names if n and n.strip()]
    if not cleaned:
        return ""
    head = cleaned[:limit]
    if len(head) == 1:
        return f"«{head[0]}»"
    if len(head) == 2:
        return f"«{head[0]}» и «{head[1]}»"
    return ", ".join(f"«{x}»" for x in head[:-1]) + f" и «{head[-1]}»"


def _section_avgs(analysis) -> list[tuple[str, float, int]]:
    stats: dict[str, list[float]] = defaultdict(list)
    for row in analysis.task_rows or []:
        section = (row.get("program_section") or "").strip()
        pct = row.get("completion_percent")
        if section and pct is not None:
            stats[section].append(float(pct))
    out = [(s, sum(v) / len(v), len(v)) for s, v in stats.items() if v]
    out.sort(key=lambda x: x[1], reverse=True)
    return out


def _pick_opener(model: SubjectExpertModel, parallel) -> str:
    # Выбор opener по параллели — разные синтаксисы, без «подстановки предмета» в одну формулу
    idx = int(parallel or 0) % len(model.overview_openers)
    return model.overview_openers[idx]


def compose_overview(
    *,
    model: SubjectExpertModel,
    parallel,
    profile_label: str,
    cognitive_label: str,
    formed: list[CompetenceInsight],
    weak: list[CompetenceInsight],
    patterns: list[PatternInsight],
) -> list[str]:
    texts = [
        _pick_opener(model, parallel),
        (
            f"В {parallel} классе сложился профиль «{profile_label}» "
            f"при когнитивном срезе «{cognitive_label}». "
            f"{model.meta_focus}"
        ),
    ]
    if formed:
        names = _join_names([c.name for c in formed])
        texts.append(
            f"{model.strength_frame} В данном классе это проявляется через {names}."
        )
    else:
        texts.append(model.strength_frame)
    if weak:
        names = _join_names([c.name for c in weak])
        texts.append(
            f"{model.limiter_frame} Наиболее уязвимы {names} — именно они "
            "задают снижение устойчивости предметных результатов."
        )
    else:
        texts.append(model.limiter_frame)
    if patterns:
        texts.append(patterns[0].explanation)
    return _dedupe(texts)


def compose_cognitive(model: SubjectExpertModel, code: str, basic_avg, advanced_avg, n_basic, n_advanced) -> list[str]:
    texts: list[str] = []
    if code in {"advanced_deficit", "advanced_gap"}:
        texts.append(model.cognitive_repro if code == "advanced_deficit" else model.cognitive_transfer)
    elif code == "basic_deficit":
        texts.append(model.cognitive_basic_gap)
    elif code == "both_levels":
        texts.append(model.cognitive_basic_gap)
        texts.append(model.cognitive_repro)
    elif code == "balanced_high":
        texts.append(
            f"По {model.genitive} задания разной когнитивной сложности выполняются "
            "относительно устойчиво: репродуктивная и продуктивная деятельность "
            "не образуют одностороннего разрыва."
        )
    else:
        texts.append(model.cognitive_transfer)

    # Объяснение влияния — без «просто цифр»
    if basic_avg is not None and advanced_avg is not None:
        delta = basic_avg - advanced_avg
        if delta >= 15:
            texts.append(
                "Разрыв между базовым и повышенным уровнем подтверждает, что класс "
                "удерживает обязательный минимум лучше, чем справляется с задачами "
                "анализа, интерпретации и применения знаний в новой ситуации. "
                "Это напрямую снижает качество выполнения продуктивных заданий."
            )
        elif delta <= -10:
            texts.append(
                "Нетипично низкий базовый контур относительно повышенного указывает "
                "на неравномерность освоения обязательного содержания и требует "
                "проверки устойчивости элементарных предметных действий."
            )
        else:
            texts.append(
                "Когнитивные уровни выражены близко: структура подготовки ближе "
                "к сбалансированной, а локальные потери связаны с отдельными "
                "содержательными линиями, а не с глобальным срывом одного уровня."
            )
    elif basic_avg is not None:
        texts.append(
            "Разметка повышенного уровня в каталоге ограничена, поэтому вывод "
            "опирается преимущественно на выполнение обязательного содержания."
        )
    return _dedupe(texts)


def compose_profile(
    *,
    model: SubjectExpertModel,
    code: str,
    label: str,
    risk_pct: float,
    high_pct: float,
    weak_share: float,
    strong_share: float,
) -> list[str]:
    texts = [
        (
            f"Автоматически определён профиль «{label}». "
            + model.profile_hooks.get(
                code,
                (
                    f"По {model.genitive} этот профиль означает особое соотношение "
                    "устойчивости предметных результатов, вариативности подготовки "
                    "и выраженности образовательных дефицитов."
                ),
            )
        )
    ]
    # Что / почему / влияние
    if risk_pct >= 20:
        texts.append(
            f"Что произошло: группа риска составляет около {risk_pct:.0f}% класса. "
            "Почему: внутри параллели сосуществуют разные уровни предметной компетентности. "
            "Как влияет: нижний полюс тянет вниз средний результат и снижает "
            "устойчивость структуры образовательных результатов."
        )
    if high_pct >= 20:
        texts.append(
            f"Одновременно группа высокого уровня (~{high_pct:.0f}%) сохраняет "
            "ресурсный потенциал: при адресной работе с дефицитами именно она "
            "поддерживает качество знаний и вариативность положительных достижений."
        )
    if weak_share >= 0.3:
        texts.append(
            "Доля проблемных содержательных линий высока — профиль усиливается "
            "тематическими и потенциально системными образовательными дефицитами."
        )
    if strong_share >= 0.35 and code not in {"critical", "elevated_risk"}:
        texts.append(
            "Наличие устойчивых содержательных опор не отменяет ограничивающих "
            "компетенций, но объясняет, за счёт чего класс всё же удерживает "
            "часть предметных результатов."
        )
    texts.append(model.meta_focus)
    return _dedupe(texts)


def compose_structure(model: SubjectExpertModel, analysis) -> list[str]:
    sections = _section_avgs(analysis)
    texts: list[str] = []
    if not sections:
        return [
            (
                f"Разделы программы по {model.genitive} сопоставлены частично; "
                "вывод о структуре подготовки строится по компетенциям и темам каталога."
            )
        ]

    strong = [s for s in sections if classify_mastery(s[1]) in {"high", "sufficient"}]
    weak = [s for s in sections if classify_mastery(s[1]) in {"problem", "critical"}]
    if strong:
        names = _join_names([s[0] for s in strong])
        texts.append(
            f"Лучше освоены разделы {names}. {model.section_strong_why} "
            "Именно эти содержательные линии поддерживают общий предметный результат."
        )
    if weak:
        names = _join_names([s[0] for s in weak])
        texts.append(
            f"Хуже освоены разделы {names}. {model.section_weak_why} "
            "Эти линии выступают ограничивающим фактором и распространяют "
            "затруднения на связанные задания."
        )
    if strong and weak:
        texts.append(
            "Дисбаланс между разделами формирует неоднородность предметной структуры: "
            "успешные линии не компенсируют полностью системное влияние дефицитных."
        )
    elif not weak and strong:
        texts.append(
            "Выраженного межраздельного разрыва не видно: структура подготовки "
            "ближе к равномерной при сохранении отдельных локальных рисков."
        )
    return _dedupe(texts)


def compose_competences_analysis(model: SubjectExpertModel, competences: list[CompetenceInsight]) -> list[str]:
    formed = [c for c in competences if c.status == "formed"]
    partial = [c for c in competences if c.status == "partial"]
    weak = [c for c in competences if c.status == "weak"]
    texts = [
        (
            f"Предметная модель {model.display.lower()} опирается на линии: "
            + ", ".join(model.competence_lines)
            + "."
        )
    ]
    if formed:
        texts.append(
            "Формируют общий результат "
            + _join_names([c.name for c in formed])
            + ": "
            + formed[0].conclusion
        )
    if weak:
        texts.append(
            "Ограничивающим фактором выступают "
            + _join_names([c.name for c in weak])
            + ". "
            + weak[0].conclusion
            + " Это влияет на смежные умения и снижает устойчивость всей структуры результатов."
        )
    if partial and not weak:
        texts.append(
            "Частично сформированные компетенции "
            + _join_names([c.name for c in partial])
            + " объясняют нестабильность применения знаний в отдельных учебных ситуациях."
        )
    for c in competences:
        if c.status in {"formed", "weak"} and c.evidence:
            # Не перечисляем задания — обобщаем evidence как проявления
            texts.append(
                f"По линии «{c.name}» проявления в каталоге согласованы: "
                + ", ".join(c.evidence[:3])
                + ". Совокупность этих проявлений важнее любого единичного процента."
            )
            break
    return _dedupe(texts)


def compose_patterns_analysis(model: SubjectExpertModel, patterns: list[PatternInsight]) -> list[str]:
    if not patterns:
        return [
            (
                f"По {model.genitive} устойчивых кластеров риска не зафиксировано: "
                "образовательные дефициты рассеяны и не складываются в одну "
                "системную содержательную линию."
            )
        ]
    texts = []
    for p in patterns[:4]:
        texts.append(p.explanation)
    systemic = [p for p in patterns if p.kind == "systemic"]
    if systemic:
        chain = " → ".join(model.systemic_chain)
        texts.append(
            f"Системный образовательный дефицит разворачивается как цепочка: {chain}."
        )
    return _dedupe(texts)


def compose_tasks_analysis(
    *,
    model: SubjectExpertModel,
    analysis,
    cognitive_label: str,
    patterns: list[PatternInsight],
    weak_competences: list[CompetenceInsight],
) -> list[str]:
    """Без перечисления «задание №…» — только кластеры компетенций/разделов."""
    texts = [
        (
            f"Выполнение работы по {model.genitive} интерпретируется через "
            f"когнитивный профиль «{cognitive_label}» и связность содержательных линий, "
            "а не через изолированные проценты отдельных заданий."
        )
    ]
    sections = _section_avgs(analysis)
    weak_sec = [s for s in sections if classify_mastery(s[1]) in {"problem", "critical"}]
    strong_sec = [s for s in sections if classify_mastery(s[1]) in {"high", "sufficient"}]
    if weak_sec:
        names = _join_names([s[0] for s in weak_sec])
        texts.append(
            f"Совокупность пониженных результатов сосредоточена в разделах {names}. "
            f"{model.section_weak_why}"
        )
    if strong_sec:
        names = _join_names([s[0] for s in strong_sec])
        texts.append(
            f"Устойчивые проявления успеха связаны с разделами {names}. "
            f"{model.section_strong_why}"
        )
    if weak_competences:
        texts.append(
            "Эти потери согласуются с недостаточной сформированностью "
            + _join_names([c.name for c in weak_competences])
            + " — единой компетенции, а не набора случайных ошибок."
        )
    thematic = [p for p in patterns if p.kind in {"thematic", "systemic", "competence"}]
    if thematic:
        texts.append(thematic[0].explanation)
    return _dedupe(texts)


def compose_topics_analysis(model: SubjectExpertModel, strong_topics, weak_topics, patterns) -> list[str]:
    texts = []
    if weak_topics:
        # Не «перечень тем», а объединение
        texts.append(
            f"Проблемные проявления по {model.genitive} стягиваются к содержательному "
            f"ядру {_join_names(weak_topics, limit=4)}. "
            "Это тематический образовательный дефицит: темы взаимосвязаны и вместе "
            "снижают результат по всей линии, а не существуют как независимые пробелы."
        )
    if strong_topics:
        texts.append(
            f"Опорные проявления сосредоточены вокруг {_join_names(strong_topics, limit=4)}. "
            f"{model.strength_frame}"
        )
    for p in patterns:
        if p.kind in {"thematic", "systemic"}:
            texts.append(p.explanation)
            break
    if not texts:
        texts.append(
            f"Тематические полюса по {model.genitive} выражены умеренно: "
            "структура подготовки не демонстрирует одного доминирующего дефицита."
        )
    return _dedupe(texts)


def compose_skills_analysis(model: SubjectExpertModel, strong_skills, weak_skills, competences) -> list[str]:
    texts = []
    if weak_skills:
        texts.append(
            "Недостаточно сформированные способы действий "
            f"{_join_names(weak_skills, limit=4)} "
            "объединяются в уменийный кластер риска. "
            f"{model.limiter_frame}"
        )
    if strong_skills:
        texts.append(
            "Устойчивые умения "
            f"{_join_names(strong_skills, limit=4)} "
            "подтверждают сохранность рабочих приёмов и поддерживают "
            "предметные результаты в типовых ситуациях."
        )
    weak_comp = [c for c in competences if c.status == "weak"]
    if weak_comp:
        texts.append(
            "На уровне предметных компетенций это проявляется как "
            f"{_join_names([c.name for c in weak_comp])} — "
            "ограничивающий фактор всей модели подготовки."
        )
    if not texts:
        texts.append(
            f"Профиль умений по {model.genitive} не образует резкого контраста; "
            "локальные колебания не складываются в системный дефицит."
        )
    return _dedupe(texts)


def compose_deficits(model: SubjectExpertModel, patterns, weak_comp, profile_label) -> list[str]:
    texts = [
        (
            f"Образовательные дефициты по {model.genitive} читаются в логике профиля "
            f"«{profile_label}»: важны тип дефицита (локальный, тематический, системный) "
            "и его влияние на остальные результаты, а не перечень единиц каталога."
        )
    ]
    kinds = {p.kind for p in patterns}
    if "systemic" in kinds:
        texts.append(
            "Зафиксирован системный образовательный дефицит: он охватывает несколько "
            "разделов/компетенций и определяет общий спад предметных результатов. "
            + " → ".join(model.systemic_chain)
            + "."
        )
    elif "thematic" in kinds:
        texts.append(
            "Преобладает тематический образовательный дефицит: несколько связанных "
            "тем/заданий одной содержательной линии образуют единую проблему."
        )
    elif "competence" in kinds:
        texts.append(
            "Преобладает компетенцийный дефицит: группа умений указывает на "
            "недостаточную сформированность одной предметной компетенции."
        )
    else:
        texts.append(
            "Дефициты ближе к локальным: точечные потери не складываются "
            "в межраздельную системную проблему."
        )
    if weak_comp:
        texts.append(
            "Ограничивающие компетенции "
            + _join_names([c.name for c in weak_comp])
            + " объясняют, почему локальные ошибки распространяются на смежные задания."
        )
    return _dedupe(texts)


def compose_causes(
    model: SubjectExpertModel,
    patterns: list[PatternInsight],
    weak_comp: list[CompetenceInsight],
    causes,
) -> tuple[list[CauseChain], list[str]]:
    chains: list[CauseChain] = []
    # Всегда даём предметную системную цепочку, если есть слабые компетенции или системный паттерн
    if weak_comp or any(p.kind == "systemic" for p in patterns):
        chains.append(
            CauseChain(
                steps=list(model.systemic_chain),
                summary=(
                    f"Системная причинно-следственная логика по {model.genitive}: "
                    "от первичного дефицита компетенции к снижению результата по разделу."
                ),
            )
        )
    for p in patterns:
        if p.kind == "thematic":
            chains.append(
                CauseChain(
                    steps=[
                        p.title,
                        "несформированность связанной предметной компетенции",
                        "ошибки в комплексе связанных заданий",
                        "влияние на общий предметный результат",
                    ],
                    summary=p.explanation,
                )
            )
        elif p.kind == "competence":
            chains.append(
                CauseChain(
                    steps=[
                        "кластер слабых умений",
                        "дефицит предметной компетенции",
                        "перенос ошибок на смежные задания",
                        "снижение устойчивости результатов",
                    ],
                    summary=p.explanation,
                )
            )
    for c in weak_comp[:2]:
        chains.append(
            CauseChain(
                steps=[
                    f"ослабление линии «{c.name}»",
                    "затруднения в применении соответствующих способов действий",
                    "снижение результата по связанным содержательным заданиям",
                    "вклад в общий профиль дефицитов класса",
                ],
                summary=c.conclusion,
            )
        )

    paragraphs = [
        (
            f"Причины по {model.genitive} излагаются как цепочки, а не как список формулировок: "
            "каждый следующий шаг объясняет, как первичный дефицит распространяется "
            "на смежные результаты."
        )
    ]
    if causes is not None:
        summary = getattr(causes, "summary", None)
        dominant = getattr(summary, "dominant_cause_type", None) if summary else None
        scale = getattr(summary, "dominant_scale", None) if summary else None
        if dominant:
            paragraphs.append(
                f"Доминирующий фактор причинно-следственного анализа — «{dominant}» "
                f"(масштаб «{scale or 'не определён'}»). Он связывает отдельные "
                "проявления в единую логику снижения предметных результатов."
            )
    if chains:
        paragraphs.append(chains[0].summary)
    else:
        paragraphs.append(
            "Выраженной сквозной цепочки не построено: дефициты остаются локальными "
            "либо данных каталога недостаточно для устойчивого обобщения."
        )

    # unique chains
    seen = set()
    unique = []
    for ch in chains:
        key = ch.summary or "|".join(ch.steps)
        if key in seen:
            continue
        seen.add(key)
        unique.append(ch)
    return unique[:6], _dedupe(paragraphs)


def compose_strengths(model, strong_topics, strong_skills, formed_comp, strong_sections, profile_label, cognitive_label):
    items = []
    if formed_comp:
        items.append(
            f"Сильные предметные компетенции — {_join_names(formed_comp)}. {model.strength_frame}"
        )
    if strong_sections:
        items.append(
            f"Устойчивые разделы программы — {_join_names(strong_sections)}. {model.section_strong_why}"
        )
    if strong_topics:
        items.append(
            f"Опорные содержательные проявления группируются вокруг {_join_names(strong_topics)}. "
            "Их устойчивость объясняет, за счёт чего класс сохраняет часть результата."
        )
    if strong_skills:
        items.append(
            f"Рабочие способы действий {_join_names(strong_skills)} подтверждают "
            "сохранность типовых предметных операций."
        )
    items.append(
        f"Когнитивный срез «{cognitive_label}» и профиль «{profile_label}» "
        f"показывают ресурсную зону подготовки по {model.genitive}."
    )
    return items[:7]


def compose_problems(model, weak_topics, weak_skills, weak_comp, patterns, profile_label):
    items = []
    if weak_comp:
        items.append(
            f"Ключевые ограничивающие компетенции — {_join_names(weak_comp)}. {model.limiter_frame}"
        )
    if weak_topics:
        items.append(
            f"Тематическое ядро риска {_join_names(weak_topics)} образует "
            "тематический образовательный дефицит и снижает результат по всей линии."
        )
    if weak_skills:
        items.append(
            f"Уменийный кластер {_join_names(weak_skills)} распространяет ошибки "
            "на смежные задания и усиливает вариативность подготовки."
        )
    for p in patterns:
        if p.kind in {"systemic", "thematic", "competence"}:
            items.append(p.explanation)
            break
    items.append(
        f"В условиях профиля «{profile_label}» указанные зоны определяют "
        f"устойчивость предметных результатов по {model.genitive}."
    )
    return items[:7]


def compose_quality(model, profile_label, cognitive_label, summary, quality_band_text: str | None):
    texts = [
        (
            f"Качество подготовки по {model.genitive} интерпретируется как профиль "
            f"«{profile_label}» с когнитивным срезом «{cognitive_label}»: "
            "речь о структуре образовательных результатов, а не о наборе процентов."
        )
    ]
    if quality_band_text:
        texts.append(quality_band_text)
    if summary is not None and summary.avg_mark_vpr is not None and summary.avg_mark_journal is not None:
        delta = float(summary.avg_mark_journal) - float(summary.avg_mark_vpr)
        if abs(delta) >= 0.3:
            if delta > 0:
                texts.append(
                    "Расхождение журнальной и внешней оценки усиливает вывод о разрыве "
                    "между текущей успеваемостью и реальной предметной компетентностью "
                    f"по {model.genitive}."
                )
            else:
                texts.append(
                    "Согласованность внешней и журнальной оценки повышает доверие "
                    f"к зафиксированному профилю по {model.genitive}."
                )
    texts.append(model.meta_focus)
    return _dedupe(texts)


def compose_statistics(model, spread_text, skew_text, profile_label, cv):
    texts = []
    if spread_text:
        texts.append(spread_text)
    if skew_text:
        texts.append(skew_text)
    texts.append(
        f"Статистическая форма распределения по {model.genitive} нужна, чтобы объяснить "
        f"вариативность и устойчивость результатов в профиле «{profile_label}», "
        "а не чтобы пересказать средние значения."
    )
    if cv is not None:
        if cv >= 30:
            texts.append(
                "Высокая неравномерность подготовки подтверждает неоднородность "
                "предметной компетентности и усиливает влияние группы риска на итоговый профиль."
            )
        elif cv < 15:
            texts.append(
                "Низкая неравномерность подготовки говорит об относительной однородности "
                "класса и большей предсказуемости средних предметных результатов."
            )
    return _dedupe(texts)


def compose_final(model, parallel, profile_label, cognitive_label, strengths, problems, overview, causes_analysis):
    texts = [
        (
            f"Итоговая экспертная оценка по {model.genitive} ({parallel} класс): "
            f"профиль «{profile_label}», когнитивный срез «{cognitive_label}»."
        ),
        overview[0] if overview else model.overview_openers[0],
    ]
    if strengths:
        texts.append("Ресурсная сторона: " + strengths[0])
    if problems:
        texts.append("Ограничивающая сторона: " + problems[0])
    if causes_analysis:
        texts.append(causes_analysis[0])
    texts.append(model.closing_focus)
    return _dedupe(texts)[:10]


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        text = (item or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return out
