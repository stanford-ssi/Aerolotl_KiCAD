"""Layout A, stage 1: 5.72 in outline (kc.DISC_IN) with five edge cut-outs with the three cut-outs, two 3/8 rod holes 120 mm apart,
two 4.5 mm COTS-mount screw holes, batteries re-spaced, ESP32 DevKitC moved to the back
(sockets on the underside, pins coming up between the holders), everything re-placed.
Starts from the user's 12:24 board. Removes all copper (re-routed in stage 2).
usage: place_A.py IN.kicad_pcb OUT.kicad_pcb"""
import os, sys, math, pcbnew, kc
PRETTY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "battery_pcb.pretty")   # project footprints

IN, OUT = sys.argv[1], sys.argv[2]
b = kc.load(IN)
mm = kc.mm
R = kc.R_BOARD                            # 72.644 mm (5.72 in)
fps = kc.fp_by_ref(b)
graveyard = []

# load library footprints first (SWIG quirk: FootprintLoad after Remove misbehaves)
rod = [pcbnew.FootprintLoad(PRETTY, "MountingHole_10.3mm_3-8in_Rod") for _ in range(2)]
# TeleMetrum sled bolts: courtyard = the sled base (SSI AVBay1), one half per hole
scr = [pcbnew.FootprintLoad(PRETTY, "MountingHole_4.5mm_TeleMetrum_Sled_" + s) for s in "LR"]
m3 = [pcbnew.FootprintLoad(PRETTY, "MountingHole_3.2mm_M3_RoundStandoff_D5") for _ in range(2)]
# latching connectors (reviewer: positive retention for vibration): Molex Micro-Fit 3.0 for battery / arming lines,
# JST GH for the camera harness; M2 SMT standoffs (Wurth WA-SMSI, 5 mm) for the RunCam Split 4 on the back
MF = ("battery_pcb", "Molex_Micro-Fit_3.0_43650-0215_1x02_P3.00mm_Vertical")   # KiCad footprint + our 3D model (tools/step_boxes.py)
GH = ("Connector_JST", "JST_GH_BM05B-GHS-TBT_1x05-1MP_P1.25mm_Vertical")
XT30 = ("battery_pcb", "AMASS_XT30UPB-F_1x02_P5.0mm_Vertical")   # J5/J6 battery outputs (7 Oct 2026): XT30, female on the
                                                                  # source side; pin 1 = minus, pin 2 = plus (housing marking)
SMSI = ("battery_pcb", "Mounting_Wuerth_WA-SMSI-M2_H5mm_9774050243_NoHole")   # Wurth land pattern minus the centre hole
newfp = {r: pcbnew.FootprintLoad(PRETTY, MF[1]) for r in ("SW1", "SW2", "SW3")}
newfp.update({r: pcbnew.FootprintLoad(PRETTY, XT30[1]) for r in ("J5", "J6")})
newfp["J3"] = pcbnew.FootprintLoad(kc.FPLIB + "/%s.pretty" % GH[0], GH[1])
# battery holders: project copy of the Keystone 1042 footprint, courtyard 0.25 mm past the tab pads (sled clearance)
BH = ("battery_pcb", "BatteryHolder_Keystone_1042_1x18650")
for r in ("BT1", "BT2", "BT3", "BT4"):
    newfp[r] = pcbnew.FootprintLoad(PRETTY, BH[1])
cam = [pcbnew.FootprintLoad(PRETTY, SMSI[1]) for _ in range(4)]
camboard = pcbnew.FootprintLoad(PRETTY, "RunCam_Split4_OnStandoffs")
# bench test points (6 Oct 2026): plain 2 mm through-hole pads, probe-able from either side
TPFP = ("TestPoint", "TestPoint_THTPad_D2.0mm_Drill1.0mm")
tpfp = [pcbnew.FootprintLoad(kc.FPLIB + "/%s.pretty" % TPFP[0], TPFP[1]) for _ in range(4)]
# review 3 (8 Oct 2026): U1 EN divider (UVLO) and a third input cap
uvlo = {"R9": pcbnew.FootprintLoad(kc.FPLIB + "/Resistor_SMD.pretty", "R_0603_1608Metric"),
        "R10": pcbnew.FootprintLoad(kc.FPLIB + "/Resistor_SMD.pretty", "R_0603_1608Metric"),
        "C11": pcbnew.FootprintLoad(kc.FPLIB + "/Capacitor_SMD.pretty", "C_0805_2012Metric")}

