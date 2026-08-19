import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "analiz_gia.settings")
django.setup()

from django.db.models import Count

from analytics.knowledge.service import get_task_knowledge
from analytics.knowledge_models import TaskKnowledge
from users.task_topics import load_subject_task_catalog

print("=== TaskKnowledge by subject ===")
for r in TaskKnowledge.objects.values("exam_type", "subject_key").annotate(c=Count("id")).order_by("exam_type", "subject_key"):
    print(f"{r['exam_type']:4} {r['subject_key']:20} {r['c']}")
print("TOTAL", TaskKnowledge.objects.count())

print("\n=== Catalog subjects ===")
for et in ("ege", "oge"):
    cat = load_subject_task_catalog(et)
    print(et, sorted(cat.keys()))

print("\n=== Sample lookups ===")
samples = [
    ("ege", "Русский язык", 21),
    ("ege", "Физика", 13),
    ("ege", "История", 13),
    ("ege", "Биология", 13),
    ("ege", "Математика профильная", 13),
    ("oge", "Русский язык", 13),
    ("oge", "Математика", 13),
    ("oge", "Обществознание", 13),
]
for et, subj, num in samples:
    k = get_task_knowledge(subj, num, et)
    topic = k.topic[:60] if k else "MISSING"
    print(f"{et} | {subj:25} | №{num:2} | {topic}")
