"""Redraws sheets 1-3 (battery + protection, buck to 5 V, pack voltage sense) as wired schematics, so the power path reads
left to right instead of as scattered net labels (review 3, 8 Oct 2026). Every existing symbol keeps its UUID, so the board
stays linked. Also: the input capacitors C1/C2 move to the buck sheet next to U1, C1 becomes the 100 nF high-frequency cap,
C11 (10 uF) is added, and U1's EN pin gets the R9/R10 UVLO divider instead of being tied to VIN.
Run once with KiCad closed; re-running redraws from the current files.  usage: python3 tools/redraw_power_sheets.py"""
import math
import os
import re
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
ROOT_UUID = "19ef3a32-de7c-46ee-a850-2420f6d47f94"
SHEET = {"power_in": "ae01c8e7-4191-4202-a535-afc32959794b", "buck_5v": "1914f4ed-278a-4026-a86a-769e5e361ab6"}
NEW_UUIDS = {"R9": "b2000000-0000-4000-8000-000000000009", "R10": "b2000000-0000-4000-8000-000000000010",
             "C11": "b2000000-0000-4000-8000-000000000011"}


def U():
    return str(uuid.uuid4())


def block_end(t, s):
    d = 0
    for j in range(s, len(t)):
        d += t[j] == "("
        d -= t[j] == ")"
        if d == 0:
            return j + 1
    raise ValueError("unbalanced")


def load(name):
    t = open(os.path.join(ROOT, "sheets", name + ".kicad_sch")).read()
    i = t.find("\t(lib_symbols")
    head = t[:block_end(t, i + 1)] + "\n"
    syms = {}
    for m in re.finditer(r"\n\t\(symbol\n", t):
        s = m.start() + 2
        blk = t[s:block_end(t, s)]
        syms[re.search(r'"Reference" "([^"]+)"', blk).group(1)] = blk
    return head, syms


def libpins(head):
    pins = {}
    for m in re.finditer(r'\n\s*\(symbol "([^"]+:[^"]+)"', head):       # lib symbols (their indentation varies)
        s = m.start() + m.group(0).index("(symbol")
        blk = head[s:block_end(head, s)]
        pins[m.group(1)] = {n: (float(x), float(y)) for x, y, n in re.findall(
            r'\(pin \w+ \w+\s*\(at ([-\d.]+) ([-\d.]+) \d+\).*?\(number "([^"]*)"', blk, re.S)}
    return pins


def rot(x, y, r):
    a = math.radians(r)
    return x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)


