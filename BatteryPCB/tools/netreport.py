"""Per-net routing report: routed length, straight-line span, layers, widths, vias."""
import sys, math, kc
from collections import defaultdict
b = kc.load(sys.argv[1])
L = defaultdict(float); layers = defaultdict(set); widths = defaultdict(set); vias = defaultdict(int)
for t in b.GetTracks():
    n = t.GetNetname().split("/")[-1]
    if t.GetClass() == "PCB_VIA":
        vias[n] += 1; continue
    a, c = kc.rel(t.GetStart()), kc.rel(t.GetEnd())
    L[n] += math.hypot(a[0]-c[0], a[1]-c[1]); layers[n].add(t.GetLayerName()[0]); widths[n].add(round(kc.to_mm(t.GetWidth()), 2))
pads = defaultdict(list)
for f in b.GetFootprints():
    for p in f.Pads():
        if p.GetNetname(): pads[p.GetNetname().split("/")[-1]].append(kc.rel(p.GetPosition()))
print("%-12s %7s %7s  %-5s %-22s %s" % ("net", "routed", "direct", "layer", "widths", "vias"))
for n in sorted(L, key=lambda n: -L[n]):
    pp = pads[n]; d = max((math.hypot(a[0]-c[0], a[1]-c[1]) for a in pp for c in pp), default=0)
    print("%-12s %7.1f %7.1f  %-5s %-22s %d" % (n[:12], L[n], d, "+".join(sorted(layers[n])), sorted(widths[n]), vias[n]))
