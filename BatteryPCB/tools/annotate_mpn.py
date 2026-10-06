"""Adds hidden Manufacturer / MPN fields to every symbol in the schematic so the KiCad BOM is ready to order.
Re-running it replaces the fields with the values below.  usage: python3 tools/annotate_mpn.py   (KiCad closed)"""
import glob
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))

YAGEO, SAMSUNG = "Yageo", "Samsung Electro-Mechanics"
PARTS = {
    # ref: (manufacturer, MPN)
    "BT1": ("Keystone Electronics", "1042"), "BT2": ("Keystone Electronics", "1042"),
    "BT3": ("Keystone Electronics", "1042"), "BT4": ("Keystone Electronics", "1042"),
    "C1": (SAMSUNG, "CL21A106KAYNNNE"), "C2": (SAMSUNG, "CL21A106KAYNNNE"), "C9": (SAMSUNG, "CL21A106KAYNNNE"),
    "C3": (SAMSUNG, "CL10B104KB8NNNC"), "C6": (SAMSUNG, "CL10B104KB8NNNC"),
    "C8": (SAMSUNG, "CL10B104KB8NNNC"), "C10": (SAMSUNG, "CL10B104KB8NNNC"),
    "C4": (SAMSUNG, "CL21A226MOQNNNE"), "C5": (SAMSUNG, "CL21A226MOQNNNE"),
    "C7": (SAMSUNG, "CL10C220JB8NNNC"),
    "D1": ("Littelfuse", "SMBJ12A"),
    "D2": ("Lite-On", "LTST-C171KRKT"),
    "D3": ("Diodes Incorporated", "B340B-13-F"),
    "F1": ("Littelfuse", "1812L200/12DR"),              # 2 A hold / 12 V (2S pack is 8.4 V max); alt: PTTC SMD1812P200TF/16
    "J1": ("Sullins Connector Solutions", "PPTC191LFBN-RC"), "J2": ("Sullins Connector Solutions", "PPTC191LFBN-RC"),
    "J3": ("JST", "BM05B-GHS-TBT"),
    "J5": ("Molex", "0436500215"), "SW1": ("Molex", "0436500215"),
    "SW2": ("Molex", "0436500215"), "SW3": ("Molex", "0436500215"),
    "J6": ("JST", "B2B-XH-A(LF)(SN)"),
    "L1": ("Bourns", "SRN6045TA-4R7M"),
    "R2": (YAGEO, "RC0603FR-07100KL"), "R4": (YAGEO, "RC0603FR-07100KL"),
    "R3": (YAGEO, "RC0603FR-0713K7L"),
    "R5": (YAGEO, "RC0603FR-0739KL"),             # 39 k: VBAT_SENSE <= 2.36 V, inside the ESP32 ADC 11 dB range (<= 2.45 V)
    "R6": (YAGEO, "RC0603FR-071KL"),
    "R7": (YAGEO, "RC0603FR-07100RL"), "R8": (YAGEO, "RC0603FR-07100RL"),
    "U1": ("Texas Instruments", "LMR51430XFDDCR"),
}


def field(name, value, at):
    return ('\t\t(property "%s" "%s"\n\t\t\t(at %s)\n\t\t\t(effects (font (size 1.27 1.27)) (hide yes))\n\t\t)\n'
            % (name, value, at))


def main():
    done = set()
    for path in [os.path.join(ROOT, "battery_pcb.kicad_sch")] + sorted(glob.glob(os.path.join(ROOT, "sheets", "*.kicad_sch"))):
        text = open(path).read()
        out, pos = [], 0
        # placed symbols are "\t(symbol\n" blocks at depth 1; library symbols sit deeper inside lib_symbols
        for m in re.finditer(r"\n\t\(symbol\n", text):
            start = m.start() + 2                   # the "(" of "(symbol"
            depth, j = 0, start
            while True:
                c = text[j]
                depth += c == "("
                depth -= c == ")"
                j += 1
                if depth == 0:
                    break
            block = text[start:j]
            ref = re.search(r'\(property "Reference" "([^"]+)"', block)
            if not ref or ref.group(1) not in PARTS:
                continue
            mfr, mpn = PARTS[ref.group(1)]
            block = re.sub(r'\t\t\(property "(Manufacturer|MPN)" .*?\n\t\t\)\n', "", block, flags=re.S)
            at = re.search(r'\(property "Datasheet" [^\n]*\n\t\t\t\(at ([^)]*)\)', block).group(1)
            k = block.find("\t\t(pin ")
            block = block[:k] + field("Manufacturer", mfr, at) + field("MPN", mpn, at) + block[k:]
            out.append(text[pos:start] + block)
            pos = j
            done.add(ref.group(1))
        out.append(text[pos:])
        new = "".join(out)
        if new != text:
            open(path, "w").write(new)
            print("updated", os.path.relpath(path, ROOT))
    missing = sorted(set(PARTS) - done)
    print("annotated %d symbols%s" % (len(done), "; NOT FOUND: " + ", ".join(missing) if missing else ""))


if __name__ == "__main__":
    main()