class Sheet:
    def __init__(self, name):
        self.name = name
        self.head, self.syms = load(name)
        self.pins = libpins(self.head)
        self.body = []
        self.placed = {}

    def place(self, blk, x, y, r=0, props=None):
        """props: {"Reference": (dx, dy, justify), "Value": (...)}; others hidden at the symbol."""
        lib = re.search(r'\(lib_id "([^"]+)"', blk).group(1)
        ox, oy = [float(v) for v in re.search(r"\n\t\t\(at ([-\d.]+) ([-\d.]+)", blk).groups()]
        blk = re.sub(r"\n\t\t\(at [-\d.]+ [-\d.]+ \d+\)", "\n\t\t(at %.2f %.2f %d)" % (x, y, r), blk, count=1)

        def fix(m):
            name, px, py = m.group(1), float(m.group(2)), float(m.group(3))
            rest = m.group(4)
            if props and name in props:
                dx, dy, just = props[name]
                rest = re.sub(r"\(justify [a-z ]+\)", "", rest).replace("(effects (font (size 1.27 1.27))",
                       "(effects (font (size 1.27 1.27))" + (" (justify %s)" % just if just else ""), 1)
                ang = 90 if r % 180 == 90 else 0      # field angles turn with the symbol: keep the text horizontal
                return '(property "%s" %s\n\t\t\t(at %.2f %.2f %d)%s' % (name, m.group(5), x + dx, y + dy, ang, rest)
            if "(hide yes)" in rest:
                return '(property "%s" %s\n\t\t\t(at %.2f %.2f 0)%s' % (name, m.group(5), x, y, rest)
            return '(property "%s" %s\n\t\t\t(at %.2f %.2f 0)%s' % (name, m.group(5), px - ox + x, py - oy + y, rest)
        blk = re.sub(r'\(property "([^"]+)" ("[^"]*")\n\t\t\t\(at ([-\d.]+) ([-\d.]+) \d+\)(\n\t\t\t\(effects[^\n]*)',
                     lambda m: fix(_M(m)), blk)
        self.body.append("\t" + blk + "\n")
        ref = re.search(r'"Reference" "([^"]+)"', blk).group(1)
        mx = -1 if "\n\t\t(mirror y)" in blk else 1          # mirrored about the y axis: pins swap sides
        my = -1 if "\n\t\t(mirror x)" in blk else 1
        self.placed[ref] = {n: (round(x + rot(mx * px, my * py, r)[0], 2), round(y - rot(mx * px, my * py, r)[1], 2))
                            for n, (px, py) in self.pins[lib].items()}
        return self.placed[ref]

    def wire(self, *pts):
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            self.body.append('\t(wire\n\t\t(pts (xy %.2f %.2f) (xy %.2f %.2f))\n\t\t(stroke (width 0) (type default))\n'
                             '\t\t(uuid "%s")\n\t)\n' % (x0, y0, x1, y1, U()))

    def junction(self, x, y):
        self.body.append('\t(junction\n\t\t(at %.2f %.2f)\n\t\t(diameter 0)\n\t\t(color 0 0 0 0)\n\t\t(uuid "%s")\n\t)\n'
                         % (x, y, U()))

    def label(self, name, x, y, r=0):
        just = "left bottom" if r in (0, 90) else "right bottom"
        self.body.append('\t(label "%s"\n\t\t(at %.2f %.2f %d)\n\t\t(fields_autoplaced yes)\n\t\t(effects (font (size 1.27 1.27)) '
                         '(justify %s))\n\t\t(uuid "%s")\n\t)\n' % (name, x, y, r, just, U()))

    def glabel(self, name, x, y, r=270):
        just = "left" if r in (0, 90) else "right"
        self.body.append('\t(global_label "%s"\n\t\t(shape input)\n\t\t(at %.2f %.2f %d)\n\t\t(fields_autoplaced yes)\n'
                         '\t\t(effects (font (size 1.27 1.27)) (justify %s))\n\t\t(uuid "%s")\n'
                         '\t\t(property "Intersheetrefs" "${INTERSHEET_REFS}"\n\t\t\t(at %.2f %.2f 0)\n'
                         '\t\t\t(effects (font (size 1.27 1.27)) (hide yes))\n\t\t)\n\t)\n' % (name, x, y, r, just, U(), x, y))

    def gnd(self, x, y):
        self.glabel("GND", x, y, 270)

    def hlabel(self, name, x, y, r):
        just = "left" if r in (0, 90) else "right"
        self.body.append('\t(hierarchical_label "%s"\n\t\t(shape passive)\n\t\t(at %.2f %.2f %d)\n\t\t(fields_autoplaced yes)\n'
                         '\t\t(effects (font (size 1.27 1.27)) (justify %s))\n\t\t(uuid "%s")\n\t)\n' % (name, x, y, r, just, U()))

    def text(self, s, x, y, size=1.27):
        s = s.replace('"', '\\"')
        self.body.append('\t(text "%s"\n\t\t(exclude_from_sim no)\n\t\t(at %.2f %.2f 0)\n\t\t(effects (font (size %s %s) (thickness 0.254) (bold yes)'
                         ' (color 0 0 194 1)) (justify left bottom))\n\t\t(uuid "%s")\n\t)\n' % (s, x, y, size, size, U()))

    def save(self):
        t = self.head + "".join(self.body) + ")\n"
        open(os.path.join(ROOT, "sheets", self.name + ".kicad_sch"), "w").write(t)


