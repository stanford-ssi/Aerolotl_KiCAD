#!/usr/bin/env python3
"""Generate the battery_pcb hierarchical schematic.

Root page = six labelled blocks wired together.
Each block is its own sheet file under sheets/.

Symbols are pulled from the installed KiCad libraries and embedded so the
project opens standalone.
"""
import os, uuid

KLIB = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols"
HERE = os.path.dirname(os.path.abspath(__file__))
SHEETDIR = os.path.join(HERE, "sheets")
os.makedirs(SHEETDIR, exist_ok=True)


# ---------------- s-expression reader ----------------
def tokens(s):
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        if c in "()":
            yield c; i += 1
        elif c == '"':
            j, buf = i + 1, []
            while j < n:
                if s[j] == "\\":
                    buf.append(s[j + 1]); j += 2
                elif s[j] == '"':
                    break
                else:
                    buf.append(s[j]); j += 1
            yield ("str", "".join(buf)); i = j + 1
        elif c.isspace():
            i += 1
        else:
            j = i
            while j < n and not s[j].isspace() and s[j] not in '()"':
                j += 1
            yield ("sym", s[i:j]); i = j


def parse(s):
    stack = [[]]
    for t in tokens(s):
        if t == "(":
            stack.append([])
        elif t == ")":
            v = stack.pop(); stack[-1].append(v)
        else:
            stack[-1].append(t)
    return stack[0][0]


def head(n):
    return n[0][1] if n and isinstance(n[0], tuple) else None


def kids(n, name):
    return [c for c in n if isinstance(c, list) and head(c) == name]


_libcache = {}


def lib_text(lib):
    if lib not in _libcache:
        _libcache[lib] = open(os.path.join(KLIB, lib + ".kicad_sym")).read()
    return _libcache[lib]


def extract_symbol(lib, name):
    txt = lib_text(lib)
    start = txt.find('\t(symbol "%s"\n' % name)
    if start < 0:
        raise SystemExit("symbol not found: %s:%s" % (lib, name))
    depth, i = 0, start
    while i < len(txt):
        ch = txt[i]
        if ch == '"':
            i += 1
            while txt[i] != '"':
                i += 2 if txt[i] == "\\" else 1
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                break
        i += 1
    block = txt[start:i + 1]
    node = parse(block)
    ext = kids(node, "extends")
    if ext:
        _, pins = extract_symbol(lib, ext[0][1][1])
        return block.strip(), pins
    pins = {}
    for sub in kids(node, "symbol"):
        for p in kids(sub, "pin"):
            at = kids(p, "at")[0]
            num = kids(p, "number")[0][1][1]
            ang = float(at[3][1]) if len(at) > 3 else 0.0
            pins[num] = (float(at[1][1]), float(at[2][1]), ang)
    return block.strip(), pins


U = lambda: str(uuid.uuid4())
ROOT_UUID = U()
GRID = 1.27
snap = lambda v: round(round(v / GRID) * GRID, 2)
STUB = 5.08


