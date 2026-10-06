"""Layout A, stage 2: copper. Zones, keepouts (rods, COTS screws, ESP32 antenna), tracks, vias, GND stitching.
usage: route_A.py IN.kicad_pcb OUT.kicad_pcb      (board-relative mm, +y down, front view)"""
import sys, math, pcbnew, kc

IN, OUT = sys.argv[1], sys.argv[2]
b = kc.load(IN)
b.GetDesignSettings().m_NetSettings.RecomputeEffectiveNetclasses()
b.SynchronizeNetsAndNetClasses(False)
mm = kc.mm
F, B = pcbnew.F_Cu, pcbnew.B_Cu
allnets = sorted({p.GetNetname() for f in b.GetFootprints() for p in f.Pads() if p.GetNetname()})
def NET(short):
    n = b.FindNet(short)
    if n:
        return n
    hits = [nm for nm in allnets if nm.endswith("/" + short)]
    if len(hits) != 1:
        raise SystemExit("net %r ambiguous or missing: %r" % (short, hits))
    return b.FindNet(hits[0])
for t in list(b.GetTracks()):
    b.Remove(t)
for z in list(b.Zones()):
    b.Remove(z)

def track(net, layer, w, pts):
    n = NET(net)
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(b)
        t.SetStart(kc.P(x0, y0)); t.SetEnd(kc.P(x1, y1)); t.SetWidth(mm(w)); t.SetLayer(layer); t.SetNet(n)
        b.Add(t)
def via(net, x, y, d=0.6, drill=0.3):
    v = pcbnew.PCB_VIA(b); v.SetPosition(kc.P(x, y)); v.SetLayerPair(F, B)
    v.SetWidth(mm(d)); v.SetDrill(mm(drill)); v.SetNet(NET(net)); b.Add(v)
def zone(net, layers, pts, prio=0, name="", clearance=0.3, keepout=False, no_copper=False):
    z = pcbnew.ZONE(b); ls = pcbnew.LSET()
    for L in layers:
        ls.AddLayer(L)
    z.SetLayerSet(ls)
    if keepout:
        z.SetIsRuleArea(True); z.SetDoNotAllowZoneFills(True)
        z.SetDoNotAllowTracks(no_copper); z.SetDoNotAllowVias(no_copper)
        z.SetDoNotAllowPads(False); z.SetDoNotAllowFootprints(False)
    else:
        z.SetNet(NET(net)); z.SetAssignedPriority(prio)
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THT_THERMAL)
        z.SetLocalClearance(mm(clearance)); z.SetMinThickness(mm(0.25))
        z.SetThermalReliefGap(mm(0.4)); z.SetThermalReliefSpokeWidth(mm(0.5))
    if name:
        z.SetZoneName(name)
    ol = z.Outline(); ol.NewOutline()
    for x, y in pts:
        ol.Append(mm(kc.CX + x), mm(kc.CY + y))
    b.Add(z)
def circle(r, cx=0.0, cy=0.0, n=120):
    return [(round(cx + r * math.cos(2 * math.pi * i / n), 3), round(cy + r * math.sin(2 * math.pi * i / n), 3)) for i in range(n)]
def rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
DX, DY = -33.6, -22.0 + kc.ESP_DY          # buck block moved as a unit from its old spot
BD, ED = kc.BAT_DY, kc.ESP_DY               # battery-holder and ESP32-block offsets (kc.py)
def T(pts):
    return [(round(x + DX, 3), round(y + DY, 3)) for x, y in pts]

# ---------------------------------------------------------------- zones and keepouts
zone("GND", [F], circle(kc.R_BOARD - 0.5), 0, "GND_front")
zone("GND", [B], circle(kc.R_BOARD - 0.5), 0, "GND_back")
for x in (-60.0, 60.0):           # 3/8 rods: SAE washer + nut on both faces, no copper under them
    zone(None, [F, B], circle(10.6, x, 0.0, 72), name="rod washer keepout", keepout=True, no_copper=True)
for x in (-8.7, 8.7):             # COTS-mount M4 screws: head / washer / nut
    zone(None, [F, B], circle(4.8, x, kc.COTS_HOLE_Y, 48), name="COTS screw keepout", keepout=True, no_copper=True)
