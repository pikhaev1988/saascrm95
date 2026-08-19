# VPR STAGE 8 — FINAL REPORT QUALITY AUDIT

Дата: production Beget · audit-only · методология Stage 7.1 не изменялась.

## Summary

| Metric | Value |
|--------|-------|
| TOTAL | 138 |
| A | 0 |
| B | 137 |
| C | 1 |
| D | 0 |
| Critical | 0 |
| High | 2 |
| Medium | 12 |
| Low | 38 |
| forbidden_wording_count | 0 |
| catalog_partial_count | 3 |
| limited_sample_count | 133 |
| html_docx_mismatch_count | 0 |
| numeric_mismatch_count | 50 |
| fioko_attribution_issues | 0 |
| status | QUALITY_AUDIT_REQUIRES_FIXES |

**Final status: `QUALITY_AUDIT_REQUIRES_FIXES`**

## Interpretation

| Signal | Meaning |
|--------|---------|
| Grade A = 0 | У всех 138 протоколов есть validator warnings → минимум Grade B (по шкале Stage 8). |
| Grade B = 137 | Методологически приемлемо; замечания Medium/Low или только warnings. |
| Grade C = 1 | Protocol **#140** (Литература, 10 кл., catalog=PARTIAL): 2× High по `deficits.evidence`. |
| Grade D = 0 | Critical-ошибок нет. |
| Critical = 0 | Нет блокирующих методологических ошибок. |
| High = 2 | Оба на #140: deficit items без evidence / linked_tasks / linked_results. |
| Medium = 12 | Подозрение text↔data (проценты в тексте не сопоставлены с известными метриками; возможны ложные срабатывания округления). |
| Low = 38 | Более слабые text↔data подозрения. |
| forbidden_wording = 0 | Запрещённые фразы не найдены. |
| FIOKO attribution issues = 0 | SYSTEM_ANALYTICS не выдаётся за FIOKO requirement. |
| HTML/DOCX mismatch = 0 | Ключевые маркеры согласованы на 138/138. |
| limited_sample_count = 133 | **Информативно**: у 133 протоколов есть ≥1 группа N&lt;10 (LIMITED_SAMPLE). Это не ошибка Stage 7.1. |
| catalog_partial = 3 | #67, #139, #140. |
| numeric_mismatch_count = 50 | Протоколы с text↔data Low/Medium на оси Numeric (не Metric Contract FAIL; FULL+PARTIAL+ZERO и NaN/inf не выявлены). |

### Proposed fixes (не применялись)

1. **P140 / deficits.evidence (High)**  
   - current: narrative deficit без `evidence` / `linked_tasks` / `linked_results`  
   - problem: дефицит без доказательного основания при catalog=PARTIAL  
   - proposed_fix: добавить evidence либо статус `INSUFFICIENT_DATA` / `LIMITED`; не усиливать формулировки в заключении.

2. **text↔data Medium/Low (12+38)**  
   - problem: автоматический scan процентов в тексте vs structured fields  
   - proposed_fix: ручная выборочная проверка; при подтверждении — единый источник чисел для narrative.

## Scope

- Все production VPR protocols (ожидается 138).
- Проверены: numeric, text↔data, FIOKO attribution, groups/LIMITED_SAMPLE,
  objectivity, multi-score wording, deficits evidence, teacher wording,
  management/KPI, catalog PARTIAL, cross-year/subject, conclusion, HTML/DOCX, design.
- Код методологии **не изменялся**.

## Quality matrix

