#!/bin/zsh
# refill.sh BOARD -> refill zones with the project's real rules (kicad-cli) and save in place
KC=/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
P=$(cd "$(dirname "$0")/.." && pwd)          # the project folder (this script lives in tools/)
S=${TMPDIR:-/tmp}/battery_pcb_refill
rm -rf $S && mkdir -p $S && cp $P/battery_pcb.kicad_pro $P/battery_pcb.kicad_sch $S/ && cp -r $P/sheets $P/battery_pcb.pretty $S/ && cp $P/fp-lib-table $S/ 2>/dev/null
cp "$1" $S/battery_pcb.kicad_pcb
"$KC" pcb drc --refill-zones --save-board -o $S/drc.rpt $S/battery_pcb.kicad_pcb >/dev/null 2>&1
cp $S/battery_pcb.kicad_pcb "$1"
echo "refilled $1"
