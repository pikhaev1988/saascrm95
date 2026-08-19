# VPR GLOBAL ANALYTICS ARCHITECTURE

Дата аудита: 2026-08-16  
Область: `apps/vpr` (все протоколы, текущие и будущие)  
Правило: изменения только на уровне общего pipeline; без `protocol_id` / school / subject forks в расчётах.

## Pipeline (end-to-end)

```
UPLOAD (.xlsx)
  → PARSE (F1 registry)
  → PERSIST ORM (VprProtocol + tasks/students/scores)
  → CATALOG SYNC (subject/class/year mapping)
  → CLEAR ANALYSIS CACHE
  → (lazy) ANALYTICS ENGINE
  → DEFICITS → CAUSES → CONCLUSION
  → COMPREHENSIVE ASSEMBLE (groups/tasks/objectivity/…)
  → FIOKO_2026 LAYER
  → EXPERT + SUBJECT REPORT (16 sections)
  → VALIDATOR
  → HTML / DOCX
  → QUALITY AUDIT (optional management command / stage runners)
```

**Важно:** аналитика **не** прекомпилируется при импорте.  
Первый запрос overview / conclusion / DOCX вызывает `get_protocol_analysis()` → полный пересчёт.  
Следовательно, любая правка общего engine автоматически применяется ко всем 138 и ко всем будущим протоколам при регенерации.

---

## 1. Parser

| | |
|--|--|
| **Files** | `parsers/registry.py`, `parsers/f1_individual.py`, `parsers/base.py`, `parsers/dto.py`, `validators/protocol.py` |
| **Key** | `detect_and_parse`, `F1IndividualResultsParser`, `validate_vpr_file` |
| **In → Out** | Excel path → `VprParseResult` (subject, parallel, year, org, tasks, students, scores) |
| **Global** | Да. Единственный production template F1; registry расширяем новыми парсерами. |

Upload entry: `views.VprUploadView` → `services/import_service.py` (`create_upload`, `validate_and_preview`, `confirm_import`).

---

## 2. Normalized data

| | |
|--|--|
| **Files** | `repositories/protocol_repository.py`, `models.py`, `services/catalog_sync.py`, `services/catalog_lookup.py` |
| **Key** | `VprProtocolRepository.persist_import`, `sync_catalog_for_protocol`, `VprTaskCatalogLookup.resolve` |
| **In → Out** | `VprParseResult` → ORM (`VprProtocol`, `VprTask`, `VprStudentResult`, `VprTaskScore`) + catalog join |
| **Global** | Да. Содержимое каталога зависит от subject/class/year (данные), не от форков формул. |

Отдельного модуля «normalize» нет: parse DTO → ORM → catalog enrichment at analyze time.

---

## 3. Metric calculation

| | |
|--|--|
| **Files** | `analytics/engine.py`, `analytics/metrics.py`, `analytics/stats.py`, `analytics/result.py`, `analytics/thresholds.py` |
| **Key** | `VprAnalyticsEngine.analyze` → `VprAnalyticsResult` |
| **Outputs** | summary (N, mean, median, stdev, CV…), marks, scores, tasks (FULL/PARTIAL/ZERO, rates, completion_percent), topics, skills, students |
| **Contracts** | FULL+PARTIAL+ZERO = N; `completion_percent ≠ full_score_rate` для multi-score |
| **Global** | Да. Чистая математика протокола. |

---

## 4. Group calculation

Две параллельные системы (не смешивать attribution):

### A. SYSTEM_ANALYTICS (completion 80/50)

| | |
|--|--|
| **Files** | `comprehensive_analysis/groups.py`, `fioko_2026/sample.py` |
| **Key** | `VprParticipantGroupAnalyzer.analyze` |
| **Buckets** | high ≥80%, medium ≥50%, else risk (+ `positive_potential` отдельно) |
| **Sample** | `group_sample_flags` → INFORMATIVE / LIMITED_SAMPLE (N&lt;10) |

### B. FIOKO mark groups

| | |
|--|--|
| **Files** | `fioko_2026/engine.py` (`_build_groups`) |
| **Key** | группировка по `mark_vpr`; anomalies только при informative samples |

**classification_origin:** SYSTEM_ANALYTICS vs FIOKO должен быть явным в отчёте.

---

## 5. Task analysis

| | |
|--|--|
| **Files** | `analytics/engine.py` (`_build_tasks`), `comprehensive_analysis/tasks.py`, `fioko_2026/engine.py` + `classification.py` |
| **Key** | `VprTaskAnalyzer`, `classify_fioko_level`, `build_task_rate_fields` |
| **Global** | Да. |

---

## 6. Planned results

| | |
|--|--|
| **Files** | `fioko_2026/engine.py` (`_enrich_planned_from_catalog`, `_build_planned_results`), `comprehensive_analysis/achievement.py`, `conclusion/rules.py` (`classify_mastery`), `expert_analysis/fioko_report.py` §7 |
| **Global** | Классификация глобальна; тексты планируемых результатов — из каталога. |

---

## 7. Educational deficits

| | |
|--|--|
| **Files** | `deficits/engine.py`, `deficits/config.py`, `deficits/result.py`, `fioko_2026` skill deficits, `expert_analysis/fioko_report.py` §9 |
| **Key** | `VprDeficitEngine.analyze`; `DeficitInsight.evidence_status` = ESTABLISHED \| INSUFFICIENT_DATA (Stage 8.1) |
| **Gap (для модернизации)** | Не всегда разделены EDUCATIONAL_DIFFICULTY / DEFICIT / CAUSE / RECOMMENDATION; expert narrative ранее мог стать категоричным deficit (исправлено 8.1). |

---

## 8. Causes

