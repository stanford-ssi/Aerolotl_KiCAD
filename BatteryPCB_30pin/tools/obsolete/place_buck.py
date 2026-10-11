#!/usr/bin/env python3
"""Reposition the back-side parts on battery_pcb.kicad_pcb.

Only touches footprints listed in MOVE — the front side (your placement) is
left exactly as saved. Validates against the board circle, same-side overlap,
and through-hole pads punching into the other side before writing.

Buck layout follows LMR51430 datasheet 9.4.1:
  - CIN as close as possible to VIN and GND pins  (the EMI-critical item)
  - SW-to-inductor path as short as possible
  - output caps at the VOUT end of the inductor
  - both feedback resistors close to the FB pin, away from SW
"""
import re, math, os, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "battery_pcb.kicad_pcb")
KFP = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints"
BOARD_DIA, CX, CY, EDGE_CLEAR = 147.0, 150.0, 150.0, 1.5
R = BOARD_DIA / 2

# ---------------------------------------------------------------- buck cluster
# positions relative to U1; U1 pins (SOT-23-6, rot 0):
#   left  x=-1.14 : 1 GND (y-0.95), 2 SW (y 0), 3 VIN (y+0.95)
#   right x=+1.14 : 6 CB  (y-0.95), 5 EN (y 0), 4 FB  (y+0.95)
UX, UY = -18.0, -14.0
BUCK = {
    "U1": (0.0, 0.0, 0),
    # CIN bridging VIN/GND. rot 90 puts pad1 at +y (VIN row) and pad2 at -y (GND row),
    # so both connections are straight 2.9 mm horizontal runs. This is the hot loop.
    "C1": (-4.2, 0.0, 90),
    "C2": (-7.2, 0.0, 90),
    # SW exits left-centre and drops straight to the inductor's SW pad
    "L1": (0.0, 5.6, 0),
    # output caps at the VOUT end of L1
    "C4": (6.0, 5.6, 90),
    "C5": (9.0, 5.6, 90),
    "C6": (12.0, 5.6, 90),
    # bootstrap: CB (right, -0.95) back to SW (left, 0). rot 180 points pad1 at CB.
    "C3": (0.0, -3.6, 180),
    # feedback divider, both close to FB, on the opposite side from SW
    "R2": (5.0, -1.6, 180),
    "R3": (5.0, 2.6, 0),
    "C7": (5.0, -4.2, 180),
}

# ------------------------------------------------- everything else on the back
ROWS = [
    (8.0, ["F1", "D3", "D1", "R4", "R5", "C8"]),
    (16.0, ["C9", "C10", "R6", "D2", "R7", "R8"]),
]
ROW_X0 = -46.0
GAP = 3.0


# ---------------------------------------------------------------- geometry
_cache = {}


def fp_file(libref):
    lib, name = libref.split(":", 1)
    for base in (KFP, HERE):
        p = os.path.join(base, lib + ".pretty", name + ".kicad_mod")
        if os.path.exists(p):
            return open(p).read()
    raise SystemExit("missing footprint " + libref)