# ESP32 antenna end (the DevKitC hangs under the board, antenna toward the top)
zone(None, [F, B], rect(-2.9, -45.0 + ED, 25.1, -37.5 + ED), name="ESP32 antenna: no pour", keepout=True)
zone("VIN", [B], T([(35.9, 5.45), (37.35, 5.45), (37.35, 6.3), (43.15, 6.3), (43.15, 8.25), (41.45, 8.25),
                    (41.45, 20.4), (36.9, 20.4), (36.9, 13.9), (39.75, 13.9), (39.75, 9.6), (35.9, 9.6)]), 2, "VIN", clearance=0.25)
zone("+5V", [B], T([(41.75, 12.45), (47.35, 12.45), (47.35, 13.35), (54.1, 13.35), (54.1, 16.6), (41.75, 16.6)]), 2, "+5V", clearance=0.25)
zone("VBAT+", [F], rect(-39.69, 34.3 + BD, -35.29, 37.2 + BD), 2, "VBAT+ front", clearance=0.3)
zone("VBAT+", [B], rect(-39.69, 30.5 + BD, -36.39, 35.8 + BD), 2, "VBAT+ back", clearance=0.3)

# ---------------------------------------------------------------- 2S pack, fuse, switch, input
for x in (-39.09, -37.89, -36.69):
    via("VBAT+", x, 35.0 + BD, 0.8, 0.4)
track("Net-(BT1--)", F, 3.0, [(-36.5, -39.69 + BD), (-14.3, -39.69 + BD)])              # series link BT1- -> BT2+
for x in (-16.09, -14.29, -12.49):                                            # pack ground into the back pour
    via("GND", x, 34.6 + BD, 0.8, 0.4)
track("VF", B, 1.5, [(-33.35, 32.6 + BD), (-33.35, 48.0), (-30.5, 50.85), (-30.5, 55.085)])   # fuse -> CAM PWR switch (Micro-Fit)
track("VSW", B, 1.5, [(-27.5, 55.085), (-27.5, 51.5), (-4.0, 34.5), (3.6, 26.9), (3.6, 13.0),
                      (4.7, 11.9), (4.7, 1.15 + ED)])   # switch -> reverse diode D3: one diagonal, right of the camera harness J3
track("VIN", B, 1.5, T([(38.3, 18.85), (38.3, 15.65)]))                       # D3 -> TVS D1

# ---------------------------------------------------------------- buck (LMR51430, datasheet fig 9-10), moved as a block
track("VIN", B, 0.6, T([(43.55, 7.137), (42.6, 7.0)]))
track("SW", B, 0.6, T([(44.5, 7.137), (44.5, 8.4)]))
track("SW", B, 1.2, T([(44.5, 8.4), (44.5, 9.675)]))
track("GND", B, 0.5, T([(45.45, 7.137), (45.45, 6.0), (42.9, 6.0), (41.9, 5.2), (41.2, 5.05)]))
track("GND", B, 0.8, T([(41.2, 5.05), (38.95, 5.05)]))
track("GND", B, 0.6, T([(45.45, 7.137), (46.2, 7.6), (47.7, 7.9)]))
track("CBOOT", B, 0.4, T([(45.45, 4.863), (45.45, 4.4), (46.925, 3.0)]))
track("SW", B, 0.4, T([(48.475, 3.0), (49.4, 3.0)]))
via("SW", *T([(49.4, 3.0)])[0]); via("SW", *T([(44.5, 8.15)])[0])
track("SW", F, 0.4, T([(44.5, 8.15), (49.4, 3.0)]))
track("VIN", B, 0.3, T([(44.5, 4.863), (44.5, 3.45)]))
via("VIN", *T([(44.5, 3.45)])[0]); via("VIN", *T([(42.2, 7.9)])[0])
track("VIN", F, 0.3, T([(44.5, 3.45), (42.2, 7.9)]))
track("FB", B, 0.25, T([(43.55, 4.863), (43.55, 3.3), (43.3, 2.425)]))
track("FB", B, 0.25, T([(41.775, 2.8), (43.3, 2.8)]))
track("FB", B, 0.25, T([(45.1, 2.375), (43.3, 2.425)]))
track("+5V", B, 0.3, T([(53.05, 13.975), (55.0, 13.975), (55.0, 0.0), (43.3, 0.0), (43.3, 0.775)]))   # VOUT sense
track("+5V", B, 0.3, T([(45.1, 0.0), (45.1, 0.825)]))
track("GND", B, 0.4, T([(40.125, 2.8), (40.1, 3.95), (40.075, 5.05)]))
for x, y in T([(40.075, 5.05), (40.1, 3.95), (37.55, 4.3), (47.7, 7.9), (49.2, 10.2), (51.1, 10.2), (53.0, 10.2)]):
    via("GND", x, y)
