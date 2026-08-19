import os, django, json
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "analiz_gia.settings")
django.setup()
from apps.vpr.comprehensive_analysis.engine import VprComprehensiveAnalysisEngine
from apps.vpr.models import VprProtocol

engine = VprComprehensiveAnalysisEngine()
group_hits = 0
proto_hits = 0
bio11 = None
mark_group_hits = 0
for p in VprProtocol.objects.all().order_by("id").iterator():
    a = engine.analyze(p)
    hit = False
    for name, g in (a.facts.groups or {}).items():
        c = int(getattr(g, "count", 0) or 0)
        if c and c < 10:
            group_hits += 1
            hit = True
    f26 = getattr(a, "fioko_2026", None)
    if f26 is not None:
        ga = getattr(f26, "groups", None)
        if ga is not None:
            for attr in ("by_mark", "mark_groups", "groups", "items"):
                items = getattr(ga, attr, None)
                if items is None:
                    continue
                if isinstance(items, dict):
                    seq = items.values()
                elif isinstance(items, (list, tuple)):
                    seq = items
                else:
                    continue
                for g in seq:
                    c = int(getattr(g, "size", None) or getattr(g, "count", None) or getattr(g, "n", 0) or 0)
                    st = str(getattr(g, "sample_status", "") or "")
                    if (c and c < 10) or st == "LIMITED_SAMPLE":
                        mark_group_hits += 1
    if hit:
        proto_hits += 1
    if p.id == 11:
        bio11 = {k: a.facts.groups[k].to_dict() for k in a.facts.groups}
        # inspect fioko groups attrs
        ga = getattr(getattr(a, "fioko_2026", None), "groups", None)
        bio11["_fioko_groups_type"] = type(ga).__name__ if ga else None
        if ga:
            bio11["_fioko_groups_dir"] = [x for x in dir(ga) if not x.startswith("_")][:40]
            for attr in ("by_mark", "mark_groups", "groups", "items", "mark_2", "high", "risk"):
                if hasattr(ga, attr):
                    val = getattr(ga, attr)
                    bio11[f"_attr_{attr}"] = repr(val)[:300]

out = {
    "limited_group_hits_count_lt10": group_hits,
    "protocols_with_any_group_lt10": proto_hits,
    "mark_group_limited_hits": mark_group_hits,
    "bio11_groups": bio11,
}
path = "apps/vpr/audit/VPR_STAGE10_EXTRAS.json"
# merge with existing if present
try:
    prev = json.load(open(path, encoding="utf-8"))
except Exception:
    prev = {}
prev.update(out)
json.dump(prev, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(json.dumps(out, ensure_ascii=False, indent=2)[:4000])