class _M:      # wraps a property match so fix() can read the quoted value as group(5)
    def __init__(self, m):
        self.m = m

    def group(self, i):
        return {1: self.m.group(1), 2: self.m.group(3), 3: self.m.group(4), 4: self.m.group(5), 5: self.m.group(2)}[i]


def repath(blk, sheet_uuid):
    return re.sub(r'\(path "/%s/[^"]+"' % ROOT_UUID, '(path "/%s/%s"' % (ROOT_UUID, sheet_uuid), blk)


def clone(blk, ref, value, sym_uuid, sheet_uuid):
    blk = re.sub(r'\n\t\t\(uuid "[^"]+"\)', '\n\t\t(uuid "%s")' % sym_uuid, blk, count=1)
    blk = re.sub(r'"Reference" "[^"]+"', '"Reference" "%s"' % ref, blk)
    blk = re.sub(r'\(reference "[^"]+"\)', '(reference "%s")' % ref, blk)
    blk = re.sub(r'"Value" "[^"]*"', '"Value" "%s"' % value, blk)
    blk = re.sub(r'\(pin "(\d+)" \(uuid "[^"]+"\)\)', lambda m: '(pin "%s" (uuid "%s"))' % (m.group(1), U()), blk)
    return repath(blk, sheet_uuid)


def set_value(blk, value):
    return re.sub(r'"Value" "[^"]*"', '"Value" "%s"' % value, blk)


V = {"Reference": (2.54, -1.27, "left"), "Value": (2.54, 1.27, "left")}       # vertical two-pin parts
H = {"Reference": (0.0, -2.54, ""), "Value": (0.0, 2.54, "")}                  # horizontal two-pin parts

# ======================================================================= 1. Battery 2S + protection
p = Sheet("power_in")
buck_syms_from_power = {r: p.syms.pop(r) for r in ("C1", "C2")}
Y = 63.5
p.text("2 x 18650 in series: 7.4 V nominal, 8.4 V full. Charge the cells off the board, one at a time, in a Li-ion charger.", 25.4, 30.48, 1.5)
p.text("F1: 2 A PTC right at the pack +.  D3: reverse-polarity Schottky (B340B, about 0.35 V at the 0.6 A load).", 25.4, 36.83)
p.text("D1: TVS, 12 V standoff (above the 8.4 V full pack), clamps below 20 V; everything on VIN is rated 25 V or more.", 25.4, 40.64)
p.text("Low-battery cut-off: U1's EN divider on sheet 2 (about 2.9 V per cell).", 25.4, 44.45)
bt1 = p.place(p.syms["BT1"], 38.10, 68.58, 0, V)
bt2 = p.place(p.syms["BT2"], 38.10, 81.28, 0, V)
p.wire(bt1["2"], bt2["1"])
p.wire(bt2["2"], (38.10, 88.90)); p.gnd(38.10, 88.90)
f1 = p.place(p.syms["F1"], 63.50, Y, 90, H)
p.wire(bt1["1"], (50.80, Y), f1["1"]); p.junction(50.80, Y); p.label("VBAT+", 41.91, Y)
tp2 = p.place(p.syms["TP2"], 50.80, Y, 0, {"Reference": (1.27, -5.08, "left"), "Value": (1.27, -3.18, "left")})
sw1 = p.place(p.syms["SW1"], 81.28, Y, 0, {"Reference": (0.0, -5.08, ""), "Value": (0.0, 3.18, "")})
p.wire(f1["2"], sw1["1"]); p.label("VF", 68.58, Y)
d3 = p.place(set_value(p.syms["D3"], "B340B"), 101.60, Y, 0, H)        # mirrored: anode left, cathode right
p.wire(sw1["2"], d3["2"]); p.label("VSW", 88.90, Y)
d1 = p.place(p.syms["D1"], 124.46, 71.12, 270, V)
flg = p.place(p.syms["#FLG0"], 139.70, Y, 0, {"Value": (0.0, -3.81, "")})
p.wire(d3["1"], (124.46, Y), (139.70, Y), (154.94, Y)); p.junction(124.46, Y); p.junction(139.70, Y)
p.wire((124.46, Y), d1["1"]); p.wire(d1["2"], (124.46, 78.74)); p.gnd(124.46, 78.74)
p.label("VIN", 110.49, Y); p.hlabel("VIN", 154.94, Y, 0)
for ref, x in (("TP3", 63.50), ("TP4", 76.20)):
    tp = p.place(p.syms[ref], x, 83.82, 0, {"Reference": (1.27, -5.08, "left"), "Value": (1.27, -3.18, "left")})
    p.wire(tp["1"], (x, 88.90)); p.gnd(x, 88.90)
