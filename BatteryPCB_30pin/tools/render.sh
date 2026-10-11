#!/bin/zsh
# render.sh BOARD OUTDIR [dpi]  -> OUTDIR/{top,bottom,both}.png
KC=/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
B=$1; O=$2; R=${3:-110}
mkdir -p "$O"
"$KC" pcb export pdf --mode-single --scale 0 -l "F.Cu,F.SilkS,F.Fab,F.CrtYd,Edge.Cuts" -o "$O/top.pdf" "$B" >/dev/null 2>&1
"$KC" pcb export pdf --mode-single --scale 0 --mirror -l "B.Cu,B.SilkS,B.Fab,B.CrtYd,Edge.Cuts" -o "$O/bottom.pdf" "$B" >/dev/null 2>&1
"$KC" pcb export pdf --mode-single --scale 0 -l "B.Cu,F.Cu,F.SilkS,B.SilkS,Edge.Cuts" -o "$O/both.pdf" "$B" >/dev/null 2>&1
for f in top bottom both; do /opt/homebrew/bin/pdftocairo -png -r $R -singlefile "$O/$f.pdf" "$O/$f" 2>/dev/null; done
ls -la "$O"/*.png