# ---------------------------------------------------------------- clear copper, zones, outline, old holes, labels
for t in list(b.GetTracks()):
    graveyard.append(t); b.Remove(t)
for z in list(b.Zones()):
    graveyard.append(z); b.Remove(z)
for d in list(b.GetDrawings()):
    if d.GetLayer() == pcbnew.Edge_Cuts or (d.GetClass() == "PCB_TEXT" and d.GetLayer() == pcbnew.F_SilkS):
        graveyard.append(d); b.Remove(d)
for r in ("H45", "H135", "H225", "H315"):
    graveyard.append(fps[r]); b.Remove(fps[r])

# ---------------------------------------------------------------- outline: circle with three rectangular notches
# notch = (centre angle in KiCad coords [y down], width, depth at centre)
NOTCHES = [(33.0, 10.0, 6.0), (90.0, 40.0, 14.0), (130.0, 10.0, 6.0),
           (160.0, 12.0, 7.0),             # wire pass-through near the camera harness (reviewer)
           (210.0, 12.0, 7.0), (240.0, 12.0, 7.0),   # spare wire pass-throughs, upper left (review 2, 7 Oct 2026)
           (330.0, 12.0, 7.0)]             # spare wire pass-through, upper right
def pt(a_deg, r):
    a = math.radians(a_deg); return (r * math.cos(a), r * math.sin(a))
def seg(p, q):
    s = pcbnew.PCB_SHAPE(b); s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(kc.P(*p)); s.SetEnd(kc.P(*q)); s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(mm(0.1)); b.Add(s)
def arc(a0, a1):
    s = pcbnew.PCB_SHAPE(b); s.SetShape(pcbnew.SHAPE_T_ARC)
    s.SetArcGeometry(kc.P(*pt(a0, R)), kc.P(*pt((a0 + a1) / 2, R)), kc.P(*pt(a1, R)))
    s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(mm(0.1)); b.Add(s)
ends = []
for a, w, d in NOTCHES:
    u = (math.cos(math.radians(a)), math.sin(math.radians(a))); t = (-u[1], u[0])
    s_out = math.sqrt(R * R - (w / 2) ** 2); rin = R - d; da = math.degrees(math.atan2(w / 2, s_out))
    D = (s_out * u[0] - w / 2 * t[0], s_out * u[1] - w / 2 * t[1]); A = (s_out * u[0] + w / 2 * t[0], s_out * u[1] + w / 2 * t[1])
    C = (rin * u[0] - w / 2 * t[0], rin * u[1] - w / 2 * t[1]); B = (rin * u[0] + w / 2 * t[0], rin * u[1] + w / 2 * t[1])
    seg(D, C); seg(C, B); seg(B, A)
    ends.append((a - da, a + da))
for i in range(len(ends)):
    a_start = ends[i][1]; a_end = ends[(i + 1) % len(ends)][0] + (360 if i == len(ends) - 1 else 0)
    arc(a_start, a_end)

# ---------------------------------------------------------------- holes
def add_hole(fp, ref, val, x, y):
    b.Add(fp); fp.SetReference(ref); fp.SetValue(val)
    fp.SetPosition(kc.P(x, y))
    fp.SetAttributes(pcbnew.FP_BOARD_ONLY | pcbnew.FP_EXCLUDE_FROM_POS_FILES | pcbnew.FP_EXCLUDE_FROM_BOM)
    fp.Reference().SetVisible(False)
