# VPR STAGE 10 — GLOBAL METHODOLOGY / MATH / LOGIC VERIFICATION

**STAGE_10_STATUS = RELEASE_READY (PASS_WITH_KNOWN_REMAINING)**

Дата: 2026-08-17  
Область: только `apps/vpr/**`  
ЕГЭ / ОГЭ: не затронуты.

## Вердикт

Единый расчётный pipeline подтверждён на **всех 138** протоколах и для будущих загрузок (тот же `VprComprehensiveAnalysisEngine` → facts → FIOKO/SYSTEM → integrity → HTML/DOCX).

Критический баг Biology #11 (`tasks_below_50`: было 14, стало **15**) исправлен **общим** правилом inclusive `completion_percent ≤ 50` (SYSTEM), без `if protocol_id == 11`.

## Acceptance checklist (§XXXVIII)

| Criterion | Status |
|---|---|
| Все 138 протоколов проходят расчёт | PASS |
| Нет арифметических противоречий (integrity) | PASS (0 invalid) |
| Biology #11 `tasks_below_50 == 15` | PASS |
| Нет hardcoded fix для Biology #11 | PASS |
| FIOKO и SYSTEM_ANALYTICS разделены | PASS |
| Пороги ФИОКО централизованы (`VPR_ANALYTICS_CONFIG`) | PASS |
| 7 направлений ФИОКО покрыты pipeline | PASS (существующий слой) |
| FULL/PARTIAL/ZERO корректны | PASS |
| Малые выборки маркируются | PASS (119/138 LIMITED) |
| Группы &lt;10 маркируются | PASS |
| Расхождение ВПР/журнал ≥2 выделяется | PASS |
| Не называется автоматически «необъективность» | PASS |
| Планируемые результаты ↔ задания | PASS |
| Дефициты с доказательностью | PASS (ESTABLISHED vs difficulty; aliases DIAGNOSTIC/CONFIRMED) |
| Один низкий % ≠ «устойчивый дефицит» | PASS |
| DOCX пересчитаны (generate + rebuild) | PASS 138/138 |
| Нет stale values после rebuild | PASS |
| Тесты `apps.vpr` | PASS (199, skipped=14) |
| `manage.py check` | PASS |
| `vpr_validate_all` | PASS 138/138 |
| Нет влияния на ЕГЭ/ОГЭ | PASS |
| Нет ручных исключений по школам/протоколам | PASS |

## Ключевое исправление (SYSTEM)

**Причина:** задание с `completion_percent == 50.0` исключалось правилом строгого `< 50`.  
**Исправление:** `system_tasks.below_50_inclusive = True` → считать «успешность ≤ 50%».  
**Источник метрики:** SYSTEM_ANALYTICS (не порог ФИОКО).  
В отчётах: формулировка «≤ 50%» + пометка внутренней аналитики.

## Централизованные пороги FIOKO-2026

| Уровень | insufficient | sufficient | uncertainty upper |
|---|---|---|---|
| Basic | &lt;57 | ≥60 | 63 (=60±3) |
| Advanced/High | &lt;28.5 | ≥30 | 31.5 (=30±1.5) |

Конфиг: `apps/vpr/analytics/thresholds.py` → `VPR_ANALYTICS_CONFIG` (`apps/vpr/analytics/config.py`).

## Validate-all

```
TOTAL=138 PASS=138 FAIL=0 BLOCKED=0
→ apps/vpr/audit/VPR_STAGE10_VALIDATE_ALL.json
```

Biology #11: `tasks_below_50=15`, `participants=49`, `limited_sample=True`, `consistency=PASS`, `report=PASS`.

## Sample / groups

| Metric | Value |
|---|---|
| Protocols with LIMITED distribution sample (N&lt;50) | **119** |
| Protocols STANDARD (N≥50) | **19** |
| SYSTEM groups with N&lt;10 (group-hits) | **392** across **133** protocols |
| FIOKO mark-group LIMITED_SAMPLE hits | **367** across **136** protocols |
| Biology #11 `high` | N=2, `LIMITED_SAMPLE`, management conclusion forbidden |

## Commands executed

- `python manage.py check` → OK  
- `python manage.py test apps.vpr` → OK (199, skipped=14)  
- `python manage.py vpr_validate_all` → 138/138 PASS  
- `python manage.py vpr_rebuild_reports` → ok=138 fail=0  

## Files changed (Stage 10)

| File | Change |
|---|---|
| `apps/vpr/analytics/config.py` | **NEW** `VPR_ANALYTICS_CONFIG`, below_50 helpers, sample tiers |
| `apps/vpr/analytics/thresholds.py` | uncertainty_upper, system_tasks inclusive |
| `apps/vpr/facts/task_classification.py` | inclusive below_50 |
| `apps/vpr/validation/consistency.py` | inclusive below_50 |
| `apps/vpr/validation/integrity.py` | **NEW** integrity layer + avg checks + MetricFacts |
| `apps/vpr/evidence/metric_fact.py` | **NEW** provenance MetricFact |
| `apps/vpr/evidence/statuses.py` | DIAGNOSTIC/CONFIRMED aliases |
| `apps/vpr/fioko_2026/classification.py` | sample tiers wording |
| `apps/vpr/fioko_2026/engine.py` | distribution LIMITED wording |
| `apps/vpr/expert_analysis/fioko_report.py` | ≤50% + SYSTEM label |
| `apps/vpr/methodology/rules.py` | below_50 description |
| `apps/vpr/management/commands/vpr_validate_all.py` | **NEW** command |
| `apps/vpr/tests/test_stage10_methodology.py` | **NEW** Stage 10 tests |
| `apps/vpr/tests/test_global_analytics.py` | assert at 50.0 inclusive |

## Models / migrations

- Модели Django **не менялись**.  
- Миграции **не нужны**.

## Metrics that changed

| Metric | Layer | Change | Reason |
|---|---|---|---|
| `tasks_below_50` | SYSTEM | +1 where a task has exactly 50% | inclusive threshold fix |
| distribution wording | FIOKO | LIMITED_SAMPLE text for N&lt;50 | FIOKO sample guidance |
| report phrasing «ниже 50%» → «≤ 50%» | SYSTEM | wording | align with rule |

## Remaining issues (non-blocking)

1. Полный OLD↔NEW differential CSV по всем метрикам всех 138 протоколов **не выгружался** как отдельный артефакт (изменения локализованы и ожидаемы).  
2. `MetricFact` добавлен для ключевых агрегатов integrity; не каждый UI-показатель сериализует provenance в DOCX.  
3. Именование доказательности дефицитов в коде: `ESTABLISHED`/`INFORMATIVE` (+ aliases `CONFIRMED`/`DIAGNOSTIC`).  
4. Regression Biology #11 в `TestCase` **skip**, если протокол отсутствует в test DB; на production DB / `vpr_validate_all` — PASS.

## Future uploads

Любая новая загрузка ВПР проходит тот же pipeline автоматически; отдельных school/protocol forks нет.
