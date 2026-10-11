"""Stage 3: tidy silkscreen reference designators (cosmetic).
Moves each reference to the first spot around its part that clears pads, holes,
other references and other parts' silk; hides mounting-hole references.
usage: fix_silk.py IN OUT"""
import sys, pcbnew, kc

IN, OUT = sys.argv[1], sys.argv[2]
b = kc.load(IN)
mm = kc.mm

def bb(item):
    r = item.GetBoundingBox()
    return (kc.to_mm(r.GetLeft()) - kc.CX, kc.to_mm(r.GetTop()) - kc.CY, kc.to_mm(r.GetRight()) - kc.CX, kc.to_mm(r.GetBottom()) - kc.CY)

def grow(r, m):
    return (r[0] - m, r[1] - m, r[2] + m, r[3] + m)

def hit(a, c):
    return a[0] < c[2] and c[0] < a[2] and a[1] < c[3] and c[1] < a[3]

pads = [grow(bb(p), 0.25) for f in b.GetFootprints() for p in f.Pads()]
pads += [grow(bb(v), 0.2) for v in b.GetTracks() if v.GetClass() == "PCB_VIA"]     # vias are bare copper too
silk = {"F": [], "B": []}           # (owner, bbox) of footprint silk graphics
for f in b.GetFootprints():
    for g in f.GraphicalItems():
        if g.GetLayer() in (pcbnew.F_SilkS, pcbnew.B_SilkS) and g.GetClass() not in ("PCB_FIELD", "PCB_TEXT"):
            silk["F" if g.GetLayer() == pcbnew.F_SilkS else "B"].append((f.GetReference(), grow(bb(g), 0.15)))
placed = {"F": [], "B": []}
# board-level silk text (connector labels) are obstacles too
for d in b.GetDrawings():
    if d.GetClass() == "PCB_TEXT" and d.GetLayer() in (pcbnew.F_SilkS, pcbnew.B_SilkS):
        placed["F" if d.GetLayer() == pcbnew.F_SilkS else "B"].append(grow(bb(d), 0.15))

def inside_board(r):
    import math
    return all(math.hypot(x, y) < kc.R_BOARD - 1.4 for x in (r[0], r[2]) for y in (r[1], r[3]))

order = sorted(b.GetFootprints(), key=lambda f: (0 if f.IsFlipped() else 1, f.GetReference()))
FRONT_FIX = {"BT1", "BT2", "BT3", "BT4", "SW1", "SW2", "SW3", "J5", "J6", "J3", "J1", "J2"}
moved = []
for f in order:
    ref = f.GetReference()
    field = f.Reference()
    side = "B" if f.IsFlipped() else "F"
    if ref.startswith("H") or ref.startswith("CAM"):
        field.SetVisible(False)
        continue
    if side == "F" and ref not in FRONT_FIX:
        continue
    f.BuildCourtyardCaches()
    cy = f.GetCourtyard(pcbnew.B_CrtYd if side == "B" else pcbnew.F_CrtYd).BBox()
    cx0, cy0 = kc.to_mm(cy.GetLeft()) - kc.CX, kc.to_mm(cy.GetTop()) - kc.CY
    cx1, cy1 = kc.to_mm(cy.GetRight()) - kc.CX, kc.to_mm(cy.GetBottom()) - kc.CY
    mx, my = (cx0 + cx1) / 2, (cy0 + cy1) / 2
    big = ref.startswith("BT")
    size = 1.0 if (side == "F" or big) else 0.8
    field.SetTextSize(pcbnew.VECTOR2I(mm(size), mm(size)))
    field.SetTextThickness(mm(0.15 if size >= 1.0 else 0.12))
    field.SetTextAngleDegrees(0)
    if big:
        cands = [(mx, my), (mx, my - 8), (mx, my + 8), (mx, my - 16)]   # middle of the holder, visible before the cell goes in
    else:
        h = size / 2 + 0.35
        cands = [(mx, cy0 - h), (mx, cy1 + h), (cx0 - 1.2, my), (cx1 + 1.2, my),
                 (mx, cy0 - h - 0.9), (mx, cy1 + h + 0.9), (cx0 - 2.2, my), (cx1 + 2.2, my),
                 (cx0 - 1.2, cy0 - h), (cx1 + 1.2, cy0 - h), (cx0 - 1.2, cy1 + h), (cx1 + 1.2, cy1 + h),
                 (mx, cy0 - h - 1.8), (mx, cy1 + h + 1.8), (cx0 - 3.2, my), (cx1 + 3.2, my),
                 (cx0 - 2.2, cy0 - h - 0.9), (cx1 + 2.2, cy0 - h - 0.9), (cx0 - 2.2, cy1 + h + 0.9), (cx1 + 2.2, cy1 + h + 0.9)]
    if ref in ("J5", "J6"):                 # XT30s: their +/- marks sit at the sides and the OUT label above, so go below
        cands = [(mx, cy1 + h)] + cands
    ok = None
    for (x, y) in cands:
        field.SetPosition(kc.P(x, y))
        r = bb(field)
        if not inside_board(r):
            continue
        if any(hit(r, p) for p in pads):
            continue
        if any(hit(r, q) for q in placed[side]):
            continue
        if any(o != ref and hit(r, s) for o, s in silk[side]):
            continue
        ok = (x, y); break
    if ok is None:                          # nowhere clean on the silk: leave it on the fab layer only
        field.SetPosition(kc.P(*cands[0])); field.SetVisible(False)
        moved.append(ref + "(hidden: no clean spot)")
    placed[side].append(grow(bb(field), 0.1))
pcbnew.SaveBoard(OUT, b, True)
print("silk refs placed; unresolved:", moved or "none")
