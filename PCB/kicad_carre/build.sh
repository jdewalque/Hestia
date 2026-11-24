#!/bin/sh
# Regenerate schematic, netlist and (unrouted) board from tools/design.py.
# Usage: ./build.sh [rect|oval]   (default: rect)
#   rect -> kicad/alert_button.*            25 x 35 mm rectangle
#   oval -> kicad_oval/alert_button_oval.*  28 x 38 mm ellipse
# WARNING: overwrites the schematic and the board of the chosen variant.
set -e
cd "$(dirname "$0")"
KC=/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
KPY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
PCB_VARIANT="${1:-rect}"
export PCB_VARIANT
if [ "$PCB_VARIANT" = oval ]; then
  DIR=../kicad_oval; PRJ=alert_button_oval
  mkdir -p "$DIR"
  [ -f "$DIR/$PRJ.kicad_pro" ] || sed 's/alert_button\.kicad_pro/alert_button_oval.kicad_pro/' alert_button.kicad_pro > "$DIR/$PRJ.kicad_pro"
else
  DIR=.; PRJ=alert_button
fi
python3 tools/gen_sch.py
"$KC" sch erc --severity-all -o "$DIR/erc.rpt" "$DIR/$PRJ.kicad_sch"
"$KC" sch export netlist --format kicadsexpr -o "$DIR/$PRJ.net" "$DIR/$PRJ.kicad_sch"
"$KPY" tools/gen_pcb.py   # a harmless wxApp assert message may be printed
"$KC" pcb drc --schematic-parity --severity-all -o "$DIR/drc.rpt" "$DIR/$PRJ.kicad_pcb"
python3 tools/gen_bom.py  # same parts in both variants: one bom.csv
