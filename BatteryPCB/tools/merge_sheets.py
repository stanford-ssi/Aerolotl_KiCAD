"""Schematic restructure (review 6, 9 Oct 2026), schematic only - the board's copper and placement don't change.
- Sheets 3 (pack voltage sense), 4 (ESP32 socket) and 5 (RunCam) become one wired sheet, "3. ESP32 + camera"
  (sheets/esp32_camera.kicad_sch), so no sheet is left holding a lone resistor.
- C9/C10 (the 5 V caps at the DevKitC's 5V pin) move onto the +5V output on the buck sheet.
- The COTS / SRAD supplies sheet is renumbered 6 -> 4; the root loses the two emptied blocks.
Every symbol keeps its UUID; tools/sync_from_sch.py then gives the board footprints their new sheet paths and net names.
usage: python3 tools/merge_sheets.py [PROJECT_DIR]      (close KiCad first)"""
import json
import math
import os
import sys
import uuid

ROOT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), ".."))
ROOT_UUID = "19ef3a32-de7c-46ee-a850-2420f6d47f94"
SH = {"power_in": "ae01c8e7-4191-4202-a535-afc32959794b", "buck_5v": "1914f4ed-278a-4026-a86a-769e5e361ab6",
      "esp32_camera": "51707861-a38d-47a0-88b0-b003633f2c22",          # keeps the old ESP32 sheet's UUID
      "supplies": "d30d38cc-20d9-4e05-9f85-c70abea8b778",
      "sense": "bb33270d-1f7a-4186-ad49-327b6f32c122", "camera": "c15ff8c2-214f-4e4d-afd4-b6b1a701e94b"}


# ------------------------------------------------------------------ s-expressions
class S(str):
    """A quoted string, kept exactly as written in the file (escapes included)."""


def parse(t):
    i, n, stack = 0, len(t), [[]]
    while i < n:
        c = t[i]
        if c == "(":
            stack.append([]); i += 1
        elif c == ")":
            x = stack.pop(); stack[-1].append(x); i += 1
        elif c in " \t\r\n":
            i += 1
        elif c == '"':
            j = i + 1
            while t[j] != '"':
                j += 2 if t[j] == "\\" else 1
            stack[-1].append(S(t[i + 1:j])); i = j + 1
        else:
            j = i
            while j < n and t[j] not in " \t\r\n()":
                j += 1
            stack[-1].append(t[i:j]); i = j
    return stack[0][0]


def ser(x, ind=0):
    if isinstance(x, S):
        return '"%s"' % x
    if isinstance(x, str):
        return x
    if not any(isinstance(c, list) for c in x):
        return "(" + " ".join(ser(c) for c in x) + ")"
    k = 0
    while k < len(x) and not isinstance(x[k], list):
        k += 1
    out = "(" + " ".join(ser(c) for c in x[:k])
    for c in x[k:]:
        out += "\n" + "\t" * (ind + 1) + ser(c, ind + 1)
    return out + "\n" + "\t" * ind + ")"


def q(s):
    return S(s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n"))


def f(v):
    s = ("%.4f" % v).rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def U():
    return str(uuid.uuid4())


def kids(n, key):
    return [c for c in n if isinstance(c, list) and c and c[0] == key]


def kid(n, key):
    k = kids(n, key)
    return k[0] if k else None


def prop(sym, name):
    for p in kids(sym, "property"):
        if p[1] == name:
            return p
    return None


def ref_of(sym):
    return str(prop(sym, "Reference")[2])


def load(name):
    return parse(open(os.path.join(ROOT, name)).read())


def save(name, tree):
    open(os.path.join(ROOT, name), "w").write(ser(tree) + "\n")


BODY = ("symbol", "wire", "junction", "label", "global_label", "hierarchical_label", "text", "no_connect", "sheet",
        "bus", "bus_entry", "text_box", "rectangle", "polyline")


# ------------------------------------------------------------------ one sheet being drawn
def rot(x, y, r):
    a = math.radians(r)
    return x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)


def pins_of(libsym):
    out = {}

    def walk(n):
        for c in n:
            if isinstance(c, list) and c:
                if c[0] == "pin":
                    at, num = kid(c, "at"), kid(c, "number")
                    out[str(num[1])] = (float(at[1]), float(at[2]))
                else:
                    walk(c)
    walk(libsym)
    return out


