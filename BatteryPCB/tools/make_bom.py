"""Writes fab/battery_pcb_BOM.csv: the ordering BOM for one CamControl board, plus a suggested order for two.
Board parts come from the schematic (Manufacturer / MPN fields, see tools/annotate_mpn.py) via kicad-cli;
the rest (board-only standoffs, plug-in modules, cells, cable-side connectors, the PCB) are listed below.
usage: python3 tools/make_bom.py"""
import collections
import csv
import os
import subprocess
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
KICAD_CLI = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
OUT = os.path.join(ROOT, "fab", "battery_pcb_BOM.csv")
BOARDS = 2                                          # "Order qty" = enough for this many boards, plus spares

DESC = {
    "1042": "Battery holder, 1x 18650, surface mount",
    "CL21A106KAYNNNE": "Capacitor 10 uF 25 V X5R, 0805",
    "CL10B104KB8NNNC": "Capacitor 100 nF 50 V X7R, 0603",
    "CL21A226MOQNNNE": "Capacitor 22 uF 16 V X5R, 0805",
    "CL10C220JB8NNNC": "Capacitor 22 pF 50 V C0G, 0603",
    "SMBJ12A": "TVS diode, 12 V standoff, SMB",
    "LTST-C171KRKT": "LED, red, 0805 (status light)",
    "B340B-13-F": "Schottky diode 40 V 3 A, SMB (reverse-polarity protection)",
    "1812L200/12DR": "Resettable fuse (PTC) 2 A hold, 12 V, 1812",
    "PPTC191LFBN-RC": "Female header 1x19, 2.54 mm (socket for the ESP32-DevKitC)",
    "BM05B-GHS-TBT": "JST GH 5-pin vertical header (camera)",
    "0436500215": "Molex Micro-Fit 3.0 2-pin vertical header",
    "XT30UPB-F": "AMASS XT30 female, vertical PCB mount (battery outputs)",
    "SRN6045TA-6R8M": "Power inductor 6.8 uH, 3.6 A rms / 5.7 A sat, 6 x 6 mm",
    "CL21B104KBCNNNC": "Capacitor 100 nF 50 V X7R, 0805",
    "RC0603FR-07402KL": "Resistor 402 k 1%, 0603",
    "RC0603FR-07100KL": "Resistor 100 k 1%, 0603",
    "RC0603FR-0713KL": "Resistor 13 k 1%, 0603",
    "RC0603FR-0739KL": "Resistor 39 k 1%, 0603",
    "RC0603FR-071KL": "Resistor 1 k 1%, 0603",
    "RC0603FR-07100RL": "Resistor 100 ohm 1%, 0603",
    "LMR51430XFDDCR": "Buck converter 4.5-36 V in, 3 A, SOT-23-6 (makes the 5 V rail)",
}
NOTES = {
    "1812L200/12DR": "Alt: Polytronics SMD1812P200TF/16",
    "0436500215": "SW1 camera power, SW2/SW3 pin-switch leads",
    "XT30UPB-F": "J5 to the TeleMetrum, J6 to the Aerolotl. Pin 1 = minus, pin 2 = plus, as marked on the housing",
}

