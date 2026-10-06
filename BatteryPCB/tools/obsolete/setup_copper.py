#!/usr/bin/env python3
"""Add net classes and copper pours to battery_pcb.

Net classes go into battery_pcb.kicad_pro; zones are appended to the .kicad_pcb.
Existing tracks, footprints and zones are left alone (existing zones are
replaced only if they carry the marker below).
"""
import json, os, re, math, uuid, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "battery_pcb.kicad_pcb")
PRO = os.path.join(HERE, "battery_pcb.kicad_pro")
CX = CY = 150.0
R_EDGE = 73.5
INSET = 0.6                      # pour stops this far inside the board edge
U = lambda: str(uuid.uuid4())

# --------------------------------------------------------------- net classes
CLASSES = [
    # name,      track, clearance, via_d, via_drill
    ("Default",  0.30, 0.20, 0.60, 0.30),
    ("Power",    1.00, 0.30, 0.80, 0.40),
    ("Pyro",     1.00, 0.40, 0.80, 0.40),
    ("Signal",   0.30, 0.20, 0.60, 0.30),
]

# nets carrying real current from the 2S pack
POWER = ["*VBAT+", "*VF", "*VSW", "*VIN", "*+5V", "*SW", "GND", "Net-(BT1--)"]
# these carry the altimeters' e-match firing surge (~10 A for a few ms)
PYRO = ["*COTS_BAT+", "*COTS_BAT-", "*COTS_SW", "*SRAD_BAT+", "*SRAD_BAT-", "*SRAD_SW"]


def write_netclasses():
    pro = json.load(open(PRO))
    pro.setdefault("net_settings", {})
    pro["net_settings"]["classes"] = [
        {
            "name": n, "track_width": tw, "clearance": cl,
            "via_diameter": vd, "via_drill": vr,
            "diff_pair_width": 0.2, "diff_pair_gap": 0.25,
            "microvia_diameter": 0.3, "microvia_drill": 0.1,
            "line_style": 0, "pcb_color": "rgba(0, 0, 0, 0.000)",
            "schematic_color": "rgba(0, 0, 0, 0.000)", "wire_width": 6, "bus_width": 12,
            "priority": i,
        } for i, (n, tw, cl, vd, vr) in enumerate(CLASSES)
    ]
    pats = [{"netclass": "Power", "pattern": p} for p in POWER]
    pats += [{"netclass": "Pyro", "pattern": p} for p in PYRO]
    pro["net_settings"]["netclass_patterns"] = pats
    json.dump(pro, open(PRO, "w"), indent=2)
    return len(pats)


# --------------------------------------------------------------- zones
def circle_pts(r, n=96):
    return [(round(CX + r * math.cos(2 * math.pi * i / n), 3),
             round(CY + r * math.sin(2 * math.pi * i / n), 3)) for i in range(n)]


def zone(net_name, layer, pts, priority=0, tag="AUTO"):
    body = " ".join("(xy %g %g)" % p for p in pts)
    return f'''	(zone
		(net "{net_name}")
		(layers "{layer}")
		(uuid "{U()}")
		(name "{tag}_{net_name}_{layer}")
		(hatch edge 0.5)
		(priority {priority})
		(connect_pads
			(clearance 0.5)
		)
		(min_thickness 0.25)
		(filled_areas_thickness no)
		(fill
			(thermal_gap 0.5)
			(thermal_bridge_width 0.5)
		)
		(polygon
			(pts {body})
		)
	)'''


def main():
    npat = write_netclasses()
    src = open(PCB).read()

    # KiCad 10 uses name-only nets on pads and has no numeric net table
    names = set(re.findall(r'\(net "([^"]*)"\)', src))
    gnd = "GND" if "GND" in names else None
    v5 = next((n for n in names if n.endswith("/+5V") or n == "+5V"), None)
    if not gnd or not v5:
        raise SystemExit("could not find GND / +5V among pad nets")

    # drop any zones this script made before, keep hand-drawn ones
    src = re.sub(r'\t\(zone\n(?:[\s\S]*?\n)?\t\)\n(?=\t\(|\)$)',
                 lambda m: "" if '"AUTO_' in m.group(0) else m.group(0), src)

    outer = circle_pts(R_EDGE - INSET)
    zones = [
        zone(gnd, "F.Cu", outer, 0),
        zone(gnd, "B.Cu", outer, 0),
    ]
    # local +5V island on the back, over the buck output and its caps
    isl = [(CX - 26, CY - 12), (CX + 2, CY - 12), (CX + 2, CY - 2), (CX - 26, CY - 2)]
    zones.append(zone(v5, "B.Cu", isl, 1))

    src = src.rstrip()
    assert src.endswith(")")
    src = src[:-1] + "\n".join(zones) + "\n)\n"
    shutil.copy(PCB, PCB + ".bak2")
    open(PCB, "w").write(src)

    print("net classes written: %d (%d patterns)" % (len(CLASSES), npat))
    for n, tw, cl, vd, vr in CLASSES:
        print("   %-8s track %.2f mm  clearance %.2f  via %.1f/%.1f" % (n, tw, cl, vd, vr))
    print("\nzones added: %d" % len(zones))
    print("   GND  F.Cu   full board, priority 0")
    print("   GND  B.Cu   full board, priority 0")
    print("   +5V  B.Cu   local island over the buck output, priority 1")
    print("\nOpen in pcbnew and press B to fill.")


main()
