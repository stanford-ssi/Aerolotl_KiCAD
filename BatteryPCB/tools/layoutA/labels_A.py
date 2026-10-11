"""Layout A, stage 3: silkscreen labels. Front: connectors and cells. Back: the ESP32 DevKitC that plugs in underneath.
usage: labels_A.py IN OUT"""
import sys, pcbnew, kc
IN, OUT = sys.argv[1], sys.argv[2]
b = kc.load(IN)
mm = kc.mm
L, C, R = pcbnew.GR_TEXT_H_ALIGN_LEFT, pcbnew.GR_TEXT_H_ALIGN_CENTER, pcbnew.GR_TEXT_H_ALIGN_RIGHT
MID, PIN = (1.0, 0.15), (0.8, 0.13)
FRONT = [
    ("CAM PWR SW",  -29.00,  60.60, MID, C),
    ("5V",           23.80,  13.30, PIN, C), ("GND", 23.80, 22.80, PIN, C),   # test points TP1 / TP3 (BT3-BT4 gap)
    ("VBAT",        -36.50,  47.30 + kc.BAT_DY - 2.25, PIN, C), ("GND", -40.50, 47.30 + kc.BAT_DY - 2.25, PIN, C),   # TP2 / TP4 (above: a notch is below)
    ("COTS OUT",     25.00,  46.05 + kc.COTS_DY, PIN, C),     # J5 XT30 to the TeleMetrum (its +/- marks are in the footprint)
    ("SRAD OUT",     40.00,  46.05 + kc.COTS_DY, PIN, C),     # J6 XT30 to the Aerolotl
    ("PIN-SWITCH STACK", 0.00, -63.00, MID, C),               # outline below (review 2)
    ("COTS ARM",     29.80, -54.60, MID, C),     # pin-switch leads, beside the pin-switch stack
    ("SRAD ARM",     40.60, -54.60, MID, C),
    ("CAM 2S PACK", -36.50, -47.00, MID, C),     # left of the pin-switch stack
    ("ESP32 PLUGS IN\nFROM THE BACK", -36.5, -51.5, PIN, C),
]
BACK = [   # seen from the back, so mirrored
    ("ESP32-DevKitC V4\nparts facing down", 11.10, -34.60 + kc.ESP_DY, MID, C),   # clear of BT3's peg hole
    ("ANTENNA END", 11.10, -43.60 + kc.ESP_DY, MID, C),
    ("ANTENNA KEEP-OUT 15 mm\nNO COPPER THIS SIDE", 11.10, -51.50, PIN, C),   # outline below (review 2)
    ("H5: NYLON M3\nBOLT AND NUT", 18.50, -46.20, PIN, C),          # the stack bolt right over the antenna
    ("USB END",     11.10,  10.20 + kc.ESP_DY, MID, C),
    ("3V3",          23.80, -43.60 + kc.ESP_DY, PIN, C), ("5V", 23.80, 8.20 + kc.ESP_DY, PIN, C),
    ("GND",          -1.60, -43.60 + kc.ESP_DY, PIN, C), ("CLK", -1.60, 8.20 + kc.ESP_DY, PIN, C),
    ("CAMERA",       -1.00,  25.60, MID, C),     # J3, JST GH 5-pin
    ("1 +5V  2 GND\n3 RX  4 TX  5 VID",  1.50, 27.70, PIN, C),   # right of BT2's peg
    ("RUNCAM SPLIT 4\nWIRE PADS TOWARD J3", -35.50, -30.00, PIN, C),   # under the camera board
]
def add(items, layer, mirror):
    for text, x, y, (h, th), just in items:
        t = pcbnew.PCB_TEXT(b); t.SetText(text); t.SetLayer(layer)
        t.SetTextSize(pcbnew.VECTOR2I(mm(h), mm(h))); t.SetTextThickness(mm(th))
        t.SetHorizJustify(just); t.SetVertJustify(pcbnew.GR_TEXT_V_ALIGN_CENTER)
        t.SetMirrored(mirror); t.SetPosition(kc.P(x, y)); b.Add(t)
