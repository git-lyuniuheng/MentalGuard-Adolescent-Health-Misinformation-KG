# -*- coding: utf-8 -*-
import json, os, sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
p = os.path.join(BASE, "data", "mentalguard_v2.0.json")
with open(p, encoding="utf-8") as f:
    d = json.load(f)

REQ = ["id","platform","rumor_text","truth_text","source","severity","keywords",
       "category","category_key","verified_sources","verification_status","source_tier"]
SEV = {"critical","high","medium","low"}
ids = []
missing = 0
bad_sev = 0
bad_vs = 0
for ck, co in d["categories"].items():
    for r in co["misconceptions"]:
        ids.append(r["id"])
        for fld in REQ:
            if fld not in r:
                missing += 1
                print("MISSING", r.get("id"), fld)
        if r.get("severity") not in SEV:
            bad_sev += 1
        if r.get("verification_status") not in ("verified","pending"):
            bad_vs += 1
        if not isinstance(r.get("verified_sources"), list) or len(r["verified_sources"]) < 1:
            print("BAD VS", r.get("id"))

print("total records:", d["meta"]["total_misconceptions"])
print("counted ids:", len(ids))
print("unique ids:", len(set(ids)))
print("duplicate ids:", len(ids) - len(set(ids)))
print("missing fields:", missing)
print("bad severity:", bad_sev)
print("bad verification_status:", bad_vs)
print("verified count:", sum(1 for ck,co in d["categories"].items() for r in co["misconceptions"] if r["verification_status"]=="verified"))
# severity distribution
from collections import Counter
c = Counter()
for ck,co in d["categories"].items():
    for r in co["misconceptions"]:
        c[r["severity"]] += 1
print("severity dist:", dict(c))