# where to buy each MPN (checked on lcsc.com / digikey.com 8 Oct 2026): LCSC number, or another distributor when LCSC has none
LCSC = {
    "CL21A106KAYNNNE": "C15850", "CL10B104KB8NNNC": "C1591", "CL21A226MOQNNNE": "C98190", "CL10C220JB8NNNC": "C1653",
    "CL21B104KBCNNNC": "C1711", "SMBJ12A": "C151251", "LTST-C171KRKT": "C284871", "B340B-13-F": "C85099",
    "1812L200/12DR": "C315901", "BM05B-GHS-TBT": "C189891", "0436500215": "C293740", "XT30UPB-F": "C108769",
    "SRN6045TA-6R8M": "C2041457", "RC0603FR-07100KL": "C14675", "RC0603FR-0713KL": "C137796",
    "RC0603FR-0739KL": "C163424", "RC0603FR-071KL": "C22548", "RC0603FR-07100RL": "C105588",
    "RC0603FR-07402KL": "C874662", "LMR51430XFDDCR": "C5219260",
    "PPTC191LFBN-RC": "C2897382",     # LCSC has no Sullins stock: HCTL PM254-1-19-Z-8.5, same 1x19, 2.54 mm, 8.5 mm tall
    "0436450200": "C114089", "0430300007": "C293530", "XT30U-M": "C99101", "GHR-05V-S": "C160419",
    "SSHL-002T-P0.2": "C189897",
}
OTHER = {
    "1042": "DigiKey 36-1042-ND (not sold by LCSC)",
    "9774050243R": "DigiKey 732-7097-1-ND / Mouser 710-9774050243R (not sold by LCSC)",
    "ESP32-DevKitC-32E": "Mouser 356-ESP32-DEVKITC32E (or DigiKey 1965-ESP32-DEVKITC-32E-ND)",
    "PPTC191LFBN-RC": "DigiKey S7017-ND if you want the Sullins part itself",
}

# not on the schematic: board-only parts, things that plug in, and the cable side of each connector
EXTRA = [
    # section, qty per board, refs, description, manufacturer, MPN, notes
    ("Board hardware", 4, "H7-H10", "SMT steel standoff, M2 thread, 5 mm (camera mounts, back side)",
     "Wurth Elektronik", "9774050243R", "Soldered like a part"),
    ("Plugs in / mounts on", 1, "", "ESP32 dev board, DevKitC V4", "Espressif", "ESP32-DevKitC-32E",
     "Plugs into J1/J2 from the back"),
    ("Plugs in / mounts on", 1, "", "Camera, RunCam Split 4", "RunCam", "Split 4",
     "Sits on H7-H10. Build its harness: J3 (JST GH 5-pin) to the camera's 3-pin power/video plug (VCC, GND, video) + 2 wires soldered to its RX/TX pads"),
    ("Plugs in / mounts on", 4, "", "Screw M2 x 4 mm, pan head", "", "", "Camera to standoffs"),
    ("Plugs in / mounts on", 4, "", "18650 Li-ion cell, flat top, high drain", "Molicel", "INR-18650-P28A",
     "Or any high-drain flat-top 18650; never mix cells in the series pair"),
    ("Cable side", 3, "SW1, SW2, SW3", "Micro-Fit 3.0 receptacle housing, 2-pin", "Molex", "0436450200", ""),
    ("Cable side", 6, "SW1, SW2, SW3", "Micro-Fit 3.0 female crimp terminal, 20-24 AWG", "Molex", "0430300007",
     "Needs a Micro-Fit crimper, or buy pre-crimped leads"),
    ("Cable side", 2, "J5, J6", "XT30 male plug, solder cup (cable to each flight computer)", "AMASS", "XT30U-M",
     "Solder 18-20 AWG; check polarity against the +/- on the board"),
    ("Cable side", 1, "J3", "JST GH housing, 5-pin", "JST", "GHR-05V-S", "Or a pre-crimped GH 5-pin cable"),
    ("Cable side", 5, "J3", "JST GH crimp terminal, 26-30 AWG", "JST", "SSHL-002T-P0.2", ""),
    ("Cable side", 1, "SW1", "Toggle switch, SPST, 3 A or more, panel mount", "", "",
     "Camera power switch, wired to the SW1 plug"),
    ("PCB", 1, "", "PCB, 2 layers, 145.3 mm (5.72 in) round, 1.6 mm FR-4, 1 oz copper", "JLCPCB (or any fab)",
     "", "Upload fab/battery_pcb_gerbers.zip; 5 is the usual minimum order"),
]


def spare(desc, qty):
    small = desc.startswith(("Capacitor", "Resistor", "LED"))
    return max(10, BOARDS * qty + 5) if small else BOARDS * qty + (0 if desc.startswith("Battery holder") else 1)