add(FRONT, pcbnew.F_SilkS, False)
add(BACK, pcbnew.B_SilkS, True)
# DevKitC outline for assembly (drawing layer, not printed)
s = pcbnew.PCB_SHAPE(b); s.SetShape(pcbnew.SHAPE_T_RECT)
s.SetStart(kc.P(11.1 - 13.95, -17.34 + kc.ESP_DY - 27.2)); s.SetEnd(kc.P(11.1 + 13.95, -17.34 + kc.ESP_DY + 27.2))
s.SetLayer(pcbnew.Dwgs_User); s.SetWidth(mm(0.15)); b.Add(s)
# RunCam Split 4 outline (29 x 29 on the four M2 standoffs) for assembly (drawing layer, not printed)
s = pcbnew.PCB_SHAPE(b); s.SetShape(pcbnew.SHAPE_T_RECT)
s.SetStart(kc.P(-35.5 - 14.5, -30.0 - 14.5)); s.SetEnd(kc.P(-35.5 + 14.5, -30.0 + 14.5))
s.SetLayer(pcbnew.Dwgs_User); s.SetWidth(mm(0.15)); b.Add(s)
# outlines on silk, broken wherever they would cross a pad, hole, via or label (review 2, 7 Oct 2026)
def obstacles(layer):
    out = []
    side_cu = pcbnew.F_Cu if layer == pcbnew.F_SilkS else pcbnew.B_Cu
    for f in b.GetFootprints():
        for p in f.Pads():
            if p.IsOnLayer(side_cu) or p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
                out.append(p.GetBoundingBox())
    out += [v.GetBoundingBox() for v in b.GetTracks() if v.GetClass() == "PCB_VIA"]
    out += [d.GetBoundingBox() for d in b.GetDrawings() if d.GetClass() == "PCB_TEXT" and d.GetLayer() == layer]
    g = 0.35
    return [(kc.to_mm(r.GetLeft()) - kc.CX - g, kc.to_mm(r.GetTop()) - kc.CY - g,
             kc.to_mm(r.GetRight()) - kc.CX + g, kc.to_mm(r.GetBottom()) - kc.CY + g) for r in out]
def outline(layer, x0, y0, x1, y1, w=0.15, bottom=True):
    obs = obstacles(layer)
    sides = [((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))]
    for (ax, ay), (bx, by) in (sides if bottom else sides[:2] + sides[3:]):
        horiz = ay == by
        lo, hi = sorted((ax, bx) if horiz else (ay, by)); c = ay if horiz else ax
        cuts = sorted((r[0], r[2]) if horiz else (r[1], r[3]) for r in obs
                      if (r[1] - w / 2 < c < r[3] + w / 2 if horiz else r[0] - w / 2 < c < r[2] + w / 2))
        cuts = [(a, e) for a, e in cuts if e > lo and a < hi]
        s = lo
        for a, e in cuts + [(hi, hi)]:
            if s >= hi:
                break
            if min(a, hi) > s + 1.0:
                q = pcbnew.PCB_SHAPE(b); q.SetShape(pcbnew.SHAPE_T_SEGMENT); q.SetLayer(layer); q.SetWidth(mm(w))
                q.SetStart(kc.P(s, c) if horiz else kc.P(c, s)); q.SetEnd(kc.P(min(a, hi), c) if horiz else kc.P(c, min(a, hi)))
                b.Add(q)
            s = max(s, e)
# pin-switch stack footprint (2 carriers, 45 mm wide, inner edge 36.88 mm and pin faces 68.88 mm from the centre;
# the outer edge is drawn 0.28 mm in so it stays on the board at the corners; its inner edge is the holders' own end lines)
outline(pcbnew.F_SilkS, -22.5, -68.6, 22.5, -37.5, bottom=False)
# ESP32 module antenna (under the board) and its 15 mm keep-out on the back copper
A0, A1, A2, A3 = kc.ANT; AC = kc.ANT_CLEAR
outline(pcbnew.B_SilkS, A0, A1, A2, A3, bottom=False)          # open at the devkit edge (the socket outlines are there)
outline(pcbnew.B_SilkS, A0 - AC, A1 - AC, A2 + AC, A3, bottom=False)
pcbnew.SaveBoard(OUT, b, True)
print("labels: %d front, %d back" % (len(FRONT), len(BACK)))
