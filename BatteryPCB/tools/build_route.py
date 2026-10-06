"""Stage 2: copper. Zones, antenna keepout, hand-planned tracks and vias, GND stitching.

usage: build_route.py IN.kicad_pcb OUT.kicad_pcb
All coordinates are board-relative mm (board centre = 0,0; +y is down, front view).
"""
import sys, math, pcbnew, kc

IN, OUT = sys.argv[1], sys.argv[2]
b = kc.load(IN)
# resolve the project's net class patterns so zone fills honour Pyro 0.4 mm etc.
b.GetDesignSettings().m_NetSettings.RecomputeEffectiveNetclasses()
b.SynchronizeNetsAndNetClasses(False)
mm = kc.mm
F, B = pcbnew.F_Cu, pcbnew.B_Cu

names = [n for n in b.GetNetsByName().keys()] if hasattr(b, "GetNetsByName") else []
def NET(short):
    """net by exact name or by unique '/short' suffix"""
    n = b.FindNet(short)
    if n:
        return n
    hits = [nm for nm in allnets if nm.endswith("/" + short)]
    if len(hits) != 1:
        raise SystemExit("net %r ambiguous or missing: %r" % (short, hits))
    return b.FindNet(hits[0])
allnets = sorted({p.GetNetname() for f in b.GetFootprints() for p in f.Pads() if p.GetNetname()})

for t in list(b.GetTracks()):
    b.Remove(t)
for z in list(b.Zones()):
    b.Remove(z)

# ---------------------------------------------------------------- primitives
def track(net, layer, w, pts):
    n = NET(net)
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(b)
        t.SetStart(kc.P(x0, y0)); t.SetEnd(kc.P(x1, y1))
        t.SetWidth(mm(w)); t.SetLayer(layer); t.SetNet(n)
        b.Add(t)

def via(net, x, y, d=0.6, drill=0.3):
    v = pcbnew.PCB_VIA(b)
    v.SetPosition(kc.P(x, y))
    v.SetLayerPair(F, B)
    v.SetWidth(mm(d)); v.SetDrill(mm(drill))
    v.SetNet(NET(net))
    b.Add(v)
    return v

def zone(net, layers, pts, prio=0, name="", solid_smd=True, clearance=0.3, keepout=False, no_copper=False):
    z = pcbnew.ZONE(b)
    ls = pcbnew.LSET()
    for L in layers:
        ls.AddLayer(L)
    z.SetLayerSet(ls)
    if keepout:
        z.SetIsRuleArea(True)
        z.SetDoNotAllowZoneFills(True)
        z.SetDoNotAllowTracks(no_copper); z.SetDoNotAllowVias(no_copper)
        z.SetDoNotAllowPads(False); z.SetDoNotAllowFootprints(False)
    else:
        z.SetNet(NET(net))
        z.SetAssignedPriority(prio)
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THT_THERMAL if solid_smd else pcbnew.ZONE_CONNECTION_THERMAL)
        z.SetLocalClearance(mm(clearance))
        z.SetMinThickness(mm(0.25))
        z.SetThermalReliefGap(mm(0.4))
        z.SetThermalReliefSpokeWidth(mm(0.5))
    if name:
        z.SetZoneName(name)
    ol = z.Outline()
    ol.NewOutline()
    for x, y in pts:
        ol.Append(mm(kc.CX + x), mm(kc.CY + y))
    b.Add(z)
    return z

def circle(r, n=120):
    return [(round(r * math.cos(2 * math.pi * i / n), 3), round(r * math.sin(2 * math.pi * i / n), 3)) for i in range(n)]

def rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]

# ---------------------------------------------------------------- zones
zone("GND", [F], circle(73.0), 0, "GND_front")
zone("GND", [B], circle(73.0), 0, "GND_back")
zone(None, [F, B], rect(37.4, -36.2, 55.4, -30.8), name="ESP32 antenna: no pour", keepout=True)
# buck: VIN copper (CIN, R4, TVS, reverse diode) and +5V copper (L1 out, COUT) on the back
zone("VIN", [B], [(35.9, 5.45), (37.35, 5.45), (37.35, 6.3), (43.15, 6.3), (43.15, 8.25), (41.45, 8.25),
                  (41.45, 20.4), (36.9, 20.4), (36.9, 13.9), (39.75, 13.9), (39.75, 9.6), (35.9, 9.6)],
     2, "VIN", clearance=0.25)
zone("+5V", [B], [(41.75, 12.45), (47.35, 12.45), (47.35, 13.35), (54.1, 13.35), (54.1, 16.6), (41.75, 16.6)],
     2, "+5V", clearance=0.25)
# battery + to fuse: pad-side copper on the front, fuse-side copper on the back
zone("VBAT+", [F], rect(-51.6, 34.3, -47.2, 37.2), 2, "VBAT+ front", clearance=0.3)
zone("VBAT+", [B], rect(-51.6, 30.5, -48.3, 35.8), 2, "VBAT+ back", clearance=0.3)

# ---------------------------------------------------------------- 2S power path
for x in (-51.0, -49.8, -48.6):
    via("VBAT+", x, 35.0, 0.8, 0.4)
