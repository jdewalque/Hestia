#!/bin/sh
# Route a board: regenerate it, hand-route the LTE feed, run the Freerouting
# autorouter, complete the leftovers, add ground fills, run DRC.
# Usage: ./route.sh [rect|oval]   (default: rect)
# WARNING: overwrites the .kicad_pcb of that variant (any manual routing is lost).
# Needs Java; Freerouting is downloaded once to ~/.cache/freerouting.
set -e
cd "$(dirname "$0")"
KC=/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
KPY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
FR_VER=2.5.0
FR_JAR="${FREEROUTING_JAR:-$HOME/.cache/freerouting/freerouting-$FR_VER.jar}"
if [ ! -f "$FR_JAR" ]; then
  mkdir -p "$(dirname "$FR_JAR")"
  curl -L -o "$FR_JAR" "https://github.com/freerouting/freerouting/releases/download/v$FR_VER/freerouting-$FR_VER.jar"
fi
PCB_VARIANT="${1:-rect}"
export PCB_VARIANT
if [ "$PCB_VARIANT" = oval ]; then DIR=../kicad_oval; PRJ=alert_button_oval; else DIR=.; PRJ=alert_button; fi
./build.sh "$PCB_VARIANT"
python3 tools/route_rules.py route
"$KPY" tools/route_prep.py
java -jar "$FR_JAR" -de "$DIR/$PRJ.dsn" -do "$DIR/$PRJ.ses" -mp 100 -l en --gui.enabled=false > "$DIR/freerouting.log" 2>&1
grep -o "Auto-routing stage completed.*violations)" "$DIR/freerouting.log" || true
rm -rf en "$DIR/en"   # log folder left behind by Freerouting
"$KPY" tools/route_finish.py import
python3 tools/route_rules.py check
for i in 1 2 3 4 5 6 7 8 9 10; do
  "$KC" pcb drc --schematic-parity --severity-all --format json -o "$DIR/drc.json" "$DIR/$PRJ.kicad_pcb" > /dev/null
  "$KPY" tools/route_finish.py fix 2>&1 | grep -E "completed|ground link|removed|FAILED" | tee fix.log
  grep -q "removed 0 " fix.log && ! grep -q "completed\|ground link" fix.log && break
done
rm -f fix.log
"$KC" pcb drc --schematic-parity --severity-all --format json -o "$DIR/drc.json" "$DIR/$PRJ.kicad_pcb"
"$KC" pcb drc --schematic-parity --severity-all -o "$DIR/drc.rpt" "$DIR/$PRJ.kicad_pcb"
