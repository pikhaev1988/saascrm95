# VPR GLOBAL ANALYTICS CHANGELOG

Дата: 2026-08-16  
Baseline: Stage 8.1 `QUALITY_AUDIT_PASS_WITH_WARNINGS`

> **Изменения реализованы на уровне общего VPR analytics pipeline  
> и автоматически применяются ко всем существующим и будущим протоколам ВПР.**

Нет `if protocol_id == …`, нет school/subject forks в расчётах.

Архитектура:

`UPLOAD → PARSE → NORMALIZE → ANALYZE → VPRReportFacts → EVIDENCE → CONSISTENCY → NARRATIVE → SANITIZE → HTML/DOCX → FINAL VALIDATION`

---

## 1. Architecture audit

Создан: `apps/vpr/audit/VPR_GLOBAL_ANALYTICS_ARCHITECTURE.md`

## 2. Files / classes / functions changed or added

### New
| Path | Role |
|------|------|
| `apps/vpr/facts/` | `VPRReportFacts`, `TaskClassificationResult`, `build_vpr_report_facts`, `classify_task` |
| `apps/vpr/narrative/` | `NarrativeSanitizer`, user-facing labels |
| `apps/vpr/evidence/` | EvidenceStatus, CauseType, AnalyticalOrigin, EvidenceEnvelope |
| `apps/vpr/methodology/rules.py` | FIOKO_2026 / SYSTEM_ANALYTICS / LOCAL_ANALYTICS registries |
| `apps/vpr/validation/consistency.py` | `CrossReportConsistencyValidator` + invariants |
| `apps/vpr/validation/narrative.py` | `NarrativeQualityValidator` |
| `apps/vpr/validation/cross_format.py` | `CrossFormatConsistencyValidator` |
| `apps/vpr/deficits/classification.py` | EDUCATIONAL_DIFFICULTY vs EDUCATIONAL_DEFICIT |
| `apps/vpr/management/commands/vpr_rebuild_reports.py` | legacy rebuild without re-upload |
| `apps/vpr/management/commands/vpr_global_quality_audit.py` | batch audit |
| `apps/vpr/tests/test_global_analytics.py` | SSOT, sanitizer, NOT_AVAILABLE, 32+17+2=51 |

### Updated
| Path | Change |
|------|--------|
| `comprehensive_analysis/engine.py` | сборка `facts` один раз |
| `comprehensive_analysis/schemas.py` | поле `facts`; group evidence metadata |
| `comprehensive_analysis/tasks.py` | статусы только через TaskClassificationEngine |
| `comprehensive_analysis/groups.py` | origin/evidence/LIMITED_SAMPLE |
| `comprehensive_analysis/service.py` | `rebuild_protocol_analysis` |
| `deficits/config.py` | `None` completion → `not_available`, не critical |
| `expert_analysis/fioko_report.py` | facts, overlapping potential, hypothesis firewall, sanitize |
| `overview_docx.py` / `protocol_overview.html` | пользовательские формулировки, без enum в основном тексте |
| `causes/result.py` | epistemic_status default HYPOTHESIS |

## 3. Duplicate calculations removed / centralized

- below_50 / critical / problem — только `TaskClassificationResult`
- exclusive groups — только `participant_groups` → `VPRReportFacts.groups`
- positive_potential — OVERLAPPING, не суммируется с risk/stable/high
- journal equal/lower/higher — facts.comparison
- mean/median/min/max/cv — facts.scores (из analytics.summary, без пересчёта)

## 4. Validators added

- CrossReportConsistencyValidator (groups, tasks, facts, score/journal invariants, NOT_AVAILABLE→0)
- NarrativeQualityValidator (technical leaks, FACT prefix, forbidden auto-cause)
- CrossFormatConsistencyValidator (HTML/DOCX vs facts)

## 5. Tests added

- LIMITED_SAMPLE, hypothesis, deficit vs difficulty
- group 32+17+2=51
- overlapping potential
- None completion ≠ critical
- sanitizer strips technical tokens
- narrative leak detector
- methodology registries separated

## 6–12. Production run (Beget)

| Metric | Value |
|--------|-------|
| Protocols checked | **138** |
| PASS | **138** |
| FAIL | **0** |
| BLOCKED | **0** |
| Critical | **0** |
| High | **0** |
| Consistency errors | **0** |
| Narrative leaks | **0** |
| Cross-format errors | **0** |
| Hardcoded protocol patches | **0** |
| HTML | **138/138 PASS** |
| DOCX | **138/138 PASS** |
| Facts SSOT | **138/138 PASS** |
| Validator warnings (sum) | 355 (catalog PARTIAL, journal/cross-year NOT_AVAILABLE и др.) |
| Status | `QUALITY_AUDIT_PASS_WITH_WARNINGS` |

Артефакты: `VPR_GLOBAL_QUALITY_AUDIT.md`, `VPR_GLOBAL_FINAL_AUDIT.md`

### Errors found / fixed

| Issue | Fix |
|-------|-----|
| Повторный расчёт групп/заданий в narrative | `VPRReportFacts` + TaskClassificationEngine |
| positive_potential в сумме групп | OVERLAPPING_GROUP |
| None completion → critical | `not_available` |
| Technical enum в DOCX | NarrativeSanitizer + user-facing labels |
| FACT из группы риска / низкого % | hypothesis firewall |
| KPI 0% без baseline ВПР | «не задан по данным ВПР» |

### Consciously left

- Medium/Low text↔data Stage 8 (не Critical/High)
- catalog PARTIAL как статус данных
- journal / cross-year / boundary NOT_AVAILABLE
- FIOKO numeric thresholds
- Metric Contract FULL/PARTIAL/ZERO
- Validator warnings по неполноте каталога/журнала (не ошибки pipeline)

## 13. Why left

Warnings отражают ограничения данных/методологии, а не баги pipeline (этап 17 ТЗ).

## Future / legacy

Новая загрузка: `UPLOAD → persist → catalog sync → clear cache → lazy get_protocol_analysis`  
уже использует тот же engine.

Существующие протоколы: `python manage.py vpr_rebuild_reports` (без повторной загрузки файла).
