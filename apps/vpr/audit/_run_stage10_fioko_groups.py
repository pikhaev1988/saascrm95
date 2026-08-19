import os, django, json

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "analiz_gia.settings")
django.setup()

from apps.vpr.comprehensive_analysis.engine import VprComprehensiveAnalysisEngine
from apps.vpr.models import VprProtocol

e = VprComprehensiveAnalysisEngine()
lim = 0
protos = 0
for p in VprProtocol.objects.all().iterator():
    a = e.analyze(p)
    ga = a.fioko_2026.groups
    hit = False
    for b in ga.buckets or []:
        c = int(getattr(b, "size", None) or getattr(b, "count", 0) or 0)
        st = str(getattr(b, "sample_status", "") or "")
        if (c and c < 10) or st == "LIMITED_SAMPLE":
            lim += 1
            hit = True
    if hit:
        protos += 1

p = VprProtocol.objects.get(pk=11)
a = e.analyze(p)
buckets = [
    {
        "mark": getattr(b, "mark", None),
        "size": getattr(b, "size", None),
        "sample_status": getattr(b, "sample_status", None),
    }
    for b in (a.fioko_2026.groups.buckets or [])
]
out = {
    "fioko_mark_group_lt10_hits": lim,
    "protocols_with_fioko_mark_group_lt10": protos,
    "bio11_buckets": buckets,
}
print(json.dumps(out, ensure_ascii=False, indent=2))
path = "apps/vpr/audit/VPR_STAGE10_EXTRAS.json"
try:
    prev = json.load(open(path, encoding="utf-8"))
except Exception:
    prev = {}
prev.update(out)
json.dump(prev, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
