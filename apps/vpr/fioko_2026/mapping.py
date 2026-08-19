"""
Mapping: 7 направлений анализа ФИОКО → существующие 16 разделов VPR-отчёта.

Программно доступно: FIOKO_DIRECTION_TO_SECTIONS / FIOKO_ANALYSIS_DIRECTION.
"""

from __future__ import annotations

from typing import Any

# Канонические коды 7 направлений (ФИОКО 2026, стр. 4)
FIOKO_ANALYSIS_DIRECTION = {
    "individual_results": {
        "code": "individual_results",
        "title": "Индивидуальные результаты",
        "section": "1",
        "page": 5,
        "source": "FIOKO_2026",
    },
    "marks_statistics": {
        "code": "marks_statistics",
        "title": "Статистика по отметкам",
        "section": "2",
        "page": 7,
        "source": "FIOKO_2026",
    },
    "journal_comparison": {
        "code": "journal_comparison",
        "title": "Сравнение отметок с отметками по журналу",
        "section": "3",
        "page": 10,
        "source": "FIOKO_2026",
    },
    "primary_distribution": {
        "code": "primary_distribution",
        "title": "Распределение первичных баллов",
        "section": "4",
        "page": 13,
        "source": "FIOKO_2026",
    },
    "task_performance": {
        "code": "task_performance",
        "title": "Выполнение заданий",
        "section": "5",
        "page": 16,
        "source": "FIOKO_2026",
    },
    "planned_results": {
        "code": "planned_results",
        "title": "Достижение планируемых результатов",
        "section": "6",
        "page": 20,
        "source": "FIOKO_2026",
    },
    "groups_of_participants": {
        "code": "groups_of_participants",
        "title": "Выполнение заданий группами участников",
        "section": "7",
        "page": 23,
        "source": "FIOKO_2026",
    },
}

# FIOKO_ANALYSIS_DIRECTION -> VPR_REPORT_SECTIONS[]
FIOKO_DIRECTION_TO_SECTIONS: dict[str, list[str]] = {
    "individual_results": ["individual_groups"],
    "marks_statistics": ["marks_rows"],
    "journal_comparison": ["objectivity_cycle"],
    "primary_distribution": ["scores_rows"],
    "task_performance": ["task_performance_rows", "deficit_items"],
    "planned_results": ["planned_results"],
    "groups_of_participants": ["group_task_insights", "individual_groups"],
}

# Обратное покрытие: раздел отчёта → направления ФИОКО
SECTION_TO_FIOKO_DIRECTIONS: dict[str, list[str]] = {
    "passport": [],
    "individual_groups": ["individual_results", "groups_of_participants"],
    "marks_rows": ["marks_statistics"],
    "objectivity_cycle": ["journal_comparison"],
    "scores_rows": ["primary_distribution"],
    "task_performance_rows": ["task_performance"],
    "planned_results": ["planned_results"],
    "group_task_insights": ["groups_of_participants"],
    "deficit_items": ["task_performance", "planned_results"],
    "admin_director": [],  # management — problem-oriented (стр. 27), не 1 из 7 отчётов
    "smo_actions": [],
    "teacher_deficits": [],
    "parent_actions": [],
    "method_recommendations": [],
    "action_plan": [],
    "final_conclusion": [],
}


def get_fioko_mapping_matrix() -> dict[str, Any]:
    return {
        "directions": dict(FIOKO_ANALYSIS_DIRECTION),
        "direction_to_sections": {k: list(v) for k, v in FIOKO_DIRECTION_TO_SECTIONS.items()},
        "section_to_directions": {k: list(v) for k, v in SECTION_TO_FIOKO_DIRECTIONS.items()},
        "source": "FIOKO_2026",
        "document_year": 2026,
    }
