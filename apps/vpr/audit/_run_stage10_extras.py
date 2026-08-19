"""Stage 10 extras: group LIMITED counts + bio#11 text check. Run on Beget."""
from __future__ import annotations

import json
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "analiz_gia.settings")
django.setup()

from apps.vpr.comprehensive_analysis.engine import VprComprehensiveAnalysisEngine
from apps.vpr.models import VprProtocol
from apps.vpr.subject_report import build_subject_report
from apps.vpr.analytics.config import get_vpr_analytics_config

engine = VprComprehensiveAnalysisEngine()
cfg = get_vpr_analytics_config()
group_min = int(cfg["fioko_2026"]["sample"]["groups_informative_min"])

limited_group_hits = 0
protocols_with_limited_group = 0
bio = None

for protocol in VprProtocol.objects.all().order_by("id").iterator():
    analysis = engine.analyze(protocol)
    facts = analysis.facts
    hit = False
    for gname, g in (facts.groups or {}).items():
        n = int(getattr(g, "n", 0) or 0)
        if n and n < group_min:
            limited_group_hits += 1
            hit = True
    if hit:
        protocols_with_limited_group += 1
    if protocol.id == 11:
        report = build_subject_report(analysis, protocol, validate=False)
        text_blob = json.dumps(report, ensure_ascii=False, default=str)
        # also check narrative strings
        fioko = getattr(analysis, "fioko_2026", None)
        bio = {
            "protocol_id": 11,
            "participants": protocol.participants_count,
            "tasks_below_50": facts.tasks.below_50,
            "tasks_total": facts.tasks.total,
            "sample_limited": protocol.participants_count < 50,
            "has_le_50_phrase": ("≤ 50%" in text_blob) or ("<= 50%" in text_blob) or ("≤50%" in text_blob),
            "has_below_50_count_15": ("15" in text_blob and "50" in text_blob),
            "report_keys_sample": list(report.keys())[:30] if isinstance(report, dict) else type(report).__name__,
        }
        # scan expert report sections for weak tasks count
        try:
            from apps.vpr.expert_analysis.fioko_report import build_fioko_expert_report

            er = build_fioko_expert_report(analysis, protocol)
            er_s = json.dumps(er, ensure_ascii=False, default=str)
            bio["expert_has_15"] = "15" in er_s
            # find line about 50%
            for needle in ("50%", "ниже 50", "≤ 50", "успешностью"):
                if needle in er_s:
                    idx = er_s.find(needle)
                    bio[f"snippet_{needle}"] = er_s[max(0, idx - 40) : idx + 80]
        except Exception as exc:  # noqa: BLE001
            bio["expert_err"] = str(exc)[:200]

out = {
    "group_min": group_min,
    "limited_group_hits": limited_group_hits,
    "protocols_with_limited_group": protocols_with_limited_group,
    "biology_11": bio,
    "thresholds": {
        "basic": cfg["fioko_2026"]["basic"],
        "advanced_high": cfg["fioko_2026"]["advanced_high"],
        "system_tasks": cfg.get("system_tasks"),
        "sample": cfg["fioko_2026"]["sample"],
    },
}
path = "apps/vpr/audit/VPR_STAGE10_EXTRAS.json"
with open(path, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print(json.dumps(out, ensure_ascii=False, indent=2))
print("→", path)