def main():
    tmp = tempfile.mktemp(suffix=".csv")
    subprocess.run([KICAD_CLI, "sch", "export", "bom", "--fields", "Reference,Value,Footprint,Manufacturer,MPN",
                    "--group-by", "", "-o", tmp, os.path.join(ROOT, "battery_pcb.kicad_sch")],
                   check=True, capture_output=True)
    groups = collections.OrderedDict()
    for row in csv.DictReader(open(tmp)):
        key = (row["Manufacturer"], row["MPN"])
        g = groups.setdefault(key, {"refs": [], "fp": row["Footprint"].split(":")[-1]})
        g["refs"] += [r.strip() for r in row["Reference"].split(",") if r.strip()]
    os.remove(tmp)

    def refkey(r):
        head = r.rstrip("0123456789")
        return head, int(r[len(head):] or 0)

    rows = []
    for (mfr, mpn), g in sorted(groups.items(), key=lambda kv: refkey(sorted(kv[1]["refs"], key=refkey)[0])):
        refs = sorted(set(g["refs"]), key=refkey)
        if not mpn:
            raise SystemExit("no MPN for %s: run tools/annotate_mpn.py" % ", ".join(refs))
        desc = DESC.get(mpn, "")
        rows.append(["Board (solder on)", len(refs), spare(desc, len(refs)), ", ".join(refs), desc, mfr, mpn,
                     LCSC.get(mpn, ""), OTHER.get(mpn, ""), g["fp"], NOTES.get(mpn, "")])
        if not (LCSC.get(mpn) or OTHER.get(mpn)):
            raise SystemExit("no supplier for %s (%s)" % (mpn, ", ".join(refs)))
    for sec, qty, refs, desc, mfr, mpn, note in EXTRA:
        order = 5 if sec == "PCB" else BOARDS * qty
        rows.append([sec, qty, order, refs, desc, mfr, mpn, LCSC.get(mpn, ""), OTHER.get(mpn, ""), "", note])

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Section", "Qty per board", "Order qty (%d boards + spares)" % BOARDS, "References",
                    "Description", "Manufacturer", "MPN", "LCSC #", "Other supplier", "Footprint", "Notes"])
        w.writerows(rows)
    print("wrote %s: %d lines (%d soldered part numbers)" % (os.path.relpath(OUT, ROOT), len(rows), len(groups)))

    # JLCPCB assembly files (optional): BOM (Comment, Designator, Footprint, LCSC Part #) + CPL from the board.
    # The battery holders and camera standoffs are not at LCSC: hand-solder them (or use JLC global sourcing).
    jlc = [r for r in rows if r[0] == "Board (solder on)" and r[7]]
    with open(os.path.join(ROOT, "fab", "battery_pcb_JLCPCB_BOM.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
        for r in jlc:
            w.writerow([r[6], r[3], r[9], r[7]])
    refs = {x.strip() for r in jlc for x in r[3].split(",")}
    pos = tempfile.mktemp(suffix=".csv")
    subprocess.run([KICAD_CLI, "pcb", "export", "pos", "--format", "csv", "--units", "mm", "--side", "both",
                    "-o", pos, os.path.join(ROOT, "battery_pcb.kicad_pcb")], check=True, capture_output=True)
    with open(os.path.join(ROOT, "fab", "battery_pcb_JLCPCB_CPL.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        n = 0
        for row in csv.DictReader(open(pos)):
            if row["Ref"] in refs:
                w.writerow([row["Ref"], row["PosX"] + "mm", row["PosY"] + "mm", "Top" if row["Side"] == "top" else "Bottom", row["Rot"]])
                n += 1
    os.remove(pos)
    print("wrote fab/battery_pcb_JLCPCB_BOM.csv (%d lines) and fab/battery_pcb_JLCPCB_CPL.csv (%d parts)" % (len(jlc), n))


if __name__ == "__main__":
    main()