class Sheet:
    def __init__(self, base, libsyms):
        self.head = [c for c in base if not (isinstance(c, list) and c and c[0] in BODY)]
        self.lib = libsyms                     # lib_id -> cached lib symbol
        self.body = []
        self.placed = {}

    def place(self, sym, x, y, r=0, mirror=None, fields=None, sheet=None):
        """fields: {"Reference": (dx, dy, justify), "Value": (...)}; every other field hidden at the symbol."""
        lib_id = str(kid(sym, "lib_id")[1])
        at = kid(sym, "at"); at[1:] = [f(x), f(y), str(r)]
        sym[:] = [c for c in sym if not (isinstance(c, list) and c and c[0] == "mirror")]
        if mirror:
            sym.insert(sym.index(at) + 1, ["mirror", mirror])
        ang = "90" if r % 180 == 90 else "0"           # field angles turn with the symbol: keep the text horizontal
        for p in kids(sym, "property"):
            pat, eff = kid(p, "at"), kid(p, "effects")
            if fields and str(p[1]) in fields:
                dx, dy, just = fields[str(p[1])]
                pat[1:] = [f(x + dx), f(y + dy), ang]
                eff[:] = [c for c in eff if not (isinstance(c, list) and c and c[0] == "justify")]
                if just:
                    eff.append(["justify"] + just.split())
                p[:] = [c for c in p if not (isinstance(c, list) and c and c[0] == "hide")]
            else:
                pat[1:] = [f(x), f(y), "0"]
                if not kid(p, "hide"):
                    p.insert(p.index(pat) + 1, ["hide", "yes"])
        sym[:] = [c for c in sym if not (isinstance(c, list) and c and c[0] == "fields_autoplaced")]
        if sheet:                                          # instance path -> this sheet
            for path in kids(kid(kid(sym, "instances"), "project"), "path"):
                path[1] = S("/%s/%s" % (ROOT_UUID, sheet))
        self.body.append(sym)
        mx, my = (-1 if mirror == "y" else 1), (-1 if mirror == "x" else 1)
        pins = {}
        for n, (px, py) in pins_of(self.lib[lib_id]).items():
            rx, ry = rot(mx * px, my * py, r)
            pins[n] = (round(x + rx, 2), round(y - ry, 2))
        self.placed[ref_of(sym)] = pins
        return pins

    def add(self, t):
        self.body.append(parse(t))

    def wire(self, *pts):
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            self.add('(wire (pts (xy %s %s) (xy %s %s)) (stroke (width 0) (type default)) (uuid "%s"))'
                     % (f(x0), f(y0), f(x1), f(y1), U()))

    def junction(self, x, y):
        self.add('(junction (at %s %s) (diameter 0) (color 0 0 0 0) (uuid "%s"))' % (f(x), f(y), U()))

    def nc(self, x, y):
        self.add('(no_connect (at %s %s) (uuid "%s"))' % (f(x), f(y), U()))

    def label(self, name, x, y, r=0):
        just = "left bottom" if r in (0, 90) else "right bottom"
        self.add('(label "%s" (at %s %s %d) (effects (font (size 1.27 1.27)) (justify %s)) (uuid "%s"))'
                 % (name, f(x), f(y), r, just, U()))

    def glabel(self, name, x, y, r=270):
        just = "left" if r in (0, 90) else "right"
        self.add('(global_label "%s" (shape input) (at %s %s %d) (fields_autoplaced yes) (effects (font (size 1.27 1.27)) '
                 '(justify %s)) (uuid "%s") (property "Intersheetrefs" "${INTERSHEET_REFS}" (at %s %s 0) '
                 '(effects (font (size 1.27 1.27)) (hide yes))))' % (name, f(x), f(y), r, just, U(), f(x), f(y)))

    def gnd(self, x, y, r=270):
        self.glabel("GND", x, y, r)

    def hlabel(self, name, x, y, r):
        just = "left" if r in (0, 90) else "right"
        self.add('(hierarchical_label "%s" (shape passive) (at %s %s %d) (effects (font (size 1.27 1.27)) (justify %s)) '
                 '(uuid "%s"))' % (name, f(x), f(y), r, just, U()))

    def text(self, s, x, y, size=1.27, color="0 0 194 1"):
        self.add('(text "%s" (exclude_from_sim no) (at %s %s 0) (effects (font (size %s %s) (thickness 0.254) (bold yes) '
                 '(color %s)) (justify left bottom)) (uuid "%s"))' % (q(s), f(x), f(y), size, size, color, U()))

    def tree(self, title=None, used=None):
        head = [parse(ser(c)) if isinstance(c, list) else c for c in self.head]
        if title:
            kid(kid(head, "title_block"), "title")[1] = q(title)
        if used is not None:                 # cache only the library symbols this sheet uses
            ls = kid(head, "lib_symbols")
            ls[1:] = [self.lib[k] for k in sorted(used)]
        k = next(i for i, c in enumerate(head) if isinstance(c, list) and c and c[0] == "embedded_fonts") \
            if kid(head, "embedded_fonts") else len(head)
        return head[:k] + self.body + head[k:]


