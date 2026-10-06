#!/bin/zsh
# drc.sh BOARD  -> runs kicad-cli DRC (with schematic parity) on a scratch copy of the project
KC=/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
P=$(cd "$(dirname "$0")/.." && pwd)          # the project folder (this script lives in tools/)
S=${TMPDIR:-/tmp}/camcontrol_drc
rm -rf $S && mkdir -p $S && cp $P/camcontrol.kicad_pro $P/camcontrol.kicad_sch $S/ && cp -r $P/sheets $P/camcontrol.pretty $S/ && cp $P/fp-lib-table $S/ 2>/dev/null
cp "$1" $S/camcontrol.kicad_pcb
"$KC" pcb drc --schematic-parity --severity-all --units mm -o $S/drc.rpt $S/camcontrol.kicad_pcb >/dev/null 2>&1
grep -E "^\[" $S/drc.rpt | sed 's/\]:.*/]/' | sort | uniq -c | sort -rn
grep -E "^\*\* Found" $S/drc.rpt
