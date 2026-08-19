# VPR_FIOKO_STAGE7_1_ACCEPTANCE

Дата прогона: 2026-08-16 (production Beget)  
Источник методологии: PDF «Рекомендации по проведению анализа результатов ВПР», ФИОКО, 2026  
Базовый статус Stage 7: RELEASE_READY_WITH_WARNINGS (138/138)  
Stage 7.1: methodology hardening only (не переписывает Stage 7)

## 1. Scope

Точечное устранение трёх методологических неоднозначностей:

1. недостаточная выборка для группового анализа (N < 10);
2. смешение FIOKO и SYSTEM_ANALYTICS;
3. смешение GENERAL_PEAK и BOUNDARY_PEAK.

Вне scope: EGE/OGE, `users/export_reports.py`, school_ege / oge_dashboard, изменение FIOKO thresholds, «починка» Biology #11 profile critical, изменение Metric Contract.

## 2. Changes

| Area | Change |
|------|--------|
| `apps/vpr/fioko_2026/sample.py` | `GROUP_SAMPLE_MIN=10`, `group_sample_flags`, `limited_sample_wording`, `resolve_official_mark_boundaries` |
| `comprehensive_analysis/groups.py` + schemas | `sample_status` / `informative` на bucket |
| `fioko_2026/engine.py` + schemas | mark-group sample flags; GENERAL vs BOUNDARY peak; official-only boundaries |
| `expert_analysis/fioko_report.py` | wording: LIMITED_SAMPLE; FIOKO ≠ SYSTEM_ANALYTICS; soft group conclusions |
| HTML / DOCX | одинаковая семантика меток |
| `validation/report_validator.py` | проверки Stage 7.1 |
| `tests/test_fioko_stage7_1.py` | обязательные cases 1–10 |

## 3. Group sample fix

- `GROUP_SAMPLE_MIN = 10`
- `N >= 10` → `sample_status=INFORMATIVE`, `informative=true`
- `N < 10` → `sample_status=LIMITED_SAMPLE`, `informative=false`
- Данные и проценты сохраняются; явная маркировка; без самостоятельного FIOKO управленческого вывода
- Пример high N=3: LIMITED_SAMPLE + диагностическая формулировка

## 4. FIOKO vs SYSTEM_ANALYTICS separation

Заменена формулировка вида «в логике ФИОКО выделены группы риска…» на:

> Индивидуальный анализ выполнен на основе рекомендаций ФИОКО.  
> Дополнительно применена внутренняя аналитическая группировка (SYSTEM_ANALYTICS)…

Сохранены как SYSTEM_ANALYTICS: 80/50, CV, PreparationProfile, positive_potential, mastery 90/75/60/40, внутренние группы.

## 5. General peak vs boundary peak

- **GENERAL_PEAK** — статистическая особенность распределения; не маркер объективности
- **BOUNDARY_PEAK** — только при официальных границах 2→3 / 3→4 / 4→5 из метаданных протокола/КИМ
- Без границ → `boundary_peak_status=NOT_AVAILABLE` (без угадывания)

## 6. Objectivity logic

- Objectivity marker только при обоснованном BOUNDARY_PEAK → «возможный маркер… требующий дополнительного анализа»
- GENERAL_PEAK не создаёт objectivity warning
- Нейтральный язык: никогда «нарушение объективности установлено» только по пику

## 7. Tests

Локально:

- `manage.py check` — OK (0 issues)
- `makemigrations --check` — No changes detected
- `test_fioko_stage7_1` + `test_fioko_primary_distribution` + `test_report_validator` + `test_metric_invariants` — **34 OK**
- Ранее в сессии: FIOKO suite **56 passed, 1 skipped**

Обязательные cases (TEST 1–10) покрыты в `test_fioko_stage7_1.py` / связанных тестах.

## 8. HTML/DOCX consistency

