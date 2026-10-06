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
    ("COTS OUT",     25.00,  46.05 + kc.COTS_DY, PIN, C),     # to the TeleMetrum (switched by the COTS pin switch)
    ("+",            26.50,  56.00 + kc.COTS_DY, PIN, C), ("-", 23.50, 56.00 + kc.COTS_DY, PIN, C),   # J5 turned 180
    ("SRAD OUT",     38.75,  46.05 + kc.COTS_DY, PIN, C),     # to the Aerolotl (switched by the SRAD pin switch)
    ("+",            40.00,  56.00 + kc.COTS_DY, PIN, C), ("-", 37.50, 56.00 + kc.COTS_DY, PIN, C),   # J6 (JST XH) turned 180
    ("COTS ARM",     29.80, -54.60, MID, C),     # pin-switch leads, beside the pin-switch stack
    ("SRAD ARM",     40.60, -54.60, MID, C),
    ("CAM 2S PACK", -36.50, -47.00, MID, C),     # left of the pin-switch stack
    ("ESP32 PLUGS IN\nFROM THE BACK", -36.5, -51.5, PIN, C),
]
BACK = [   # seen from the back, so mirrored
    ("ESP32-DevKitC V4\nparts facing down", 11.10, -34.60 + kc.ESP_DY, MID, C),   # clear of BT3's peg hole
    ("ANTENNA END", 11.10, -43.60 + kc.ESP_DY, MID, C),
    ("USB END",     11.10,  10.20 + kc.ESP_DY, MID, C),
    ("3V3",          23.80, -43.60 + kc.ESP_DY, PIN, C), ("5V", 23.80, 8.20 + kc.ESP_DY, PIN, C),
    ("GND",          -1.60, -43.60 + kc.ESP_DY, PIN, C), ("CLK", -1.60, 8.20 + kc.ESP_DY, PIN, C),
    ("CAMERA",       -1.00,  25.60, MID, C),     # J3, JST GH 5-pin
    ("1 +5V  2 GND\n3 RX  4 TX  5 VID",  1.50, 27.70, PIN, C),   # right of BT2's peg
    ("RUNCAM SPLIT 4\nWIRE PADS TOWARD J3", -24.00, 14.75, PIN, C),   # under the camera board
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
s.SetStart(kc.P(-24.0 - 14.5, 14.75 - 14.5)); s.SetEnd(kc.P(-24.0 + 14.5, 14.75 + 14.5))
s.SetLayer(pcbnew.Dwgs_User); s.SetWidth(mm(0.15)); b.Add(s)
pcbnew.SaveBoard(OUT, b, True)
print("labels: %d front, %d back" % (len(FRONT), len(BACK)))
