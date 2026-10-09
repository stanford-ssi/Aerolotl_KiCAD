#!/bin/zsh
# Regenerates everything in fab/ from the current schematic and board: BOM (+ JLCPCB BOM/CPL), schematic PDF,
# Gerbers + separate plated / non-plated drill files (zip), and the shareable KiCad project zip.  usage: tools/make_fab.sh
set -e
cd "$(dirname $0)/.."
K=/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
python3 tools/make_bom.py
$K sch export pdf -o fab/battery_pcb_schematic.pdf battery_pcb.kicad_sch >/dev/null 2>&1
G=$(mktemp -d)
$K pcb export gerbers -l "F.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts" -o $G/ battery_pcb.kicad_pcb >/dev/null 2>&1
$K pcb export drill --format excellon --excellon-separate-th -o $G/ battery_pcb.kicad_pcb >/dev/null 2>&1
rm -f fab/battery_pcb_gerbers.zip; (cd $G && zip -q -j "$OLDPWD/fab/battery_pcb_gerbers.zip" *)
P=$(mktemp -d); mkdir $P/battery_pcb
cp battery_pcb.kicad_pro battery_pcb.kicad_sch battery_pcb.kicad_pcb fp-lib-table README.md fab/battery_pcb_schematic.pdf $P/battery_pcb/
cp -R sheets battery_pcb.pretty 3dmodels $P/battery_pcb/
rm -f fab/battery_pcb_kicad_project.zip; (cd $P && zip -qr "$OLDPWD/fab/battery_pcb_kicad_project.zip" battery_pcb -x "*.DS_Store")
unzip -l fab/battery_pcb_gerbers.zip | awk 'NR>3 && $4 {print "  " $4}' | grep -v "^  ----"
echo "fab/ regenerated"