class Page:
    """One schematic file - root or sub-sheet."""

    def __init__(self, title, uuid_, path_prefix, paper="A3"):
        self.title, self.uuid, self.prefix, self.paper = title, uuid_, path_prefix, paper
        self.body, self.libs, self.pins, self.refs = [], {}, {}, {}

    def need(self, lib_id):
        if lib_id not in self.libs:
            lib, name = lib_id.split(":", 1)
            blk, pins = extract_symbol(lib, name)
            blk = blk.replace('(symbol "%s"\n' % name, '(symbol "%s"\n' % lib_id, 1)
            self.libs[lib_id], self.pins[lib_id] = blk, pins
        return self.pins[lib_id]

    def place(self, lib_id, ref, value, x, y, footprint="", mirror=False):
        x, y = snap(x), snap(y)
        pins = self.need(lib_id)
        self.refs[ref] = (lib_id, x, y, mirror)
        m = "\n\t\t(mirror y)" if mirror else ""
        pe = "\n".join('\t\t(pin "%s" (uuid "%s"))' % (n, U()) for n in pins)
        self.body.append(f'''	(symbol
		(lib_id "{lib_id}")
		(at {x} {y} 0){m}
		(unit 1)
		(exclude_from_sim no)
		(in_bom yes)
		(on_board yes)
		(dnp no)
		(fields_autoplaced yes)
		(uuid "{U()}")
		(property "Reference" "{ref}"
			(at {snap(x + 3.81)} {snap(y - 2.54)} 0)
			(effects (font (size 1.27 1.27)) (justify left))
		)
		(property "Value" "{value}"
			(at {snap(x + 3.81)} {snap(y + 1.27)} 0)
			(effects (font (size 1.27 1.27)) (justify left))
		)
		(property "Footprint" "{footprint}"
			(at {x} {y} 0)
			(effects (font (size 1.27 1.27)) (hide yes))
		)
		(property "Datasheet" ""
			(at {x} {y} 0)
			(effects (font (size 1.27 1.27)) (hide yes))
		)
{pe}
		(instances
			(project "battery_pcb"
				(path "{self.prefix}"
					(reference "{ref}")
					(unit 1)
				)
			)
		)
	)''')

    def pin_abs(self, ref, num):
        lib_id, sx, sy, mirror = self.refs[ref]
        px, py, ang = self.pins[lib_id][str(num)]
        if mirror:
            px = -px
            if ang in (0.0, 180.0):
                ang = (ang + 180.0) % 360.0
        return round(sx + px, 2), round(sy - py, 2), ang

    def wire(self, a, b):
        a = (snap(a[0]), snap(a[1])); b = (snap(b[0]), snap(b[1]))
        if a == b:
            return
        self.body.append(f'''	(wire
		(pts (xy {a[0]} {a[1]}) (xy {b[0]} {b[1]}))
		(stroke (width 0) (type default))
		(uuid "{U()}")
	)''')

    def poly(self, pts):
        for a, b in zip(pts, pts[1:]):
            self.wire(a, b)

    def junction(self, p):
        p = (snap(p[0]), snap(p[1]))
        self.body.append(f'''	(junction (at {p[0]} {p[1]}) (diameter 0) (color 0 0 0 0) (uuid "{U()}"))''')

    def _lbl(self, kind, x, y, text, angle, shape=None):
        x, y = snap(x), snap(y)
        sh = f'\n\t\t(shape {shape})' if shape else ''
        self.body.append(f'''	({kind} "{text}"{sh}
		(at {x} {y} {angle})
		(fields_autoplaced yes)
		(effects (font (size 1.27 1.27)) (justify {'left' if angle in (0, 90) else 'right'}))
		(uuid "{U()}")
	)''')

    def net(self, ref, pin, name, kind="label"):
        """Stub outward from a pin to a label. kind: label | global_label"""
        x, y, ang = self.pin_abs(ref, pin)
        if ang == 0:      d, la = (-STUB, 0), 180
        elif ang == 180:  d, la = (STUB, 0), 0
        elif ang == 90:   d, la = (0, STUB), 270
        else:             d, la = (0, -STUB), 90
        e = (round(x + d[0], 2), round(y + d[1], 2))
        self.wire((x, y), e)
        if kind == "hier":
            self._lbl("hierarchical_label", e[0], e[1], name, la, shape="passive")
        else:
            self._lbl(kind, e[0], e[1], name, la)

    def link(self, refa, pina, refb, pinb):
        """Direct wire between two pins (same x or same y)."""
        a = self.pin_abs(refa, pina)[:2]
        b = self.pin_abs(refb, pinb)[:2]
        if a[0] == b[0] or a[1] == b[1]:
            self.wire(a, b)
        else:
            self.poly([a, (a[0], b[1]), b])

    def tap(self, x, y, name, dx=12.7, kind="label"):
        x, y = snap(x), snap(y)
        self.junction((x, y))
        self.wire((x, y), (x + dx, y))
        if kind == "hier":
            self._lbl("hierarchical_label", x + dx, y, name, 0, shape="passive")
        else:
            self._lbl(kind, x + dx, y, name, 0)

    def hier(self, x, y, name, angle=0):
        self._lbl("hierarchical_label", snap(x), snap(y), name, angle, shape="passive")

    def text(self, x, y, s, size=1.8):
        self.body.append(f'''	(text "{s}"
		(exclude_from_sim no)
		(at {snap(x)} {snap(y)} 0)
		(effects (font (size {size} {size}) (bold yes)) (justify left bottom))
		(uuid "{U()}")
	)''')

    def render(self):
        libs = "\n".join(self.libs[k] for k in sorted(self.libs)) if self.libs else ""
        tail = '	(sheet_instances\n		(path "/" (page "1"))\n	)\n' if self.prefix == "/" + ROOT_UUID else ""
        return f'''(kicad_sch
	(version 20250114)
	(generator "battery_pcb-gen")
	(generator_version "10.0")
	(uuid "{self.uuid}")
	(paper "{self.paper}")
	(title_block
		(title "{self.title}")
		(company "Stanford SSI")
		(rev "A")
	)
	(lib_symbols
{libs}
	)
{chr(10).join(self.body)}
{tail})
'''


