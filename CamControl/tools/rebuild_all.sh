#!/bin/zsh
# Rebuilds the routed board from the 04:02 snapshot of the hand placement.
# WARNING: discards any edits made to camcontrol.kicad_pcb after that snapshot.
# Close KiCad first.  usage: tools/rebuild_all.sh OUT.kicad_pcb
set -e
cd "$(dirname $0)/.."
KP=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3
T=$(mktemp -d)
PYTHONPATH=tools $KP tools/build_place.py backups/camcontrol_before_overnight_0402.kicad_pcb $T/place.kicad_pcb
PYTHONPATH=tools $KP tools/build_route.py $T/place.kicad_pcb $T/route.kicad_pcb
tools/refill.sh $T/route.kicad_pcb
PYTHONPATH=tools $KP tools/labels.py $T/route.kicad_pcb $T/labels.kicad_pcb
PYTHONPATH=tools $KP tools/fix_silk.py $T/labels.kicad_pcb "$1"
tools/drc.sh "$1"
