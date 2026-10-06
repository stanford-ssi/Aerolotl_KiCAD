#!/bin/zsh
# refill.sh BOARD -> refill zones with the project's real rules (kicad-cli) and save in place
KC=/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
P=$(cd "$(dirname "$0")/.." && pwd)          # the project folder (this script lives in tools/)
S=${TMPDIR:-/tmp}/camcontrol_refill
rm -rf $S && mkdir -p $S && cp $P/camcontrol.kicad_pro $P/camcontrol.kicad_sch $S/ && cp -r $P/sheets $P/camcontrol.pretty $S/ && cp $P/fp-lib-table $S/ 2>/dev/null
cp "$1" $S/camcontrol.kicad_pcb
"$KC" pcb drc --refill-zones --save-board -o $S/drc.rpt $S/camcontrol.kicad_pcb >/dev/null 2>&1
cp $S/camcontrol.kicad_pcb "$1"
echo "refilled $1"