# ================== footprints ==================
C0805 = "Capacitor_SMD:C_0805_2012Metric"
C0603 = "Capacitor_SMD:C_0603_1608Metric"
R0603 = "Resistor_SMD:R_0603_1608Metric"
SOT23 = "Package_TO_SOT_SMD:SOT-23"
SOT236 = "Package_TO_SOT_SMD:SOT-23-6"
HDR19 = "Connector_PinSocket_2.54mm:PinSocket_1x19_P2.54mm_Vertical"
JST5 = "Connector_JST:JST_PH_B5B-PH-K_1x05_P2.00mm_Vertical"
JST2 = "Connector_JST:JST_PH_B2B-PH-K_1x02_P2.00mm_Vertical"
BATT = "Battery:BatteryHolder_Keystone_1042_1x18650"
IND = "Inductor_SMD:L_Bourns_SRN6045TA"
SWFP = "Connector_JST:JST_PH_B2B-PH-K_1x02_P2.00mm_Vertical"  # wires out to a panel switch
FUSE = "Fuse:Fuse_1812_4532Metric"
SMB = "Diode_SMD:D_SMB"
SOD123 = "Diode_SMD:D_SOD-123"
LED0805 = "LED_SMD:LED_0805_2012Metric"

SHEETS = {}          # name -> (uuid, filename, Page)


def new_sheet(key, fname, title):
    su = U()
    p = Page(title, su, "/%s/%s" % (ROOT_UUID, su), paper="A4")
    SHEETS[key] = (su, fname, p)
    return p


# ================== 1. battery / input ==================
p = new_sheet("power", "sheets/power_in.kicad_sch", "1. Camera + ESP32 supply (2S)")
p.text(20, 20, "2 x 18650 in series -> 7.4 V nom, 8.4 V max")
p.place("Device:Battery_Cell", "BT1", "18650 Li-ion", 35, 45, BATT)
p.place("Device:Battery_Cell", "BT2", "18650 Li-ion", 35, 62, BATT)
p.link("BT1", 2, "BT2", 1)
p.net("BT1", 1, "VBAT+")
p.net("BT2", 2, "GND", "global_label")
p.place("Device:Polyfuse", "F1", "2 A hold", 70, 45, FUSE)
p.net("F1", 1, "VBAT+"); p.net("F1", 2, "VF")
p.place("Switch:SW_SPST", "SW1", "CAM POWER", 70, 75, SWFP)
p.net("SW1", 1, "VF"); p.net("SW1", 2, "VSW")
p.place("Device:D_Schottky", "D3", "SS34 reverse prot", 115, 75, SMB, mirror=True)
p.net("D3", 2, "VSW"); p.net("D3", 1, "VIN", "hier")
p.place("Device:D_TVS", "D1", "SMBJ12A", 150, 45, SMB)
p.net("D1", 1, "VIN"); p.net("D1", 2, "GND", "global_label")
p.place("Device:C", "C1", "10u / 25V", 185, 45, C0805)
p.net("C1", 1, "VIN"); p.net("C1", 2, "GND", "global_label")
p.place("Device:C", "C2", "10u / 25V", 205, 45, C0805)
p.net("C2", 1, "VIN"); p.net("C2", 2, "GND", "global_label")
p.place("power:PWR_FLAG", "#FLG0", "PWR_FLAG", 150, 105, "")
p.net("#FLG0", 1, "VIN")
p.text(138, 118, "Power flag - ERC only.")

