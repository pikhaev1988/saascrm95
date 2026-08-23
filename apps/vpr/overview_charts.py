"""Диаграммы для аналитической справки ВПР (DOCX)."""

from __future__ import annotations

from io import BytesIO
from typing import Sequence


def _configure_matplotlib() -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "axes.titlesize": 11,
            "axes.labelsize": 9,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.edgecolor": "#4A5568",
            "axes.grid": False,
        }
    )


def _to_png(fig) -> BytesIO:
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=140, bbox_inches="tight", facecolor="white")
    import matplotlib.pyplot as plt

    plt.close(fig)
    buf.seek(0)
    return buf


def chart_marks_distribution(rows: Sequence) -> BytesIO | None:
    """Круговая диаграмма распределения отметок."""
    labels: list[str] = []
    sizes: list[float] = []
    for row in rows or []:
        count = int(getattr(row, "count", 0) or 0)
        if count <= 0:
            continue
        labels.append(f"«{getattr(row, 'mark', '')}» — {count}")
        sizes.append(float(count))
    if not sizes:
        return None

    _configure_matplotlib()
    import matplotlib.pyplot as plt

    colors = ["#2F855A", "#3182CE", "#D69E2E", "#E53E3E", "#718096"]
    fig, ax = plt.subplots(figsize=(5.2, 3.6))
    wedges, texts, autotexts = ax.pie(
        sizes,
        labels=labels,
        autopct=lambda p: f"{p:.1f}%" if p >= 5 else "",
        colors=colors[: len(sizes)],
        startangle=90,
        wedgeprops={"linewidth": 1, "edgecolor": "white"},
        textprops={"color": "#1A202C"},
    )
    for t in autotexts:
        t.set_fontsize(8)
        t.set_color("white")
        t.set_fontweight("bold")
    ax.set_title("Распределение отметок ВПР")
    ax.axis("equal")
    return _to_png(fig)


def chart_groups_distribution(groups: Sequence) -> BytesIO | None:
    """Столбчатая диаграмма состава групп участников."""
    labels: list[str] = []
    values: list[float] = []
    colors: list[str] = []
    palette = {
        "risk": "#E53E3E",
        "medium": "#D69E2E",
        "high": "#2F855A",
        "potential": "#3182CE",
    }
    for g in groups or []:
        count = int(getattr(g, "count", 0) or 0)
        if count <= 0:
            continue
        title = str(getattr(g, "title", "") or getattr(g, "key", ""))
        labels.append(title.replace("Группа ", "").replace("Обучающиеся с ", ""))
        values.append(float(count))
        colors.append(palette.get(str(getattr(g, "key", "")), "#4A5568"))
    if not values:
        return None

    _configure_matplotlib()
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(6.0, 3.4))
    bars = ax.bar(labels, values, color=colors, width=0.65, edgecolor="white")
    ax.set_ylabel("Человек")
    ax.set_title("Состав групп участников")
    ax.set_ylim(0, max(values) * 1.25)
    for bar, val in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.05,
            f"{int(val)}",
            ha="center",
            va="bottom",
            fontsize=9,
            color="#1A202C",
        )
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.setp(ax.get_xticklabels(), rotation=15, ha="right")
    return _to_png(fig)


def chart_primary_scores(rows: Sequence) -> BytesIO | None:
    """Гистограмма распределения первичных баллов."""
    labels: list[str] = []
    values: list[float] = []
    for row in rows or []:
        count = int(getattr(row, "count", 0) or 0)
        if count <= 0:
            continue
        labels.append(str(getattr(row, "score", "")))
        values.append(float(count))
    if not values:
        return None

    _configure_matplotlib()
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    x = list(range(len(labels)))
    ax.bar(x, values, color="#2B6CB0", edgecolor="white", width=0.75)
    ax.set_xticks(x, labels)
    ax.set_xlabel("Первичный балл")
    ax.set_ylabel("Количество обучающихся")
    ax.set_title("Распределение первичных баллов")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    if len(labels) > 10:
        for label in ax.get_xticklabels():
            label.set_rotation(45)
            label.set_ha("right")
    return _to_png(fig)


def chart_task_success(rows: Sequence, *, limit: int = 16) -> BytesIO | None:
    """Горизонтальная диаграмма успешности заданий (% полного балла)."""
    items = []
    for row in rows or []:
        pct = getattr(row, "completion_percent", None)
        if pct is None:
            continue
        code = str(getattr(row, "task_code", "") or "").strip()
        if not code:
            continue
        items.append((code, float(pct)))
    if not items:
        return None
    items = items[:limit]
    labels = [f"№{c}" for c, _ in items]
    values = [v for _, v in items]
    colors = ["#E53E3E" if v < 50 else "#D69E2E" if v < 70 else "#2F855A" for v in values]

    _configure_matplotlib()
    import matplotlib.pyplot as plt

    height = max(3.2, 0.38 * len(items) + 1.2)
    fig, ax = plt.subplots(figsize=(6.4, height))
    y = range(len(items))
    ax.barh(list(y), values, color=colors, edgecolor="white", height=0.7)
    ax.set_yticks(list(y), labels)
    ax.set_xlim(0, 100)
    ax.set_xlabel("% выполнения (полный балл)")
    ax.set_title("Успешность выполнения заданий")
    ax.axvline(50, color="#A0AEC0", linestyle="--", linewidth=0.9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    for i, val in enumerate(values):
        ax.text(min(val + 1.5, 96), i, f"{val:.0f}%", va="center", fontsize=8, color="#1A202C")
    ax.invert_yaxis()
    return _to_png(fig)


def chart_objectivity(rows: Sequence) -> BytesIO | None:
    """Столбцы совпадение / завышение / занижение отметок."""
    mapping = {
        "совпад": ("Совпадение", "#2F855A"),
        "завыш": ("Завышение", "#E53E3E"),
        "заниж": ("Занижение", "#D69E2E"),
    }
    found: dict[str, float] = {}
    for row in rows or []:
        if isinstance(row, dict):
            label = str(row.get("label") or "")
            value = str(row.get("value") or "")
        else:
            label = str(getattr(row, "label", "") or "")
            value = str(getattr(row, "value", "") or "")
        low = label.lower()
        for key, (short, _) in mapping.items():
            if key in low:
                # value like "17 (73.9%)" → take count before (
                num = value.split("(")[0].strip().split()[0] if value else "0"
                try:
                    found[short] = float(num.replace(",", "."))
                except ValueError:
                    found[short] = 0.0
                break
    if not found:
        return None

    _configure_matplotlib()
    import matplotlib.pyplot as plt

    labels = list(found.keys())
    values = [found[k] for k in labels]
    colors = [mapping[next(k for k in mapping if mapping[k][0] == lab)][1] for lab in labels]
    fig, ax = plt.subplots(figsize=(5.2, 3.2))
    bars = ax.bar(labels, values, color=colors, width=0.55, edgecolor="white")
    ax.set_ylabel("Количество")
    ax.set_title("Сопоставление отметок ВПР и журнала")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    for bar, val in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.05,
            f"{int(val)}",
            ha="center",
            va="bottom",
            fontsize=9,
        )
    return _to_png(fig)