rod[0].SetFPID(pcbnew.LIB_ID("battery_pcb", "MountingHole_10.3mm_3-8in_Rod")); rod[1].SetFPID(pcbnew.LIB_ID("battery_pcb", "MountingHole_10.3mm_3-8in_Rod"))
add_hole(rod[0], "H1", "3/8 rod", -60.0, 0.0)
add_hole(rod[1], "H2", "3/8 rod", 60.0, 0.0)
for f, side in zip(scr, "LR"):
    f.SetFPID(pcbnew.LIB_ID("battery_pcb", "MountingHole_4.5mm_TeleMetrum_Sled_" + side))
add_hole(scr[0], "H3", "TeleMetrum sled M4", -8.7, kc.COTS_HOLE_Y)
add_hole(scr[1], "H4", "TeleMetrum sled M4", 8.7, kc.COTS_HOLE_Y)
# pin-switch stack (2 double pin switches, Onshape "Pin switch stack 1"), across the cells from the COTS mount.
# The carriers are used exactly as built and sit flat on the board (inner edge on BT2/BT3's 0.3 mm solder tabs),
# upside down, centred, pin faces 68.88 mm out; these are the two M3 bolts through both carriers
for f in m3:
    f.SetFPID(pcbnew.LIB_ID("battery_pcb", "MountingHole_3.2mm_M3_RoundStandoff_D5"))
add_hole(m3[0], "H5", "Pin switch stack M3", 18.5, -41.88)
add_hole(m3[1], "H6", "Pin switch stack M3", -18.5, -48.88)

# ---------------------------------------------------------------- front: batteries
# BT2-BT3 and BT3-BT4 gaps are 4.75 mm so the ESP32 socket pins (25.4 mm apart) come up between them
# BT3 / BT4 turned so + is at the top, next to the pin switches (+ -> SW2/SW3 -> J5/J6 at the bottom)
# (placed below, after the footprint swaps)

# front connectors placed by courtyard centre
def place_cc(ref, cx, cy, rot):
    f = fps[ref]; f.SetOrientationDegrees(rot); f.SetPosition(kc.P(0, 0))
    f.BuildCourtyardCaches()
    bb = f.GetCourtyard(pcbnew.F_CrtYd).BBox()
    ox = (kc.to_mm(bb.GetLeft()) + kc.to_mm(bb.GetRight())) / 2 - kc.CX
    oy = (kc.to_mm(bb.GetTop()) + kc.to_mm(bb.GetBottom())) / 2 - kc.CY
    f.SetPosition(kc.P(cx - ox, cy - oy))
def swap(ref, lib, name):
    """Replace a footprint by a library one, keeping reference, value, schematic link and pad nets."""
    old, new = fps[ref], newfp[ref]
    new.SetFPID(pcbnew.LIB_ID(lib, name))
    new.SetReference(old.GetReference()); new.SetValue(old.GetValue())
    new.SetPath(old.GetPath()); new.SetSheetname(old.GetSheetname()); new.SetSheetfile(old.GetSheetfile())
    nets = {p.GetNumber(): p.GetNet() for p in old.Pads()}
    for p in new.Pads():
        if p.GetNumber() in nets:
            p.SetNet(nets[p.GetNumber()])
    b.Add(new); graveyard.append(old); b.Remove(old); fps[ref] = new
for ref in ("SW1", "SW2", "SW3"):
    swap(ref, *MF)
for ref in ("J5", "J6"):
    swap(ref, *XT30)
# XT30: pin 1 = battery minus, pin 2 = switched plus (the seed board had them the other way round)
padnet0 = lambda ref, num: [p.GetNet() for p in fps[ref].Pads() if p.GetNumber() == num][0]
for j, cell, sw in (("J5", "BT3", "SW2"), ("J6", "BT4", "SW3")):
    nets = {"1": padnet0(cell, "2"), "2": padnet0(sw, "2")}
    for p in fps[j].Pads():
        p.SetNet(nets[p.GetNumber()])
swap("J3", *GH)
for ref in ("BT1", "BT2", "BT3", "BT4"):
    swap(ref, *BH)
for ref, x, rot in (("BT1", -36.5, 90), ("BT2", -14.3, 270), ("BT3", 11.1, 270), ("BT4", 36.5, 270)):
    fps[ref].SetOrientationDegrees(rot); fps[ref].SetPosition(kc.P(x, kc.BAT_DY))
