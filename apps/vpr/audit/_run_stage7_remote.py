import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "analiz_gia.settings")
django.setup()

from apps.vpr.audit.run_stage7_acceptance import run_stage7_acceptance

result = run_stage7_acceptance(
    out_path="apps/vpr/audit/VPR_FIOKO_STAGE7_1_ACCEPTANCE.json"
)
print(
    "TOTAL={TOTAL} PASS={PASS} FAIL={FAIL} BLOCKED={BLOCKED}".format(**result)
)
