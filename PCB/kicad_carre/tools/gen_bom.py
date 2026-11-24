"""Write ../../bom.csv from design.py (one line per distinct part)."""
import csv
import os
import re
import design

HERE = os.path.dirname(os.path.abspath(__file__))
groups = {}
for p in design.PARTS:
    if not p["fp"] or p["ref"].startswith("TP"):
        continue
    key = (p["value"], p["fp"], p["mpn"], p["dnp"])
    groups.setdefault(key, []).append(p["ref"])


def order(ref):
    m = re.match(r"([A-Z]+)(\d+)", ref)
    return (m.group(1), int(m.group(2)))


rows = sorted(groups.items(), key=lambda kv: order(kv[1][0]))
with open(os.path.join(HERE, "..", "..", "bom.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["Refs", "Qty", "Value", "MPN", "Footprint", "Mounted"])
    for (value, fp, mpn, dnp), refs in rows:
        refs.sort(key=order)
        w.writerow([" ".join(refs), len(refs), value, mpn, fp.split(":")[1], "no" if dnp else "yes"])
print("bom.csv written:", len(rows), "lines")
