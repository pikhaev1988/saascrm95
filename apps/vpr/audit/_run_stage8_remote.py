import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "analiz_gia.settings")
django.setup()

from apps.vpr.audit.run_stage8_quality_audit import run_stage8_quality_audit

result = run_stage8_quality_audit(out_dir="apps/vpr/audit")
print(
    "TOTAL={TOTAL} A={A} B={B} C={C} D={D} Critical={Critical} High={High} "
    "Medium={Medium} Low={Low} status={status}".format(**result)
)
