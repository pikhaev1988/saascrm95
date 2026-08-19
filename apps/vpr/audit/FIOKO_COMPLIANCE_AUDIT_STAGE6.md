# VPR FIOKO COMPLIANCE AUDIT — ЭТАП 6

Дата: 2026-08-16  
Область: только `apps/vpr/**` (+ VPR templates / dashboard / DOCX / HTML)  
Код **не изменялся**.

---

## 1. SOURCES

### Найдено в репозитории

| Артефакт | Путь | Тип | Пригодность для compliance анализа ОО |
|----------|------|-----|----------------------------------------|
| Код, цитирующий название рекомендаций | `apps/vpr/expert_analysis/fioko_report.py` (docstring) | Implementation claim | **Не источник** |
| Производные JSON каталога КИМ | `apps/vpr/catalog/data/**/*.json` | Task metadata (тема/умение/max) | Частично: только КИМ, не алгоритм анализа ОО |
| Политика каталога | `apps/vpr/catalog/data/README.md`, `MANIFEST.json` | Project rule | Не нормативный текст ФИОКО |
| Seed/bootstrap комментарии | `apps/vpr/services/catalog_bootstrap.py` | «ФИОКО 2026 / sdamgia» | Не документ |
| UI/DOCX branding | `protocol_overview.html`, `overview_docx.py` | «по методологии ФИОКО» | Не источник |

### Не найдено

- PDF/DOCX/MD актуальных **«Рекомендаций по проведению анализа результатов ВПР на уровне ОО»**
- URL на fioko.ru / официальную публикацию рекомендаций анализа
- Версия/дата нормативного документа анализа
- Страницы/разделы источника с цитатами требований

### Documents needed for full compliance (запросить у заказчика)

1. Актуальные методические рекомендации ФИОКО по **анализу результатов ВПР на уровне ОО** (полный текст, год/версия).
2. При наличии — приложения/шаблоны справки ОО, если ФИОКО их публикует.
3. Предметные описания КИМ (официальные PDF) для всех предметов/классов, уже присутствующих в 138 протоколах (сейчас в repo в основном производные JSON для части 4 класса).

---

## 2. SOURCE CONFIDENCE

**FIOKO SOURCE STATUS: не найден (для методологии анализа ОО); найден частично (только производные КИМ-каталоги).**

| Класс требований | Confidence |
|------------------|------------|
| 16-раздельная структура справки как «алгоритм ФИОКО» | **SOURCE_NOT_CONFIRMED** |
| AnalyticCycle (интерпретация→причины→решения→эффект) как «обязательный цикл ФИОКО» | **SOURCE_NOT_CONFIRMED** |
| Пороги mastery 90/75/60/40 | **SOURCE_NOT_CONFIRMED** (зафиксированы как Stage-2 contract системы) |
| Группы high≥80 / medium≥50 / risk&lt;50 | **SOURCE_NOT_CONFIRMED** → классифицировать как SYSTEM_ADDED_ANALYTICS |
| Preparation Profile / cognitive codes | **SOURCE_NOT_CONFIRMED** → SYSTEM ENHANCEMENT |
| CV / SOU / KPI baseline-target | **SOURCE_NOT_CONFIRMED** → SYSTEM ENHANCEMENT |
| Сопоставление ВПР↔журнал | **SOURCE_NOT_CONFIRMED** (логика есть в системе; норма обязательности не подтверждена файлом) |
| Связь задание→умение→планируемый результат через каталог КИМ | **частично confirmed** только как *данные КИМ* в JSON `source` field, не как алгоритм анализа ОО |

---

## 3. OVERALL COMPLIANCE (относительно подтверждаемых источников)

Поскольку нормативный документ **анализа ОО отсутствует**, статусы требований ФИОКО по разделам отчёта массово:

| Status | Count (methodology requirements) |
|--------|----------------------------------|
| COMPLIANT | 0 (нельзя подтвердить) |
| PARTIALLY_COMPLIANT | 0 |
| NON_COMPLIANT | 0 |
| NOT_APPLICABLE | — |
| **SOURCE_NOT_CONFIRMED** | **все заявленные «требования ФИОКО» по 16 разделам** |

Отдельно (не ФИОКО, а **техническая корректность системы**, Stage 5):

- 138/138 validator PASS, HTML/DOCX PASS — **технически согласованная реализация**
- Это **не** равно `FIOKO_COMPLIANT`

---

## 4. 16 SECTIONS