track("VF", B, 1.5, [(-45.263, 32.6), (-44.3, 33.0), (43.4, 33.0), (43.4, 28.96), (41.15, 28.96)])
track("VSW", B, 1.5, [(41.15, 30.96), (38.3, 30.96), (38.3, 23.15)])
track("VIN", B, 1.5, [(38.3, 18.85), (38.3, 15.65)])
# series link BT1- -> BT2+: both terminals at the top now (BT2 is turned end-for-end)
track("Net-(BT1--)", F, 3.0, [(-48.41, -39.69), (-26.21, -39.69)])
# BT2- (pack ground, now at the bottom) into the back GND pour right beside it
for x in (-28.0, -26.2, -24.4):
    via("GND", x, 34.6, 0.8, 0.4)

# ---------------------------------------------------------------- buck (LMR51430, fig 9-10)
track("VIN", B, 0.6, [(43.55, 7.137), (42.6, 7.0)])                     # VIN pin into CIN copper
track("SW", B, 0.6, [(44.5, 7.137), (44.5, 8.4)])                       # SW pin straight down to L1
track("SW", B, 1.2, [(44.5, 8.4), (44.5, 9.675)])
track("GND", B, 0.5, [(45.45, 7.137), (45.45, 6.0), (42.9, 6.0), (41.9, 5.2), (41.2, 5.05)])  # under-IC GND strip to CIN
track("GND", B, 0.8, [(41.2, 5.05), (38.95, 5.05)])
track("GND", B, 0.6, [(45.45, 7.137), (46.2, 7.6), (47.7, 7.9)])        # GND pin to COUT ground band
track("CBOOT", B, 0.4, [(45.45, 4.863), (45.45, 4.4), (46.925, 3.0)])
track("SW", B, 0.4, [(48.475, 3.0), (49.4, 3.0)])
via("SW", 49.4, 3.0)
via("SW", 44.5, 8.15)
track("SW", F, 0.4, [(44.5, 8.15), (49.4, 3.0)])                        # boot cap to SW, under the plane side
track("VIN", B, 0.3, [(44.5, 4.863), (44.5, 3.45)])                     # EN tied to VIN
via("VIN", 44.5, 3.45)
via("VIN", 42.2, 7.9)
track("VIN", F, 0.3, [(44.5, 3.45), (42.2, 7.9)])
track("FB", B, 0.25, [(43.55, 4.863), (43.55, 3.3), (43.3, 2.425)])
track("FB", B, 0.25, [(41.775, 2.8), (43.3, 2.8)])
track("FB", B, 0.25, [(45.1, 2.375), (43.3, 2.425)])
track("+5V", B, 0.3, [(53.05, 13.975), (55.0, 13.975), (55.0, 0.0), (43.3, 0.0), (43.3, 0.775)])  # VOUT sense
track("+5V", B, 0.3, [(45.1, 0.0), (45.1, 0.825)])
track("+5V", B, 1.2, [(50.66, 16.3), (50.66, 25.96)])                   # to camera J3.1
via("+5V", 42.4, 16.0, 0.8, 0.4); via("+5V", 43.6, 16.0, 0.8, 0.4)   # +5V pour -> front
track("+5V", F, 1.0, [(43.6, 16.0), (33.66, 16.0)])                    # straight to ESP32 5V pin (J1.19)
track("+5V", B, 0.8, [(33.66, 16.28), (30.975, 16.28), (30.85, 18.6)])  # ESP32 decoupling
track("GND", B, 0.4, [(40.125, 2.8), (40.1, 3.95), (40.075, 5.05)])
for x, y in ((40.075, 5.05), (40.1, 3.95), (37.55, 4.3)):
    via("GND", x, y)
for x, y in ((47.7, 7.9), (49.2, 10.2), (51.1, 10.2), (53.0, 10.2)):
    via("GND", x, y)
track("GND", B, 0.8, [(38.3, 11.35), (36.6, 11.35)])
via("GND", 36.6, 10.8, 0.8, 0.4); via("GND", 36.6, 12.0, 0.8, 0.4)
track("GND", B, 0.6, [(29.425, 16.28), (28.2, 16.28)]); via("GND", 28.2, 16.28)
track("GND", B, 0.6, [(28.95, 18.6), (27.7, 18.6)]); via("GND", 27.7, 18.6)

# ---------------------------------------------------------------- signals
track("VBAT_SENSE", B, 0.3, [(36.5, 4.375), (36.5, -16.5), (36.525, -17.3), (36.475, -19.28), (33.66, -19.28)])
track("GND", B, 0.4, [(38.125, -19.28), (39.3, -18.3), (38.075, -17.3)]); via("GND", 39.3, -18.3)
track("ESP_TX2", B, 0.3, [(59.06, -4.04), (56.2, -4.04), (56.2, 29.96), (55.025, 29.96)])
track("ESP_RX2", B, 0.3, [(59.06, -1.50), (57.0, -1.50), (57.0, 31.96), (55.025, 31.96)])
track("CAM_RX", B, 0.3, [(53.375, 29.96), (50.66, 29.96)])
track("CAM_TX", B, 0.3, [(53.375, 31.96), (50.66, 31.96)])
track("LED_GPIO", B, 0.3, [(59.06, 6.12), (61.775, 6.12)])
track("LED_A", B, 0.3, [(63.425, 6.12), (65.262, 6.12)])
track("GND", B, 0.4, [(67.138, 6.12), (68.6, 6.12)]); via("GND", 68.6, 6.12)

