#!/usr/bin/env python3
"""Generate camcontrol.kicad_pcb — round board, footprints placed, nets assigned.

Board diameter is a single parameter. Placement is checked against the board
circle and against every other footprint before the file is written.
"""
import os, re, subprocess, uuid, math, sys

HERE = os.path.dirname(os.path.abspath(__file__))
KFP = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints"
PRJFP = os.path.join(HERE, "camcontrol.pretty")
KC = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"

# ======================= PARAMETERS =======================
BOARD_DIA = 147.0          # <-- change this if the coupler ID differs
CX = CY = 150.0            # board centre in KiCad page coords
ROD_BC = 134.0             # rod bolt circle diameter
ROD_DRILL = 4.5
EDGE_CLEAR = 1.5           # keep footprints this far inside the edge

R = BOARD_DIA / 2.0
U = lambda: str(uuid.uuid4())
NETSTATS = []


# ------------- netlist -------------
def netlist():
    out = os.path.join(HERE, "_net.net")
    subprocess.run([KC, "sch", "export", "netlist", "--format", "kicadsexpr",
                    "-o", out, os.path.join(HERE, "camcontrol.kicad_sch")],
                   capture_output=True)
    t = open(out).read()
    fps = dict(re.findall(r'\(ref "([^"]+)"\)[\s\S]{0,300}?\(footprint "([^"]*)"\)', t))
    nets, order = {}, []
    seg = t[t.find("(nets"):]
    for b in re.split(r"\n\s+\(net\n", seg)[1:]:
        m = re.search(r'\(name "([^"]*)"\)', b)
        if not m:
            continue
        nm = m.group(1)
        order.append(nm)
        for r_, p_ in re.findall(r'\(ref "([^"]+)"\)[\s\S]{0,60}?\(pin "([^"]+)"\)', b):
            nets[(r_, p_)] = nm
    os.remove(out)
    return fps, nets, order


# ------------- footprint file handling -------------
def fp_path(libref):
    lib, name = libref.split(":", 1)
    for base in (KFP, os.path.dirname(PRJFP)):
        p = os.path.join(base, lib + ".pretty", name + ".kicad_mod")
        if os.path.exists(p):
            return p
    raise SystemExit("footprint not found: " + libref)


_fpcache = {}


def fp_text(libref):
    if libref not in _fpcache:
        _fpcache[libref] = open(fp_path(libref)).read()
    return _fpcache[libref]


def rot_pt(px, py, a):
    r = math.radians(-a)
    return (px * math.cos(r) - py * math.sin(r), px * math.sin(r) + py * math.cos(r))


def tht_pads(libref):
    """[(x, y, w, h)] of through-hole pads, in footprint-local coords."""
    t_ = fp_text(libref)
    out = []
    for m in re.finditer(r'\(pad "[^"]*" (?:np_)?thru_hole [\s\S]{0,200}?\(at (-?[\d.]+) (-?[\d.]+)[\s\S]{0,120}?\(size (-?[\d.]+) (-?[\d.]+)\)', t_):
        out.append((float(m.group(1)), float(m.group(2)), float(m.group(3)), float(m.group(4))))
    return out


def has_tht(libref):
    return "thru_hole" in fp_text(libref)