# ================== 2. buck ==================
p = new_sheet("buck", "sheets/buck_5v.kicad_sch", "2. Buck 8.4 V -> 5.0 V")
p.text(20, 20, "LMR51430   Vout = 0.6 x (1 + 100k / 13k7) = 4.98 V")
p.place("Regulator_Switching:LMR51430", "U1", "LMR51430XFDDCR", 65, 60, SOT236)
p.net("U1", 3, "VIN", "hier")
p.net("U1", 5, "VIN")
p.net("U1", 1, "GND", "global_label")
p.net("U1", 2, "SW"); p.net("U1", 6, "CBOOT"); p.net("U1", 4, "FB")
p.place("Device:C", "C3", "100n", 100, 38, C0603)
p.net("C3", 1, "CBOOT"); p.net("C3", 2, "SW")
p.place("Device:L", "L1", "4u7 / 3A", 125, 60, IND)
p.net("L1", 1, "SW"); p.net("L1", 2, "+5V", "hier")
for r, v, x, fp in [("C4", "22u / 16V", 150, C0805), ("C5", "22u / 16V", 170, C0805),
                    ("C6", "100n", 190, C0603)]:
    p.place("Device:C", r, v, x, 60, fp)
    p.net(r, 1, "+5V"); p.net(r, 2, "GND", "global_label")
p.place("Device:R", "R2", "100k 1%", 220, 45, R0603)
p.place("Device:R", "R3", "13k7 1%", 220, 72, R0603)
p.link("R2", 2, "R3", 1)
p.net("R2", 1, "+5V"); p.net("R3", 2, "GND", "global_label")
p.tap(p.pin_abs("R2", 2)[0], 58.42, "FB")
p.place("Device:C", "C7", "22p", 255, 45, C0603)
p.net("C7", 1, "+5V"); p.net("C7", 2, "FB")
p.place("power:PWR_FLAG", "#FLG1", "PWR_FLAG", 55, 105, "")
p.net("#FLG1", 1, "+5V")
p.place("power:PWR_FLAG", "#FLG2", "PWR_FLAG", 90, 105, "")
p.net("#FLG2", 1, "GND", "global_label")
p.text(45, 118, "Power flags - ERC only, not real parts.")

# ================== 3. pack sense ==================
p = new_sheet("sense", "sheets/sense.kicad_sch", "3. Pack voltage sense")
p.text(20, 20, "8.4 V x 47 / 147 = 2.69 V at the ADC")
p.place("Device:R", "R4", "100k", 60, 50, R0603)
p.place("Device:R", "R5", "47k", 60, 77, R0603)
p.link("R4", 2, "R5", 1)
p.net("R4", 1, "VIN", "hier"); p.net("R5", 2, "GND", "global_label")
p.tap(p.pin_abs("R4", 2)[0], 63.5, "VBAT_SENSE", dx=19.05, kind="hier")
p.place("Device:C", "C8", "100n", 110, 77, C0603)
p.net("C8", 1, "VBAT_SENSE"); p.net("C8", 2, "GND", "global_label")

# ================== 4. ESP32 ==================
p = new_sheet("esp32", "sheets/esp32.kicad_sch", "4. ESP32-DevKitC V4 socket")
p.text(20, 18, "2 x 1x19 female header.  GPIO6-11 go to the module SPI flash - do not use.")
ESP_L = ["3V3", "EN", "IO36", "IO39", "IO34", "IO35", "IO32", "IO33", "IO25",
         "IO26", "IO27", "IO14", "IO12", "GND", "IO13", "IO9", "IO10", "IO11", "5V"]
ESP_R = ["GND", "IO23", "IO22", "TX0", "RX0", "IO21", "GND", "IO19", "IO18",
         "IO5", "IO17", "IO16", "IO4", "IO0", "IO2", "IO15", "IO8", "IO7", "IO6"]
L_NET = {19: ("+5V", "hier"), 14: ("GND", "global_label"),
         5: ("VBAT_SENSE", "hier")}
R_NET = {1: ("GND", "global_label"), 7: ("GND", "global_label"),
         11: ("ESP_TX2", "hier"), 12: ("ESP_RX2", "hier"), 15: ("LED_GPIO", "label")}
p.place("Connector_Generic:Conn_01x19", "J1", "ESP32 left", 80, 75, HDR19)
for i in range(1, 20):
    n, k = L_NET.get(i, ("L%02d_%s" % (i, ESP_L[i - 1]), "label"))
    p.net("J1", i, n, k)