| Protocol | Subject | Class | Numeric | Text | FIOKO | Groups | Objectivity | Multi | Deficits | KPI | HTML/DOCX | Grade |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Математика | 10 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 2 | Физика | 10 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 3 | Обществознание | 10 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 4 | Русский язык | 10 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 5 | Математика | 4 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 6 | Английский язык | 4 | Low | Low | OK | OK | OK | OK | OK | OK | OK | B |
| 7 | Окружающий мир | 4 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 8 | Литературное чтение | 4 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 9 | Русский язык | 4 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 10 | Математика | 5 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 11 | Биология | 5 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 12 | История | 5 | Low | Low | OK | OK | OK | OK | OK | OK | OK | B |
| 13 | География | 5 | Low | Low | OK | OK | OK | OK | OK | OK | OK | B |
| 14 | Английский язык | 5 | Low | Low | OK | OK | OK | OK | OK | OK | OK | B |
| 15 | Литература | 5 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 16 | Русский язык | 5 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 17 | Математика | 6 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 18 | Биология | 6 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 19 | История | 6 | Low | Low | OK | OK | OK | OK | OK | OK | OK | B |
| 20 | География | 6 | Low | Low | OK | OK | OK | OK | OK | OK | OK | B |
| 21 | Английский язык | 6 | Medium | Medium | OK | OK | OK | OK | OK | OK | OK | B |
| 22 | Литература | 6 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 23 | Русский язык | 6 | Low | Low | OK | OK | OK | OK | OK | OK | OK | B |
| 24 | Математика | 7 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 25 | Физика | 7 | Low | Low | OK | OK | OK | OK | OK | OK | OK | B |
| 26 | Информатика | 7 | Low | Low | OK | OK | OK | OK | OK | OK | OK | B |
| 27 | Биология | 7 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 28 | История | 7 | Low | Low | OK | OK | OK | OK | OK | OK | OK | B |
| 29 | География | 7 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 30 | Английский язык | 7 | Medium | Medium | OK | OK | OK | OK | OK | OK | OK | B |
| 31 | Литература | 7 | Low | Low | OK | OK | OK | OK | OK | OK | OK | B |
| 32 | Русский язык | 7 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 33 | Математика | 8 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 34 | Физика | 8 | Low | Low | OK | OK | OK | OK | OK | OK | OK | B |
| 35 | Химия | 8 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 36 | Биология | 8 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 37 | История | 8 | Low | Low | OK | OK | OK | OK | OK | OK | OK | B |
| 38 | География | 8 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 39 | Английский язык | 8 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 40 | Обществознание | 8 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 41 | Литература | 8 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 42 | Русский язык | 8 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 43 | Русский язык | 5 | Low | Low | OK | OK | OK | OK | OK | OK | OK | B |
| 44 | Русский язык | 6 | Low | Low | OK | OK | OK | OK | OK | OK | OK | B |
| 45 | Математика | 5 | Low | Low | OK | OK | OK | OK | OK | OK | OK | B |
| 46 | Математика | 6 | Medium | Medium | OK | OK | OK | OK | OK | OK | OK | B |
| 49 | Русский язык | 6 | Medium | Medium | OK | OK | OK | OK | OK | OK | OK | B |
| 50 | Русский язык | 4 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 51 | Русский язык | 7 | Low | Low | OK | OK | OK | OK | OK | OK | OK | B |
| 52 | Русский язык | 4 | Low | Low | OK | OK | OK | OK | OK | OK | OK | B |
| 53 | Русский язык | 4 | Low | Low | OK | OK | OK | OK | OK | OK | OK | B |
| 54 | Математика | 4 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 55 | Английский язык | 4 | Medium | Medium | OK | OK | OK | OK | OK | OK | OK | B |
| 56 | Окружающий мир | 4 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 57 | Английский язык | 5 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 58 | Биология | 5 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 59 | Русский язык | 5 | Low | Low | OK | OK | OK | OK | OK | OK | OK | B |
| 60 | География | 5 | Low | Low | OK | OK | OK | OK | OK | OK | OK | B |
| 61 | История | 5 | Low | Low | OK | OK | OK | OK | OK | OK | OK | B |
| 62 | Литература | 5 | Low | Low | OK | OK | OK | OK | OK | OK | OK | B |
| 63 | Математика | 5 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 64 | Русский язык | 4 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 65 | Математика | 4 | Medium | Medium | OK | OK | OK | OK | OK | OK | OK | B |
| 66 | Окружающий мир | 4 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 67 | Литературное чтение | 4 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 68 | Русский язык | 5 | Medium | Medium | OK | OK | OK | OK | OK | OK | OK | B |
| 69 | Математика | 5 | Low | Low | OK | OK | OK | OK | OK | OK | OK | B |
| 70 | Биология | 5 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 71 | История | 5 | Low | Low | OK | OK | OK | OK | OK | OK | OK | B |
| 72 | География | 5 | Medium | Medium | OK | OK | OK | OK | OK | OK | OK | B |
| 73 | Английский язык | 5 | Low | Low | OK | OK | OK | OK | OK | OK | OK | B |
| 74 | Литература | 5 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 75 | Биология | 6 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 76 | География | 6 | Low | Low | OK | OK | OK | OK | OK | OK | OK | B |
| 77 | История | 6 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 78 | Литература | 6 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 79 | Математика | 6 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 80 | Русский язык | 6 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 81 | Английский язык | 7 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 82 | Информатика | 7 | Medium | Medium | OK | OK | OK | OK | OK | OK | OK | B |
| 83 | Литература | 7 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 84 | Математика | 7 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 85 | Русский язык | 7 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 86 | Физика | 7 | Low | Low | OK | OK | OK | OK | OK | OK | OK | B |
| 87 | Биология | 8 | Low | Low | OK | OK | OK | OK | OK | OK | OK | B |
| 88 | История | 8 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 89 | Литература | 8 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 90 | Математика | 8 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 91 | Русский язык | 8 | Low | Low | OK | OK | OK | OK | OK | OK | OK | B |
| 92 | Химия | 8 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 93 | Математика | 10 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 94 | Обществознание | 10 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 95 | Русский язык | 10 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 96 | Физика | 10 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 97 | Биология | 6 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 98 | География | 6 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 99 | История | 6 | Low | Low | OK | OK | OK | OK | OK | OK | OK | B |
| 100 | Литература | 6 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 101 | Математика | 6 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 102 | Русский язык | 6 | Medium | Medium | OK | OK | OK | OK | OK | OK | OK | B |
| 103 | Английский язык | 7 | Low | Low | OK | OK | OK | OK | OK | OK | OK | B |
| 104 | Информатика | 7 | Low | Low | OK | OK | OK | OK | OK | OK | OK | B |
| 105 | Литература | 7 | Low | Low | OK | OK | OK | OK | OK | OK | OK | B |
| 106 | Математика | 7 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 107 | Русский язык | 7 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 108 | Физика | 7 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 109 | Окружающий мир | 4 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 110 | Математика | 4 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 111 | Русский язык | 4 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 112 | Литературное чтение | 4 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 113 | Русский язык | 5 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 114 | Математика | 5 | Low | Low | OK | OK | OK | OK | OK | OK | OK | B |
| 115 | Биология | 5 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 116 | История | 5 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 117 | География | 5 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 118 | Английский язык | 5 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 119 | Русский язык | 6 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 120 | Математика | 6 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 121 | Биология | 6 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 122 | География | 6 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 123 | Английский язык | 6 | Medium | Medium | OK | OK | OK | OK | OK | OK | OK | B |
| 124 | История | 6 | Medium | Medium | OK | OK | OK | OK | OK | OK | OK | B |
| 125 | Русский язык | 7 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 126 | Математика | 7 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 127 | Физика | 7 | Low | Low | OK | OK | OK | OK | OK | OK | OK | B |
| 128 | История | 7 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 129 | География | 7 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 130 | Литература | 7 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 131 | Русский язык | 8 | Low | Low | OK | OK | OK | OK | OK | OK | OK | B |
| 132 | Математика | 8 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 133 | Физика | 8 | Low | Low | OK | OK | OK | OK | OK | OK | OK | B |
| 134 | Химия | 8 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 135 | Английский язык | 8 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 136 | Обществознание | 8 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 137 | Русский язык | 10 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 138 | Математика | 10 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 139 | Химия | 10 | OK | OK | OK | OK | OK | OK | OK | OK | OK | B |
| 140 | Литература | 10 | OK | OK | OK | OK | OK | OK | High | OK | OK | C |

