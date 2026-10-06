"""Writes fab/camcontrol_BOM.csv: the ordering BOM for one CamControl board, plus a suggested order for two.
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
OUT = os.path.join(ROOT, "fab", "camcontrol_BOM.csv")
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
    "B2B-XH-A(LF)(SN)": "JST XH 2-pin vertical header (to the Aerolotl)",
    "SRN6045TA-4R7M": "Power inductor 4.7 uH 4.5 A, 6 x 6 mm",
    "RC0603FR-07100KL": "Resistor 100 k 1%, 0603",
    "RC0603FR-0713K7L": "Resistor 13.7 k 1%, 0603",
    "RC0603FR-0747KL": "Resistor 47 k 1%, 0603",
    "RC0603FR-071KL": "Resistor 1 k 1%, 0603",
    "RC0603FR-07100RL": "Resistor 100 ohm 1%, 0603",
    "LMR51430XFDDCR": "Buck converter 4.5-36 V in, 3 A, SOT-23-6 (makes the 5 V rail)",
}
NOTES = {
    "1812L200/12DR": "Alt: Polytronics SMD1812P200TF/16",
    "0436500215": "SW1 camera power, SW2/SW3 pin-switch leads, J5 to the TeleMetrum",
    "B2B-XH-A(LF)(SN)": "Friction fit, not latching",
}

# not on the schematic: board-only parts, things that plug in, and the cable side of each connector
EXTRA = [
    # section, qty per board, refs, description, manufacturer, MPN, notes
    ("Board hardware", 4, "H7-H10", "SMT steel standoff, M2 thread, 5 mm (camera mounts, back side)",
     "Wurth Elektronik", "9774050243", "Soldered like a part"),
    ("Plugs in / mounts on", 1, "", "ESP32 dev board, DevKitC V4", "Espressif", "ESP32-DevKitC-32E",
     "Plugs into J1/J2 from the back"),
    ("Plugs in / mounts on", 1, "", "Camera, RunCam Split 4", "RunCam", "Split 4",
     "Sits on H7-H10; check its cable ends in a JST GH 5-pin for J3"),
    ("Plugs in / mounts on", 4, "", "Screw M2 x 4 mm, pan head", "", "", "Camera to standoffs"),
    ("Plugs in / mounts on", 4, "", "18650 Li-ion cell, flat top, high drain", "Molicel", "INR-18650-P28A",
     "Or any high-drain flat-top 18650; never mix cells in the series pair"),
    ("Cable side", 4, "SW1, SW2, SW3, J5", "Micro-Fit 3.0 receptacle housing, 2-pin", "Molex", "0436450200", ""),
    ("Cable side", 8, "SW1, SW2, SW3, J5", "Micro-Fit 3.0 female crimp terminal, 20-24 AWG", "Molex", "0430300007",
     "Needs a Micro-Fit crimper, or buy pre-crimped leads"),
    ("Cable side", 1, "J6", "JST XH housing, 2-pin", "JST", "XHP-2", ""),
    ("Cable side", 2, "J6", "JST XH crimp terminal, 22-28 AWG", "JST", "SXH-001T-P0.6", ""),
    ("Cable side", 1, "J3", "JST GH housing, 5-pin", "JST", "GHR-05V-S", "Or a pre-crimped GH 5-pin cable"),
    ("Cable side", 5, "J3", "JST GH crimp terminal, 26-30 AWG", "JST", "SSHL-002T-P0.2", ""),
    ("Cable side", 1, "SW1", "Toggle switch, SPST, 3 A or more, panel mount", "", "",
     "Camera power switch, wired to the SW1 plug"),
    ("PCB", 1, "", "PCB, 2 layers, 145.3 mm (5.72 in) round, 1.6 mm FR-4, 1 oz copper", "JLCPCB (or any fab)",
     "", "Upload fab/camcontrol_gerbers.zip; 5 is the usual minimum order"),
]


def spare(desc, qty):
    small = desc.startswith(("Capacitor", "Resistor", "LED"))
    return max(10, BOARDS * qty + 5) if small else BOARDS * qty + (0 if desc.startswith("Battery holder") else 1)


def main():
    tmp = tempfile.mktemp(suffix=".csv")
    subprocess.run([KICAD_CLI, "sch", "export", "bom", "--fields", "Reference,Value,Footprint,Manufacturer,MPN",
                    "--group-by", "", "-o", tmp, os.path.join(ROOT, "camcontrol.kicad_sch")],
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
                     g["fp"], NOTES.get(mpn, "")])
    for sec, qty, refs, desc, mfr, mpn, note in EXTRA:
        order = 5 if sec == "PCB" else BOARDS * qty
        rows.append([sec, qty, order, refs, desc, mfr, mpn, "", note])

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Section", "Qty per board", "Order qty (%d boards + spares)" % BOARDS, "References",
                    "Description", "Manufacturer", "MPN", "Footprint", "Notes"])
        w.writerows(rows)
    print("wrote %s: %d lines (%d soldered part numbers)" % (os.path.relpath(OUT, ROOT), len(rows), len(groups)))


if __name__ == "__main__":
    main()