def libsyms(tree):
    return {str(c[1]): c for c in kids(kid(tree, "lib_symbols"), "symbol")}


def symbols(tree):
    return {ref_of(s): s for s in kids(tree, "symbol")}


V = {"Reference": (2.54, -1.27, "left"), "Value": (2.54, 1.27, "left")}          # vertical two-pin parts
TPF = {"Reference": (1.27, -5.08, "left"), "Value": (1.27, -3.18, "left")}        # test points
FLAG = {"Value": (0.0, -3.81, "")}

# ================================================================== load
trees = {n: load("sheets/%s.kicad_sch" % n) for n in ("buck_5v", "esp32", "camera", "sense", "supplies")}
LIBS, SY = {}, {}
for t in trees.values():
    LIBS.update(libsyms(t)); SY.update(symbols(t))

# ================================================================== 2. Buck to 5 V  (+ C9/C10 on the output)
b = Sheet(trees["buck_5v"], LIBS)
BU = SH["buck_5v"]
b.text("LMR51430 buck, 500 kHz:  VOUT = 0.6 x (1 + 100k / 13k7) = 4.98 V", 25.4, 30.48, 1.5)
b.text("Input caps: C1 (100 nF) sits right at U1's VIN/GND pins; C2, C11 (10 uF) are the bulk.", 25.4, 36.83)
b.text("UVLO (R9/R10 on EN): on above 1.23 V x (1 + 402k/100k) = 6.2 V, off below 1.08 V x 5.02 = 5.4 V at VIN,", 25.4, 40.64)
b.text("so the camera pack stops at about 2.85 V per cell instead of being run flat (U1's own UVLO is 3.6 V).", 25.4, 44.45)
b.text("Output caps: C4, C5 (22 uF) and C6 (100 nF) sit at L1 / U1.  C9 (10 uF) and C10 (100 nF) sit at the DevKitC's 5V pin"
       " (J1 pin 19) on the board.", 25.4, 48.26)
YI, YO, UX = 76.20, 88.90, 129.54
u1 = b.place(SY["U1"], UX, 88.90, 0, None, {"Reference": (0.0, -6.35, ""), "Value": (3.81, 10.16, "left")})
b.hlabel("VIN", 30.48, YI, 180); b.label("VIN", 33.02, YI)
for ref, x in zip(("C11", "C2", "C1"), (43.18, 60.96, 78.74)):   # 17.78 apart: "10u / 25V" clears the next cap
    c = b.place(SY[ref], x, 83.82, 0, None, V)
    b.wire((x, YI), c["1"]); b.wire(c["2"], (x, 92.71)); b.gnd(x, 92.71)
XR, XV = 96.52, u1["3"][0] - 5.08
r9 = b.place(SY["R9"], XR, 83.82, 0, None, V)
r10 = b.place(SY["R10"], XR, 99.06, 0, None, V)
b.wire((30.48, YI), (43.18, YI), (60.96, YI), (78.74, YI), (XR, YI), (XV, YI), (XV, u1["3"][1]), u1["3"])
for x in (43.18, 60.96, 78.74, XR):
    b.junction(x, YI)