| Section | Status vs FIOKO source | Evidence (system) | Gap | Priority |
|---------|------------------------|-------------------|-----|----------|
| 1 Паспорт | SOURCE_NOT_CONFIRMED | OO, год, предмет, класс, N, max, avg, marks avg, quality, abs, SOU, CV, profile | Нельзя доказать обязательный набор полей без документа | CRITICAL* |
| 2 Индивидуальные | SOURCE_NOT_CONFIRMED | groups risk/medium/high + potential disclaimer | Являются ли группы официальной классификацией ФИОКО — не подтверждено | CRITICAL* |
| 3 Отметки | SOURCE_NOT_CONFIRMED | 2–5, доли, quality/absolute | Формулы есть; обязательность интерпретации — не подтверждена | HIGH* |
| 4 ВПР/журнал | SOURCE_NOT_CONFIRMED | equal/lower/higher, risk_level, осторожные формулировки | Обязательность раздела — не подтверждена | HIGH* |
| 5 Первичные баллы | SOURCE_NOT_CONFIRMED | distribution + min/max/mean/median/stdev/CV | Какие статистики обязательны — не подтверждено | MEDIUM* |
| 6 Задания | SOURCE_NOT_CONFIRMED | full/partial/zero + rates + completion | Терминология vs ФИОКО — не сверена с документом | CRITICAL* |
| 7 Планируемые результаты | SOURCE_NOT_CONFIRMED | classify_mastery + catalog fgos_result | Каталог КИМ частичный; покрытие 138 протоколов неоднородно | HIGH* |
| 8 Группы×задания | SOURCE_NOT_CONFIRMED | barrier/differentiating tasks | SYSTEM ENHANCEMENT until proven | MEDIUM* |
| 9 Дефициты | SOURCE_NOT_CONFIRMED | topics/skills + evidence | Доказательность улучшена; статус «ФИОКО» не подтверждён | HIGH* |
| 10 Администрация | SOURCE_NOT_CONFIRMED | actions + cycle | SYSTEM ENHANCEMENT until proven | MEDIUM* |
| 11 ШМО | SOURCE_NOT_CONFIRMED | | SYSTEM ENHANCEMENT until proven | MEDIUM* |
| 12 Педагоги | SOURCE_NOT_CONFIRMED | softened «зона риска» | Корректнее, чем «дефицит педагога»; ФИОКО-статус неизвестен | HIGH* |
| 13 Родители | SOURCE_NOT_CONFIRMED | | SYSTEM ENHANCEMENT until proven | LOW* |
| 14 Метод. рекомендации | SOURCE_NOT_CONFIRMED | baseline→target в текстах | SYSTEM ENHANCEMENT until proven | MEDIUM* |
| 15 План / KPI | SOURCE_NOT_CONFIRMED | problem/action/KPI/baseline/target | KPI как обязательное требование ФИОКО — **не подтверждено** | MEDIUM* |
| 16 Заключение | SOURCE_NOT_CONFIRMED | profile→problems→KPI | Структура управленческая; соответствие источнику — нет | HIGH* |

\*Priority = приоритет **закрытия SOURCE gap** (получить документ), не доказанное нарушение ФИОКО.

---

## 5. METRICS

| Metric | FIOKO requirement | Current system | Status |
|--------|-------------------|----------------|--------|
| N, max, mean primary | SOURCE_NOT_CONFIRMED | Implemented, validated on 138 | SOURCE_NOT_CONFIRMED |
| Marks 2–5, quality, absolute | SOURCE_NOT_CONFIRMED | Implemented | SOURCE_NOT_CONFIRMED |
| SOU | SOURCE_NOT_CONFIRMED | Implemented | SOURCE_NOT_CONFIRMED → likely SYSTEM |
| CV / stdev / median | SOURCE_NOT_CONFIRMED | Implemented | SOURCE_NOT_CONFIRMED → SYSTEM ENHANCEMENT |
| full/partial/zero rates | SOURCE_NOT_CONFIRMED | Canonical metric layer | SOURCE_NOT_CONFIRMED (технически обязательно для честности multi-score) |
| completion ≠ full_rate | Project Stage-2 contract | Enforced | SYSTEM ENHANCEMENT / quality rule |
| Groups 80/50 | SOURCE_NOT_CONFIRMED | Implemented | SYSTEM_ADDED_ANALYTICS |
| Objectivity thresholds 40/20 | SOURCE_NOT_CONFIRMED | Implemented | SYSTEM_ADDED_ANALYTICS |
| Mastery 90/75/60/40 | SOURCE_NOT_CONFIRMED | deficits + classify_mastery | SYSTEM contract until source proves |

---

## 6. 138 PROTOCOLS

Технический Stage 5: все PASS.  
Методологический compliance ко всем 138:

| Protocol | Subject | Class | Compliance vs FIOKO source | Critical | High | Medium | Low |
|----------|---------|-------|----------------------------|----------|------|--------|-----|
| 1…140 (138 шт.) | все предметы production | 4–10 | **SOURCE_NOT_CONFIRMED** (единый статус из-за отсутствия документа) | — | — | — | — |

Нельзя дифференцировать COMPLIANT/NON_COMPLIANT по протоколам без текста источника.

---

## 7. SUBJECT ANALYSIS

| Subject | Protocols (≈) | Compliant | Partial | Non-compliant | Note |
|---------|---------------|-----------|---------|---------------|------|
| Все предметы из Stage 5 discovery | 138 | 0 | 0 | 0 | Все → SOURCE_NOT_CONFIRMED |
| Русский / Математика / Биология / Английский / … | — | — | — | — | Предметная универсальность **кода** есть; **нормативная** предметная дифференциация анализа ОО не подтверждена |

Риск: одинаковые пороги/шаблоны текстов применяются ко всем предметам (`subject_models.py` — SYSTEM narrative packs). Без документа нельзя сказать, требует ли ФИОКО предметно-разный алгоритм анализа ОО.

---

## 8. CLASS ANALYSIS

| Class | Status |
|-------|--------|
| 4–10 (все присутствующие) | SOURCE_NOT_CONFIRMED для «ФИОКО требует одинаковый 16-разделный анализ» |

Класс-зависимые КИМ есть в каталоге частично; класс-зависимая методология анализа ОО в repo **не подтверждена**.

---

## 9. SYSTEM ENHANCEMENTS

Явно **собственная аналитика системы** (нельзя называть «требование ФИОКО» без документа):

1. `VPR_THRESHOLDS` (groups, CV, objectivity, conclusion shares, positive_potential)
2. `PreparationProfile` / `elevated_risk` / `critical` и порядок if-условий
3. Cognitive codes (`basic_deficit`, `advanced_gap`, …)
4. AnalyticCycle 5 блоков на каждый раздел
5. KPI / baseline / target (+8/+10 п.п. auto-targets в §14)
6. `VPR_REPORT_VALIDATOR`
7. Positive potential + disclaimer
8. FACT/HYPOTHESIS префиксы в текстах
9. Barrier / differentiating tasks (§8)
10. Subject narrative models («ФИОКО 2.0» packaging)
11. Passport CV + profile evidence KPI
12. Softened teacher «зона методического риска»

---

## 10. METHODOLOGICAL RISKS

| # | Risk | Severity | Note |
|---|------|----------|------|
| 1 | Branding «по методологии ФИОКО» без вложенного документа | CRITICAL | Юридически/методически вводит в заблуждение |
| 2 | Название порогов/профилей как «ФИОКО» в комментариях | HIGH | Смешение LEVEL1/LEVEL2 |
| 3 | Одинаковые пороги на все предметы/классы | HIGH until source | Может быть ок или нет — неизвестно |
| 4 | Auto target +8/+10 п.п. без методики ФИОКО | MEDIUM | SYSTEM KPI enhancement |
| 5 | Profile critical vs elevated_risk порядок порогов | MEDIUM | SYSTEM; см. §11 |
| 6 | rates.sum_approx_100 warnings | LOW | округление; см. §12 |
| 7 | Частичное покрытие catalog → planned results | HIGH | для многих предметов planned_result из fallback skill/topic |
| 8 | Гипотезы причин (даже с HYPOTHESIS:) всё ещё генерируются шаблоном | MEDIUM | лучше, чем «факт», но объём шаблона велик |
| 9 | Objectivity «риск» без подтверждённой шкалы ФИОКО | MEDIUM | формулировки осторожные — хорошо |
| 10 | Отсутствие journal → NOT_AVAILABLE | LOW/OK | методологически разумно; см. §13 |

Риски 3–6 Stage 3–5 (N−full, partial wording, teacher deficit, proven objectivity) — **технически смягчены**; ФИОКО-соответствие всё равно SOURCE_NOT_CONFIRMED.

---

## 11. BIOLOGY #11 PROFILE

| Item | Value |
|------|-------|
| Stage 2 label expectation | «повышенного риска» / `elevated_risk` |
| Production actual | **`critical` / «критический профиль»** |
| File | `apps/vpr/expert_analysis/profiles.py` → `classify_preparation_profile` |
| Order | `critical` if mastery==critical OR absolute&lt;40 OR **risk_pct≥45**; else `elevated_risk` if mastery==problem OR risk≥30 OR weak_topic≥0.4 |
| Actual risk | ≈67% → срабатывает **critical** |
| Is profile a FIOKO requirement? | **SOURCE_NOT_CONFIRMED** → **SYSTEM ENHANCEMENT** |
| Action Stage 6 | **Не менять алгоритм** |