p.save()

# ======================================================================= 2. Buck to 5 V
b = Sheet("buck_5v")
BU = SHEET["buck_5v"]
for r, blk in buck_syms_from_power.items():
    b.syms[r] = repath(blk, BU)
b.syms["C1"] = set_value(b.syms["C1"], "100n / 50V")
b.syms["C11"] = clone(b.syms["C2"], "C11", "10u / 25V", NEW_UUIDS["C11"], BU)
b.syms["R9"] = clone(b.syms["R2"], "R9", "402k 1%", NEW_UUIDS["R9"], BU)
b.syms["R10"] = clone(b.syms["R2"], "R10", "100k 1%", NEW_UUIDS["R10"], BU)
b.syms["L1"] = set_value(b.syms["L1"], "6u8 / 3.6A")
b.text("LMR51430 buck, 500 kHz:  VOUT = 0.6 x (1 + 100k / 13k7) = 4.98 V", 25.4, 30.48, 1.5)
b.text("Input caps: C1 (100 nF) sits right at U1's VIN/GND pins; C2, C11 (10 uF) are the bulk.", 25.4, 36.83)
b.text("UVLO (R9/R10 on EN): on above 1.23 V x (1 + 402k/100k) = 6.2 V, off below 1.08 V x 5.02 = 5.4 V at VIN,", 25.4, 40.64)
b.text("so the camera pack stops at about 2.85 V per cell instead of being run flat (U1's own UVLO is 3.6 V).", 25.4, 44.45)
YI = 76.20                          # VIN rail
u1 = b.place(b.syms["U1"], 152.40, 88.90, 0, {"Reference": (0.0, -6.35, ""), "Value": (3.81, 10.16, "left")})
b.hlabel("VIN", 30.48, YI, 180); b.label("VIN", 35.56, YI)
xs = [45.72, 60.96, 76.20]
for ref, x in zip(("C11", "C2", "C1"), xs):
    c = b.place(b.syms[ref], x, 83.82, 0, V)
    b.wire((x, YI), c["1"]); b.wire(c["2"], (x, 92.71)); b.gnd(x, 92.71)
XR = 101.60                        # EN divider column
r9 = b.place(b.syms["R9"], XR, 83.82, 0, V)
r10 = b.place(b.syms["R10"], XR, 99.06, 0, V)
b.wire((30.48, YI), (45.72, YI), (60.96, YI), (76.20, YI), (XR, YI), (137.16, YI), (137.16, u1["3"][1]), u1["3"])
for x in (45.72, 60.96, 76.20, XR):
    b.junction(x, YI)
b.wire((XR, YI), r9["1"])
b.wire(r9["2"], (XR, u1["5"][1]), r10["1"]); b.junction(XR, u1["5"][1])
b.wire((XR, u1["5"][1]), u1["5"]); b.label("EN", 109.22, u1["5"][1])
b.wire(r10["2"], (XR, 106.68)); b.gnd(XR, 106.68)
b.wire(u1["1"], (152.40, 102.87)); b.gnd(152.40, 102.87)
c3 = b.place(b.syms["C3"], 170.18, 73.66, 90, H)
b.wire(u1["6"], (c3["1"][0], u1["6"][1]), c3["1"]); b.label("CBOOT", c3["1"][0], 81.28, 90)
l1 = b.place(b.syms["L1"], 186.69, 88.90, 90, H)
b.wire(u1["2"], (c3["2"][0], 88.90), l1["1"]); b.junction(c3["2"][0], 88.90)
b.wire(c3["2"], (c3["2"][0], 88.90)); b.label("SW", 176.53, 88.90)
YO = 88.90                          # +5V rail
xo = [203.20, 218.44, 233.68]
for ref, x in zip(("C4", "C5", "C6"), xo):
    c = b.place(b.syms[ref], x, 96.52, 0, V)
    b.wire((x, YO), c["1"]); b.wire(c["2"], (x, 104.14)); b.gnd(x, 104.14)
