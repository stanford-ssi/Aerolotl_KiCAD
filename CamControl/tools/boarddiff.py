"""Structural diff of two boards: footprints, tracks/vias, zones, drawings, text."""
import sys, pcbnew, kc
def snap(path):
    b = kc.load(path)
    d = {}
    for f in b.GetFootprints():
        x, y = kc.rel(f.GetPosition())
        d["FP " + f.GetReference()] = ("B" if f.IsFlipped() else "F", round(x, 2), round(y, 2), round(f.GetOrientationDegrees(), 1), f.GetValue(), f.GetFPIDAsString(),
                                       tuple(sorted((p.GetNumber(), p.GetNetname()) for p in f.Pads())))
        rf = f.Reference(); rx, ry = kc.rel(rf.GetPosition())
        d["REF " + f.GetReference()] = (round(rx, 2), round(ry, 2), rf.IsVisible(), round(kc.to_mm(rf.GetTextSize().y), 2))
    tr = []
    for t in b.GetTracks():
        if t.GetClass() == "PCB_VIA":
            tr.append(("via", t.GetNetname(), kc.rel(t.GetPosition()), round(kc.to_mm(t.GetWidth(pcbnew.F_Cu)), 2)))
        else:
            tr.append(("trk", t.GetNetname(), t.GetLayerName(), kc.rel(t.GetStart()), kc.rel(t.GetEnd()), round(kc.to_mm(t.GetWidth()), 2)))
    d["TRACKS"] = tuple(sorted(map(str, tr)))
    zs = []
    for z in b.Zones():
        o = z.Outline()
        pts = tuple(kc.rel(o.CVertex(i)) for i in range(o.TotalVertices()))
        zs.append((z.GetZoneName(), z.GetNetname(), z.GetIsRuleArea(), tuple(sorted(L for L in ("F.Cu", "B.Cu") if z.IsOnLayer(b.GetLayerID(L)))), pts))
    d["ZONES"] = tuple(sorted(map(str, zs)))
    dr = []
    for g in b.GetDrawings():
        bb = g.GetBoundingBox()
        txt = g.GetText() if hasattr(g, "GetText") and g.GetClass() == "PCB_TEXT" else ""
        dr.append((g.GetClass(), g.GetLayerName(), kc.rel(bb.GetOrigin()), kc.rel(bb.GetEnd()), txt))
    d["DRAWINGS"] = tuple(sorted(map(str, dr)))
    return d
a, b = snap(sys.argv[1]), snap(sys.argv[2])
for k in sorted(set(a) | set(b)):
    if a.get(k) != b.get(k):
        if k in ("TRACKS", "ZONES", "DRAWINGS"):
            sa, sb = set(a.get(k, ())), set(b.get(k, ()))
            print("== %s: %d only in A, %d only in B" % (k, len(sa - sb), len(sb - sa)))
            for x in sorted(sa - sb)[:12]: print("   A-only:", x[:230])
            for x in sorted(sb - sa)[:12]: print("   B-only:", x[:230])
        else:
            print("== %s\n   A: %s\n   B: %s" % (k, str(a.get(k))[:250], str(b.get(k))[:250]))
print("diff done")
