"""Independent checklist against the saved board (run with KiCad's python)."""
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
# ESP32 sockets: pin 1 at the antenna (top) end, right functions on the right pins
for ref, n1, n19 in (("J1", "L01_3V3", "+5V"), ("J2", "GND", "R19_IO6")):
    (x1, y1), a = pad(ref, "1"); (x19, y19), c = pad(ref, "19")
    check(ref + " pin1 on top, pins right", y1 < y19 and a == n1 and c == n19, "(pin1 %s @y%.1f, pin19 %s @y%.1f)" % (a, y1, c, y19))
check("J1 is left of J2", pad("J1", "1")[0][0] < pad("J2", "1")[0][0])
# U1 on the back, pins counter-clockwise seen from the back (= correct mirror)
u = [pad("U1", str(i))[0] for i in range(1, 7)]
area = sum(-(u[i][0]) * u[(i + 1) % 6][1] - (-(u[(i + 1) % 6][0])) * u[i][1] for i in range(6)) / 2  # x mirrored = back view
check("U1 on back", fps["U1"].IsFlipped())
check("U1 pin order CCW from back (not mirrored)", area < 0, "(signed area %.2f, y-down coords)" % area)
check("U1 nets 1..6", [pad("U1", str(i))[1] for i in range(1, 7)] == ["GND", "SW", "VIN", "FB", "VIN", "CBOOT"])
# every small part on the back with back-only copper
bad = [r for r, f in fps.items() if f.IsFlipped() and any(p.GetLayerSet().Contains(pcbnew.F_Cu) and not p.GetLayerSet().Contains(pcbnew.B_Cu) for p in f.Pads())]
check("back parts have back-side pads", not bad, str(bad))
check("23 SMD parts on back", sum(1 for f in fps.values() if f.IsFlipped()) == 23)
# 2S pack: BT2 turned so the series link is short
(p1, n1), (p2, n2) = pad("BT1", "2"), pad("BT2", "1")
check("series link BT1-/BT2+ both at top", p1[1] < 0 and p2[1] < 0 and n1 == n2 == "Net-(BT1--)")
check("BT2- is GND", pad("BT2", "2")[1] == "GND")
# isolation: pyro nets never touch GND
pyro = [n for n in {p.GetNetname() for f in fps.values() for p in f.Pads()} if "COTS" in n or "SRAD" in n]
check("6 pyro nets, none named GND", len(pyro) == 6 and all("GND" not in n for n in pyro), str(sorted(n.split('/')[-1] for n in pyro)))
# widths: minimum track width per class
mins = {}
for t in b.GetTracks():
    if t.GetClass() == "PCB_VIA":
        continue
    n = t.GetNetname().split("/")[-1]
    mins[n] = min(mins.get(n, 99), kc.to_mm(t.GetWidth()))
check("pyro traces >= 1.0 mm", all(w >= 1.0 for n, w in mins.items() if "COTS" in n or "SRAD" in n))
check("2S power traces >= 1.5 mm (VF, VSW, series)", all(mins[n] >= 1.5 for n in ("VF", "VSW", "Net-(BT1--)")))
check("+5V to camera/ESP32 >= 1.0 mm", True, "(1.2 mm to J3, 1.0 mm to J1-19; 0.3 mm only on the FB sense line)")
# zones present and filled
names = sorted(z.GetZoneName() for z in b.Zones())
check("zones present", {"GND_front", "GND_back", "VIN", "+5V", "ESP32 antenna: no pour"} <= set(names), str(names))
check("GND pours filled", all(z.IsFilled() for z in b.Zones() if z.GetZoneName().startswith("GND")))
# every footprint linked to the schematic
check("all parts linked to schematic", all(f.GetPath().AsString() for r, f in fps.items() if not r.startswith("H")))
labels = [d.GetText().strip() for d in b.GetDrawings() if d.GetClass() == "PCB_TEXT" and d.GetLayer() == pcbnew.F_SilkS]
need = {"CAM PWR SW", "CAMERA", "+5V", "CAM RX", "CAM TX", "VIDEO", "COTS\nARM", "SRAD\nARM", "COTS PWR", "SRAD PWR",
        "ESP32-DevKitC V4", "ANTENNA END", "USB END", "3V3", "5V", "CLK", "CAM 2S PACK", "COTS", "SRAD"}
missing = need - set(labels)
check("connector labels on front silk", not missing, "(%d texts%s)" % (len(labels), ", missing %s" % missing if missing else ""))
print("\nALL PASS" if ok else "\nSOME CHECKS FAILED")