# ---------------------------------------------------------------- COTS / SRAD supplies (pyro current)
track("COTS_BAT+", F, 1.5, [(-4.01, 39.69), (-4.0, 25.0)])
track("COTS_BAT+", F, 1.0, [(-5.2, 25.0), (-2.8, 25.0)])
for x in (-5.2, -4.0, -2.8):
    via("COTS_BAT+", x, 25.0, 0.8, 0.4)
track("COTS_BAT+", B, 1.0, [(-5.2, 25.0), (-2.8, 25.0)])
# COTS+: under BT3, then one 45 deg run above J1 straight into SW2 pin 1 (back)
track("COTS_BAT+", B, 1.5, [(-4.0, 25.0), (-4.0, 4.5), (40.02, -39.52)])   # clears J1 pin 1 by 0.68 mm
track("COTS_BAT+", B, 1.0, [(40.02, -39.52), (43.05, -39.52)])
# COTS switched +: front, up between the switch and J5, across between J5 and J6, into J5.1
track("COTS_SW", F, 1.0, [(43.05, -37.52), (39.4, -37.52), (39.4, -49.65), (33.6, -49.65), (33.6, -46.4)])
# COTS-: front, under BT4's top pad, straight up into J5.2
track("COTS_BAT-", F, 1.2, [(-4.01, -39.69), (-1.6, -37.0), (0.4, -34.75), (35.6, -34.75), (35.6, -45.0)])
track("COTS_BAT-", F, 1.0, [(35.6, -45.0), (35.6, -46.4)])
# SRAD+: front, up beside BT4, above J1, into SW3 pin 1 through the gap between the switches
track("SRAD_BAT+", F, 1.2, [(18.19, 39.69), (20.9, 37.0), (22.8, 35.1), (22.8, -32.8), (46.85, -32.8)])
track("SRAD_BAT+", F, 1.0, [(46.85, -32.8), (46.85, -39.44), (50.65, -39.44)])
# SRAD switched +: back, 45 deg between J5 and J6 into J6.1
track("SRAD_SW", B, 1.0, [(50.65, -37.44), (48.7, -37.44), (48.7, -41.3), (41.3, -48.7), (33.55, -48.7), (33.55, -52.91)])
# SRAD-: front, 45 deg from BT4's top pad over J6 into J6.2
track("SRAD_BAT-", F, 1.2, [(18.19, -39.69), (18.19, -44.5), (29.2, -55.5), (35.55, -55.5)])
track("SRAD_BAT-", F, 1.0, [(35.55, -55.5), (35.55, -52.91)])

# ---------------------------------------------------------------- fill, then stitch GND
filler = pcbnew.ZONE_FILLER(b)
filler.Fill(b.Zones())
gF = [z for z in b.Zones() if not z.GetIsRuleArea() and z.GetNetname() == "GND" and z.IsOnLayer(F)][0]
gB = [z for z in b.Zones() if not z.GetIsRuleArea() and z.GetNetname() == "GND" and z.IsOnLayer(B)][0]
existing = [kc.rel(t.GetPosition()) for t in b.GetTracks() if t.GetClass() == "PCB_VIA"]
added = 0
STEP = 10.0
k = int(73 / STEP)
for i in range(-k, k + 1):
    for j in range(-k, k + 1):
        x, y = i * STEP + (STEP / 2 if j % 2 else 0), j * STEP
        if math.hypot(x, y) > 70.5:
            continue
        p = kc.P(x, y)
        # needs solid GND on both sides with margin (via ring 0.3 + 0.35)
        ok = all(z.HitTestFilledArea(L, p, mm(0.0)) and
                 all(z.HitTestFilledArea(L, kc.P(x + dx, y + dy), mm(0.0))
                     for dx, dy in ((0.75, 0), (-0.75, 0), (0, 0.75), (0, -0.75), (0.55, 0.55), (-0.55, 0.55), (0.55, -0.55), (-0.55, -0.55)))
                 for z, L in ((gF, F), (gB, B)))
        if not ok:
            continue
        if any(math.hypot(x - ex, y - ey) < 2.0 for ex, ey in existing):
            continue
        via("GND", x, y)
        existing.append((x, y)); added += 1
filler.Fill(b.Zones())
pcbnew.SaveBoard(OUT, b, True)
print("tracks %d  vias %d (stitching %d)  zones %d" % (
    sum(1 for t in b.GetTracks() if t.GetClass() != "PCB_VIA"),
    sum(1 for t in b.GetTracks() if t.GetClass() == "PCB_VIA"), added, len(list(b.Zones()))))