b.wire((XR, YI), r9["1"])
b.wire(r9["2"], (XR, u1["5"][1]), r10["1"]); b.junction(XR, u1["5"][1])
b.wire((XR, u1["5"][1]), u1["5"]); b.label("EN", XR + 7.62, u1["5"][1])
b.wire(r10["2"], (XR, 106.68)); b.gnd(XR, 106.68)
b.wire(u1["1"], (UX, 102.87)); b.gnd(UX, 102.87)
c3 = b.place(SY["C3"], UX + 17.78, 73.66, 90, None, {"Reference": (0.0, -2.54, ""), "Value": (0.0, 2.54, "")})
b.wire(u1["6"], (c3["1"][0], u1["6"][1]), c3["1"]); b.label("CBOOT", c3["1"][0], 81.28, 90)
l1 = b.place(SY["L1"], UX + 34.29, YO, 90, None, {"Reference": (0.0, -2.54, ""), "Value": (0.0, 2.54, "")})
b.wire(u1["2"], (c3["2"][0], YO), l1["1"]); b.junction(c3["2"][0], YO)
b.wire(c3["2"], (c3["2"][0], YO)); b.label("SW", UX + 24.13, YO)
XF = UX + 44.45                     # power flag, then the output caps
xo = [XF + 6.35 + dx for dx in (0, 17.78, 35.56, 48.26, 60.96)]     # wide gaps after the "22u / 16V" values
for ref, x in zip(("C4", "C5", "C6", "C9", "C10"), xo):
    c = b.place(SY[ref], x, 96.52, 0, None, V, sheet=BU if ref in ("C9", "C10") else None)
    b.wire((x, YO), c["1"]); b.wire(c["2"], (x, 104.14)); b.gnd(x, 104.14)
XT = xo[-1]                        # TP1 sits on the rail above C10
XR2, XC7 = XT + 10.16, XT + 25.40
tp1 = b.place(SY["TP1"], XT, YO, 0, None, TPF)
r2 = b.place(SY["R2"], XR2, 96.52, 0, None, V)
r3 = b.place(SY["R3"], XR2, 109.22, 0, None, V)
c7 = b.place(SY["C7"], XC7, 96.52, 0, None, V)
rail = [l1["2"], (XF, YO)] + [(x, YO) for x in xo] + [(XR2, YO), (XC7, YO), (XC7 + 10.16, YO)]
b.wire(*rail)
for x in [XF] + xo + [XR2, XC7]:
    b.junction(x, YO)
b.label("+5V", XF + 1.27, YO); b.hlabel("+5V", XC7 + 10.16, YO, 0)
b.place(SY["#FLG1"], XF, YO, 0, None, FLAG)
for x, c in ((XR2, r2), (XC7, c7)):
    b.wire((x, YO), c["1"])
b.wire(r2["2"], (XR2, 102.87), r3["1"]); b.junction(XR2, 102.87)
b.wire(c7["2"], (XC7, 102.87), (XR2, 102.87))
b.wire((XR2, 102.87), (XR2 - 5.08, 102.87), (XR2 - 5.08, 116.84), (UX + 15.24, 116.84), (UX + 15.24, u1["4"][1]), u1["4"])
b.label("FB", UX + 15.24, 110.49, 90)
b.wire(r3["2"], (XR2, 116.84)); b.gnd(XR2, 116.84)
f2g = b.place(SY["#FLG2"], 30.48, 101.60, 0, None, FLAG)
b.wire(f2g["1"], (30.48, 106.68)); b.gnd(30.48, 106.68)
used = {str(kid(s, "lib_id")[1]) for s in b.body if s[0] == "symbol"}
save("sheets/buck_5v.kicad_sch", b.tree(used=used))

# ================================================================== 3. ESP32 + camera (sense + ESP32 + RunCam)
e = Sheet(trees["esp32"], LIBS)
ES = SH["esp32_camera"]
e.text("2 x 1x19 female header for the ESP32-DevKitC V4.  GPIO6-11 go to the module SPI flash - do not use.", 25.4, 30.48, 1.5)
e.text("Pack sense: VBAT_SENSE = VIN x 39k / (100k + 39k).  Full pack 8.4 V (VIN about 8.1 V after D3) -> 2.26 V at GPIO34,"
       " inside the ESP32 ADC's 2.45 V range (11 dB).", 25.4, 36.83)
e.text("Firmware: VIN = VBAT_SENSE x 139 / 39; pack = VIN + about 0.35 V.", 25.4, 40.64)
e.text("RunCam Split 4: 5-20 V in.  Single 5-pin harness: power, ground and UART (R7 / R8 in series with the UART lines).",
       25.4, 44.45)
