"""Brings a board's footprints in line with the schematic, like KiCad's "Update PCB from Schematic" but without
moving anything: each footprint gets its symbol's sheet path / sheet name / sheet file and value, and each pad its
schematic net. A net that only changed name is renamed in place, so its tracks, vias and zones follow it.
usage (KiCad's Python): tools/sync_from_sch.py BOARD.kicad_pcb  (the schematic is battery_pcb.kicad_sch next to tools/)"""
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

import pcbnew

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
CLI = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
board_path = sys.argv[1]
sch = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "battery_pcb.kicad_sch")

tmp = tempfile.mktemp(suffix=".xml")
subprocess.run([CLI, "sch", "export", "netlist", "--format", "kicadxml", "-o", tmp, sch], check=True,
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
x = ET.parse(tmp).getroot()
os.remove(tmp)

b = pcbnew.LoadBoard(board_path)
fps = {f.GetReference(): f for f in b.GetFootprints()}

moved = 0
for c in x.find("components"):
    ref = c.get("ref")
    f = fps.get(ref)
    if f is None:
        sys.exit("schematic part %s has no footprint on the board" % ref)
    sp = c.find("sheetpath")
    props = {p.get("name"): p.get("value") for p in c.findall("property")}
    path = sp.get("tstamps") + c.find("tstamps").text.strip()
    if f.GetPath().AsString() != path or f.GetSheetfile() != props.get("Sheetfile"):
        moved += 1
    f.SetPath(pcbnew.KIID_PATH(path))
    f.SetSheetname(props.get("Sheetname", sp.get("names").strip("/")))
    f.SetSheetfile(props.get("Sheetfile", ""))
    f.SetValue(c.find("value").text or "")

want = {}                                            # (ref, pad number) -> schematic net name
for n in x.find("nets"):
    for node in n.findall("node"):
        want[(node.get("ref"), node.get("pin"))] = n.get("name")

# old name -> new name, from every pad whose net changed
rename = {}
for (ref, pin), new in want.items():
    for p in fps[ref].Pads():
        if p.GetNumber() == pin:
            old = p.GetNetname()
            if old != new:
                rename.setdefault(old, set()).add(new)

renamed = 0
for old, news in sorted(rename.items()):
    oldnet = b.FindNet(old) if old else None
    pads_on_old = [(fr, p.GetNumber()) for fr, f in fps.items() for p in f.Pads() if old and p.GetNetname() == old]
    clean = (oldnet is not None and len(news) == 1 and b.FindNet(next(iter(news))) is None
             and all(want.get(k) == next(iter(news)) for k in pads_on_old))
    if clean:                                        # pure rename: everything on the net follows
        oldnet.SetNetname(next(iter(news)))
        renamed += 1
b.GetNetInfo().RebuildList() if hasattr(b.GetNetInfo(), "RebuildList") else None

# anything left: assign pads one by one (new nets are created as needed)
for (ref, pin), name in want.items():
    for p in fps[ref].Pads():
        if p.GetNumber() == pin and p.GetNetname() != name:
            net = b.FindNet(name)
            if net is None:
                net = pcbnew.NETINFO_ITEM(b, name)
                b.Add(net)
            p.SetNet(net)

bad = [(ref, pin, name) for (ref, pin), name in want.items()
       for p in fps[ref].Pads() if p.GetNumber() == pin and p.GetNetname() != name]
if bad:
    sys.exit("pads still off their schematic net: %s" % bad[:5])
b.Save(board_path)
print("sync_from_sch: %d footprints re-pathed, %d nets renamed, %d pads checked" % (moved, renamed, len(want)))