Production acceptance: HTML **138/138 PASS**, DOCX **138/138 PASS**.  
Validator: LIMITED_SAMPLE wording и SYSTEM_ANALYTICS labels согласованы.

## 9. 138-protocol production acceptance

| Metric | Value |
|--------|-------|
| TOTAL | **138** |
| PASS | **138** |
| FAIL | **0** |
| BLOCKED | **0** |
| HTML PASS | **138** |
| DOCX PASS | **138** |
| FIOKO ERRORS (sum) | **0** |
| Avg warnings / protocol | ~2.57 |
| Catalog COMPLETE | 135 |
| Catalog PARTIAL | 3 (ids 67, 139, 140) |
| Control Biology #11 | PASS (warnings=5; profile SYSTEM_ANALYTICS — не менялся) |
| Control English #6 | PASS (warnings=4) |

Артефакт JSON: `apps/vpr/audit/VPR_FIOKO_STAGE7_1_ACCEPTANCE.json`

TOTAL=138 PASS=138 FAIL=0 BLOCKED=0

## 10. Git isolation

Изменения в VPR-контуре (`apps/vpr/*`, `templates/users/includes/school_vpr_analytics.html`, `users/report_ui/school_vpr_dashboard.py`).

Не затронуты: EGE, OGE, `users/export_reports.py`, school_ege, oge_dashboard.

`apps/vpr/analytics/engine.py` / `result.py` — наследие Stage 7 (metric contract wiring), не Stage 7.1 methodology fixes. Stage 7.1 логика — в `fioko_2026/`, groups, report, validator, tests.

## 11. Remaining warnings

Методологические WARNING (не ERROR):

- LIMITED_SAMPLE для малых групп;
- distribution / sample notes;
- journal / cross-year NOT_AVAILABLE где данных нет;
- boundary peaks NOT_AVAILABLE при отсутствии официальной шкалы перевода;
- catalog PARTIAL (3 протокола);
- Biology #11 profile critical остаётся как SYSTEM_ANALYTICS_DIFFERENCE.

## 12. Final status

**RELEASE_READY_WITH_WARNINGS**

Условия выполнены:

- 138/138 PASS, FAIL=0, BLOCKED=0  
- HTML=138/138, DOCX=138/138  
- validator PASS, errors=0  

---

## Protocol table

