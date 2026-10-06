"""Independent checklist for layout A (run with KiCad's python): mechanics from the av-bay CAD + electrical sanity."""
import sys, math, pcbnew, kc
b = kc.load(sys.argv[1] if len(sys.argv) > 1 else "battery_pcb.kicad_pcb")
fps = kc.fp_by_ref(b)
ok = True
def check(name, cond, detail=""):
    global ok
    ok &= bool(cond)
    print("%-4s %s %s" % ("PASS" if cond else "FAIL", name, detail))
def pad(ref, num):
    for p in fps[ref].Pads():
        if p.GetNumber() == num:
            return kc.rel(p.GetPosition()), p.GetNetname().split("/")[-1]
R = kc.R_BOARD
# ---- mechanics (match the Onshape av bay stack)
arcs = [d for d in b.GetDrawings() if d.GetLayer() == pcbnew.Edge_Cuts and d.GetShape() == pcbnew.SHAPE_T_ARC]
segs = [d for d in b.GetDrawings() if d.GetLayer() == pcbnew.Edge_Cuts and d.GetShape() == pcbnew.SHAPE_T_SEGMENT]
radii = [kc.to_mm(a.GetRadius()) for a in arcs]
check("outline %.2f in (%.2f mm) circle" % (kc.DISC_IN, 2 * R), len(arcs) == 5 and all(abs(r - R) < 0.01 for r in radii), "(%d arcs, r=%s)" % (len(arcs), [round(r, 3) for r in radii]))
check("five edge cut-outs", len(segs) == 15, "(%d notch segments)" % len(segs))
h = {r: (kc.rel(fps[r].GetPosition()), kc.to_mm(list(fps[r].Pads())[0].GetDrillSize().x)) for r in ("H1", "H2", "H3", "H4")}
check("rod holes 13/32 in, 120 mm apart through the centre", abs(h["H1"][1] - 10.32) < 0.01 and abs(h["H2"][1] - 10.32) < 0.01
      and abs(h["H2"][0][0] - h["H1"][0][0] - 120) < 0.01 and h["H1"][0][1] == h["H2"][0][1] == 0, str(h["H1"]) + str(h["H2"]))
check("COTS screw holes 4.5 mm, 17.4 mm apart", abs(h["H3"][1] - 4.5) < 0.01 and abs(h["H4"][0][0] - h["H3"][0][0] - 17.4) < 0.01, str(h["H3"]) + str(h["H4"]))
h5 = {r: (kc.rel(fps[r].GetPosition()), kc.to_mm(list(fps[r].Pads())[0].GetDrillSize().x)) for r in ("H5", "H6")}
check("pin-switch stack M3 holes at (18.5, -41.88) and (-18.5, -48.88)", all(abs(h5[r][1] - 3.2) < 0.01 for r in h5)
      and h5["H5"][0] == (18.5, -41.88) and h5["H6"][0] == (-18.5, -48.88), str(h5))
# nothing within a 3/8 SAE washer (r 10.32) of a rod on either side, and no copper there
bad = []
for f in b.GetFootprints():
    if f.GetReference().startswith("H"): continue
    for p in f.Pads():
        x, y = kc.rel(p.GetPosition())
        for rx in (-60, 60):
            if math.hypot(x - rx, y) < 10.32 + 1.0: bad.append(f.GetReference())
for t in b.GetTracks():
    for v in (t.GetStart(), t.GetEnd()):
        x, y = kc.rel(v)
        for rx in (-60, 60):
            if math.hypot(x - rx, y) < 10.6: bad.append("track " + t.GetNetname())
check("no pads or tracks under the rod washers", not bad, str(bad))
# ---- ESP32 DevKitC underneath: sockets on the back, pin 1 at the antenna (top) end, mirrored columns
for ref, n1, n19 in (("J1", "L01_3V3", "+5V"), ("J2", "GND", "R19_IO6")):
    (x1, y1), a = pad(ref, "1"); (x19, y19), c = pad(ref, "19")
    check(ref + " on back, pin1 at top, right nets", fps[ref].IsFlipped() and y1 < y19 and a == n1 and c == n19, "(pin1 %s @y%.1f, pin19 %s @y%.1f)" % (a, y1, c, y19))
