# Нормативный справочник заданий ВПР

Каталог JSON-файлов для импорта в `VprTaskCatalogEntry`.

## Структура

```
data/
├── MANIFEST.json
├── russian/grade4/2026.json
├── mathematics/grade4/2026.json
└── <subject>/grade<N>/<year>.json
```

## Правила наполнения

1. Источник — только официальные материалы ФИОКО / Рособрнадзора (описание КИМ, спецификация, критерии).
2. Нельзя придумывать темы и умения.
3. Поля `section`, `topic`, `skill`, `planned_result`, `complexity`, `max_score` обязательны.
4. Коды заданий должны совпадать с протоколами Ф1 (включая подкоды `9.1`, `5.2` и т.п.).

## Импорт

```bash
python manage.py import_vpr_task_catalog
python manage.py import_vpr_task_catalog apps/vpr/catalog/data
python manage.py check_vpr_catalog
```

## Покрытие

Актуальные seed-файлы: русский язык 4 кл. 2026, математика 4 кл. 2026.

Остальные предметы/классы добавляются отдельными официальными JSON по мере публикации описаний КИМ.