| | |
|--|--|
| **Files** | `causes/engine.py`, `causes/labels.py`, `causes/result.py` |
| **Key** | `VprCauseAnalysisEngine.analyze(analytics, deficits)` |
| **Gap** | Нет явного `cause_type=FACT|HYPOTHESIS` на всех выходах; риск автоматической причинности из completion. |

---

## 9. Recommendations

| | |
|--|--|
| **Files** | `comprehensive_analysis/recommendations.py`, `fioko_2026/management.py`, `fioko_report.py` §§10–15 |
| **Key** | `VprRecommendationEngine`, `build_management_recommendations`, `_section15_plan` |
| **Chain (целевая)** | PROBLEM → EVIDENCE → POSSIBLE INTERPRETATION → ACTION → RESPONSIBLE → PERIOD → KPI → CONTROL |

---

## 10. DOCX renderer

| | |
|--|--|
| **Files** | `overview_docx.py` (протокол, 16 разделов), `school_analysis/docx_export.py` (школа) |
| **Key** | `generate_overview_report_docx` |
| **Gate** | `validate=True` → `VprReportBlockedError` блокирует выгрузку |
| **Gap** | Служебные метки (SYSTEM_ANALYTICS, LIMITED_SAMPLE, evidence_status) иногда в основном тексте. |

HTML: `templates/vpr/protocol_overview.html`, `views_overview.py`.

---

## 11. Quality audit

| | |
|--|--|
| **Runtime** | `validation/report_validator.py` — `VprReportValidator` |
| **Batch** | `audit/run_stage7_acceptance.py`, `audit/run_stage8_quality_audit.py` |
| **Artifacts** | `audit/VPR_*_ACCEPTANCE*`, `VPR_STAGE8_*` |
| **Gap** | Нет единой management-команды `vpr_global_quality_audit` с CrossReportConsistencyValidator. |

Baseline Stage 8.1: `QUALITY_AUDIT_PASS_WITH_WARNINGS` (High=0, Critical=0).

---

## 12. Upload integration

```
confirm_import / reimport
  → persist_import
  → sync_catalog_for_protocol
  → clear_protocol_analysis_cache
```

Новый протокол **автоматически** попадает в тот же lazy pipeline при первом открытии отчёта.  
Отдельный ручной «patch» не требуется.

---

## 13. Regeneration integration

| | |
|--|--|
| **Files** | `comprehensive_analysis/service.py`, `comprehensive_analysis/cache.py` |
| **Key** | `get_protocol_analysis(protocol, use_cache=…)`, `clear_protocol_analysis_cache` |
| **Default** | `VPR_ANALYSIS_CACHE_ENABLED=False` → полный пересчёт на каждый запрос |
| **Reports** | `SubjectReport` / DOCX не персистятся — всегда из актуального analysis |

Повторная генерация старого отчёта = новая логика engine.

---

## Comprehensive call graph (один запрос)

```
get_protocol_analysis
  → VprComprehensiveAnalysisEngine.analyze
      → VprAnalyticsEngine
      → VprDeficitEngine
      → VprCauseAnalysisEngine
      → VprConclusionEngine
      → achievement / tasks / topics / skills / groups / objectivity / recommendations
      → build_fioko_2026_layer
  → (view) build_subject_report → build_fioko_report + build_expert_analysis
  → VprReportValidator (optional hard gate)
  → HTML template | generate_overview_report_docx
```

---

## Thresholds / magic numbers (текущее состояние)

| Location | Role |
|----------|------|
| `analytics/thresholds.py` → `VPR_THRESHOLDS` | Канон: deficits, groups 80/50, CV, objectivity, fioko_2026 bands, sample mins |
| `deficits/thresholds.json` | Mastery bands для deficit engine |
| `causes/labels.py` | SHARE_LOCAL_MAX / SHARE_MASS_MAX (дубли) |
| `fioko_2026/sample.py` | GROUP_SAMPLE_MIN=10 fallback |
| `fioko_2026/engine.py` | 40/80 hard_for_all/easiest; +5pp anomaly |
| `fioko_2026/management.py` | mark_2 ≥ 30 |
| `validation/report_validator.py` | RATE_SUM_TOLERANCE; forbidden phrases |

**Цель модернизации:** явные `FIOKO_2026_RULES` / `SYSTEM_ANALYTICS_RULES` / `LOCAL_ANALYTICS_RULES` с name/value/source/description/scope/effective_year.

---

## Protocol / school / subject patches

| Kind | Status |
|------|--------|
| Runtime `if protocol_id == …` в analytics | **Не найдено** |
| Runtime school-specific formula forks | **Не найдено** |
| Subject-specific | Только interpretation wording (`expert_analysis/subject_models.py`) и catalog data |
| Audit baseline ids (6, 11, 140) | Только QA matrices, не production branching |

---

## Gaps prioritized for global modernization

1. **Evidence envelope** — единый статус для выводов (не только deficits).  
2. **CAUSE FACT vs HYPOTHESIS** — запрет FACT из одного completion_percent.  
3. **CrossReportConsistencyValidator** — risk+stable+high == N; % ↔ count.  
4. **Centralized methodology config** — убрать разрозненные magic numbers.  
5. **DOCX presentation** — служебные метки отдельно от управленческого текста.  
6. **`manage.py vpr_global_quality_audit`** — прогон всех протоколов + отчёт.  
7. Сохранить Stage 8.1 baseline; не ломать Metric Contract / LIMITED_SAMPLE / peak logic.

---

## Statement

Архитектура уже единая для всех протоколов: upload → lazy analyze → report.  
Модернизация должна усиливать **этот** pipeline, а не добавлять исключения по protocol_id.

**Этап 1 (аудит) завершён. Далее — изменения в общем pipeline.**
