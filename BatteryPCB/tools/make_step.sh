#!/bin/zsh
# Exports the board STEP centred on the board (--user-origin 150x150mm = the disc centre, board bottom at z = 0), then
# merges it with the exact pin-switch stack, raised 18 mm into the Onshape av-bay stack frame (what AVBay1 imports).
# usage: tools/make_step.sh
set -e
cd "$(dirname $0)/.."
K=/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
M=/Applications/KiCad/KiCad.app/Contents/SharedSupport/3dmodels
$K pcb export step --force --subst-models --user-origin 150x150mm -D KICAD10_3DMODEL_DIR=$M -o cad/battery_pcb.step battery_pcb.kicad_pcb 2>&1 | grep -iE "error|time" || true
python3 tools/step_merge.py cad/avbay1_board_and_pin_switch_stack.step cad/battery_pcb.step 18 cad/pin_switch_stack_8parts_mm.step