r2 = b.place(b.syms["R2"], 254.00, 96.52, 0, V)
r3 = b.place(b.syms["R3"], 254.00, 109.22, 0, V)
c7 = b.place(b.syms["C7"], 266.70, 96.52, 0, V)
tp1 = b.place(b.syms["TP1"], 243.84, YO, 0, {"Reference": (1.27, -5.08, "left"), "Value": (1.27, -3.18, "left")})
b.wire(l1["2"], (196.85, YO), (203.20, YO), (218.44, YO), (233.68, YO), (243.84, YO), (254.00, YO), (266.70, YO), (276.86, YO))
for x in (196.85, 203.20, 218.44, 233.68, 243.84, 254.00, 266.70):
    b.junction(x, YO)
b.label("+5V", 207.01, YO); b.hlabel("+5V", 276.86, YO, 0)
f1g = b.place(b.syms["#FLG1"], 196.85, YO, 0, {"Value": (0.0, -3.81, "")})
for x, c in ((254.00, r2), (266.70, c7)):
    b.wire((x, YO), c["1"])
b.wire(r2["2"], (254.00, 102.87), r3["1"]); b.junction(254.00, 102.87)
b.wire(c7["2"], (266.70, 102.87), (254.00, 102.87))
b.wire((254.00, 102.87), (246.38, 102.87), (246.38, 116.84), (167.64, 116.84), (167.64, u1["4"][1]), u1["4"])
b.label("FB", 167.64, 110.49, 90)
b.wire(r3["2"], (254.00, 116.84)); b.gnd(254.00, 116.84)
f2g = b.place(b.syms["#FLG2"], 30.48, 101.60, 0, {"Value": (0.0, -3.81, "")})
b.wire(f2g["1"], (30.48, 106.68)); b.gnd(30.48, 106.68)
b.save()

# ======================================================================= 3. Pack voltage sense
s = Sheet("sense")
s.text("VBAT_SENSE = VIN x 39k / (100k + 39k).  Full pack 8.4 V (VIN about 8.1 V after D3) -> 2.26 V at GPIO34,", 25.4, 30.48, 1.5)
s.text("inside the ESP32 ADC's 2.45 V range (11 dB).  Firmware: VIN = VBAT_SENSE x 139 / 39; pack = VIN + about 0.35 V.", 25.4, 35.56, 1.5)
r4 = s.place(s.syms["R4"], 63.50, 55.88, 0, V)
r5 = s.place(s.syms["R5"], 63.50, 71.12, 0, V)
c8 = s.place(s.syms["C8"], 76.20, 71.12, 0, V)
s.hlabel("VIN", 50.80, 48.26, 180)
s.wire((50.80, 48.26), (63.50, 48.26), r4["1"])
s.wire(r4["2"], (63.50, 63.50), r5["1"]); s.junction(63.50, 63.50)
s.wire((63.50, 63.50), (76.20, 63.50), (96.52, 63.50)); s.junction(76.20, 63.50)
s.wire((76.20, 63.50), c8["1"])
s.label("VBAT_SENSE", 80.01, 63.50); s.hlabel("VBAT_SENSE", 96.52, 63.50, 0)
for x, c in ((63.50, r5), (76.20, c8)):
    s.wire(c["2"], (x, 78.74)); s.gnd(x, 78.74)
s.save()
print("redrew power_in, buck_5v, sense")