place_cc("SW1", -29.0, 55.5, 0)        # CAM PWR switch landing, beside BT1 + / the fuse
place_cc("J5", 25.0, 50.0 + kc.COTS_DY, 0)   # COTS OUT (XT30): minus toward BT3-, plus toward the switched line
place_cc("J6", 40.0, 50.0 + kc.COTS_DY, 0)   # SRAD OUT (XT30), 15 mm over so the two housings' +/- marks don't touch
place_cc("SW2", 29.8, -50.0, 0)        # COTS ARM: pin-switch leads, right beside the pin-switch stack (clear of its footprint)
place_cc("SW3", 41.1, -50.0, 0)        # SRAD ARM
# camera harness on the back, just past the bottom end of the J2 column and beside the camera's wire-pad edge,
# so the UART and +5 V runs from the ESP32 / regulator are a few cm long
J3C = (-4.0, 18.5)                     # courtyard centre
f = fps["J3"]; f.SetOrientationDegrees(0); f.SetPosition(kc.P(*J3C))
f.Flip(kc.P(*J3C), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
f.BuildCourtyardCaches()
bb = f.GetCourtyard(pcbnew.B_CrtYd).BBox()
ox = (kc.to_mm(bb.GetLeft()) + kc.to_mm(bb.GetRight())) / 2 - kc.CX - J3C[0]
oy = (kc.to_mm(bb.GetTop()) + kc.to_mm(bb.GetBottom())) / 2 - kc.CY - J3C[1]
f.SetPosition(kc.P(J3C[0] - ox, J3C[1] - oy))
# RunCam Split 4 (29 x 29 mm, M2 holes on a 25.5 mm square) on four 5 mm SMT standoffs, under BT1/BT2,
# clear of the DevKitC, the holder pegs and the fuse; its wire pads face J3 (right, toward the ESP32)
CAM_C = (-35.5, -30.0)          # review 5 (8 Oct 2026): out toward the upper-left rim, clear of the ESP32/buck/J3 area
for k, (sx, sy) in enumerate(((-1, -1), (1, -1), (-1, 1), (1, 1))):
    x, y = CAM_C[0] + sx * 12.75, CAM_C[1] + sy * 12.75
    f = cam[k]; f.SetFPID(pcbnew.LIB_ID(*SMSI)); b.Add(f)
    f.SetReference("H%d" % (7 + k)); f.SetValue("Wurth 9774050243 M2x5 standoff (camera)")
    f.SetPosition(kc.P(x, y)); f.Reference().SetVisible(False)
    f.Flip(kc.P(x, y), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
# the camera board itself (placement / 3D model only) so it shows in the STEP and in Onshape
f = camboard; f.SetFPID(pcbnew.LIB_ID("battery_pcb", "RunCam_Split4_OnStandoffs")); b.Add(f)
f.SetReference("CAM1"); f.SetValue("RunCam Split 4 (on standoffs)"); f.SetPosition(kc.P(*CAM_C))
f.Reference().SetVisible(False); f.Flip(kc.P(*CAM_C), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)

# ---------------------------------------------------------------- back: ESP32 DevKitC sockets (component side of the devkit faces down)
# seen from the front the devkit is mirrored: J1 (3V3..5V) is the right column, J2 (GND..CLK) the left one.
# pin 1 (antenna end) at the top so the antenna sits past the end of the battery holders.
PIN1_Y = -40.2 + kc.ESP_DY
for ref, x in (("J1", 23.8), ("J2", -1.6)):
    f = fps[ref]
    if not f.IsFlipped():
        f.SetOrientationDegrees(0); f.SetPosition(kc.P(x, PIN1_Y))
        f.Flip(kc.P(x, PIN1_Y), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
    f.SetPosition(kc.P(x, PIN1_Y))

# ---------------------------------------------------------------- back: buck block moved as a unit, small parts beside their pins
DX, DY = -33.6, -22.0 + kc.ESP_DY
for ref in ("U1", "L1", "C1", "C2", "C3", "C4", "C5", "C6", "C7", "R2", "R3", "D1", "D3", "R4"):
    x, y = kc.rel(fps[ref].GetPosition()); fps[ref].SetPosition(kc.P(x + DX, y + DY))
x, y = kc.rel(fps["D3"].GetPosition()); fps["D3"].SetPosition(kc.P(x, y + 0.2))   # silk 0.15 mm clear of D1
def move_back(ref, x, y, rot):
    f = fps[ref]
    f.SetOrientationDegrees(rot if True else 0)
    f.SetPosition(kc.P(x, y))
# ESP32 5 V decoupling: same offset from J1-19 as before
J19 = (23.8, PIN1_Y + 18 * 2.54)
for ref, (ox, oy) in (("C10", (30.2 - 33.66, 16.28 - 16.28)), ("C9", (29.9 - 33.66, 18.6 - 16.28))):
    x, y = kc.rel(fps[ref].GetPosition()); fps[ref].SetPosition(kc.P(J19[0] + ox, J19[1] + oy))
# VBAT sense divider bottom + filter at J1-5 (same side relation as before: J1 column to the right)
J5p = (23.8, PIN1_Y + 4 * 2.54)
for ref, (ox, oy) in (("R5", (37.3 - 33.66, 0.0)), ("C8", (37.3 - 33.66, -17.3 + 19.28))):
    x, y = kc.rel(fps[ref].GetPosition()); fps[ref].SetPosition(kc.P(J5p[0] - ox, J5p[1] + oy))
for ref in ("R5", "C8"):
    fps[ref].SetOrientationDegrees(fps[ref].GetOrientationDegrees() + 180)
fps["R5"].SetValue("39k")   # was 47k: keeps VBAT_SENSE inside the ESP32 ADC range at a full 8.4 V pack
# status LED beside J2-15 (IO2), to the left of the J2 column
J15 = (-1.6, PIN1_Y + 14 * 2.54)
for ref, ox in (("R6", 62.6 - 59.06), ("D2", 66.2 - 59.06)):
    fps[ref].SetPosition(kc.P(J15[0] - ox, J15[1] - 3.04)); fps[ref].SetOrientationDegrees(fps[ref].GetOrientationDegrees() + 180)   # a bit up: clear of the camera standoff H8
# camera UART series resistors on the back, right next to the ESP32 pins (J2-11 TX2, J2-12 RX2)
for ref, y in (("R7", -14.8 + kc.ESP_DY), ("R8", -12.26 + kc.ESP_DY)):
    fps[ref].SetPosition(kc.P(-6.2, y)); fps[ref].SetOrientationDegrees(180)
fps["R8"].SetValue("1k")   # review 4: camera TX -> ESP32 RX; protects GPIO16 if the camera's UART is 5 V
# your assembly notes on Cmts.User: COTS board note moves next to the new mount
for d in b.GetDrawings():
    if d.GetClass() == "PCB_TEXT" and d.GetLayer() == pcbnew.Cmts_User and d.GetText().startswith("COTS altimeter"):
        d.SetPosition(kc.P(0.0, 56.5))
# fuse behind BT1 + (same offset as before)
fps["F1"].SetPosition(kc.P(-47.4 + 11.91, 32.6 + kc.BAT_DY))

# bench test points, in spots that are open on BOTH sides (no cell, holder, DevKit or camera over them):
# TP1 +5V just past J1-19 and TP3 GND below it, in the 4.6 mm gap between the BT3 and BT4 holders;
# TP2 VBAT+ (2S pack, before the fuse) just past BT1's + tab and TP4 GND beside it. Symbols: tools/add_testpoints.py
POWER_SHEET, BUCK_SHEET = "/ae01c8e7-4191-4202-a535-afc32959794b", "/1914f4ed-278a-4026-a86a-769e5e361ab6"
padnet = lambda ref, num: [p.GetNet() for p in fps[ref].Pads() if p.GetNumber() == num][0]
bx, by = kc.rel(fps["BT1"].GetPosition())
for f, (ref, val, sheet, suid, sname, sfile, (x, y), net) in zip(tpfp, (
        ("TP1", "TP_5V", BUCK_SHEET, "b1000000-0000-4000-8000-000000000001", "2. Buck to 5 V", "sheets/buck_5v.kicad_sch",
         (23.8, J19[1] + 5.4), padnet("J1", "19")),
        ("TP3", "TP_GND", POWER_SHEET, "b1000000-0000-4000-8000-000000000003", "1. Battery 2S + protection",
         "sheets/power_in.kicad_sch", (23.8, J19[1] + 9.9), padnet("J2", "1")),
        ("TP2", "TP_VBAT", POWER_SHEET, "b1000000-0000-4000-8000-000000000002", "1. Battery 2S + protection",
         "sheets/power_in.kicad_sch", (bx, by + 47.25), padnet("BT1", "1")),
        ("TP4", "TP_GND", POWER_SHEET, "b1000000-0000-4000-8000-000000000004", "1. Battery 2S + protection",
         "sheets/power_in.kicad_sch", (bx - 4.0, by + 47.25), padnet("J2", "1")))):
    f.SetFPID(pcbnew.LIB_ID(*TPFP)); b.Add(f)
    f.SetReference(ref); f.SetValue(val)
    f.SetPath(pcbnew.KIID_PATH(sheet + "/" + suid)); f.SetSheetname(sname); f.SetSheetfile(sfile)
    f.SetPosition(kc.P(x, y)); f.Reference().SetVisible(False); f.Value().SetVisible(False)
    f.SetField("Description", "Bench test point")
    for p in f.Pads():
        p.SetNet(net)

# ---------------------------------------------------------------- review 3: buck input caps and EN (UVLO) divider
# C1/C2 now sit on the buck sheet (next to U1 in the schematic); C1 is the 100 nF high-frequency cap closest to U1.
# U1 EN no longer ties to VIN: R9 (VIN -> EN) / R10 (EN -> GND) set the turn-on / turn-off points.
for ref in ("C1", "C2"):
    f = fps[ref]; f.SetPath(pcbnew.KIID_PATH(BUCK_SHEET + "/" + f.GetPath().AsString().split("/")[-1]))
    f.SetSheetname("2. Buck to 5 V"); f.SetSheetfile("sheets/buck_5v.kicad_sch")
fps["C1"].SetValue("100n / 50V"); fps["L1"].SetValue("6u8 / 3.6A"); fps["D3"].SetValue("B340B")
VIN, GND = padnet("U1", "3"), padnet("U1", "1")
EN = pcbnew.NETINFO_ITEM(b, "/2. Buck to 5 V/EN"); b.Add(EN)
[p for p in fps["U1"].Pads() if p.GetNumber() == "5"][0].SetNet(EN)
for ref, val, suid, (x, y), nets in (
        ("R9", "402k 1%", "b2000000-0000-4000-8000-000000000009", (17.2, -15.6), {"1": VIN, "2": EN}),
        ("R10", "100k 1%", "b2000000-0000-4000-8000-000000000010", (14.0, -15.6), {"1": EN, "2": GND}),
        ("C11", "10u / 25V", "b2000000-0000-4000-8000-000000000011", (5.0, -8.15), {"1": VIN, "2": GND})):
    f = uvlo[ref]; b.Add(f)
    f.SetFPID(pcbnew.LIB_ID("Capacitor_SMD", "C_0805_2012Metric") if ref == "C11" else pcbnew.LIB_ID("Resistor_SMD", "R_0603_1608Metric"))
    f.SetReference(ref); f.SetValue(val)
    f.SetPath(pcbnew.KIID_PATH(BUCK_SHEET + "/" + suid)); f.SetSheetname("2. Buck to 5 V"); f.SetSheetfile("sheets/buck_5v.kicad_sch")
    f.SetPosition(kc.P(x, y)); f.Flip(kc.P(x, y), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)     # back side, with the buck
    for p in f.Pads():
        p.SetNet(nets[p.GetNumber()])
    fps[ref] = f

pcbnew.SaveBoard(OUT, b, True)
print("placed")
