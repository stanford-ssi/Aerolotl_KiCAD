"""Export board geometry to JSON for plotting (run with KiCad's python).
usage: export_geom.py BOARD OUT.json [--fill]"""
import sys, json, pcbnew, kc

def chain_pts(ch):
    return [kc.rel(ch.CPoint(i)) for i in range(ch.PointCount())]

def polyset(ps):
    out = []
    for i in range(ps.OutlineCount()):
        out.append({"outline": chain_pts(ps.Outline(i)),
                    "holes": [chain_pts(ps.Hole(i, j)) for j in range(ps.HoleCount(i))]})
    return out

b = kc.load(sys.argv[1])
if "--fill" in sys.argv:
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
res = {"footprints": [], "pads": [], "tracks": [], "vias": [], "zones": [], "ratsnest": [], "drawings": []}
for f in b.GetFootprints():
    f.BuildCourtyardCaches()
    side = "B" if f.IsFlipped() else "F"
    cy = f.GetCourtyard(pcbnew.B_CrtYd if side == "B" else pcbnew.F_CrtYd)
    res["footprints"].append({"ref": f.GetReference(), "value": f.GetValue(), "side": side,
        "pos": kc.rel(f.GetPosition()), "rot": f.GetOrientationDegrees(),
        "court": [o["outline"] for o in polyset(cy)],
        "path": f.GetPath().AsString()})
    for p in f.Pads():
        lset = p.GetLayerSet()
        onF, onB = lset.Contains(pcbnew.F_Cu), lset.Contains(pcbnew.B_Cu)
        lay = pcbnew.F_Cu if onF else pcbnew.B_Cu
        try:
            poly = p.GetEffectivePolygon(lay, pcbnew.ERROR_INSIDE)
            pp = [o["outline"] for o in polyset(poly)]
        except Exception as e:
            pp = []
        d = p.GetDrillSize()
        res["pads"].append({"ref": f.GetReference(), "num": p.GetNumber(), "net": p.GetNetname(),
            "pos": kc.rel(p.GetPosition()), "F": onF, "B": onB,
            "npth": p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH,
            "drill": kc.to_mm(d.x) if d.x else 0, "poly": pp})
for t in b.GetTracks():
    if t.GetClass() == "PCB_VIA":
        res["vias"].append({"net": t.GetNetname(), "pos": kc.rel(t.GetPosition()),
                            "d": kc.to_mm(t.GetWidth(pcbnew.F_Cu)), "drill": kc.to_mm(t.GetDrillValue())})
    else:
        res["tracks"].append({"net": t.GetNetname(), "layer": t.GetLayerName(),
            "a": kc.rel(t.GetStart()), "b": kc.rel(t.GetEnd()), "w": kc.to_mm(t.GetWidth())})
for z in b.Zones():
    zd = {"net": z.GetNetname(), "keepout": z.GetIsRuleArea(), "name": z.GetZoneName(),
          "layers": [], "outline": [o["outline"] for o in polyset(z.Outline())], "filled": {}}
    for L, nm in ((pcbnew.F_Cu, "F"), (pcbnew.B_Cu, "B")):
        if z.IsOnLayer(L):
            zd["layers"].append(nm)
            if not z.GetIsRuleArea():
                zd["filled"][nm] = polyset(z.GetFilledPolysList(L))
    res["zones"].append(zd)
for d in b.GetDrawings():
    if d.GetLayerName() in ("Cmts.User", "Dwgs.User") and d.GetClass() == "PCB_SHAPE":
        bb = d.GetBoundingBox()
        res["drawings"].append({"layer": d.GetLayerName(), "bbox": [kc.rel(bb.GetOrigin()), kc.rel(bb.GetEnd())]})
b.BuildConnectivity()
conn = b.GetConnectivity()
from collections import defaultdict
import math
key = lambda p: (p.GetParentFootprint().GetReference(), p.GetNumber())
by_net = defaultdict(list)
for f in b.GetFootprints():
    for p in f.Pads():
        if p.GetNetCode() > 0:
            by_net[p.GetNetname()].append(p)
for net, pads in by_net.items():
    if len(pads) < 2:
        continue
    parent = {key(p): key(p) for p in pads}
    def find(k):
        while parent[k] != k:
            parent[k] = parent[parent[k]]; k = parent[k]
        return k
    for p in pads:
        for q in conn.GetConnectedPads(p):
            kq = key(q)
            if kq in parent:
                parent[find(key(p))] = find(kq)
    clusters = defaultdict(list)
    for p in pads:
        clusters[find(key(p))].append(kc.rel(p.GetPosition()))
    cl = list(clusters.values())
    if len(cl) < 2:
        continue
    done = [cl[0]]; todo = cl[1:]
    while todo:
        best = None
        for i, c in enumerate(todo):
            for a in c:
                for d in done:
                    for bb in d:
                        dist = math.hypot(a[0]-bb[0], a[1]-bb[1])
                        if best is None or dist < best[0]:
                            best = (dist, i, a, bb)
        _, i, a, bb = best
        res["ratsnest"].append({"net": net, "a": a, "b": bb})
        done.append(todo.pop(i))
res["unconnected"] = len(res["ratsnest"])
json.dump(res, open(sys.argv[2], "w"))
print("footprints %d pads %d tracks %d vias %d zones %d ratsnest %d unconnected %s" % (
    len(res["footprints"]), len(res["pads"]), len(res["tracks"]), len(res["vias"]), len(res["zones"]),
    len(res["ratsnest"]), res["unconnected"]))
