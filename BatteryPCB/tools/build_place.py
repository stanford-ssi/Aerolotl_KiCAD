"""Stage 1: fix front orientation issues, rebuild back-side parts from the library
(properly mirrored by KiCad's own Flip), place them next to what they connect to,
and link every footprint to its schematic symbol.

usage: build_place.py BASE.kicad_pcb OUT.kicad_pcb
"""
import sys, pcbnew, kc, schparse

BASE, OUT = sys.argv[1], sys.argv[2]
b = kc.load(BASE)
sch = schparse.read(".")
fps = kc.fp_by_ref(b)

def set_meta(fp, ref):
    s = sch[ref]
    fp.SetReference(ref)
    fp.SetValue(s["value"])
    fp.SetPath(pcbnew.KIID_PATH(s["path"]))
    fp.SetSheetname(s["sheetname"])
    fp.SetSheetfile(s["sheetfile"])

# ------------------------------------------------------------------ front fixes
# ESP32-DevKitC V4: left header 3V3(1)..5V(19), right header GND(1)..CLK(19), counted
# from the antenna end. The sockets were at 180 deg, i.e. mirrored: the board could not
# accept the module the right way round. Same columns, same span, pin 1 now at the top.
for ref, x in (("J1", 33.66), ("J2", 59.06)):
    fps[ref].SetOrientationDegrees(0)
    fps[ref].SetPosition(kc.P(x, -29.44))
# Battery bank centred between the mounting-hole rows (was y=+3.07, which put hole
# H135 1.4 mm into BT1's + pad).
BANK_Y = 0.0
for ref, x in (("BT1", -48.41), ("BT2", -26.21), ("BT3", -4.01), ("BT4", 18.19)):
    fps[ref].SetPosition(kc.P(x, BANK_Y))
# BT2 turned end-for-end: its + terminal now sits next to BT1's - terminal, so the
# 2S series link is a 22 mm bar across the top instead of a 95 mm run down the board
fps["BT2"].SetOrientationDegrees(270)
for ref, fp in fps.items():
    if ref in sch:
        set_meta(fp, ref)
# mounting holes are mechanical only: fresh library copies, marked board-only so the
# schematic-parity check doesn't report them as extra footprints
HOLES = {r: (kc.rel(fps[r].GetPosition()), fps[r].GetOrientationDegrees()) for r in fps if r.startswith("H")}
hole_lib = {r: pcbnew.FootprintLoad(kc.FPLIB + "/MountingHole.pretty", "MountingHole_4.5mm") for r in HOLES}

# ------------------------------------------------------------------ back side
# (x, y, R): board coordinates of the footprint origin; R is the rotation applied
# before KiCad flips the part to the back.  For two-pad parts that puts pad 1:
#   R=0 -> right   R=180 -> left   R=90 -> down   R=270 -> up
X0, Y0 = 44.5, 6.0          # U1; buck laid out like LMR51430 datasheet fig 9-10
BACK = {
    # buck converter
    "U1": (X0, Y0, 90),
    "L1": (X0, Y0 + 5.75, 270),          # SW pad straight under the SW pin
    "C1": (X0 - 3.3, Y0, 90),            # CIN: VIN pad beside VIN pin, GND pad to under-IC strip
    "C2": (X0 - 5.55, Y0, 90),
    "C4": (X0 + 4.4, Y0 + 7.2, 90),      # COUT at the VOUT end of L1, GND back to pin 1
    "C5": (X0 + 6.6, Y0 + 7.2, 90),
    "C6": (X0 + 8.55, Y0 + 7.2, 90),
    "C3": (X0 + 3.2, Y0 - 3.0, 180),     # bootstrap, next to CB
    "R2": (X0 - 1.2, Y0 - 4.4, 270),     # feedback divider on the quiet side, next to FB
    "C7": (X0 + 0.6, Y0 - 4.4, 270),
    "R3": (X0 - 3.55, Y0 - 3.2, 0),
    # input protection, in signal order from the switch: SW1 -> D3 -> D1 -> CIN
    "D3": (38.3, 21.0, 270),             # SS34, cathode (VIN) up
    "D1": (38.3, 13.5, 90),              # SMBJ12A, cathode (VIN) down
    "F1": (-47.4, 32.6, 180),            # fuse right at BT1 +
    # pack-voltage sense: top resistor at the source, divider bottom + filter at the ADC pin
    "R4": (36.5, 5.2, 90),
    "R5": (37.3, -19.28, 180),
    "C8": (37.3, -17.3, 180),
    # ESP32 5 V decoupling right at the 5V pin (J1.19)
    "C10": (30.2, 16.28, 0),
    "C9": (29.9, 18.6, 0),
    # camera UART series resistors at the camera connector
    "R7": (54.2, 29.96, 0),
    "R8": (54.2, 31.96, 0),
    # status LED at the board edge beside J2.15 (IO2)
    "R6": (62.6, 6.12, 180),
    "D2": (66.2, 6.12, 0),
}

