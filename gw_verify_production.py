"""Apply gw_verify_results.py invariants to the PRODUCTION OMEGA result.

Add-on (new file; the production gate gw_verify_results.py is not edited).
Imports the gate so its fixture CASES run first and share one failure list,
then adds omega_core_v2_results.json as a production "certified" case.

Exit 0 only when BOTH the smoke fixtures AND the production N=800 row
satisfy every invariant.
"""
import json
import os
import sys

import mpmath as mp

import gw_verify_results as gv  # importing runs the fixture CASES (prints OK)

# float64 underflows bounds like 1e-2877 (and entry radii like 1e-5144) to
# 0.0, which would make "> 0" silently trivial -- parse with arbitrary
# precision instead so the sign check is meaningful at the real scale.
mp.mp.dps = 60

# Production result defaults to this script's own directory (a fresh clone
# works from any working directory); pass an explicit file path as argv[1].
PROD = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    "omega_core_v2_results.json")
if len(sys.argv) > 1:
    PROD = os.path.abspath(sys.argv[1])

rows = json.load(open(PROD, encoding="utf-8"))
gv.check(len(rows) == 1, "production: expected exactly 1 row")
r = rows[0]
tag = "[production N=800]"

for key in gv.REQUIRED:
    gv.check(key in r, "%s missing required key %r" % (tag, key))

gv.check(r["anomaly"] is False, "%s anomaly must be False" % tag)
gv.check(r["anomalies"] == [],
         "%s anomalies must be EMPTY, got %r" % (tag, r["anomalies"]))
gv.check("non_result_reason" not in r,
         "%s certified path must NOT carry non_result_reason" % tag)
gv.check(r["non_result"] is False, "%s non_result must be False" % tag)
gv.check(r["undetermined_pivot"] is None,
         "%s undetermined_pivot must be null" % tag)
gv.check(r["n_pos"] == r["dim"], "%s n_pos must equal dim" % tag)
gv.check(r["n_neg"] == 0, "%s n_neg must be 0" % tag)
gv.check(r["n_pos"] + r["n_neg"] == r["dim"],
         "%s every sign determined (n_pos + n_neg == dim)" % tag)
gv.check(r["lambda_min_lower_bound"] is not None,
         "%s lambda_min_lower_bound must be present" % tag)
gv.check(mp.mpf(r["lambda_min_lower_bound"]) > 0,
         "%s lambda_min_lower_bound must be > 0" % tag)
gv.check(r["symmetry_exact"] is True, "%s symmetry_exact must be True" % tag)
gv.check(r["symmetry_dev"] == "0",
         "%s symmetry_dev must be exactly '0', got %r"
         % (tag, r["symmetry_dev"]))
gv.check(r["caveats"] == [],
         "%s caveats must be EMPTY, got %r" % (tag, r["caveats"]))
gv.check(abs(mp.mpf(r["max_entry_radius"])) < mp.mpf("1e-50"),
         "%s max_entry_radius = %s exceeds 1e-50"
         % (tag, r["max_entry_radius"]))
gv.check(r["sha256"] and len(r["sha256"]) == 64,
         "%s sha256 must be a 64-hex digest" % tag)
gv.check(r.get("attempts") and r["attempts"][0].get("n_pos") is not None,
         "%s attempts record must carry the measured n_pos" % tag)

if gv.failures:
    print("\nFAILURES:")
    for f in gv.failures:
        print("  - " + f)
    sys.exit(1)

print("%s OK  n_pos=%s n_neg=%s bound=%s sha256=%s..."
      % (tag, r["n_pos"], r["n_neg"],
         r["lambda_min_lower_bound"], r["sha256"][:16]))
print("\nALL JSON INVARIANTS PASS (fixtures + production N=800)")
