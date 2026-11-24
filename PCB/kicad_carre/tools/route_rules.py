"""Write the routing design rules and net classes into the .kicad_pro file.

Usage: route_rules.py [route|check]
  route : clearances given to the autorouter (0.127 mm)
  check : clearances checked by DRC afterwards (0.11 mm). The autorouter rounds
          some gaps down to about 0.115 mm; checking at 0.127 would flag them
          although they are above the manufacturing limit (0.1 mm)."""
import json
import os
import sys
import design

MODE = sys.argv[1] if len(sys.argv) > 1 else "route"
CLR = 0.127 if MODE == "route" else 0.11

path = os.path.join(design.OUT_DIR, design.PROJECT + ".kicad_pro")
d = json.load(open(path))
d["board"]["design_settings"]["rules"].update(
    min_clearance=0.1, min_track_width=0.1, min_via_diameter=0.4,
    min_through_hole_diameter=0.2, min_via_annular_width=0.1,
    min_hole_clearance=0.2, min_copper_edge_clearance=0.3)
ns = d["net_settings"]
base = [c for c in ns["classes"] if c["name"] == "Default"][0]
base.update(clearance=CLR, track_width=0.127, via_diameter=0.4, via_drill=0.2)
power = dict(base, name="Power", track_width=0.25, priority=0)
rf = dict(base, name="RF", track_width=0.3, clearance=0.15, priority=1)
ns["classes"] = [base, power, rf]
ns["netclass_patterns"] = (
    [{"netclass": "Power", "pattern": n}
     for n in ["/VBAT", "/3V3", "/VBUS", "/VCHG", "/LX1", "/LX2", "/GND"]]
    + [{"netclass": "RF", "pattern": n} for n in ["/RF_LTE", "/RF_M1", "/RF_ANT"]])
json.dump(d, open(path, "w"), indent=2)
print("rules written (%s):" % MODE, path)