track("GND", B, 0.8, T([(38.3, 11.35), (36.6, 11.35)]))
for x, y in T([(36.6, 10.8), (36.6, 12.0)]):
    via("GND", x, y, 0.8, 0.4)

# ---------------------------------------------------------------- +5V out: ESP32 (J1-19, back) and camera (J3-1, back)
track("+5V", B, 1.0, [(18.0, -5.8 + ED), (18.0, 3.6 + ED), (21.11, 3.6 + ED), (21.11, 5.52 + ED)])
track("+5V", B, 0.8, [(23.8, 5.52 + ED), (21.11, 5.52 + ED), (20.99, 7.84 + ED)])           # J1-19 + decoupling C10, C9
track("GND", B, 0.6, [(19.57, 5.52 + ED), (18.345, 5.52 + ED)]); via("GND", 18.345, 5.52 + ED)
track("GND", B, 0.6, [(19.09, 7.84 + ED), (19.09, 9.3 + ED)]); via("GND", 19.09, 9.3 + ED)       # clear of the front +5V run
via("+5V", 16.6, -6.0 + ED, 0.8, 0.4); via("+5V", 17.8, -6.0 + ED, 0.8, 0.4)
track("+5V", F, 1.0, [(17.2, -6.0 + ED), (17.2, 12.6), (-1.5, 12.6), (-1.5, 13.4)])   # front, under BT3, past the end of the J2 column
via("+5V", -1.5, 13.4, 0.8, 0.4)
track("+5V", B, 0.8, [(-1.5, 13.4), (-1.5, 20.45)])                         # J3-1 (camera harness, back)

# ---------------------------------------------------------------- ESP32 signals (all on the back)
track("VBAT_SENSE", B, 0.3, [(x, y + ED) for x, y in [(2.9, -17.62), (2.9, -24.5), (16.5, -24.5), (20.93, -28.06), (20.98, -30.04), (23.8, -30.04)]])
track("GND", B, 0.4, [(19.34, -30.04 + ED), (18.2, -29.05 + ED), (19.39, -28.06 + ED)]); via("GND", 18.2, -29.05 + ED)
track("ESP_TX2", B, 0.3, [(-1.6, -14.8 + ED), (-5.375, -14.8 + ED)])                 # series R7 / R8 right at the ESP32 pins
track("ESP_RX2", B, 0.3, [(-1.6, -12.26 + ED), (-5.375, -12.26 + ED)])
# camera UART: R7/R8 -> straight down on the front (the back is busy with the LED and the camera standoffs) -> J3-3/4
track("CAM_RX", B, 0.3, [(-7.025, -14.8 + ED), (-8.0, -14.8 + ED)]); via("CAM_RX", -8.0, -14.8 + ED)
track("CAM_RX", F, 0.3, [(-8.0, -14.8 + ED), (-8.0, 21.7), (-7.0, 22.7), (-4.0, 22.7)]); via("CAM_RX", -4.0, 22.7)
track("CAM_RX", B, 0.3, [(-4.0, 22.7), (-4.0, 20.45)])
track("CAM_TX", B, 0.3, [(-7.025, -12.26 + ED), (-8.8, -12.26 + ED)]); via("CAM_TX", -8.8, -12.26 + ED)
track("CAM_TX", F, 0.3, [(-8.8, -12.26 + ED), (-8.8, 22.9), (-7.99, 23.71), (-5.25, 23.71)]); via("CAM_TX", -5.25, 23.71)
track("CAM_TX", B, 0.3, [(-5.25, 23.71), (-5.25, 20.45)])
LY = -4.64 + ED - 3.04                       # R6 / D2 row (just above the camera standoff H8)
track("LED_GPIO", B, 0.3, [(-1.6, -4.64 + ED), (-3.0, -4.64 + ED), (-3.6, -5.24 + ED), (-3.6, LY), (-4.32, LY)])
track("LED_A", B, 0.3, [(-5.96, LY), (-7.80, LY)])
track("GND", B, 0.4, [(-9.68, LY), (-11.2, LY)]); via("GND", -11.2, LY)
track("GND", B, 0.4, [(-1.6, -40.2 + ED), (-4.0, -40.2 + ED)])                         # J2-1 sits in the antenna no-pour area