## Control cases

- #6 Английский язык class=4: Grade=B, catalog=COMPLETE, findings=1, warnings=4
- #11 Биология class=5: Grade=B, catalog=COMPLETE, findings=0, warnings=5
- #67 Литературное чтение class=4: Grade=B, catalog=PARTIAL, findings=0, warnings=2
- #139 Химия class=10: Grade=B, catalog=PARTIAL, findings=0, warnings=2
- #140 Литература class=10: Grade=C, catalog=PARTIAL, findings=2, warnings=4

## Catalog PARTIAL detail

### Protocol 67 — Литературное чтение

- PARTIAL зафиксирован; отдельных catalog-findings нет (mapping gap отражён статусом).

### Protocol 139 — Химия

- PARTIAL зафиксирован; отдельных catalog-findings нет (mapping gap отражён статусом).

### Protocol 140 — Литература

- catalog=PARTIAL; Grade=C; warnings=4.
- **High:** 2 deficit items без evidence/tasks/results (см. Findings).
- Риск: narrative по дефицитам при неполном catalog mapping — требуется `INSUFFICIENT_DATA` / `LIMITED`, а не усиленные выводы.

## Findings (by severity)

### Critical (0)

_none_

### High (2)

- **P140** / `deficits.evidence`: Дефицит без доказательного основания  
  current: Образовательные дефициты по предмета читаются в логике профиля «сбалансированная подготовка»: важны тип дефицита (локаль  
  evidence: no evidence/tasks/results  
  proposed_fix: Добавить evidence или пометить INSUFFICIENT_DATA
- **P140** / `deficits.evidence`: Дефицит без доказательного основания  
  current: Дефициты ближе к локальным: точечные потери не складываются в межраздельную системную проблему.  
  evidence: no evidence/tasks/results  
  proposed_fix: Добавить evidence или пометить INSUFFICIENT_DATA

### Medium (12)

- **P21** / `text_data`: Подозрение на text↔data inconsistency (проценты в тексте не найдены в данных)  
  current: unmatched_percents≈8  
  evidence: marks_cycle.interpretation:33.3% :: Доля отметок «4» и «5» (33.3%) недостаточна: выявлены признаки ухудшения / ограничения качества обра; marks_cycle.interpretation:45.8% :: Высокая доля «3» (45.8%) с  
  proposed_fix: Сверить округления и источники чисел в тексте
- **P30** / `text_data`: Подозрение на text↔data inconsistency (проценты в тексте не найдены в данных)  
  current: unmatched_percents≈10  
  evidence: individual_cycle.interpretation:70.0% :: Обучающиеся с положительным потенциалом: 70086, 70097, 70100, 70109. SYSTEM_ANALYTICS: дополнительна; marks_cycle.interpretation:58.6% :: Высокая доля «3» (58.  
  proposed_fix: Сверить округления и источники чисел в тексте
- **P46** / `text_data`: Подозрение на text↔data inconsistency (проценты в тексте не найдены в данных)  
  current: unmatched_percents≈8  
  evidence: marks_cycle.interpretation:40.9% :: Доля отметок «4» и «5» (40.9%) соответствует умеренному качеству знаний: положительный контур есть, ; marks_cycle.interpretation:47.7% :: Высокая доля «3» (47.7%) с  
  proposed_fix: Сверить округления и источники чисел в тексте
- **P49** / `text_data`: Подозрение на text↔data inconsistency (проценты в тексте не найдены в данных)  
  current: unmatched_percents≈9  
  evidence: marks_cycle.interpretation:52.1% :: Высокая доля «3» (52.1%) свидетельствует о преобладании базового уровня без устойчивого перехода к п; groups.task_evidence:96.0% :: задание 1K3 (сильные 96% / риск   
  proposed_fix: Сверить округления и источники чисел в тексте
- **P55** / `text_data`: Подозрение на text↔data inconsistency (проценты в тексте не найдены в данных)  
  current: unmatched_percents≈9  
  evidence: individual_cycle.interpretation:70.0% :: Обучающиеся с положительным потенциалом: 40011, 40003, 40005, 40002, 40004…. SYSTEM_ANALYTICS: допол; marks_cycle.interpretation:41.2% :: Доля отметок «4» и «5  
  proposed_fix: Сверить округления и источники чисел в тексте
- **P65** / `text_data`: Подозрение на text↔data inconsistency (проценты в тексте не найдены в данных)  
  current: unmatched_percents≈8  
  evidence: marks_cycle.interpretation:11.9% :: Отметки «2» (11.9%) присутствуют локально и задают зону индивидуального сопровождения.; groups.task_evidence:14.0% :: задание 9.1 (сильные 100% / риск 14%); groups.  
  proposed_fix: Сверить округления и источники чисел в тексте
- **P68** / `text_data`: Подозрение на text↔data inconsistency (проценты в тексте не найдены в данных)  
  current: unmatched_percents≈10  
  evidence: individual_cycle.interpretation:70.0% :: Обучающиеся с положительным потенциалом: 50012, 50031, 50056, 50043, 50020…. SYSTEM_ANALYTICS: допол; marks_cycle.interpretation:45.6% :: Доля отметок «4» и «5  
  proposed_fix: Сверить округления и источники чисел в тексте
- **P72** / `text_data`: Подозрение на text↔data inconsistency (проценты в тексте не найдены в данных)  
  current: unmatched_percents≈9  
  evidence: individual_cycle.interpretation:70.0% :: Обучающиеся с положительным потенциалом: 50010, 50043, 50056, 50047, 50007…. SYSTEM_ANALYTICS: допол; marks_cycle.interpretation:44.7% :: Доля отметок «4» и «5  
  proposed_fix: Сверить округления и источники чисел в тексте
- **P82** / `text_data`: Подозрение на text↔data inconsistency (проценты в тексте не найдены в данных)  
  current: unmatched_percents≈8  
  evidence: individual_cycle.interpretation:70.0% :: Обучающиеся с положительным потенциалом: 70027. SYSTEM_ANALYTICS: дополнительная характеристика (не ; marks_cycle.interpretation:41.2% :: Доля отметок «4» и «5  
  proposed_fix: Сверить округления и источники чисел в тексте
- **P102** / `text_data`: Подозрение на text↔data inconsistency (проценты в тексте не найдены в данных)  
  current: unmatched_percents≈8  
  evidence: individual_cycle.interpretation:70.0% :: Обучающиеся с положительным потенциалом: 60023, 60027, 60007, 60008, 60010…. SYSTEM_ANALYTICS: допол; marks_cycle.interpretation:40.0% :: Доля отметок «4» и «5  
  proposed_fix: Сверить округления и источники чисел в тексте
- **P123** / `text_data`: Подозрение на text↔data inconsistency (проценты в тексте не найдены в данных)  
  current: unmatched_percents≈9  
  evidence: individual_cycle.interpretation:70.0% :: Обучающиеся с положительным потенциалом: 60009, 60005, 60007, 60010. SYSTEM_ANALYTICS: дополнительна; groups.characteristic:70.0% :: SYSTEM_ANALYTICS: дополнит  
  proposed_fix: Сверить округления и источники чисел в тексте
- **P124** / `text_data`: Подозрение на text↔data inconsistency (проценты в тексте не найдены в данных)  
  current: unmatched_percents≈9  
  evidence: marks_cycle.interpretation:46.7% :: Доля отметок «4» и «5» (46.7%) соответствует умеренному качеству знаний: положительный контур есть, ; marks_cycle.interpretation:46.7% :: Высокая доля «3» (46.7%) с  
  proposed_fix: Сверить округления и источники чисел в тексте

### Low (38)

- **P6** / `text_data`: Подозрение на text↔data inconsistency (проценты в тексте не найдены в данных)  
  current: unmatched_percents≈5  
  evidence: marks_cycle.interpretation:31.0% :: Доля отметок «4» и «5» (31.0%) недостаточна: выявлены признаки ухудшения / ограничения качества обра; groups.task_evidence:87.0% :: задание 1 (сильные 87% / риск 14  
  proposed_fix: Сверить округления и источники чисел в тексте
- **P12** / `text_data`: Подозрение на text↔data inconsistency (проценты в тексте не найдены в данных)  
  current: unmatched_percents≈6  
  evidence: marks_cycle.interpretation:23.3% :: Доля отметок «4» и «5» (23.3%) недостаточна: выявлены признаки ухудшения / ограничения качества обра; groups.task_evidence:38.0% :: задание 3 (сильные 100% / риск 3  
  proposed_fix: Сверить округления и источники чисел в тексте
- **P13** / `text_data`: Подозрение на text↔data inconsistency (проценты в тексте не найдены в данных)  
  current: unmatched_percents≈7  
  evidence: individual_cycle.interpretation:70.0% :: Обучающиеся с положительным потенциалом: 50050, 50055, 50030, 50037, 50047…. SYSTEM_ANALYTICS: допол; marks_cycle.interpretation:46.4% :: Высокая доля «3» (46.  
  proposed_fix: Сверить округления и источники чисел в тексте
- **P14** / `text_data`: Подозрение на text↔data inconsistency (проценты в тексте не найдены в данных)  
  current: unmatched_percents≈6  
  evidence: individual_cycle.interpretation:70.0% :: Обучающиеся с положительным потенциалом: 50037, 50095, 50035, 50047, 50051…. SYSTEM_ANALYTICS: допол; groups.characteristic:70.0% :: SYSTEM_ANALYTICS: дополнит  
  proposed_fix: Сверить округления и источники чисел в тексте
- **P19** / `text_data`: Подозрение на text↔data inconsistency (проценты в тексте не найдены в данных)  
  current: unmatched_percents≈6  
  evidence: individual_cycle.interpretation:70.0% :: Обучающиеся с положительным потенциалом: 60083, 60060, 60052. SYSTEM_ANALYTICS: дополнительная харак; marks_cycle.interpretation:42.0% :: Высокая доля «3» (42.  
  proposed_fix: Сверить округления и источники чисел в тексте
- **P20** / `text_data`: Подозрение на text↔data inconsistency (проценты в тексте не найдены в данных)  
  current: unmatched_percents≈6  
  evidence: individual_cycle.interpretation:70.0% :: Обучающиеся с положительным потенциалом: 60091, 60021, 60016, 60077. SYSTEM_ANALYTICS: дополнительна; groups.characteristic:70.0% :: SYSTEM_ANALYTICS: дополнит  
  proposed_fix: Сверить округления и источники чисел в тексте
- **P23** / `text_data`: Подозрение на text↔data inconsistency (проценты в тексте не найдены в данных)  
  current: unmatched_percents≈6  
  evidence: marks_cycle.interpretation:38.1% :: Доля отметок «4» и «5» (38.1%) недостаточна: выявлены признаки ухудшения / ограничения качества обра; groups.task_evidence:12.0% :: задание 4.1 (сильные 86% / риск   
  proposed_fix: Сверить округления и источники чисел в тексте
- **P25** / `text_data`: Подозрение на text↔data inconsistency (проценты в тексте не найдены в данных)  
  current: unmatched_percents≈5  
  evidence: marks_cycle.interpretation:57.1% :: Высокая доля «3» (57.1%) свидетельствует о преобладании базового уровня без устойчивого перехода к п; groups.task_evidence:12.0% :: задание 3 (сильные 100% / риск 1  
  proposed_fix: Сверить округления и источники чисел в тексте
- **P26** / `text_data`: Подозрение на text↔data inconsistency (проценты в тексте не найдены в данных)  
  current: unmatched_percents≈6  
  evidence: marks_cycle.interpretation:24.1% :: Доля отметок «4» и «5» (24.1%) недостаточна: выявлены признаки ухудшения / ограничения качества обра; groups.task_evidence:83.0% :: задание 14 (сильные 83% / риск 0  
  proposed_fix: Сверить округления и источники чисел в тексте
- **P28** / `text_data`: Подозрение на text↔data inconsistency (проценты в тексте не найдены в данных)  
  current: unmatched_percents≈5  
  evidence: marks_cycle.interpretation:48.3% :: Высокая доля «3» (48.3%) свидетельствует о преобладании базового уровня без устойчивого перехода к п; groups.task_evidence:89.0% :: задание 10 (сильные 89% / риск 2  
  proposed_fix: Сверить округления и источники чисел в тексте
- **P31** / `text_data`: Подозрение на text↔data inconsistency (проценты в тексте не найдены в данных)  
  current: unmatched_percents≈6  
  evidence: individual_cycle.interpretation:70.0% :: Обучающиеся с положительным потенциалом: 70017, 70018, 70010, 70023, 70014…. SYSTEM_ANALYTICS: допол; groups.characteristic:70.0% :: SYSTEM_ANALYTICS: дополнит  
  proposed_fix: Сверить округления и источники чисел в тексте
- **P34** / `text_data`: Подозрение на text↔data inconsistency (проценты в тексте не найдены в данных)  
  current: unmatched_percents≈6  
  evidence: individual_cycle.interpretation:70.0% :: Обучающиеся с положительным потенциалом: 80037, 80030, 80035. SYSTEM_ANALYTICS: дополнительная харак; marks_cycle.interpretation:55.6% :: Высокая доля «3» (55.  
  proposed_fix: Сверить округления и источники чисел в тексте
- **P37** / `text_data`: Подозрение на text↔data inconsistency (проценты в тексте не найдены в данных)  
  current: unmatched_percents≈5  
  evidence: marks_cycle.interpretation:33.3% :: Доля отметок «4» и «5» (33.3%) недостаточна: выявлены признаки ухудшения / ограничения качества обра; groups.task_evidence:11.0% :: задание 2 (сильные 100% / риск 1  
  proposed_fix: Сверить округления и источники чисел в тексте
- **P43** / `text_data`: Подозрение на text↔data inconsistency (проценты в тексте не найдены в данных)  
  current: unmatched_percents≈5  
  evidence: individual_cycle.interpretation:70.0% :: Обучающиеся с положительным потенциалом: 50006, 50016, 50007, 50019, 50020…. SYSTEM_ANALYTICS: допол; groups.characteristic:70.0% :: SYSTEM_ANALYTICS: дополнит  
  proposed_fix: Сверить округления и источники чисел в тексте
- **P44** / `text_data`: Подозрение на text↔data inconsistency (проценты в тексте не найдены в данных)  
  current: unmatched_percents≈5  
  evidence: marks_cycle.interpretation:40.9% :: Доля отметок «4» и «5» (40.9%) соответствует умеренному качеству знаний: положительный контур есть, ; groups.task_evidence:22.0% :: задание 2K2 (сильные 100% / риск  
  proposed_fix: Сверить округления и источники чисел в тексте
- **P45** / `text_data`: Подозрение на text↔data inconsistency (проценты в тексте не найдены в данных)  
  current: unmatched_percents≈5  
  evidence: individual_cycle.interpretation:70.0% :: Обучающиеся с положительным потенциалом: 50010, 50021, 50033, 50019, 50042. SYSTEM_ANALYTICS: дополн; marks_cycle.interpretation:12.8% :: Отметки «2» (12.8%) п  
  proposed_fix: Сверить округления и источники чисел в тексте
- **P51** / `text_data`: Подозрение на text↔data inconsistency (проценты в тексте не найдены в данных)  
  current: unmatched_percents≈6  
  evidence: marks_cycle.interpretation:37.1% :: Доля отметок «4» и «5» (37.1%) недостаточна: выявлены признаки ухудшения / ограничения качества обра; marks_cycle.interpretation:11.8% :: Отметки «2» (11.8%) присут  
  proposed_fix: Сверить округления и источники чисел в тексте
- **P52** / `text_data`: Подозрение на text↔data inconsistency (проценты в тексте не найдены в данных)  
  current: unmatched_percents≈6  
  evidence: marks_cycle.interpretation:10.8% :: Отметки «2» (10.8%) присутствуют локально и задают зону индивидуального сопровождения.; groups.task_evidence:12.0% :: задание 11 (сильные 100% / риск 12%); groups.t  
  proposed_fix: Сверить округления и источники чисел в тексте
- **P53** / `text_data`: Подозрение на text↔data inconsistency (проценты в тексте не найдены в данных)  
  current: unmatched_percents≈6  
  evidence: marks_cycle.interpretation:10.8% :: Отметки «2» (10.8%) присутствуют локально и задают зону индивидуального сопровождения.; groups.task_evidence:12.0% :: задание 11 (сильные 100% / риск 12%); groups.t  
  proposed_fix: Сверить округления и источники чисел в тексте
- **P59** / `text_data`: Подозрение на text↔data inconsistency (проценты в тексте не найдены в данных)  
  current: unmatched_percents≈5  
  evidence: marks_cycle.interpretation:40.5% :: Высокая доля «3» (40.5%) свидетельствует о преобладании базового уровня без устойчивого перехода к п; groups.task_evidence:29.0% :: задание 3 (сильные 100% / риск 2  
  proposed_fix: Сверить округления и источники чисел в тексте
- **P60** / `text_data`: Подозрение на text↔data inconsistency (проценты в тексте не найдены в данных)  
  current: unmatched_percents≈7  
  evidence: groups.task_evidence:29.0% :: задание 2 (сильные 100% / риск 29%); groups.task_evidence:29.0% :: задание 5 (сильные 100% / риск 29%); groups.task_evidence:29.0% :: задание 6 (сильные 100% / риск 29%)  
  proposed_fix: Сверить округления и источники чисел в тексте
- **P61** / `text_data`: Подозрение на text↔data inconsistency (проценты в тексте не найдены в данных)  
  current: unmatched_percents≈7  
  evidence: individual_cycle.interpretation:70.0% :: Обучающиеся с положительным потенциалом: 50036, 50032, 50040. SYSTEM_ANALYTICS: дополнительная харак; groups.characteristic:70.0% :: SYSTEM_ANALYTICS: дополнит  
  proposed_fix: Сверить округления и источники чисел в тексте
- **P62** / `text_data`: Подозрение на text↔data inconsistency (проценты в тексте не найдены в данных)  
  current: unmatched_percents≈7  
  evidence: individual_cycle.interpretation:70.0% :: Обучающиеся с положительным потенциалом: 50007, 50001, 50002, 50011, 50014…. SYSTEM_ANALYTICS: допол; marks_cycle.interpretation:46.7% :: Доля отметок «4» и «5  
  proposed_fix: Сверить округления и источники чисел в тексте
- **P69** / `text_data`: Подозрение на text↔data inconsistency (проценты в тексте не найдены в данных)  
  current: unmatched_percents≈5  
  evidence: marks_cycle.interpretation:50.9% :: Доля отметок «4» и «5» (50.9%) соответствует умеренному качеству знаний: положительный контур есть, ; marks_cycle.interpretation:42.1% :: Высокая доля «3» (42.1%) с  
  proposed_fix: Сверить округления и источники чисел в тексте
- **P71** / `text_data`: Подозрение на text↔data inconsistency (проценты в тексте не найдены в данных)  
  current: unmatched_percents≈6  
  evidence: groups.task_evidence:28.0% :: задание 6 (сильные 100% / риск 28%); groups.task_evidence:67.0% :: задание 8 (сильные 67% / риск 22%); groups.task_evidence:22.0% :: задание 8 (сильные 67% / риск 22%)  
  proposed_fix: Сверить округления и источники чисел в тексте
- **P73** / `text_data`: Подозрение на text↔data inconsistency (проценты в тексте не найдены в данных)  
  current: unmatched_percents≈6  
  evidence: groups.task_evidence:83.0% :: задание 4К3 (сильные 83% / риск 7%); groups.task_evidence:7.0% :: задание 4К3 (сильные 83% / риск 7%); groups.task_evidence:52.0% :: задание 1 (сильные 100% / риск 52%)  
  proposed_fix: Сверить округления и источники чисел в тексте
- **P76** / `text_data`: Подозрение на text↔data inconsistency (проценты в тексте не найдены в данных)  
  current: unmatched_percents≈5  
  evidence: individual_cycle.interpretation:70.0% :: Обучающиеся с положительным потенциалом: 60009, 60001, 60008, 60010, 60017. SYSTEM_ANALYTICS: дополн; groups.characteristic:70.0% :: SYSTEM_ANALYTICS: дополнит  
  proposed_fix: Сверить округления и источники чисел в тексте
- **P86** / `text_data`: Подозрение на text↔data inconsistency (проценты в тексте не найдены в данных)  
  current: unmatched_percents≈6  
  evidence: groups.task_evidence:33.0% :: задание 8 (сильные 100% / риск 33%); groups.task_evidence:44.0% :: задание 6 (сильные 100% / риск 44%); groups.task_evidence:44.0% :: задание 9 (сильные 100% / риск 44%)  
  proposed_fix: Сверить округления и источники чисел в тексте
- **P87** / `text_data`: Подозрение на text↔data inconsistency (проценты в тексте не найдены в данных)  
  current: unmatched_percents≈5  
  evidence: individual_cycle.interpretation:70.0% :: Обучающиеся с положительным потенциалом: 80028. SYSTEM_ANALYTICS: дополнительная характеристика (не ; groups.characteristic:70.0% :: SYSTEM_ANALYTICS: дополнит  
  proposed_fix: Сверить округления и источники чисел в тексте
- **P91** / `text_data`: Подозрение на text↔data inconsistency (проценты в тексте не найдены в данных)  
  current: unmatched_percents≈6  
  evidence: individual_cycle.interpretation:70.0% :: Обучающиеся с положительным потенциалом: 80012, 80010, 80028, 80021, 80037…. SYSTEM_ANALYTICS: допол; marks_cycle.interpretation:38.1% :: Доля отметок «4» и «5  
  proposed_fix: Сверить округления и источники чисел в тексте
- **P99** / `text_data`: Подозрение на text↔data inconsistency (проценты в тексте не найдены в данных)  
  current: unmatched_percents≈7  
  evidence: individual_cycle.interpretation:70.0% :: Обучающиеся с положительным потенциалом: 60023, 60022, 60031, 60027, 60029. SYSTEM_ANALYTICS: дополн; marks_cycle.interpretation:13.3% :: Отметки «2» (13.3%) п  
  proposed_fix: Сверить округления и источники чисел в тексте
- **P103** / `text_data`: Подозрение на text↔data inconsistency (проценты в тексте не найдены в данных)  
  current: unmatched_percents≈6  
  evidence: individual_cycle.interpretation:70.0% :: Обучающиеся с положительным потенциалом: 70019, 70007, 70001, 70005, 70013…. SYSTEM_ANALYTICS: допол; marks_cycle.interpretation:10.0% :: Отметки «2» (10.0%) п  
  proposed_fix: Сверить округления и источники чисел в тексте
- **P104** / `text_data`: Подозрение на text↔data inconsistency (проценты в тексте не найдены в данных)  
  current: unmatched_percents≈6  
  evidence: individual_cycle.interpretation:70.0% :: Обучающиеся с положительным потенциалом: 70001, 70005. SYSTEM_ANALYTICS: дополнительная характеристи; groups.characteristic:70.0% :: SYSTEM_ANALYTICS: дополнит  
  proposed_fix: Сверить округления и источники чисел в тексте
- **P105** / `text_data`: Подозрение на text↔data inconsistency (проценты в тексте не найдены в данных)  
  current: unmatched_percents≈6  
  evidence: individual_cycle.interpretation:70.0% :: Обучающиеся с положительным потенциалом: 70029, 70022, 70024, 70025, 70026…. SYSTEM_ANALYTICS: допол; marks_cycle.interpretation:41.2% :: Доля отметок «4» и «5  
  proposed_fix: Сверить округления и источники чисел в тексте
- **P114** / `text_data`: Подозрение на text↔data inconsistency (проценты в тексте не найдены в данных)  
  current: unmatched_percents≈5  
  evidence: individual_cycle.interpretation:70.0% :: Обучающиеся с положительным потенциалом: 50026, 50028, 50013, 50001, 50010. SYSTEM_ANALYTICS: дополн; marks_cycle.interpretation:31.0% :: Доля отметок «4» и «5  
  proposed_fix: Сверить округления и источники чисел в тексте
- **P127** / `text_data`: Подозрение на text↔data inconsistency (проценты в тексте не найдены в данных)  
  current: unmatched_percents≈6  
  evidence: individual_cycle.interpretation:70.0% :: Обучающиеся с положительным потенциалом: 70030, 70019, 70027, 70028, 70031…. SYSTEM_ANALYTICS: допол; groups.characteristic:70.0% :: SYSTEM_ANALYTICS: дополнит  
  proposed_fix: Сверить округления и источники чисел в тексте
- **P131** / `text_data`: Подозрение на text↔data inconsistency (проценты в тексте не найдены в данных)  
  current: unmatched_percents≈7  
  evidence: individual_cycle.interpretation:70.0% :: Обучающиеся с положительным потенциалом: 80021, 80002, 80011, 80013, 80020…. SYSTEM_ANALYTICS: допол; marks_cycle.interpretation:48.0% :: Высокая доля «3» (48.  
  proposed_fix: Сверить округления и источники чисел в тексте
- **P133** / `text_data`: Подозрение на text↔data inconsistency (проценты в тексте не найдены в данных)  
  current: unmatched_percents≈7  
  evidence: individual_cycle.interpretation:70.0% :: Обучающиеся с положительным потенциалом: 0 чел. (0.0%). SYSTEM_ANALYTICS: дополнительная характерист; marks_cycle.interpretation:38.5% :: Доля отметок «4» и «5  
  proposed_fix: Сверить округления и источники чисел в тексте

## Forbidden wording hits

Total hits: 0


## Notes

- STAGE 8 = audit only; исправления не вносились.
- Grade C = требуется ручная проверка (есть High).
- Grade D = методологическая/критическая ошибка (есть Critical).
- Validator warnings сами по себе дают Grade B при отсутствии High/Critical findings.

## STOP

Аудит завершён. Production code не изменять на основании этого файла без отдельного STAGE.