---

## 12. 97 WARNINGS (`rates.sum_approx_100`)

| Question | Answer |
|----------|--------|
| Математическая ошибка? | **Нет** (по Stage 5: invariants full+partial+zero==N проходят) |
| Эффект округления? | **Да**: три rate округляются до 2 знаков → сумма может ≠100.00 |
| Соответствует реальной ошибке? | Warning **шумный**; не critical |
| PROPOSED FIX (не внедрять сейчас) | Проверять raw `count/N*100` до округления или допуск ±0.5–1.0 п.п.; UI показывать rounded |

---

## 13. PROTOCOL 79 (Математика 6, нет journal pairs)

| Item | Assessment |
|------|------------|
| Status | objectivity **unavailable** |
| Ошибка данных? | **Нет**, если журнал не загружен |
| Корректная методология | **Да**: не подменять нулями; warning / NOT_AVAILABLE |
| ФИОКО | SOURCE_NOT_CONFIRMED, требуется ли раздел при отсутствии журнала |

---

## 14. PROPOSED CHANGES (только план → ЭТАП 7)

| ID | File / area | Current | Required (after source) | Proposed | Risk | Priority |
|----|-------------|---------|-------------------------|----------|------|----------|
| P0 | Project docs / `docs/vpr/` | Нет PDF рекомендаций | Вложить официальный документ | Запросить и приложить источник | None | CRITICAL |
| P1 | UI/DOCX branding | «по методологии ФИОКО» | Либо подтвердить, либо смягчить формулировку | После источника: cite version; иначе «в структуре, ориентированной на рекомендации ФИОКО (документ не приложен)» | Reputation | CRITICAL |
| P2 | Comments `thresholds.py` etc. | «пороги ФИОКО» | Разделить FIOKO vs SYSTEM | Переименовать комментарии/метаданные | Low | HIGH |
| P3 | profiles.py | SYSTEM profile | Если ФИОКО не требует — документировать как enhancement | Не «чинить» Biology critical | Medium | MEDIUM |
| P4 | validator rates warning | шумный | толерантность/raw | Adjust tolerance | Low | LOW |
| P5 | catalog coverage | частичный | полные КИМ | Импорт официальных JSON по предметам 138 протоколов | Medium | HIGH |
| P6 | KPI auto +8/+10 | эвристика | только если источник допускает | Отключить auto-target или пометить HYPOTHESIS | Medium | MEDIUM |

**Код на этапе 6 не менялся.**

---

## 15. FINAL STATUS

# **AUDIT_BLOCKED_SOURCE_NOT_CONFIRMED**

### Почему не FIOKO_COMPLIANT / PARTIALLY / NON

Существенные заявленные требования («16 разделов алгоритма ФИОКО», обязательный AnalyticCycle, пороги как «ФИОКО», профиль подготовки) **нельзя подтвердить** вложенным нормативным документом анализа ОО.

Система при этом:

- технически целостна на 138 протоколах (Stage 5);
- содержит сильный слой **SYSTEM ENHANCEMENT**;
- улучшила доказательность формулировок (partial, objectivity, teachers, KPI).

### Что нужно до ЭТАПА 7

1. Предоставить актуальный PDF/DOCX рекомендаций ФИОКО по анализу ВПР на уровне ОО.  
2. Повторно проставить матрицу: COMPLIANT / PARTIAL / NON с цитатами page/section.  
3. Только затем править код под подтверждённые gaps.

---

## A–O MATRIX INDEX (кратко)

| Block | Result |
|-------|--------|
| A Sources | Analysis recommendations **missing**; KIM JSON partial |
| B 16 sections | Implemented; FIOKO status SOURCE_NOT_CONFIRMED |
| C Metrics | Technically OK; FIOKO SOURCE_NOT_CONFIRMED |
| D Tasks | Metric layer OK; terminology vs FIOKO unconfirmed |
| E Planned results | Catalog-dependent; partial coverage |
| F Deficits | Engine + evidence; FIOKO unconfirmed |
| G Causes | FACT/HYPOTHESIS present; still template-heavy |
| H Admin measures | SYSTEM ENHANCEMENT |
| I Method recs | SYSTEM ENHANCEMENT |
| J KPI | SYSTEM ENHANCEMENT |
| K Conclusion | SYSTEM ENHANCEMENT structure |
| L Subject universality | Code universal; normative differentiation unknown |
| M Classes | Same |
| N System enhancements | Listed in §9 |
| O Risks | Listed in §10 |

---

**STOP. ЭТАП 7 не начинать без нормативного источника.**
