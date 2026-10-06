#!/bin/zsh
# Rebuilds layout A from the seed board (tools/layoutA/seed_user_1224.kicad_pcb, the hand-placed 12:24 version). Close KiCad first.  usage: tools/layoutA/build_A.sh OUT.kicad_pcb
set -e
cd "$(dirname $0)/../.."
KP=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3
T=$(mktemp -d)
PYTHONPATH=tools $KP tools/layoutA/place_A.py tools/layoutA/seed_user_1224.kicad_pcb $T/1.kicad_pcb
PYTHONPATH=tools $KP tools/layoutA/route_A.py $T/1.kicad_pcb $T/2.kicad_pcb
tools/refill.sh $T/2.kicad_pcb
PYTHONPATH=tools $KP tools/layoutA/labels_A.py $T/2.kicad_pcb $T/3.kicad_pcb
PYTHONPATH=tools $KP tools/fix_silk.py $T/3.kicad_pcb "$1"
PYTHONPATH=tools $KP tools/layoutA/fields_A.py "$1"
tools/refill.sh "$1"; tools/drc.sh "$1"
PYTHONPATH=tools $KP tools/layoutA/verify_A.py "$1"
