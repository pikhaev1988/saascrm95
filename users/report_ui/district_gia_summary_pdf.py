"""
PDF presentation for district GIA summary — formatting only.
"""

from __future__ import annotations

from io import BytesIO
from typing import Any

DOC_VERSION = "1.0"


def render_district_gia_summary_pdf(data: dict[str, Any], *, helpers: dict) -> BytesIO:
    """
    helpers: pdf_register_font, pdf_table, pdf_build_document from export_reports
    """
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import KeepTogether, PageBreak, Paragraph, Spacer, Table, TableStyle

    pdf_register = helpers["register_font"]
    pdf_table = helpers["table"]
    pdf_build = helpers["build"]

    font_name = pdf_register()
    story: list = []

    title_s = ParagraphStyle(
        "DgsTitle",
        fontName=font_name,
        fontSize=22,
        leading=26,
        textColor=colors.HexColor("#0B1F3A"),
        alignment=TA_CENTER,
        spaceAfter=8,
    )
    h1_s = ParagraphStyle(
        "DgsH1",
        fontName=font_name,
        fontSize=12,
        leading=15,
        textColor=colors.HexColor("#0B1F3A"),
        spaceBefore=10,
        spaceAfter=5,
    )
    body_s = ParagraphStyle(
        "DgsBody",
        fontName=font_name,
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#1A2332"),
        alignment=TA_LEFT,
        spaceAfter=2,
    )
    muted_s = ParagraphStyle(
        "DgsMuted",
        fontName=font_name,
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#5D6D7E"),
        alignment=TA_CENTER,
        spaceAfter=4,
    )
    card_s = ParagraphStyle(
        "DgsCard",
        fontName=font_name,
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#1A2332"),
        leftIndent=2,
        spaceAfter=0,
    )
    kpi_val = ParagraphStyle(
        "DgsKpiVal",
        fontName=font_name,
        fontSize=14,
        leading=16,
        textColor=colors.HexColor("#0B1F3A"),
        alignment=TA_LEFT,
    )
    kpi_lab = ParagraphStyle(
        "DgsKpiLab",
        fontName=font_name,
        fontSize=7,
        leading=9,
        textColor=colors.HexColor("#5D6D7E"),
        alignment=TA_LEFT,
    )

    if not data.get("has_data"):
        story.append(Paragraph(data.get("message") or "Недостаточно данных.", body_s))
        return pdf_build(story)

    label = "ЕГЭ" if data.get("exam_type") == "ege" else "ОГЭ"
    district = data.get("district_name") or "Муниципалитет"
    year = data.get("year") or ""
    formed = data.get("generated_at") or ""
    avg_label = "Средняя оценка" if data.get("exam_type") == "oge" else "Средний балл"

    # Title page
    story.append(Spacer(1, 24 * mm))
    story.append(Paragraph("УПРАВЛЕНИЕ ОБРАЗОВАНИЯ", muted_s))
    story.append(Paragraph(str(district), muted_s))
    story.append(Spacer(1, 14 * mm))
    story.append(Paragraph("ОФИЦИАЛЬНЫЙ АНАЛИТИЧЕСКИЙ ОТЧЁТ", muted_s))
    story.append(Paragraph("Свод результатов ГИА по району", title_s))
    story.append(Paragraph(f"Муниципальный свод итогов {label}", muted_s))
    story.append(Spacer(1, 10 * mm))
    for line in (
        f"Вид экзамена: <b>{label}</b>",
        f"Отчётный период: <b>{year}</b>",
        f"Муниципалитет: <b>{district}</b>",
        f"Дата формирования: <b>{formed}</b>",
        f"Версия документа: <b>{DOC_VERSION}</b>",
    ):
        story.append(Paragraph(line, body_s))
    story.append(Spacer(1, 18 * mm))
    story.append(Paragraph("Конфиденциально · для служебного пользования", muted_s))
    story.append(PageBreak())

    # KPI dashboard
    story.append(Paragraph("◆  Общие показатели", h1_s))
    delta = data.get("avg_delta")
    if delta is None:
        delta_s = "—"
    else:
        try:
            df = float(delta)
            delta_s = f"+{df}" if df > 0 else str(df)
        except (TypeError, ValueError):
            delta_s = "—"

    kpi_defs = [
        ("Участники", str(data.get("participants"))),
        (avg_label, str(data.get("avg_score"))),
        ("Качество знаний", f"{data.get('quality_rate')}%"),
        ("Успеваемость", f"{data.get('pass_rate')}%"),
        ("Высокобалльники", str(data.get("high_count"))),
        ("Неудовлетворительные", str(data.get("failed_count"))),
        ("Динамика", delta_s),
        ("Количество школ", str(data.get("schools_count"))),
    ]

    def _kpi_cell(label: str, value: str):
        return [
            Paragraph(f"<b>{value}</b>", kpi_val),
            Paragraph(label, kpi_lab),
        ]

    row1 = []
    row2 = []
    for i, (lab, val) in enumerate(kpi_defs):
        cell = Table(
            [[Paragraph(f"<b>{val}</b>", kpi_val)], [Paragraph(lab, kpi_lab)]],
            colWidths=[38 * mm],
        )
        cell.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F4F7FA")),
                    ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#D5DDE5")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("LINEBEFORE", (0, 0), (0, -1), 2.2, colors.HexColor("#5B9BD5")),
                ]
            )
        )
        (row1 if i < 4 else row2).append(cell)
    story.append(Table([row1], colWidths=[40 * mm] * 4))
    story.append(Spacer(1, 3 * mm))
    story.append(Table([row2], colWidths=[40 * mm] * 4))
    story.append(Spacer(1, 5 * mm))

    def _card(text: str, *, fill: str, accent: str, badge: str, num: int | None = None):
        prefix = f"<b>{num:02d}</b>  " if num is not None else ""
        inner = Paragraph(f"{prefix}<font color='{accent}'><b>{badge}</b></font>  {text}", card_s)
        t = Table([[inner]], colWidths=[170 * mm])
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(fill)),
                    ("LINEBEFORE", (0, 0), (0, -1), 2.5, colors.HexColor(accent)),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        return KeepTogether([t, Spacer(1, 2)])

    def _kind(title: str) -> str:
        t = (title or "").lower()
        if "пять главных проблем" in t or ("проблем" in t and "пять" in t):
            return "problems"
        if "сильн" in t:
            return "strengths"
        if "прогноз риск" in t or ("риск" in t and "прогноз" in t):
            return "risk"
        if "приоритетный план" in t or "план действий" in t or "рекоменд" in t:
            return "plan"
        return "info"

    sections = data.get("report_sections") or []
    if sections:
        for section in sections:
            title = str(section.get("title") or "Раздел")
            items = list(section.get("items") or [])
            story.append(Paragraph(f"◆  {title}", h1_s))
            kind = _kind(title)
            for i, item in enumerate(items, start=1):
                text = str(item)
                if not text.strip():
                    continue
                if kind == "problems":
                    story.append(_card(text, fill="#F8ECEC", accent="#9B2C2C", badge="Риск", num=i))
                elif kind == "strengths":
                    story.append(_card(text, fill="#EAF6EF", accent="#1E7A4A", badge="Рост", num=i))
                elif kind == "risk":
                    story.append(_card(text, fill="#F8F1E6", accent="#A85A1A", badge="Риск", num=i))
                elif kind == "plan":
                    story.append(_card(text, fill="#EAF2F8", accent="#1B4F72", badge="Приоритет", num=i))
                else:
                    story.append(_card(text, fill="#EAF2F8", accent="#5B9BD5", badge="Информация"))
    else:
        story.append(Paragraph("◆  Краткое резюме", h1_s))
        for line in data.get("executive_summary") or data.get("summary") or []:
            story.append(_card(str(line), fill="#EAF2F8", accent="#5B9BD5", badge="Информация"))

    # Subjects / schools tables
    story.append(Paragraph("Таблица · предметные результаты", h1_s))
    subj = []
    for row in data.get("subject_rows") or []:
        subj.append(
            [
                str(row.get("exam__subject") or "—")[:30],
                str(row.get("participants") or ""),
                f"{float(row.get('avg') or 0):.2f}",
                str(row.get("pass_rate") if row.get("pass_rate") is not None else ""),
                str(row.get("quality_rate") if row.get("quality_rate") is not None else ""),
                str(row.get("risk") if row.get("risk") not in (None, "") else "—")[:18],
            ]
        )
    story.append(
        _navy_table(
            ["Предмет", "Участ.", "Средний", "Усп., %", "Кач., %", "Риск"],
            subj,
            [48 * mm, 16 * mm, 20 * mm, 18 * mm, 18 * mm, 30 * mm],
            font_name,
        )
    )
    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph("Таблица · результаты образовательных организаций", h1_s))
    schools = []
    for row in (data.get("school_rows") or [])[:50]:
        schools.append(
            [
                str(row.get("student__school__name") or "—")[:40],
                str(row.get("student__school__code") or "")[:10],
                str(row.get("participants") or ""),
                f"{float(row.get('avg') or 0):.2f}",
                str(row.get("pass_rate") if row.get("pass_rate") is not None else ""),
            ]
        )
    story.append(
        _navy_table(
            ["ОО", "Код", "Участ.", "Средний", "Усп., %"],
            schools,
            [78 * mm, 18 * mm, 18 * mm, 22 * mm, 20 * mm],
            font_name,
        )
    )

    return pdf_build(story)


def _navy_table(headers: list[str], rows: list[list], col_widths: list, font_name: str):
    from reportlab.lib import colors
    from reportlab.platypus import Table, TableStyle

    data = [headers] + rows
    tbl = Table(data, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(
        TableStyle(
            [
                ("FONT", (0, 0), (-1, -1), font_name, 8),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B1F3A")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#DCE8F3")),
                ("FONT", (0, 0), (-1, 0), font_name, 8),
                ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                ("ALIGN", (0, 0), (0, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D5DDE5")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7FAFC")]),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return tbl