# ---------------------------------------------------------------- COTS / SRAD supplies (isolated, pyro clearance)
# BT3/BT4 + is at the top: + -> SW2/SW3 (pin-switch leads, beside the stack) -> switched line down the back -> J5/J6-1
track("COTS_BAT+", F, 1.0, [(11.1, -39.69 + BD), (11.1, -40.0), (16.8, -45.7), (23.6, -45.7), (28.3, -50.4), (28.3, -50.415)])   # BT3+ -> SW2-1 (below H5)
CD = kc.COTS_DY                            # J5 / J6 moved out with the COTS mount
JY = 50.415 + CD                           # J5 / J6 pin row (turned 180: pin 1 = switched +, on the side the switched line comes from)
track("COTS_SW", B, 1.0, [(31.3, -50.415), (31.3, -45.0), (31.5, -44.8), (31.5, JY - 5.0), (26.5, JY)])  # SW2-2 -> J5-1
track("COTS_BAT-", F, 1.0, [(11.1, 39.69 + BD), (11.1, 45.5), (16.0, 50.4), (23.5, 50.4), (23.5, JY)])  # BT3- -> J5-2
track("SRAD_BAT+", F, 1.0, [(36.5, -39.69 + BD), (36.5, -44.6), (39.6, -47.7), (39.6, -50.415)])           # BT4+ -> SW3-1
j6 = {p.GetNumber(): kc.rel(p.GetPosition()) for p in kc.fp_by_ref(b)["J6"].Pads()}   # J6 is a JST XH (2.5 mm pitch)
(J6X1, J6Y), J6X2 = j6["1"], j6["2"][0]
track("SRAD_SW", B, 1.0, [(42.6, -50.415), (42.6, -45.0), (38.0, -40.4), (38.0, J6Y - 4.0), (J6X1, J6Y - 2.0), (J6X1, J6Y)])  # SW3-2 -> J6-1
track("SRAD_BAT-", F, 1.0, [(36.5, 39.69 + BD), (36.5, 46.5), (J6X2, 46.5 + J6X2 - 36.5), (J6X2, J6Y)])               # BT4- -> J6-2

# ---------------------------------------------------------------- fill, then stitch GND on a grid
filler = pcbnew.ZONE_FILLER(b)
filler.Fill(b.Zones())
gF = [z for z in b.Zones() if not z.GetIsRuleArea() and z.GetNetname() == "GND" and z.IsOnLayer(F)][0]
gB = [z for z in b.Zones() if not z.GetIsRuleArea() and z.GetNetname() == "GND" and z.IsOnLayer(B)][0]
existing = [kc.rel(t.GetPosition()) for t in b.GetTracks() if t.GetClass() == "PCB_VIA"]
added = 0; STEP = 10.0; k = int(74 / STEP)
for i in range(-k, k + 1):
    for j in range(-k, k + 1):
        x, y = i * STEP + (STEP / 2 if j % 2 else 0), j * STEP
        if math.hypot(x, y) > kc.R_BOARD - 3.4:
            continue
        ok = all(z.HitTestFilledArea(L, kc.P(x + dx, y + dy), mm(0.0))
                 for dx, dy in ((0, 0), (0.75, 0), (-0.75, 0), (0, 0.75), (0, -0.75), (0.55, 0.55), (-0.55, 0.55), (0.55, -0.55), (-0.55, -0.55))
                 for z, L in ((gF, F), (gB, B)))
        if not ok or any(math.hypot(x - ex, y - ey) < 2.0 for ex, ey in existing):
            continue
        via("GND", x, y); existing.append((x, y)); added += 1
filler.Fill(b.Zones())
pcbnew.SaveBoard(OUT, b, True)
print("tracks %d  vias %d (stitching %d)  zones %d" % (
    sum(1 for t in b.GetTracks() if t.GetClass() != "PCB_VIA"),
    sum(1 for t in b.GetTracks() if t.GetClass() == "PCB_VIA"), added, len(list(b.Zones()))))
