"""Adds the bench test points to the schematic (once; re-running does nothing):
TP1 = +5V (buck output), TP2 = VBAT+ (2S pack, before the fuse), TP3/TP4 = GND for the meter's black lead.
The board side is in tools/layoutA (place_A, route_A, labels_A).  usage: python3 tools/add_testpoints.py"""
import os
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
LIB = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols/Connector.kicad_sym"
ROOT_UUID = "19ef3a32-de7c-46ee-a850-2420f6d47f94"
SHEET_UUID = {"power_in": "ae01c8e7-4191-4202-a535-afc32959794b", "buck_5v": "1914f4ed-278a-4026-a86a-769e5e361ab6"}
FOOTPRINT = "TestPoint:TestPoint_THTPad_D2.0mm_Drill1.0mm"
G = 1.27
# ref: (sheet, symbol uuid, value, net, x grid, y grid, global label?)
TPS = {
    "TP1": ("buck_5v", "b1000000-0000-4000-8000-000000000001", "TP_5V", "+5V", 100, 20, False),
    "TP2": ("power_in", "b1000000-0000-4000-8000-000000000002", "TP_VBAT", "VBAT+", 184, 36, False),
    "TP3": ("power_in", "b1000000-0000-4000-8000-000000000003", "TP_GND", "GND", 198, 36, True),
    "TP4": ("power_in", "b1000000-0000-4000-8000-000000000004", "TP_GND", "GND", 208, 36, True),
}


def U():
    return str(uuid.uuid4())


def lib_symbol():
    t = open(LIB).read()
    i = t.find('\n\t(symbol "TestPoint"') + 2
    d = 0
    for j in range(i, len(t)):
        d += t[j] == "("
        d -= t[j] == ")"
        if d == 0:
            break
    return t[i:j + 1].replace('(symbol "TestPoint"', '(symbol "Connector:TestPoint"', 1)


def prop(k, v, x, y, hide=False, justify=""):
    return ('\t\t(property "%s" "%s"\n\t\t\t(at %.2f %.2f 0)\n\t\t\t(effects (font (size 1.27 1.27))%s%s)\n\t\t)\n'
            % (k, v, x, y, " (justify %s)" % justify if justify else "", " (hide yes)" if hide else ""))


def placed(ref, sheet, suid, value, x, y):
    s = ('\t(symbol\n\t\t(lib_id "Connector:TestPoint")\n\t\t(at %.2f %.2f 0)\n\t\t(unit 1)\n\t\t(exclude_from_sim no)\n'
         '\t\t(in_bom no)\n\t\t(on_board yes)\n\t\t(dnp no)\n\t\t(uuid "%s")\n' % (x, y, suid))
    s += prop("Reference", ref, x + 2.54, y - 5.08, justify="left")
    s += prop("Value", value, x + 2.54, y - 2.54, justify="left")
    s += prop("Footprint", FOOTPRINT, x, y, hide=True)
    s += prop("Datasheet", "~", x, y, hide=True)
    s += prop("Description", "Bench test point", x, y, hide=True)
    s += '\t\t(pin "1" (uuid "%s"))\n' % U()
    s += ('\t\t(instances\n\t\t\t(project "battery_pcb"\n\t\t\t\t(path "/%s/%s"\n\t\t\t\t\t(reference "%s")\n'
          '\t\t\t\t\t(unit 1)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n\t)\n' % (ROOT_UUID, SHEET_UUID[sheet], ref))
    return s


def wire(x1, y1, x2, y2):
    return ('\t(wire\n\t\t(pts (xy %.2f %.2f) (xy %.2f %.2f))\n\t\t(stroke (width 0) (type default))\n\t\t(uuid "%s")\n\t)\n'
            % (x1, y1, x2, y2, U()))


def label(net, x, y, glob):
    if glob:
        return ('\t(global_label "%s"\n\t\t(shape input)\n\t\t(at %.2f %.2f 270)\n\t\t(fields_autoplaced yes)\n'
                '\t\t(effects (font (size 1.27 1.27)) (justify right))\n\t\t(uuid "%s")\n'
                '\t\t(property "Intersheetrefs" "${INTERSHEET_REFS}"\n\t\t\t(at %.2f %.2f 0)\n'
                '\t\t\t(effects (font (size 1.27 1.27)) (hide yes))\n\t\t)\n\t)\n' % (net, x, y, U(), x, y + 5))
    return ('\t(label "%s"\n\t\t(at %.2f %.2f 0)\n\t\t(fields_autoplaced yes)\n'
            '\t\t(effects (font (size 1.27 1.27)) (justify left bottom))\n\t\t(uuid "%s")\n\t)\n' % (net, x, y, U()))


def main():
    for sheet in sorted({v[0] for v in TPS.values()}):
        path = os.path.join(ROOT, "sheets", sheet + ".kicad_sch")
        text = open(path).read()
        mine = {r: v for r, v in TPS.items() if v[0] == sheet}
        if all(v[1] in text for v in mine.values()):
            print(sheet, "already has", ", ".join(sorted(mine)))
            continue
        if '(symbol "Connector:TestPoint"' not in text:
            i = text.find("(lib_symbols") + len("(lib_symbols")
            text = text[:i] + "\n\t\t" + lib_symbol().replace("\n", "\n\t") + text[i:]
        add = ""
        for ref, (sh, suid, value, net, gx, gy, glob) in sorted(mine.items()):
            x, y = gx * G, gy * G
            add += placed(ref, sheet, suid, value, x, y) + wire(x, y, x, y + 4 * G) + label(net, x, y + 4 * G, glob)
        k = text.rfind("\n\t(sheet_instances") + 1
        if k <= 0:                              # sub-sheets have none: insert before the file's final ")"
            k = len(text.rstrip()) - 1
        assert text[k:].strip().startswith(("(sheet_instances", ")"))
        text = text[:k] + add + text[k:]
        open(path, "w").write(text)
        print(sheet, "added", ", ".join(sorted(mine)))


if __name__ == "__main__":
    main()
