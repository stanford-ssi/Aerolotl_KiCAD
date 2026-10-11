"""Layout A, last stage: copy the Manufacturer / MPN fields (tools/annotate_mpn.py) onto the board footprints,
hidden, so the board matches the schematic (DRC parity) and both BOMs carry part numbers.
usage: fields_A.py BOARD.kicad_pcb   (edits in place)"""
import os
import sys

import pcbnew

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from annotate_mpn import PARTS  # noqa: E402

BOARD = sys.argv[1]
b = pcbnew.LoadBoard(BOARD)
n = 0
for f in b.GetFootprints():
    ref = f.GetReference()
    if ref not in PARTS:
        continue
    for name, value in zip(("Manufacturer", "MPN"), PARTS[ref]):
        f.SetField(name, value)
        fld = f.GetField(name)
        fld.SetVisible(False)
        fld.SetLayer(pcbnew.F_Fab if not f.IsFlipped() else pcbnew.B_Fab)
    n += 1
b.Save(BOARD)
print("fields set on %d footprints" % n)