def extent(libref):
    if libref in _cache:
        return _cache[libref]
    t = fp_file(libref)
    pts = []
    for m in re.finditer(r"\((fp_line|fp_rect|fp_poly|fp_circle|fp_arc)\b([\s\S]*?)\n\t\)", t):
        if '"F.CrtYd"' not in m.group(2):
            continue
        for c in re.finditer(r"\((?:start|end|center|mid|xy) (-?[\d.]+) (-?[\d.]+)\)", m.group(2)):
            pts.append((float(c.group(1)), float(c.group(2))))
    if not pts:
        for m in re.finditer(r"\(pad [\s\S]{0,400}?\(at (-?[\d.]+) (-?[\d.]+)", t):
            pts.append((float(m.group(1)), float(m.group(2))))
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    tht = []
    for m in re.finditer(r'\(pad "[^"]*" (?:np_)?thru_hole [\s\S]{0,200}?\(at (-?[\d.]+) (-?[\d.]+)[\s\S]{0,120}?\(size (-?[\d.]+) (-?[\d.]+)\)', t):
        tht.append(tuple(float(m.group(i)) for i in (1, 2, 3, 4)))
    v = (max(xs) - min(xs), max(ys) - min(ys),
         (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2, tht)
    _cache[libref] = v
    return v


def rot_pt(px, py, a):
    r = math.radians(-a)
    return px * math.cos(r) - py * math.sin(r), px * math.sin(r) + py * math.cos(r)


def box(libref, x, y, rot):
    w, h, ox, oy, _ = extent(libref)
    if rot:
        cx_, cy_ = rot_pt(ox, oy, rot)
        cs = [rot_pt(sx, sy, rot) for sx in (ox - w / 2, ox + w / 2) for sy in (oy - h / 2, oy + h / 2)]
        w = max(c[0] for c in cs) - min(c[0] for c in cs)
        h = max(c[1] for c in cs) - min(c[1] for c in cs)
    else:
        cx_, cy_ = ox, oy
    return (x + cx_ - w / 2, y + cy_ - h / 2, x + cx_ + w / 2, y + cy_ + h / 2)


def pads_abs(libref, x, y, rot):
    out = []
    for px, py, pw, ph in extent(libref)[4]:
        rx, ry = rot_pt(px, py, rot) if rot else (px, py)
        pw_, ph_ = (ph, pw) if rot % 180 else (pw, ph)
        out.append((x + rx - pw_ / 2 - .4, y + ry - ph_ / 2 - .4,
                    x + rx + pw_ / 2 + .4, y + ry + ph_ / 2 + .4))
    return out


# ---------------------------------------------------------------- read board
src = open(PCB).read()
cur = {}
for m in re.finditer(r'\t\(footprint "([^"]+)"\n\t\t\(layer "([BF])\.Cu"\)\n\t\t\(uuid "[^"]*"\)\n\t\t\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)', src):
    blk = src[m.start():m.start() + 2500]
    ref = re.search(r'\(property "Reference" "([^"]+)"', blk)
    if ref:
        cur[ref.group(1)] = dict(lib=m.group(1), side=m.group(2), span=m.span(),
                                 x=float(m.group(3)) - CX, y=float(m.group(4)) - CY,
                                 rot=float(m.group(5) or 0))

# ---------------------------------------------------------------- new positions
MOVE = {}
for ref, (dx, dy, rot) in BUCK.items():
    MOVE[ref] = (round(UX + dx, 3), round(UY + dy, 3), rot)
for ry, refs in ROWS:
    x = ROW_X0
    for ref in refs:
        w = extent(cur[ref]["lib"])[0]
        MOVE[ref] = (round(x + w / 2, 3), ry, 0)
        x += w + GAP

# ---------------------------------------------------------------- validate
final = {}
for ref, d in cur.items():
    if ref in MOVE:
        x, y, rot = MOVE[ref]
    else:
        x, y, rot = d["x"], d["y"], d["rot"]
    final[ref] = (d["lib"], x, y, rot, d["side"])

problems, preexisting = [], []
boxes, thts = {}, {}
for ref, (lib, x, y, rot, side) in final.items():
    if ref.startswith("H"):
        continue
    b = box(lib, x, y, rot)
    boxes[ref] = (b, side)
    far = max(math.hypot(sx, sy) for sx in (b[0], b[2]) for sy in (b[1], b[3]))
    if far > R - EDGE_CLEAR:
        (problems if ref in MOVE else preexisting).append(
            "%-4s courtyard reaches %.1f mm (board radius %.1f)" % (ref, far, R))
    p = pads_abs(lib, x, y, rot)
    if p:
        thts[ref] = (p, side)

def hit(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]

names = list(boxes)
for i in range(len(names)):
    for j in range(i + 1, len(names)):
        (a, sa), (b, sb) = boxes[names[i]], boxes[names[j]]
        if sa == sb and hit(a, b):
            problems.append("OVERLAP %s / %s" % (names[i], names[j]))
for ref, (pads, side) in thts.items():
    for other, (ob, oside) in boxes.items():
        if other == ref or oside == side:
            continue
        if any(hit(p, ob) for p in pads):
            problems.append("THT %s punches into %s" % (ref, other))

if preexisting:
    print("pre-existing, not introduced by this move (%d):" % len(preexisting))
    for q in preexisting:
        print("  " + q)
    print()
if problems:
    print("PROBLEMS (%d):" % len(problems))
    for p in problems:
        print("  " + p)
    if "--force" not in sys.argv:
        sys.exit(1)

# ---------------------------------------------------------------- write
shutil.copy(PCB, PCB + ".bak")
out, last = [], 0
for ref, d in sorted(cur.items(), key=lambda kv: kv[1]["span"][0]):
    if ref not in MOVE:
        continue
    x, y, rot = MOVE[ref]
    s, e = d["span"]
    head = src[s:e]
    new = re.sub(r"\(at [-\d.]+ [-\d.]+(?: [-\d.]+)?\)",
                 "(at %g %g%s)" % (CX + x, CY + y, (" %g" % rot) if rot else ""), head, count=1)
    out.append(src[last:s]); out.append(new); last = e
out.append(src[last:])
open(PCB, "w").write("".join(out))

print("moved %d footprints (backup at battery_pcb.kicad_pcb.bak)" % len(MOVE))
print("\nbuck cluster, relative to U1:")
for ref in ["C1", "C2", "L1", "C3", "C4", "C5", "C6", "R2", "R3", "C7"]:
    dx, dy, rot = BUCK[ref]
    print("   %-3s  %+6.1f %+6.1f  rot %3d   %.1f mm from U1" % (ref, dx, dy, rot, math.hypot(dx, dy)))