check("J1 right of J2 (DevKitC parts-down, seen from the front)", abs(pad("J1", "1")[0][0] - pad("J2", "1")[0][0] - 25.4) < 0.01)
hold = [kc.rel(fps[r].GetPosition())[0] for r in ("BT1", "BT2", "BT3", "BT4")]
gaps = min(abs(pad(j, "1")[0][0] - x) - 10.325 for j in ("J1", "J2") for x in hold)
check("socket pins come up between the holders (>=1.4 mm from holder bodies)", gaps >= 1.4, "(min %.2f mm)" % gaps)
# Keystone 1042 (3D model): body ends 38.525 mm and the 6.35 mm wide solder tabs 43.205 mm from the holder centre.
# TeleMetrum sled base (SSI AVBay1): 25.4 mm wide, near edge 4 mm in from the bolt holes. Pin-switch carriers: inner edge 36.88 mm.
by = {r: kc.rel(fps[r].GetPosition()) for r in ("BT1", "BT2", "BT3", "BT4")}
under = [r for r, (x, y) in by.items() if abs(x) - 3.175 < 12.7]
sled = min(h["H3"][0][1] - 4.0 - (y + 43.205) for r, (x, y) in by.items() if r in under)
check("TeleMetrum sled base clears the BT2/BT3 solder tabs (>= 0.4 mm)", sled >= 0.4 and len(under) == 2, "(%.2f mm, %s)" % (sled, under))
stack = min((y - 38.525) + 36.88 for r, (x, y) in by.items() if abs(x) - 10.325 < 22.5)
check("pin-switch carriers clear the holder ends (>= 0.4 mm)", stack >= 0.4, "(%.2f mm)" % stack)
# ---- buck and power
u = [pad("U1", str(i))[0] for i in range(1, 7)]
area = sum(-(u[i][0]) * u[(i + 1) % 6][1] - (-(u[(i + 1) % 6][0])) * u[i][1] for i in range(6)) / 2
check("U1 on back, pin order not mirrored", fps["U1"].IsFlipped() and area < 0)
check("U1 nets 1..6", [pad("U1", str(i))[1] for i in range(1, 7)] == ["GND", "SW", "VIN", "FB", "VIN", "CBOOT"])
check("31 parts on back (23 SMD + 2 ESP32 sockets + camera J3 + 4 camera standoffs + camera model)", sum(1 for f in fps.values() if f.IsFlipped()) == 31)
(p1, n1), (p2, n2) = pad("BT1", "2"), pad("BT2", "1")
check("series link BT1-/BT2+ both at top", p1[1] < 0 and p2[1] < 0 and n1 == n2 == "Net-(BT1--)")
check("BT2- is GND", pad("BT2", "2")[1] == "GND")
pyro = [n for n in {p.GetNetname() for f in fps.values() for p in f.Pads()} if "COTS" in n or "SRAD" in n]
check("6 pyro nets (BAT+, switched, BAT- for COTS and SRAD), none named GND", len(pyro) == 6 and all("GND" not in n for n in pyro))
for cell, sw, j in (("BT3", "SW2", "J5"), ("BT4", "SW3", "J6")):
    check("%s+ -> %s (pin switch) -> %s-1, %s- -> %s-2" % (cell, sw, j, cell, j),
          pad(cell, "1")[1] == pad(sw, "1")[1] and pad(sw, "2")[1] == pad(j, "1")[1] and pad(cell, "2")[1] == pad(j, "2")[1]
          and len({pad(cell, "1")[1], pad(sw, "2")[1], pad(cell, "2")[1]}) == 3)
    check("%s+ at the top, %s beside the pin-switch stack (< 25 mm from H5)" % (cell, sw),
          pad(cell, "1")[0][1] < 0 and math.hypot(pad(sw, "1")[0][0] - 18.5, pad(sw, "1")[0][1] + 41.88) < 25)
lat = {r: fps[r].GetFPIDAsString() for r in ("SW1", "SW2", "SW3", "J5", "J6", "J3")}
check("harness connectors: Micro-Fit 3.0 (SW1-3, J5), JST XH to the Aerolotl (J6), JST GH camera (J3)",
      all("Micro-Fit_3.0" in lat[r] for r in ("SW1", "SW2", "SW3", "J5")) and "JST_XH" in lat["J6"] and "JST_GH" in lat["J3"], str(lat))
cams = [kc.rel(fps["H%d" % k].GetPosition()) for k in range(7, 11)]
xs, ys = sorted({c[0] for c in cams}), sorted({c[1] for c in cams})
check("camera: 4 M2 standoffs on the back on a 25.5 mm square, J3 on the back",
      all(fps["H%d" % k].IsFlipped() for k in range(7, 11)) and len(xs) == len(ys) == 2 and abs(xs[1] - xs[0] - 25.5) < 0.01
      and abs(ys[1] - ys[0] - 25.5) < 0.01 and fps["J3"].IsFlipped(), str(cams))
mins = {}
for t in b.GetTracks():
    if t.GetClass() == "PCB_VIA": continue
    n = t.GetNetname().split("/")[-1]; mins[n] = min(mins.get(n, 99), kc.to_mm(t.GetWidth()))
check("pyro traces >= 1.0 mm", all(w >= 1.0 for n, w in mins.items() if "COTS" in n or "SRAD" in n))
check("2S power traces >= 1.5 mm (VF, VSW, series)", all(mins[n] >= 1.5 for n in ("VF", "VSW", "Net-(BT1--)")))
names = sorted(z.GetZoneName() for z in b.Zones())
check("zones + keepouts present", {"GND_front", "GND_back", "VIN", "+5V", "ESP32 antenna: no pour", "rod washer keepout", "COTS screw keepout"} <= set(names))
check("GND pours filled", all(z.IsFilled() for z in b.Zones() if z.GetZoneName().startswith("GND")))
check("all parts linked to schematic", all(f.GetPath().AsString() for r, f in fps.items() if not r.startswith("H") and not r.startswith("CAM")))
labels = {d.GetText().strip() for d in b.GetDrawings() if d.GetClass() == "PCB_TEXT" and d.GetLayer() in (pcbnew.F_SilkS, pcbnew.B_SilkS)}
tpn = {r: {p.GetNetname().split("/")[-1] for p in fps[r].Pads()} for r in ("TP1", "TP2", "TP3", "TP4") if r in fps}
check("test points: TP1 +5V, TP2 VBAT+, TP3/TP4 GND (through-hole)", tpn == {"TP1": {"+5V"}, "TP2": {"VBAT+"}, "TP3": {"GND"}, "TP4": {"GND"}}
      and all(p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH for r in tpn for p in fps[r].Pads()), str(tpn))
need = {"CAM PWR SW", "CAMERA", "COTS OUT", "SRAD OUT", "COTS ARM", "SRAD ARM", "CAM 2S PACK", "ANTENNA END", "USB END", "3V3", "5V", "CLK"}
check("connector labels on silk", need <= labels, str(need - labels) if need - labels else "(%d texts)" % len(labels))
print("\nALL PASS" if ok else "\nSOME CHECKS FAILED")
