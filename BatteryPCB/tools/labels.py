"""Stage 4: front silkscreen labels saying what every connector (and cell) is for.
usage: labels.py IN OUT"""
import sys, pcbnew, kc

IN, OUT = sys.argv[1], sys.argv[2]
b = kc.load(IN)
mm = kc.mm
L, C, R = pcbnew.GR_TEXT_H_ALIGN_LEFT, pcbnew.GR_TEXT_H_ALIGN_CENTER, pcbnew.GR_TEXT_H_ALIGN_RIGHT
BIG, MID, PIN = (1.5, 0.22), (1.0, 0.15), (0.8, 0.13)

LABELS = [
    # text,              x,      y,      size, justify
    # 2S camera/ESP32 pack switch and the camera harness
    ("CAM PWR SW",       40.75,  34.30,  MID, C),
    ("CAMERA",           50.26,  37.30,  MID, C),
    ("+5V",              53.40,  25.96,  PIN, L),
    ("GND",              53.40,  27.96,  PIN, L),
    ("CAM RX",           53.40,  29.96,  PIN, L),
    ("CAM TX",           53.40,  31.96,  PIN, L),
    ("VIDEO",            53.40,  33.96,  PIN, L),
    # arming switches and altimeter outputs
    ("COTS\nARM",        42.65, -33.55,  MID, C),   # two lines: the switches are only 7.6 mm apart
    ("SRAD\nARM",        50.25, -33.55,  MID, C),
    ("COTS PWR",         28.00, -45.85,  MID, R),     # your wording
    ("+",                33.60, -42.55,  PIN, C),
    ("-",                35.60, -42.55,  PIN, C),
    ("SRAD PWR",         28.00, -52.35,  MID, R),
    ("+",                33.55, -55.95,  PIN, C),
    ("-",                35.55, -55.95,  PIN, C),
    # ESP32-DevKitC socket: which way round the module goes
    ("ESP32-DevKitC V4", 46.36, -12.00,  MID, C),
    ("ANTENNA END",      46.36, -28.20,  MID, C),
    ("USB END",          46.36,  18.90,  MID, C),
    ("3V3",              35.70, -29.44,  PIN, L),
    ("5V",               35.70,  16.28,  PIN, L),
    ("GND",              61.00, -29.44,  PIN, L),
    ("CLK",              61.00,  16.28,  PIN, L),
    # what each cell feeds - outside the holders so it stays visible after assembly
    ("CAM 2S PACK",     -37.30, -46.00,  MID, C),
    ("COTS",             -4.01, -46.20,  MID, C),
    ("SRAD",             17.40, -46.60,  MID, C),
]
for text, x, y, (h, th), just in LABELS:
    t = pcbnew.PCB_TEXT(b)
    t.SetText(text)
    t.SetLayer(pcbnew.F_SilkS)
    t.SetTextSize(pcbnew.VECTOR2I(mm(h), mm(h)))
    t.SetTextThickness(mm(th))
    t.SetHorizJustify(just)
    t.SetVertJustify(pcbnew.GR_TEXT_V_ALIGN_CENTER)
    t.SetPosition(kc.P(x, y))
    b.Add(t)
pcbnew.SaveBoard(OUT, b, True)
print("added %d silkscreen labels" % len(LABELS))