Y = 101.60
jf1 = {"Reference": (2.54, -1.27, "left"), "Value": (2.54, 1.27, "left")}
jf2 = {"Reference": (-2.54, -1.27, "right"), "Value": (-2.54, 1.27, "right")}
j1 = e.place(SY["J1"], 132.08, Y, 0, None, jf1, sheet=ES)            # pins face left
j2 = e.place(SY["J2"], 162.56, Y, 0, "y", jf2, sheet=ES)             # mirrored: pins face right
J1L = ["L01_3V3", "L02_EN", "L03_IO36", "L04_IO39", None, "L06_IO35", "L07_IO32", "L08_IO33", "L09_IO25", "L10_IO26",
       "L11_IO27", "L12_IO14", "L13_IO12", None, "L15_IO13", "L16_IO9", "L17_IO10", "L18_IO11", None]
J2L = [None, "R02_IO23", "R03_IO22", "R04_TX0", "R05_RX0", "R06_IO21", None, "R08_IO19", "R09_IO18", "R10_IO5", None, None,
       "R13_IO4", "R14_IO0", None, "R16_IO15", "R17_IO8", "R18_IO7", "R19_IO6"]
for n, name in enumerate(J1L, 1):
    if name:
        x, y = j1[str(n)]; e.wire((x, y), (x - 7.62, y)); e.label(name, x - 7.62, y, 180)
for n, name in enumerate(J2L, 1):
    if name:
        x, y = j2[str(n)]; e.wire((x, y), (x + 5.08, y)); e.label(name, x + 5.08, y, 0)
# left: pack voltage sense into J1-5 (GPIO34), GND, 5V
r4 = e.place(SY["R4"], 91.44, 80.01, 0, None, V, sheet=ES)
r5 = e.place(SY["R5"], 91.44, 97.79, 0, None, V, sheet=ES)
c8 = e.place(SY["C8"], 104.14, 97.79, 0, None, V, sheet=ES)
e.hlabel("VIN", 78.74, 72.39, 180); e.wire((78.74, 72.39), (91.44, 72.39), r4["1"])
YS = j1["5"][1]
e.wire(r4["2"], (91.44, YS), r5["1"]); e.junction(91.44, YS)
e.wire((91.44, YS), (104.14, YS), j1["5"]); e.junction(104.14, YS)
e.wire((104.14, YS), c8["1"]); e.label("VBAT_SENSE", 106.68, YS)
for x, c in ((91.44, r5), (104.14, c8)):
    e.wire(c["2"], (x, 104.14)); e.gnd(x, 104.14)
e.wire(j1["14"], (119.38, j1["14"][1])); e.gnd(119.38, j1["14"][1], 180)
e.hlabel("+5V", 114.30, j1["19"][1], 180); e.wire((114.30, j1["19"][1]), j1["19"])
# right: GND, camera UART through R7/R8 to J3, status LED
for n in ("1", "7"):
    e.wire(j2[n], (172.72, j2[n][1])); e.gnd(172.72, j2[n][1], 0)