# load every replacement from the library first (pcbnew's SWIG layer misbehaves if
# FootprintLoad is called after Remove), remember the old pad nets, then swap
fresh = {}
for ref in BACK:
    lib, name = sch[ref]["footprint"].split(":", 1)
    fresh[ref] = pcbnew.FootprintLoad(kc.FPLIB + "/" + lib + ".pretty", name)
    fresh[ref].SetFPID(pcbnew.LIB_ID(lib, name))
old_nets = {}
for ref in BACK:
    old_nets[ref] = {p.GetNumber(): p.GetNetname() for p in fps[ref].Pads()}
graveyard = []                      # keep removed objects alive until exit
for ref in BACK:
    graveyard.append(fps[ref])
    b.Remove(fps[ref])
for ref, ((hx, hy), hrot) in HOLES.items():
    graveyard.append(fps[ref])
    b.Remove(fps[ref])
    h = hole_lib[ref]
    h.SetFPID(pcbnew.LIB_ID("MountingHole", "MountingHole_4.5mm"))
    b.Add(h)
    h.SetReference(ref)
    h.SetValue("MountingHole_4.5mm")
    h.SetPosition(kc.P(hx, hy)); h.SetOrientationDegrees(hrot)
    h.SetAttributes(pcbnew.FP_BOARD_ONLY | pcbnew.FP_EXCLUDE_FROM_POS_FILES | pcbnew.FP_EXCLUDE_FROM_BOM)
fps = None

for ref, (x, y, rot) in BACK.items():
    fp = fresh[ref]
    b.Add(fp)
    set_meta(fp, ref)
    fp.SetPosition(kc.P(x, y))
    fp.SetOrientationDegrees(rot)
    fp.Flip(kc.P(x, y), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
    for p in fp.Pads():
        n = old_nets[ref].get(p.GetNumber(), "")
        if n:
            p.SetNet(b.FindNet(n))

for z in list(b.Zones()):
    graveyard.append(z)
    b.Remove(z)
pcbnew.SaveBoard(OUT, b, True)

# ------------------------------------------------------------------ report
b = kc.load(OUT)
for f in sorted(b.GetFootprints(), key=lambda f: f.GetReference()):
    if not f.IsFlipped() and f.GetReference() not in ("J1", "J2"):
        continue
    pads = ", ".join("%s:(%.2f,%.2f)%s" % (p.GetNumber(), *kc.rel(p.GetPosition()), p.GetNetname().split("/")[-1][:8])
                     for p in f.Pads() if f.GetReference() not in ("J1", "J2") or p.GetNumber() in ("1", "5", "11", "12", "14", "15", "19"))
    print("%-4s %s %-7s %s" % (f.GetReference(), "B" if f.IsFlipped() else "F", f.GetOrientationDegrees(), pads))