p.place("Connector_Generic:Conn_01x19", "J2", "ESP32 right", 165, 75, HDR19, mirror=True)
for i in range(1, 20):
    n, k = R_NET.get(i, ("R%02d_%s" % (i, ESP_R[i - 1]), "label"))
    p.net("J2", i, n, k)
p.place("Device:C", "C9", "10u", 235, 40, C0805)
p.net("C9", 1, "+5V"); p.net("C9", 2, "GND", "global_label")
p.place("Device:C", "C10", "100n", 255, 40, C0603)
p.net("C10", 1, "+5V"); p.net("C10", 2, "GND", "global_label")
p.place("Device:R", "R6", "1k", 235, 90, R0603)
p.place("Device:LED", "D2", "STATUS", 235, 112, LED0805)
p.net("R6", 1, "LED_GPIO"); p.net("R6", 2, "LED_A")
p.net("D2", 2, "LED_A"); p.net("D2", 1, "GND", "global_label")

# ================== 5. camera ==================
p = new_sheet("camera", "sheets/camera.kicad_sch", "5. RunCam Split 4")
p.text(20, 18, "5-20 V in.  Single 5-pin harness: power, ground and UART.")
p.place("Device:R", "R7", "100R", 75, 55, R0603)
p.net("R7", 1, "ESP_TX2", "hier"); p.net("R7", 2, "CAM_RX")
p.place("Device:R", "R8", "100R", 110, 55, R0603)
p.net("R8", 1, "ESP_RX2", "hier"); p.net("R8", 2, "CAM_TX")
p.place("Connector_Generic:Conn_01x05", "J3", "RunCam Split 4", 175, 55, JST5)
for i, n in enumerate(["+5V", "GND", "CAM_RX", "CAM_TX", "CAM_VIDEO"], 1):
    p.net("J3", i, n, {"GND": "global_label", "+5V": "hier"}.get(n, "label"))
# ================== 6. COTS / SRAD supplies ==================
p = new_sheet("supplies", "sheets/supplies.kicad_sch", "6. Independent 1S supplies")
p.text(20, 18, "Own cell, own switch, per DTEG 6.9.1.")
p.text(20, 26, "These returns are deliberately NOT tied to GND - that independence is the point.")
p.place("Device:Battery_Cell", "BT3", "18650 - COTS", 45, 60, BATT)
p.net("BT3", 1, "COTS_BAT+"); p.net("BT3", 2, "COTS_BAT-")
p.place("Switch:SW_SPST", "SW2", "COTS ARM", 95, 55, SWFP)
p.net("SW2", 1, "COTS_BAT+"); p.net("SW2", 2, "COTS_SW")
p.place("Connector_Generic:Conn_01x02", "J5", "to COTS altimeter", 155, 55, JST2)
p.net("J5", 1, "COTS_SW"); p.net("J5", 2, "COTS_BAT-")
p.place("Device:Battery_Cell", "BT4", "18650 - SRAD", 45, 115, BATT)
p.net("BT4", 1, "SRAD_BAT+"); p.net("BT4", 2, "SRAD_BAT-")
p.place("Switch:SW_SPST", "SW3", "SRAD ARM", 95, 110, SWFP)
p.net("SW3", 1, "SRAD_BAT+"); p.net("SW3", 2, "SRAD_SW")
p.place("Connector_Generic:Conn_01x02", "J6", "to SRAD flight computer", 155, 110, JST2)
p.net("J6", 1, "SRAD_SW"); p.net("J6", 2, "SRAD_BAT-")

# ================== ROOT ==================
root = Page("Battery PCB - AV bay power, arming and camera", ROOT_UUID, "/" + ROOT_UUID, "A3")
PIN = {}


