import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "analiz_gia.settings")
django.setup()

from apps.vpr.audit.run_stage7_acceptance import run_stage7_acceptance
from apps.vpr.audit.run_stage8_quality_audit import run_stage8_quality_audit

print("=== STAGE7/7.1 acceptance (138) ===")
acc = run_stage7_acceptance(out_path="apps/vpr/audit/VPR_STAGE8_1_ACCEPTANCE_PROTOCOLS.json")
print(
    "TOTAL={TOTAL} PASS={PASS} FAIL={FAIL} BLOCKED={BLOCKED}".format(**acc)
)

print("=== STAGE8 re-audit ===")
audit = run_stage8_quality_audit(out_dir="apps/vpr/audit")
# write stage8 re-audit under stage8.1 names as well
import json
from pathlib import Path
payload = {
    k: audit[k]
    for k in (
        "TOTAL",
        "A",
        "B",
        "C",
        "D",
        "Critical",
        "High",
        "Medium",
        "Low",
        "forbidden_wording_count",
        "catalog_partial_count",
        "limited_sample_count",
        "html_docx_mismatch_count",
        "numeric_mismatch_count",
        "fioko_attribution_issues",
        "status",
    )
}
payload["acceptance"] = {k: acc[k] for k in ("TOTAL", "PASS", "FAIL", "BLOCKED")}
Path("apps/vpr/audit/VPR_STAGE8_1_AUDIT_SUMMARY.json").write_text(
    json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(
    "TOTAL={TOTAL} A={A} B={B} C={C} D={D} Critical={Critical} High={High} "
    "Medium={Medium} Low={Low} status={status}".format(**audit)
)