YT, YR = j2["11"][1], j2["12"][1]
j3 = e.place(SY["J3"], 241.30, YT, 0, None, {"Reference": (3.81, -2.54, "left"), "Value": (3.81, 0.0, "left")}, sheet=ES)
r7 = e.place(SY["R7"], 185.42, YT, 90, None, {"Reference": (0.0, -5.08, ""), "Value": (0.0, -2.54, "")}, sheet=ES)
r8 = e.place(SY["R8"], 195.58, YR, 90, None, {"Reference": (0.0, 5.08, ""), "Value": (0.0, 2.54, "")}, sheet=ES)
e.wire(j2["11"], r7["1"]); e.wire(r7["2"], j3["3"])
e.wire(j2["12"], r8["1"]); e.wire(r8["2"], j3["4"])
e.label("ESP_TX2", 170.18, YT); e.label("ESP_RX2", 170.18, YR)
e.label("CAM_RX", 213.36, YT); e.label("CAM_TX", 213.36, YR)
e.wire(j3["1"], (231.14, j3["1"][1])); e.hlabel("+5V", 231.14, j3["1"][1], 180)
e.wire(j3["2"], (231.14, j3["2"][1])); e.gnd(231.14, j3["2"][1], 180)
e.wire(j3["5"], (231.14, j3["5"][1])); e.label("CAM_VIDEO", 231.14, j3["5"][1], 180)
YL = j2["15"][1]
r6 = e.place(SY["R6"], 187.96, YL, 90, None, {"Reference": (0.0, 5.08, ""), "Value": (0.0, 2.54, "")}, sheet=ES)
d2 = e.place(SY["D2"], 201.93, YL, 180, None, {"Reference": (0.0, -5.08, ""), "Value": (0.0, -2.54, "")}, sheet=ES)
e.wire(j2["15"], r6["1"]); e.wire(r6["2"], d2["2"]); e.wire(d2["1"], (d2["1"][0], YL + 2.54)); e.gnd(d2["1"][0], YL + 2.54)
e.label("LED_GPIO", 168.91, YL); e.label("LED_A", 192.41, YL)
used = {str(kid(s, "lib_id")[1]) for s in e.body if s[0] == "symbol"}
save("sheets/esp32_camera.kicad_sch", e.tree(title="3. ESP32-DevKitC V4 socket + RunCam Split 4", used=used))

# ================================================================== 4. supplies: renumbered only
sup = trees["supplies"]
kid(kid(sup, "title_block"), "title")[1] = q("4. Independent 1S supplies")
save("sheets/supplies.kicad_sch", sup)

# ================================================================== root: drop the emptied blocks, rewire
r = load("battery_pcb.kicad_sch")
r[:] = [c for c in r if not (isinstance(c, list) and c and c[0] in ("wire", "junction"))]
for c in list(kids(r, "sheet")):
    uid = str(kid(c, "uuid")[1])
    if uid in (SH["sense"], SH["camera"]):
        r.remove(c); continue
    if uid == SH["supplies"]:
        prop(c, "Sheetname")[2] = q("4. COTS / SRAD supplies")
    if uid == SH["esp32_camera"]:
        prop(c, "Sheetname")[2] = q("3. ESP32 + camera")
        prop(c, "Sheetfile")[2] = q("sheets/esp32_camera.kicad_sch")
        c[:] = [p for p in c if not (isinstance(p, list) and p and p[0] == "pin")]
        k = c.index(kid(c, "instances"))
        for name, y in (("+5V", 64.77), ("VIN", 100.33)):
            c.insert(k, parse('(pin "%s" passive (at 232.41 %s 180) (uuid "%s") (effects (font (size 1.27 1.27)) '
                              '(justify left)))' % (name, f(y), U())))
            k += 1
    for page in kids(kid(kid(c, "instances"), "project"), "path"):
        page_node = kid(page, "page")
        page_node[1] = S({SH["power_in"]: "2", SH["buck_5v"]: "3", SH["esp32_camera"]: "4", SH["supplies"]: "5"}[uid])
for t in kids(r, "text"):
    if str(t[1]).startswith("Block 6"):
        t[1] = q("Block 4 is electrically isolated from the rest of this board on purpose.")
root = Sheet([], {})
root.wire((86.36, 54.61), (104.14, 54.61), (121.92, 54.61)); root.junction(104.14, 54.61)
root.wire((104.14, 54.61), (104.14, 100.33), (232.41, 100.33))
root.wire((182.88, 64.77), (232.41, 64.77))
k = r.index(kid(r, "sheet"))
r[k:k] = root.body
save("battery_pcb.kicad_sch", r)

# ================================================================== files and project
for n in ("esp32", "camera", "sense"):
    os.remove(os.path.join(ROOT, "sheets", n + ".kicad_sch"))
pro = os.path.join(ROOT, "battery_pcb.kicad_pro")
d = json.load(open(pro))
d["sheets"] = [[ROOT_UUID, "battery_pcb"]] + [[SH[k], n] for k, n in (
    ("power_in", "1. Battery 2S + protection"), ("buck_5v", "2. Buck to 5 V"), ("esp32_camera", "3. ESP32 + camera"),
    ("supplies", "4. COTS / SRAD supplies"))]
json.dump(d, open(pro, "w"), indent=2)
open(pro, "a").write("\n")
print("merged: sheets 3-5 -> 3. ESP32 + camera; C9/C10 -> buck output; supplies renumbered 4")