| protocol_id | subject | class | year | N | tasks | difficulty_mapped | planned_results_mapped | FIOKO_status | warnings | errors | HTML | DOCX |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Математика | 10 | 2026 | 24 | 17 | 17/17 | COMPLETE | PASS | 2 | 0 | PASS | PASS |
| 2 | Физика | 10 | 2026 | 24 | 14 | 14/14 | COMPLETE | PASS | 3 | 0 | PASS | PASS |
| 3 | Обществознание | 10 | 2026 | 24 | 15 | 15/15 | COMPLETE | PASS | 2 | 0 | PASS | PASS |
| 4 | Русский язык | 10 | 2026 | 24 | 16 | 16/16 | COMPLETE | PASS | 5 | 0 | PASS | PASS |
| 5 | Математика | 4 | 2026 | 89 | 14 | 14/14 | COMPLETE | PASS | 1 | 0 | PASS | PASS |
| 6 | Английский язык | 4 | 2026 | 29 | 5 | 5/5 | COMPLETE | PASS | 4 | 0 | PASS | PASS |
| 7 | Окружающий мир | 4 | 2026 | 29 | 22 | 22/22 | COMPLETE | PASS | 2 | 0 | PASS | PASS |
| 8 | Литературное чтение | 4 | 2026 | 31 | 15 | 15/15 | COMPLETE | PASS | 2 | 0 | PASS | PASS |
| 9 | Русский язык | 4 | 2026 | 89 | 15 | 15/15 | COMPLETE | PASS | 1 | 0 | PASS | PASS |
| 10 | Математика | 5 | 2026 | 104 | 18 | 18/18 | COMPLETE | PASS | 1 | 0 | PASS | PASS |
| 11 | Биология | 5 | 2026 | 49 | 29 | 29/29 | COMPLETE | PASS | 5 | 0 | PASS | PASS |
| 12 | История | 5 | 2026 | 30 | 8 | 8/8 | COMPLETE | PASS | 3 | 0 | PASS | PASS |
| 13 | География | 5 | 2026 | 56 | 17 | 17/17 | COMPLETE | PASS | 1 | 0 | PASS | PASS |
| 14 | Английский язык | 5 | 2026 | 47 | 7 | 7/7 | COMPLETE | PASS | 4 | 0 | PASS | PASS |
| 15 | Литература | 5 | 2026 | 29 | 11 | 11/11 | COMPLETE | PASS | 4 | 0 | PASS | PASS |
| 16 | Русский язык | 5 | 2026 | 105 | 10 | 10/10 | COMPLETE | PASS | 1 | 0 | PASS | PASS |
| 17 | Математика | 6 | 2026 | 97 | 18 | 18/18 | COMPLETE | PASS | 1 | 0 | PASS | PASS |
| 18 | Биология | 6 | 2026 | 46 | 27 | 27/27 | COMPLETE | PASS | 2 | 0 | PASS | PASS |
| 19 | История | 6 | 2026 | 50 | 9 | 9/9 | COMPLETE | PASS | 1 | 0 | PASS | PASS |
| 20 | География | 6 | 2026 | 51 | 17 | 17/17 | COMPLETE | PASS | 1 | 0 | PASS | PASS |
| 21 | Английский язык | 6 | 2026 | 24 | 7 | 7/7 | COMPLETE | PASS | 3 | 0 | PASS | PASS |
| 22 | Литература | 6 | 2026 | 23 | 11 | 11/11 | COMPLETE | PASS | 2 | 0 | PASS | PASS |
| 23 | Русский язык | 6 | 2026 | 97 | 10 | 10/10 | COMPLETE | PASS | 3 | 0 | PASS | PASS |
| 24 | Математика | 7 | 2026 | 112 | 19 | 19/19 | COMPLETE | PASS | 1 | 0 | PASS | PASS |
| 25 | Физика | 7 | 2026 | 28 | 10 | 10/10 | COMPLETE | PASS | 2 | 0 | PASS | PASS |
| 26 | Информатика | 7 | 2026 | 29 | 15 | 15/15 | COMPLETE | PASS | 3 | 0 | PASS | PASS |
| 27 | Биология | 7 | 2026 | 25 | 27 | 27/27 | COMPLETE | PASS | 2 | 0 | PASS | PASS |
| 28 | История | 7 | 2026 | 58 | 10 | 10/10 | COMPLETE | PASS | 3 | 0 | PASS | PASS |
| 29 | География | 7 | 2026 | 30 | 17 | 17/17 | COMPLETE | PASS | 2 | 0 | PASS | PASS |
| 30 | Английский язык | 7 | 2026 | 29 | 7 | 7/7 | COMPLETE | PASS | 2 | 0 | PASS | PASS |
| 31 | Литература | 7 | 2026 | 25 | 11 | 11/11 | COMPLETE | PASS | 2 | 0 | PASS | PASS |
| 32 | Русский язык | 7 | 2026 | 112 | 13 | 13/13 | COMPLETE | PASS | 1 | 0 | PASS | PASS |
| 33 | Математика | 8 | 2026 | 105 | 18 | 18/18 | COMPLETE | PASS | 1 | 0 | PASS | PASS |
| 34 | Физика | 8 | 2026 | 27 | 10 | 10/10 | COMPLETE | PASS | 2 | 0 | PASS | PASS |
| 35 | Химия | 8 | 2026 | 28 | 21 | 21/21 | COMPLETE | PASS | 2 | 0 | PASS | PASS |
| 36 | Биология | 8 | 2026 | 22 | 29 | 29/29 | COMPLETE | PASS | 3 | 0 | PASS | PASS |
| 37 | История | 8 | 2026 | 27 | 10 | 10/10 | COMPLETE | PASS | 2 | 0 | PASS | PASS |
| 38 | География | 8 | 2026 | 28 | 17 | 17/17 | COMPLETE | PASS | 2 | 0 | PASS | PASS |
| 39 | Английский язык | 8 | 2026 | 28 | 7 | 7/7 | COMPLETE | PASS | 2 | 0 | PASS | PASS |
| 40 | Обществознание | 8 | 2026 | 22 | 15 | 15/15 | COMPLETE | PASS | 2 | 0 | PASS | PASS |
| 41 | Литература | 8 | 2026 | 28 | 11 | 11/11 | COMPLETE | PASS | 3 | 0 | PASS | PASS |
| 42 | Русский язык | 8 | 2026 | 105 | 16 | 16/16 | COMPLETE | PASS | 1 | 0 | PASS | PASS |
| 43 | Русский язык | 5 | 2026 | 47 | 10 | 10/10 | COMPLETE | PASS | 3 | 0 | PASS | PASS |
| 44 | Русский язык | 6 | 2026 | 44 | 10 | 10/10 | COMPLETE | PASS | 4 | 0 | PASS | PASS |
| 45 | Математика | 5 | 2026 | 47 | 18 | 18/18 | COMPLETE | PASS | 3 | 0 | PASS | PASS |
| 46 | Математика | 6 | 2026 | 44 | 18 | 18/18 | COMPLETE | PASS | 2 | 0 | PASS | PASS |
| 49 | Русский язык | 6 | 2026 | 117 | 10 | 10/10 | COMPLETE | PASS | 4 | 0 | PASS | PASS |
| 50 | Русский язык | 4 | 2026 | 153 | 15 | 15/15 | COMPLETE | PASS | 2 | 0 | PASS | PASS |
| 51 | Русский язык | 7 | 2026 | 170 | 13 | 13/13 | COMPLETE | PASS | 2 | 0 | PASS | PASS |
| 52 | Русский язык | 4 | 2026 | 37 | 15 | 15/15 | COMPLETE | PASS | 3 | 0 | PASS | PASS |
| 53 | Русский язык | 4 | 2026 | 37 | 15 | 15/15 | COMPLETE | PASS | 3 | 0 | PASS | PASS |
| 54 | Математика | 4 | 2026 | 37 | 14 | 14/14 | COMPLETE | PASS | 2 | 0 | PASS | PASS |
| 55 | Английский язык | 4 | 2026 | 17 | 5 | 5/5 | COMPLETE | PASS | 2 | 0 | PASS | PASS |
| 56 | Окружающий мир | 4 | 2026 | 20 | 22 | 22/22 | COMPLETE | PASS | 2 | 0 | PASS | PASS |
| 57 | Английский язык | 5 | 2026 | 15 | 7 | 7/7 | COMPLETE | PASS | 2 | 0 | PASS | PASS |
| 58 | Биология | 5 | 2026 | 12 | 29 | 29/29 | COMPLETE | PASS | 3 | 0 | PASS | PASS |
| 59 | Русский язык | 5 | 2026 | 42 | 10 | 10/10 | COMPLETE | PASS | 3 | 0 | PASS | PASS |
| 60 | География | 5 | 2026 | 31 | 17 | 17/17 | COMPLETE | PASS | 2 | 0 | PASS | PASS |
| 61 | История | 5 | 2026 | 12 | 8 | 8/8 | COMPLETE | PASS | 3 | 0 | PASS | PASS |
| 62 | Литература | 5 | 2026 | 15 | 11 | 11/11 | COMPLETE | PASS | 3 | 0 | PASS | PASS |
| 63 | Математика | 5 | 2026 | 42 | 18 | 18/18 | COMPLETE | PASS | 2 | 0 | PASS | PASS |
| 64 | Русский язык | 4 | 2026 | 42 | 15 | 15/15 | COMPLETE | PASS | 3 | 0 | PASS | PASS |
| 65 | Математика | 4 | 2026 | 42 | 14 | 14/14 | COMPLETE | PASS | 2 | 0 | PASS | PASS |
| 66 | Окружающий мир | 4 | 2026 | 22 | 22 | 22/22 | COMPLETE | PASS | 4 | 0 | PASS | PASS |
| 67 | Литературное чтение | 4 | 2026 | 20 | 19 | 19/19 | PARTIAL | PASS | 2 | 0 | PASS | PASS |
| 68 | Русский язык | 5 | 2026 | 57 | 10 | 10/10 | COMPLETE | PASS | 1 | 0 | PASS | PASS |
| 69 | Математика | 5 | 2026 | 57 | 18 | 18/18 | COMPLETE | PASS | 1 | 0 | PASS | PASS |
| 70 | Биология | 5 | 2026 | 19 | 29 | 29/29 | COMPLETE | PASS | 5 | 0 | PASS | PASS |
| 71 | История | 5 | 2026 | 17 | 8 | 8/8 | COMPLETE | PASS | 4 | 0 | PASS | PASS |
| 72 | География | 5 | 2026 | 38 | 17 | 17/17 | COMPLETE | PASS | 3 | 0 | PASS | PASS |
| 73 | Английский язык | 5 | 2026 | 21 | 7 | 7/7 | COMPLETE | PASS | 2 | 0 | PASS | PASS |
| 74 | Литература | 5 | 2026 | 19 | 11 | 11/11 | COMPLETE | PASS | 2 | 0 | PASS | PASS |
| 75 | Биология | 6 | 2026 | 21 | 27 | 27/27 | COMPLETE | PASS | 5 | 0 | PASS | PASS |
| 76 | География | 6 | 2026 | 18 | 17 | 17/17 | COMPLETE | PASS | 2 | 0 | PASS | PASS |
| 77 | История | 6 | 2026 | 18 | 9 | 9/9 | COMPLETE | PASS | 4 | 0 | PASS | PASS |
| 78 | Литература | 6 | 2026 | 21 | 11 | 11/11 | COMPLETE | PASS | 2 | 0 | PASS | PASS |
| 79 | Математика | 6 | 2026 | 39 | 18 | 18/18 | COMPLETE | PASS | 4 | 0 | PASS | PASS |
| 80 | Русский язык | 6 | 2026 | 39 | 10 | 10/10 | COMPLETE | PASS | 3 | 0 | PASS | PASS |
| 81 | Английский язык | 7 | 2026 | 17 | 7 | 7/7 | COMPLETE | PASS | 2 | 0 | PASS | PASS |
| 82 | Информатика | 7 | 2026 | 17 | 15 | 15/15 | COMPLETE | PASS | 2 | 0 | PASS | PASS |
| 83 | Литература | 7 | 2026 | 23 | 11 | 11/11 | COMPLETE | PASS | 3 | 0 | PASS | PASS |
| 84 | Математика | 7 | 2026 | 40 | 19 | 19/19 | COMPLETE | PASS | 2 | 0 | PASS | PASS |
| 85 | Русский язык | 7 | 2026 | 40 | 13 | 13/13 | COMPLETE | PASS | 2 | 0 | PASS | PASS |
| 86 | Физика | 7 | 2026 | 17 | 10 | 10/10 | COMPLETE | PASS | 2 | 0 | PASS | PASS |
| 87 | Биология | 8 | 2026 | 18 | 29 | 29/29 | COMPLETE | PASS | 9 | 0 | PASS | PASS |
| 88 | История | 8 | 2026 | 24 | 10 | 10/10 | COMPLETE | PASS | 2 | 0 | PASS | PASS |
| 89 | Литература | 8 | 2026 | 18 | 11 | 11/11 | COMPLETE | PASS | 3 | 0 | PASS | PASS |
| 90 | Математика | 8 | 2026 | 42 | 18 | 18/18 | COMPLETE | PASS | 3 | 0 | PASS | PASS |
| 91 | Русский язык | 8 | 2026 | 42 | 16 | 16/16 | COMPLETE | PASS | 3 | 0 | PASS | PASS |
| 92 | Химия | 8 | 2026 | 24 | 21 | 21/21 | COMPLETE | PASS | 5 | 0 | PASS | PASS |
| 93 | Математика | 10 | 2026 | 16 | 17 | 17/17 | COMPLETE | PASS | 2 | 0 | PASS | PASS |
| 94 | Обществознание | 10 | 2026 | 16 | 15 | 15/15 | COMPLETE | PASS | 2 | 0 | PASS | PASS |
| 95 | Русский язык | 10 | 2026 | 16 | 16 | 16/16 | COMPLETE | PASS | 2 | 0 | PASS | PASS |
| 96 | Физика | 10 | 2026 | 16 | 14 | 14/14 | COMPLETE | PASS | 2 | 0 | PASS | PASS |
| 97 | Биология | 6 | 2026 | 15 | 27 | 27/27 | COMPLETE | PASS | 6 | 0 | PASS | PASS |
| 98 | География | 6 | 2026 | 16 | 17 | 17/17 | COMPLETE | PASS | 2 | 0 | PASS | PASS |
| 99 | История | 6 | 2026 | 15 | 9 | 9/9 | COMPLETE | PASS | 4 | 0 | PASS | PASS |
| 100 | Литература | 6 | 2026 | 16 | 11 | 11/11 | COMPLETE | PASS | 2 | 0 | PASS | PASS |
| 101 | Математика | 6 | 2026 | 30 | 18 | 18/18 | COMPLETE | PASS | 4 | 0 | PASS | PASS |
| 102 | Русский язык | 6 | 2026 | 30 | 10 | 10/10 | COMPLETE | PASS | 2 | 0 | PASS | PASS |
| 103 | Английский язык | 7 | 2026 | 20 | 7 | 7/7 | COMPLETE | PASS | 2 | 0 | PASS | PASS |
| 104 | Информатика | 7 | 2026 | 20 | 15 | 15/15 | COMPLETE | PASS | 2 | 0 | PASS | PASS |
| 105 | Литература | 7 | 2026 | 17 | 11 | 11/11 | COMPLETE | PASS | 2 | 0 | PASS | PASS |
| 106 | Математика | 7 | 2026 | 37 | 19 | 19/19 | COMPLETE | PASS | 2 | 0 | PASS | PASS |
| 107 | Русский язык | 7 | 2026 | 37 | 13 | 13/13 | COMPLETE | PASS | 2 | 0 | PASS | PASS |
| 108 | Физика | 7 | 2026 | 17 | 10 | 10/10 | COMPLETE | PASS | 2 | 0 | PASS | PASS |
| 109 | Окружающий мир | 4 | 2026 | 21 | 22 | 22/22 | COMPLETE | PASS | 3 | 0 | PASS | PASS |
| 110 | Математика | 4 | 2026 | 42 | 14 | 14/14 | COMPLETE | PASS | 2 | 0 | PASS | PASS |
| 111 | Русский язык | 4 | 2026 | 42 | 15 | 15/15 | COMPLETE | PASS | 2 | 0 | PASS | PASS |
| 112 | Литературное чтение | 4 | 2026 | 21 | 15 | 15/15 | COMPLETE | PASS | 5 | 0 | PASS | PASS |
| 113 | Русский язык | 5 | 2026 | 28 | 10 | 10/10 | COMPLETE | PASS | 3 | 0 | PASS | PASS |
| 114 | Математика | 5 | 2026 | 29 | 18 | 18/18 | COMPLETE | PASS | 2 | 0 | PASS | PASS |
| 115 | Биология | 5 | 2026 | 14 | 29 | 29/29 | COMPLETE | PASS | 3 | 0 | PASS | PASS |
| 116 | История | 5 | 2026 | 14 | 8 | 8/8 | COMPLETE | PASS | 2 | 0 | PASS | PASS |
| 117 | География | 5 | 2026 | 15 | 17 | 17/17 | COMPLETE | PASS | 2 | 0 | PASS | PASS |
| 118 | Английский язык | 5 | 2026 | 15 | 7 | 7/7 | COMPLETE | PASS | 3 | 0 | PASS | PASS |
| 119 | Русский язык | 6 | 2026 | 42 | 10 | 10/10 | COMPLETE | PASS | 5 | 0 | PASS | PASS |
| 120 | Математика | 6 | 2026 | 41 | 18 | 18/18 | COMPLETE | PASS | 3 | 0 | PASS | PASS |
| 121 | Биология | 6 | 2026 | 26 | 27 | 27/27 | COMPLETE | PASS | 3 | 0 | PASS | PASS |
| 122 | География | 6 | 2026 | 15 | 17 | 17/17 | COMPLETE | PASS | 2 | 0 | PASS | PASS |
| 123 | Английский язык | 6 | 2026 | 11 | 7 | 7/7 | COMPLETE | PASS | 2 | 0 | PASS | PASS |
| 124 | История | 6 | 2026 | 15 | 9 | 9/9 | COMPLETE | PASS | 3 | 0 | PASS | PASS |
| 125 | Русский язык | 7 | 2026 | 32 | 13 | 13/13 | COMPLETE | PASS | 2 | 0 | PASS | PASS |
| 126 | Математика | 7 | 2026 | 33 | 19 | 19/19 | COMPLETE | PASS | 2 | 0 | PASS | PASS |
| 127 | Физика | 7 | 2026 | 15 | 10 | 10/10 | COMPLETE | PASS | 3 | 0 | PASS | PASS |
| 128 | История | 7 | 2026 | 13 | 10 | 10/10 | COMPLETE | PASS | 3 | 0 | PASS | PASS |
| 129 | География | 7 | 2026 | 18 | 17 | 17/17 | COMPLETE | PASS | 2 | 0 | PASS | PASS |
| 130 | Литература | 7 | 2026 | 18 | 11 | 11/11 | COMPLETE | PASS | 3 | 0 | PASS | PASS |
| 131 | Русский язык | 8 | 2026 | 25 | 16 | 16/16 | COMPLETE | PASS | 2 | 0 | PASS | PASS |
| 132 | Математика | 8 | 2026 | 25 | 18 | 18/18 | COMPLETE | PASS | 2 | 0 | PASS | PASS |
| 133 | Физика | 8 | 2026 | 13 | 10 | 10/10 | COMPLETE | PASS | 2 | 0 | PASS | PASS |
| 134 | Химия | 8 | 2026 | 12 | 21 | 21/21 | COMPLETE | PASS | 4 | 0 | PASS | PASS |
| 135 | Английский язык | 8 | 2026 | 13 | 7 | 7/7 | COMPLETE | PASS | 3 | 0 | PASS | PASS |
| 136 | Обществознание | 8 | 2026 | 12 | 15 | 15/15 | COMPLETE | PASS | 2 | 0 | PASS | PASS |
| 137 | Русский язык | 10 | 2026 | 12 | 16 | 16/16 | COMPLETE | PASS | 2 | 0 | PASS | PASS |
| 138 | Математика | 10 | 2026 | 12 | 17 | 17/17 | COMPLETE | PASS | 3 | 0 | PASS | PASS |
| 139 | Химия | 10 | 2026 | 11 | 16 | 16/16 | PARTIAL | PASS | 2 | 0 | PASS | PASS |
| 140 | Литература | 10 | 2026 | 12 | 19 | 19/19 | PARTIAL | PASS | 4 | 0 | PASS | PASS |
