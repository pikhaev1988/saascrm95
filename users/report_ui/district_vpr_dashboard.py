"""
Presentation packaging for district-level VPR analytics (municipal cabinet).
Aggregates VprProtocol in the district scope — no ExamResult.
"""

from __future__ import annotations

from typing import Any


def build_district_vpr_dashboard_ui(
    *,
    protocols,
    selected_year: int | None = None,
    district=None,
) -> dict[str, Any]:
    from apps.vpr.analytics import VprAnalyticsEngine

    protocol_list = list(protocols) if protocols is not None else []
    engine = VprAnalyticsEngine()

    by_school: dict[int, dict[str, Any]] = {}
    recent = []
    total_participants = 0
    weighted_quality = 0.0
    weight_quality = 0
    weighted_abs = 0.0
    weight_abs = 0
    subjects = set()
    grades = set()

    for protocol in protocol_list:
        school = getattr(protocol, "school", None)
        sid = int(getattr(protocol, "school_id", 0) or (school.id if school else 0) or 0)
        if not sid:
            continue
        bucket = by_school.setdefault(
            sid,
            {
                "school_id": sid,
                "school_name": getattr(school, "name", None) or protocol.organization_name or "Школа",
                "school_code": getattr(school, "code", None) or "—",
                "protocols_count": 0,
                "participants": 0,
                "subjects": set(),
                "quality_sum": 0.0,
                "quality_w": 0,
                "abs_sum": 0.0,
                "abs_w": 0,
                "avg_mark_sum": 0.0,
                "avg_mark_w": 0,
            },
        )
        participants = int(protocol.participants_count or 0)
        bucket["protocols_count"] += 1
        bucket["participants"] += participants
        bucket["subjects"].add(protocol.subject or "")
        subjects.add(protocol.subject or "")
        grades.add(int(protocol.parallel or 0))
        total_participants += participants

        summary = None
        try:
            summary = engine.analyze(protocol).summary
        except Exception:
            summary = None
        if summary is not None and participants:
            if summary.knowledge_quality_percent is not None:
                q = float(summary.knowledge_quality_percent)
                bucket["quality_sum"] += q * participants
                bucket["quality_w"] += participants
                weighted_quality += q * participants
                weight_quality += participants
            if summary.absolute_achievement_percent is not None:
                a = float(summary.absolute_achievement_percent)
                bucket["abs_sum"] += a * participants
                bucket["abs_w"] += participants
                weighted_abs += a * participants
                weight_abs += participants
            if summary.avg_mark_vpr is not None:
                bucket["avg_mark_sum"] += float(summary.avg_mark_vpr) * participants
                bucket["avg_mark_w"] += participants

        recent.append(protocol)

    school_rows = []
    risk_schools = 0
    best_school = None
    best_metric = None
    for bucket in by_school.values():
        quality = (
            round(bucket["quality_sum"] / bucket["quality_w"], 1) if bucket["quality_w"] else None
        )
        abs_rate = round(bucket["abs_sum"] / bucket["abs_w"], 1) if bucket["abs_w"] else None
        avg_mark = (
            round(bucket["avg_mark_sum"] / bucket["avg_mark_w"], 2) if bucket["avg_mark_w"] else None
        )
        tone = "neutral"
        if abs_rate is not None:
            if abs_rate >= 85:
                tone = "good"
            elif abs_rate < 70:
                tone = "risk"
                risk_schools += 1
            else:
                tone = "mid"
        metric = abs_rate if abs_rate is not None else quality
        if metric is not None and (best_metric is None or float(metric) > float(best_metric)):
            best_metric = metric
            best_school = bucket["school_name"]
        school_rows.append(
            {
                "school_id": bucket["school_id"],
                "school_name": bucket["school_name"],
                "school_code": bucket["school_code"],
                "protocols_count": bucket["protocols_count"],
                "participants": bucket["participants"],
                "subjects_count": len({s for s in bucket["subjects"] if s}),
                "quality_rate": quality,
                "pass_rate": abs_rate,
                "avg_mark": avg_mark,
                "tone": tone,
                "level_pct": float(abs_rate if abs_rate is not None else (quality or 0)),
            }
        )

    school_rows.sort(key=lambda r: (-(r["pass_rate"] or -1), r["school_name"]))
    recent_sorted = sorted(
        recent,
        key=lambda p: (
            getattr(getattr(p, "upload", None), "created_at", None) is not None,
            getattr(getattr(p, "upload", None), "created_at", None),
        ),
        reverse=True,
    )[:8]

    quality_rate = round(weighted_quality / weight_quality, 1) if weight_quality else None
    pass_rate = round(weighted_abs / weight_abs, 1) if weight_abs else None
    status = _district_status(pass_rate, quality_rate, risk_schools)

    district_meta = {
        "name": getattr(district, "name", None) or "Район",
        "code": getattr(district, "code", None) or "—",
    }

    return {
        "district": district_meta,
        "status": status,
        "schools_count": len(school_rows),
        "protocols_count": len(protocol_list),
        "subjects_count": len({s for s in subjects if s}),
        "grades_count": len({g for g in grades if g}),
        "participants": total_participants,
        "quality_rate": quality_rate,
        "pass_rate": pass_rate,
        "risk_schools": risk_schools,
        "best_school": best_school,
        "best_school_score": round(float(best_metric), 1) if best_metric is not None else None,
        "schools": school_rows,
        "recent_protocols": [
            {
                "id": p.id,
                "subject": p.subject,
                "parallel": p.parallel,
                "year": p.academic_year,
                "school_name": getattr(getattr(p, "school", None), "name", None)
                or p.organization_name
                or "—",
                "uploaded_at": getattr(getattr(p, "upload", None), "created_at", None),
            }
            for p in recent_sorted
        ],
        "has_data": bool(protocol_list),
        "selected_year": selected_year,
    }


def _district_status(pass_rate, quality_rate, risk_schools) -> dict:
    if pass_rate is None:
        return {"label": "Нет данных", "tone": "neutral"}
    if float(pass_rate) >= 85 and (quality_rate or 0) >= 40 and risk_schools == 0:
        return {"label": "Устойчивый уровень", "tone": "good"}
    if float(pass_rate) < 70 or risk_schools >= 3:
        return {"label": "Требует внимания", "tone": "risk"}
    if float(pass_rate) < 85 or (quality_rate or 0) < 30:
        return {"label": "Рабочий уровень", "tone": "mid"}
    return {"label": "Стабильный уровень", "tone": "good"}