def fp_extent(libref):
    """(w, h) of the courtyard, falling back to pads."""
    t = fp_text(libref)
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
    return (max(xs) - min(xs), max(ys) - min(ys),
            (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2)


def add_nets(body, netmap):
    """Insert (net N "name") inside each pad block, matching parens properly."""
    out, i, hit = [], 0, 0
    while True:
        j = body.find('(pad "', i)
        if j < 0:
            out.append(body[i:]); break
        num = re.match(r'\(pad "([^"]*)"', body[j:]).group(1)
        depth, k = 0, j
        while k < len(body):
            c = body[k]
            if c == '"':
                k += 1
                while body[k] != '"':
                    k += 2 if body[k] == "\\" else 1
            elif c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
                if depth == 0:
                    break
            k += 1
        blk = body[j:k + 1]
        net = netmap.get(num)
        if net and "(net " not in blk:
            indent = body[:j].split("\n")[-1]
            blk = blk[:-1] + '\t(net %d "%s")\n%s)' % (net[0], net[1], indent)
            hit += 1
        out.append(body[i:j]); out.append(blk)
        i = k + 1
    return "".join(out), hit


def mirror_text(body):
    """Add (justify mirror) to every (effects ...) block so back silk reads correctly."""
    out, i = [], 0
    while True:
        j = body.find("(effects", i)
        if j < 0:
            out.append(body[i:]); break
        depth, k = 0, j
        while k < len(body):
            if body[k] == "(":
                depth += 1
            elif body[k] == ")":
                depth -= 1
                if depth == 0:
                    break
            k += 1
        blk = body[j:k + 1]
        if "justify" in blk:
            blk = re.sub(r"\(justify ([^)]*)\)", lambda m: "(justify %s mirror)" % m.group(1).strip()
                         if "mirror" not in m.group(1) else m.group(0), blk, count=1)
        else:
            indent = "\t" * (len(body[:j].split("\n")[-1]) + 1)
            blk = blk[:-1] + "%s(justify mirror)\n%s)" % (indent, "\t" * (len(body[:j].split("\n")[-1])))
        out.append(body[i:j]); out.append(blk)
        i = k + 1
    return "".join(out)


def emit_footprint(libref, ref, x, y, rot, netmap, side='F'):
    """Return the .kicad_pcb footprint block."""
    t = fp_text(libref)
    body = t[t.index("\n", t.index("(footprint")) + 1:t.rindex(")")]
    # strip the library's own version/generator lines
    body = re.sub(r"^\t\((?:version|generator|generator_version)[^\n]*\n", "", body, flags=re.M)
    # rotation onto every pad
    if rot:
        def padrot(m):
            a = m.group(3)
            newang = (float(a) if a else 0.0) + rot
            return "(at %s %s %g)" % (m.group(1), m.group(2), newang)
        body = re.sub(r"\(at (-?[\d.]+) (-?[\d.]+)(?: (-?[\d.]+))?\)(?=[\s\S]{0,200}?\(layers)",
                      padrot, body)
    # net assignment
    body, _hits = add_nets(body, netmap)
    NETSTATS.append((ref, len(netmap), _hits))
    # reference/value text
    body = re.sub(r'\(property "Reference" "[^"]*"', '(property "Reference" "%s"' % ref, body, count=1)
    if side == "B":
        body = re.sub(r'"F\.(Cu|SilkS|Mask|Paste|CrtYd|Fab|Adhes)"', r'"@.\1"', body)
        body = re.sub(r'"B\.(Cu|SilkS|Mask|Paste|CrtYd|Fab|Adhes)"', r'"F.\1"', body)
        body = body.replace('"@.', '"B.')
        body = mirror_text(body)
    return '\t(footprint "%s"\n\t\t(layer "%s.Cu")\n\t\t(uuid "%s")\n\t\t(at %g %g%s)\n%s\t)' % (
        libref, side, U(), x, y, (" %g" % rot) if rot else "", body)


# ======================= PLACEMENT =======================
# (ref, x, y, rot)   coordinates are relative to the board centre
# Ø147 plate, 3 mm (measured in Onshape: face-to-face max 147.03 at 3 mm thick).
#   FRONT  battery bank (4 holders) shifted up so the bottom cap can hold the ESP32
#          ESP32 socket in the bottom cap
#          all 7 wire landings packed tightly in the top cap
#          COTS vertical board gets a real 24 x 30 mm reserved area in the right lens
#   BACK   every SMD part, in the wide open area beneath the battery bank
PLACE = {
    "BT1": (-33.3, -12, 90, "F"),
    "BT2": (-11.1, -12, 90, "F"),
    "BT3": (11.1, -12, 90, "F"),
    "BT4": (33.3, -12, 90, "F"),

}

# ---- 7 wire landings, packed shoulder to shoulder in the top cap ----
_CONN = ["SW1", "J3", "SW2", "J5", "J6", "SW3"]

# ---- every SMD on the back, under the battery bank ----
_SMD = ["F1", "D3", "D1", "C1", "C2",
        "U1", "L1", "C3", "C4", "C5", "C6", "R2", "R3", "C7",
        "R4", "R5", "C8", "C9", "C10", "R6", "D2",
        "R7", "R8"]

_probe = dict(re.findall(r'\(ref "([^"]+)"\)[\s\S]{0,300}?\(footprint "([^"]*)"\)',
                         subprocess.run([KC, "sch", "export", "netlist", "--format",
                                         "kicadsexpr", "-o", "/dev/stdout",
                                         os.path.join(HERE, "camcontrol.kicad_sch")],
                                        capture_output=True, text=True).stdout))

_CONN_FP = "Connector_JST:JST_PH_B2B-PH-K_1x02_P2.00mm_Vertical"


def _centre(ref, x, y, rot, side, fpmap):
    """Place so the footprint's bounding box centres on (x, y)."""
    w, h, ox, oy = fp_extent(fpmap[ref])
    cxl, cyl = rot_pt(ox, oy, rot) if rot else (ox, oy)
    PLACE[ref] = (round(x - cxl, 2), round(y - cyl, 2), rot, side)


def _pack(refs, rows, side, fpmap, gap, override=None):
    """Pack refs into rows [(y, ...)], centred, using real part widths."""
    i = 0
    for y in rows:
        halfw = min(math.sqrt(max((BOARD_DIA / 2 - 5.0) ** 2 - y ** 2, 0)), 42.0)
        row, tot = [], 0.0
        while i < len(refs):
            lib = override or fpmap[refs[i]]
            w = fp_extent(lib)[0] + gap
            if tot + w > 2 * halfw:
                break
            row.append((refs[i], w)); tot += w; i += 1
        x = -tot / 2
        for ref, w in row:
            PLACE[ref] = (round(x + w / 2, 2), y, 0, side)
            x += w
    return i


_centre("J1", 0, 38.0, 90, "F", _probe)
_centre("J2", 0, 63.4, 90, "F", _probe)

# 7 wire landings: a tight column down the left lens, pitched by real part size
_hts = [fp_extent(_probe[_r])[0] + 1.5 for _r in _CONN]   # width becomes height at 90 deg
_ytot = sum(_hts)
_yc = -_ytot / 2
for _ref, _ht in zip(_CONN, _hts):
    _centre(_ref, -55.0, round(_yc + _ht / 2, 2), 90, "F", _probe)
    _yc += _ht

_n = _pack(_SMD, [-34.0, -26.0, -18.0, -10.0, -2.0, 6.0, 14.0, 22.0], "B", _probe, 2.2)
if _n < len(_SMD):
    raise SystemExit("no room for: " + ", ".join(_SMD[_n:]))

# switches and battery-arm outputs land on 2-pin connectors, not board-mounted switches
FP_OVERRIDE = {
    "SW1": "Connector_JST:JST_PH_B2B-PH-K_1x02_P2.00mm_Vertical",
    "SW2": "Connector_JST:JST_PH_B2B-PH-K_1x02_P2.00mm_Vertical",
    "SW3": "Connector_JST:JST_PH_B2B-PH-K_1x02_P2.00mm_Vertical",
}

# vertical TeleMetrum board: reserved area (w, h) centred at (x, y)
TELEM = (58.0, 0, 24.0, 30.0)


def main():
    fps, nets, order = netlist()
    netnum = {n: i + 1 for i, n in enumerate(order)}

    # ---- validate placement ----
    problems, boxes, thtboxes = [], {}, {}
    for ref, (x, y, rot, side) in PLACE.items():
        lib = FP_OVERRIDE.get(ref) or fps.get(ref)
        if not lib:
            problems.append("%s: no footprint" % ref); continue
        w, h, ox, oy = fp_extent(lib)
        if rot:
            cxl, cyl = rot_pt(ox, oy, rot)
            corners = [rot_pt(sx, sy, rot) for sx in (ox - w / 2, ox + w / 2)
                       for sy in (oy - h / 2, oy + h / 2)]
            w = max(c[0] for c in corners) - min(c[0] for c in corners)
            h = max(c[1] for c in corners) - min(c[1] for c in corners)
        else:
            cxl, cyl = ox, oy
        cx, cy = x + cxl, y + cyl
        boxes[ref] = (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2, side)
        far = max(math.hypot(sx, sy) for sx in (cx - w / 2, cx + w / 2)
                  for sy in (cy - h / 2, cy + h / 2))
        if far > R - EDGE_CLEAR:
            problems.append("%-5s reaches %.1f mm from centre (limit %.1f)" % (ref, far, R - EDGE_CLEAR))
        # through-hole pads block the OTHER side too, but only where the pads are
        for px, py, pw, ph in tht_pads(lib):
            rx, ry = rot_pt(px, py, rot) if rot else (px, py)
            pw_, ph_ = (ph, pw) if rot % 180 else (pw, ph)
            m_ = 0.4
            thtboxes.setdefault(ref, []).append(
                (x + rx - pw_ / 2 - m_, y + ry - ph_ / 2 - m_,
                 x + rx + pw_ / 2 + m_, y + ry + ph_ / 2 + m_, side))

    tx, ty, tw, th = TELEM
    boxes["COTS_SLOT"] = (tx - tw / 2, ty - th / 2, tx + tw / 2, ty + th / 2, "F")

    def hit(a, b):
        return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]

    refs = list(boxes)
    for i in range(len(refs)):
        for j in range(i + 1, len(refs)):
            a, b = boxes[refs[i]], boxes[refs[j]]
            if a[4] == b[4] and hit(a, b):
                ov = (min(a[2], b[2]) - max(a[0], b[0]), min(a[3], b[3]) - max(a[1], b[1]))
                problems.append("OVERLAP %s / %s by %.1f x %.1f mm" % (refs[i], refs[j], ov[0], ov[1]))
    for ref, pads in thtboxes.items():
        for other in refs:
            if other == ref or boxes[other][4] == pads[0][4]:
                continue
            for pb in pads:
                if hit(pb, boxes[other]):
                    problems.append("THT PAD %s punches into %s" % (ref, other))
                    break

    missing = sorted(set(fps) - set(PLACE) - {r for r in fps if not fps[r]})
    if missing:
        problems.append("not placed: " + ", ".join(missing))

    if problems:
        print("PLACEMENT PROBLEMS (%d):" % len(problems))
        for p in problems:
            print("  " + p)
        if "--force" not in sys.argv:
            sys.exit(1)

    # ---- build nets list ----
    netlines = ['\t(net 0 "")']
    for n in order:
        netlines.append('\t(net %d "%s")' % (netnum[n], n))

    # ---- footprints ----
    fpblocks = []
    for ref, (x, y, rot, side) in sorted(PLACE.items()):
        lib = FP_OVERRIDE.get(ref) or fps[ref]
        nm = {}
        for (r_, p_), net in nets.items():
            if r_ == ref:
                nm[p_] = (netnum[net], net)
        fpblocks.append(emit_footprint(lib, ref, CX + x, CY + y, rot, nm, side))

    # ---- board outline + holes + keepout ----
    gfx = [f'''	(gr_circle
		(center {CX} {CY})
		(end {CX + R} {CY})
		(stroke (width 0.15) (type default))
		(fill none)
		(layer "Edge.Cuts")
		(uuid "{U()}")
	)''']
    for a in (45, 135, 225, 315):
        hx = CX + (ROD_BC / 2) * math.cos(math.radians(a))
        hy = CY + (ROD_BC / 2) * math.sin(math.radians(a))
        gfx.append(f'''	(footprint "MountingHole:MountingHole_4.5mm"
		(layer "F.Cu")
		(uuid "{U()}")
		(at {hx:.3f} {hy:.3f})
		(attr exclude_from_pos_files exclude_from_bom)
		(property "Reference" "H{a}"
			(at 0 -5 0)
			(layer "F.SilkS")
			(uuid "{U()}")
			(effects (font (size 1 1) (thickness 0.15)))
		)
		(pad "" np_thru_hole circle
			(at 0 0)
			(size {ROD_DRILL} {ROD_DRILL})
			(drill {ROD_DRILL})
			(layers "*.Cu" "*.Mask")
			(uuid "{U()}")
		)
	)''')
    x0, y0 = CX + tx - tw / 2, CY + ty - th / 2
    x1, y1 = CX + tx + tw / 2, CY + ty + th / 2
    gfx.append(f'''	(gr_rect
		(start {x0:.2f} {y0:.2f})
		(end {x1:.2f} {y1:.2f})
		(stroke (width 0.2) (type dash))
		(fill none)
		(layer "Cmts.User")
		(uuid "{U()}")
	)''')
    gfx.append(f'''	(gr_text "COTS altimeter\\nvertical board"
		(at {CX + tx:.2f} {CY + ty:.2f} 0)
		(layer "Cmts.User")
		(uuid "{U()}")
		(effects (font (size 1.5 1.5) (thickness 0.2)))
	)''')
    gfx.append(f'''	(gr_text "CamControl  -  {BOARD_DIA:.0f} mm"
		(at {CX:.2f} {CY + R - 6:.2f} 0)
		(layer "F.SilkS")
		(uuid "{U()}")
		(effects (font (size 2 2) (thickness 0.3)))
	)''')

    layers = """		(0 "F.Cu" signal)
		(2 "B.Cu" signal)
		(9 "F.Adhes" user "F.Adhesive")
		(11 "B.Adhes" user "B.Adhesive")
		(13 "F.Paste" user)
		(15 "B.Paste" user)
		(5 "F.SilkS" user "F.Silkscreen")
		(7 "B.SilkS" user "B.Silkscreen")
		(1 "F.Mask" user)
		(3 "B.Mask" user)
		(17 "Dwgs.User" user "User.Drawings")
		(19 "Cmts.User" user "User.Comments")
		(21 "Eco1.User" user "User.Eco1")
		(23 "Eco2.User" user "User.Eco2")
		(25 "Edge.Cuts" user)
		(27 "Margin" user)
		(31 "F.CrtYd" user "F.Courtyard")
		(29 "B.CrtYd" user "B.Courtyard")
		(35 "F.Fab" user)
		(33 "B.Fab" user)"""

    out = f'''(kicad_pcb
	(version 20241229)
	(generator "camcontrol-gen")
	(generator_version "10.0")
	(general
		(thickness 1.6)
		(legacy_teardrops no)
	)
	(paper "A3")
	(layers
{layers}
	)
	(setup
		(pad_to_mask_clearance 0)
		(allow_soldermask_bridges_in_footprints no)
	)
{chr(10).join(netlines)}
{chr(10).join(fpblocks)}
{chr(10).join(gfx)}
)
'''
    open(os.path.join(HERE, "camcontrol.kicad_pcb"), "w").write(out)
    print("wrote camcontrol.kicad_pcb")
    print("  board  %.0f mm dia" % BOARD_DIA)
    print("  parts  %d placed" % len(PLACE))
    print("  nets   %d" % len(order))
    want = sum(n for _, n, _ in NETSTATS)
    got = sum(h for _, _, h in NETSTATS)
    print("  pad nets assigned: %d / %d" % (got, want))
    bad = [(r, n, h) for r, n, h in NETSTATS if h < n]
    for r, n, h in bad:
        print("     %-6s %d of %d pads got a net" % (r, h, n))


main()