def sheet_sym(key, name, x, y, w, h, pins):
    """pins: list of (netname, 'L'|'R', slot_index). Positions derive from the snapped rect."""
    su, fname, _ = SHEETS[key]
    x, y, w, h = snap(x), snap(y), snap(w), snap(h)
    out = []
    for nm, side, slot in pins:
        px = x if side == "L" else snap(x + w)
        py = snap(y + 12.7 + slot * 10.16)
        ang = 180 if side == "L" else 0
        PIN[(key, nm)] = (px, py)
        out.append(f'''		(pin "{nm}" passive
			(at {px} {py} {ang})
			(uuid "{U()}")
			(effects (font (size 1.27 1.27)) (justify {"left" if side == "L" else "right"}))
		)''')
    root.body.append(f'''	(sheet
		(at {x} {y})
		(size {w} {h})
		(exclude_from_sim no)
		(in_bom yes)
		(on_board yes)
		(dnp no)
		(fields_autoplaced yes)
		(stroke (width 0.2) (type solid))
		(fill (color 0 0 0 0.0000))
		(uuid "{su}")
		(property "Sheetname" "{name}"
			(at {x} {snap(y - 2.54)} 0)
			(effects (font (size 1.6 1.6) (bold yes)) (justify left bottom))
		)
		(property "Sheetfile" "{fname}"
			(at {x} {snap(y + h + 2.54)} 0)
			(effects (font (size 1.1 1.1)) (justify left top))
		)
{chr(10).join(out)}
		(instances
			(project "battery_pcb"
				(path "/{ROOT_UUID}"
					(page "{list(SHEETS).index(key) + 2}")
				)
			)
		)
	)''')


root.text(25, 24, "CAMERA CONTROLLER - signal flow", 3.0)
root.text(25, 32, "GND is a global net on every sheet. Double-click a block to open it.", 1.6)

sheet_sym("power", "1. Battery 2S + protection", 25, 42, 61, 36, [("VIN", "R", 0)])
sheet_sym("buck", "2. Buck to 5 V", 122, 42, 61, 36, [("VIN", "L", 0), ("+5V", "R", 1)])
sheet_sym("sense", "3. Pack voltage sense", 122, 102, 61, 30, [("VIN", "L", 0), ("VBAT_SENSE", "R", 1)])
sheet_sym("esp32", "4. ESP32 socket", 233, 42, 81, 71,
          [("+5V", "L", 0), ("VBAT_SENSE", "L", 1),
           ("ESP_TX2", "R", 2), ("ESP_RX2", "R", 3)])
sheet_sym("camera", "5. RunCam Split 4", 233, 142, 81, 50,
          [("+5V", "L", 0), ("ESP_TX2", "R", 1), ("ESP_RX2", "R", 2)])
sheet_sym("supplies", "6. COTS / SRAD supplies", 25, 152, 96, 50, [])

P = PIN
bx = snap(104)                       # VIN branch column
root.poly([P[("power", "VIN")], (bx, P[("power", "VIN")][1]), P[("buck", "VIN")]])
root.poly([(bx, P[("power", "VIN")][1]), (bx, P[("sense", "VIN")][1]), P[("sense", "VIN")]])
root.junction((bx, P[("power", "VIN")][1]))

vx = snap(208)                       # +5V branch column
root.poly([P[("buck", "+5V")], (vx, P[("buck", "+5V")][1]),
           (vx, P[("esp32", "+5V")][1]), P[("esp32", "+5V")]])
root.poly([(vx, P[("buck", "+5V")][1]), (vx, P[("camera", "+5V")][1]), P[("camera", "+5V")]])
root.junction((vx, P[("buck", "+5V")][1]))

sx = snap(218)
root.poly([P[("sense", "VBAT_SENSE")], (sx, P[("sense", "VBAT_SENSE")][1]),
           (sx, P[("esp32", "VBAT_SENSE")][1]), P[("esp32", "VBAT_SENSE")]])

for nm, col in [("ESP_TX2", 362), ("ESP_RX2", 346)]:
    c = snap(col)
    root.poly([P[("esp32", nm)], (c, P[("esp32", nm)][1]),
               (c, P[("camera", nm)][1]), P[("camera", nm)]])

root.text(25, 216, "Block 6 is electrically isolated from the rest of this board on purpose.", 1.6)

# ================== write ==================
open(os.path.join(HERE, "battery_pcb.kicad_sch"), "w").write(root.render())
for key, (su, fname, page) in SHEETS.items():
    open(os.path.join(HERE, fname), "w").write(page.render())
print("root + %d sheets written" % len(SHEETS))
for k, (su, f, pg) in SHEETS.items():
    print("  %-10s %-32s %2d parts" % (k, f, len(pg.refs)))
