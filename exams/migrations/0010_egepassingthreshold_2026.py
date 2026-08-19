# Generated manually for EGE thresholds 2026+

from django.db import migrations


SUBJECTS = [
    {"subject_key": "russian", "minimum_score": 24, "minimum_grade": None},
    {"subject_key": "math_profile", "minimum_score": 27, "minimum_grade": None},
    {"subject_key": "math_basic", "minimum_score": None, "minimum_grade": 3},
    {"subject_key": "social", "minimum_score": 42, "minimum_grade": None},
    {"subject_key": "informatics", "minimum_score": 40, "minimum_grade": None},
    {"subject_key": "physics", "minimum_score": 36, "minimum_grade": None},
    {"subject_key": "chemistry", "minimum_score": 36, "minimum_grade": None},
    {"subject_key": "biology", "minimum_score": 36, "minimum_grade": None},
    {"subject_key": "history", "minimum_score": 32, "minimum_grade": None},
    {"subject_key": "literature", "minimum_score": 32, "minimum_grade": None},
    {"subject_key": "geography", "minimum_score": 37, "minimum_grade": None},
    {"subject_key": "foreign_language", "minimum_score": 22, "minimum_grade": None},
]


def seed_thresholds_2026(apps, schema_editor):
    EgePassingThreshold = apps.get_model("exams", "EgePassingThreshold")
    for year in (2026, 2027):
        for item in SUBJECTS:
            EgePassingThreshold.objects.update_or_create(
                year=year,
                subject_key=item["subject_key"],
                defaults={
                    "minimum_score": item["minimum_score"],
                    "minimum_grade": item["minimum_grade"],
                },
            )


def unseed_thresholds_2026(apps, schema_editor):
    EgePassingThreshold = apps.get_model("exams", "EgePassingThreshold")
    EgePassingThreshold.objects.filter(year__in=[2026, 2027]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("exams", "0009_merge_0008_branches"),
    ]

    operations = [
        migrations.RunPython(seed_thresholds_2026, unseed_thresholds_2026),
    ]
