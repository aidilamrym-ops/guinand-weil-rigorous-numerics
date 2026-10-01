"""Assert the invariants of OMEGA-CORE result JSONs.

Run after every engine edit.  Reads the real files produced by the engine
and fails loudly on any invariant break, so a schema regression cannot pass
just because the summary table still printed something plausible.
"""
import json
import os
import sys

# Fixture paths default to this script's own directory, so a fresh clone runs
# from any working directory.  GW_FIXTURE_DIR overrides the default (an
# environment variable, not argv, because gw_verify_production.py imports this
# module and owns argv itself).
BASE = os.environ.get("GW_FIXTURE_DIR") or os.path.dirname(os.path.abspath(__file__))

CASES = [
    (os.path.join(BASE, "smoke_results.json"), "certified"),
    (os.path.join(BASE, "smoke_escalate.json"), "escalation_exhausted"),
]
REQUIRED = ["c", "N", "dim", "prec", "attempts", "n_pos", "n_neg",
            "max_entry_radius", "max_pivot_radius", "symmetry_dev",
            "symmetry_exact", "caveats", "lambda_min_lower_bound",
            "bound_detail", "anomalies", "anomaly", "non_result", "sha256"]

failures = []


def check(cond, msg):
    if not cond:
        failures.append(msg)


for path, kind in CASES:
    rows = json.load(open(path, encoding="utf-8"))
    check(len(rows) == 1, "%s: expected exactly 1 row" % kind)
    r = rows[0]
    tag = "[%s]" % kind

    for key in REQUIRED:
        check(key in r, "%s missing required key %r" % (tag, key))

    # The falsification signal must be a pure function of the measurements.
    check(r["anomaly"] is False, "%s anomaly must be False here" % tag)
    check(r["anomalies"] == [],
          "%s anomalies must be EMPTY, got %r" % (tag, r["anomalies"]))
    # Undetermined is a non-result, never a pass.
    if kind == "escalation_exhausted":
        check("non_result_reason" in r,
              "%s escalation path must carry non_result_reason" % tag)
        check(r["non_result"] is True,
              "%s escalation path must be non_result" % tag)
        check(r["undetermined_pivot"] is not None,
              "%s undetermined_pivot must be set" % tag)
        check(r["lambda_min_lower_bound"] is None,
              "%s no bound may be claimed without a completed LDL^T" % tag)
        check("UNDETERMINED" in r.get("non_result_reason", ""),
              "%s non_result_reason must name the undetermined pivot" % tag)
        check(r["n_neg"] == 0, "%s n_neg must be 0" % tag)
    else:
        check("non_result_reason" not in r,
              "%s certified path must NOT carry non_result_reason" % tag)
        check(r["non_result"] is False,
              "%s certified path must not be non_result" % tag)
        check(r["undetermined_pivot"] is None,
              "%s certified path must have no undetermined pivot" % tag)
        check(r["n_pos"] == r["dim"],
              "%s n_pos must equal dim" % tag)
        check(r["n_neg"] == 0, "%s n_neg must be 0" % tag)
        check(r["lambda_min_lower_bound"] is not None,
              "%s lambda_min_lower_bound must be present" % tag)
        check(float(r["lambda_min_lower_bound"]) > 0,
              "%s lambda_min_lower_bound must be > 0" % tag)
        check(r["symmetry_exact"] is True,
              "%s symmetry_exact must be True" % tag)
        check(r["symmetry_dev"] == "0",
              "%s symmetry_dev must be exactly '0', got %r"
              % (tag, r["symmetry_dev"]))
        check(r["caveats"] == [], "%s caveats must be empty" % tag)

    # The 1e-50 halt threshold applies to the MATRIX ENTRY radius -- it measures
    # how tightly build_arb_tau enclosed the closed forms, and the engine checks
    # exactly that.  It must NOT be applied to max_pivot_radius: d[i] naturally
    # has the scale of its own value (a pivot of size 1e10 with radius 1e-30 is
    # perfectly certified), and what the LDL^T certificate requires is a
    # DETERMINED SIGN, which n_pos + n_neg == dim already proves.  On the
    # exhausted path max_pivot_radius is the undetermined pivot itself, whose
    # radius necessarily swamps its midpoint -- that is why it was undetermined.
    if "max_entry_radius" in r and r["max_entry_radius"]:
        check(abs(float(r["max_entry_radius"])) < 1e-50,
              "%s max_entry_radius = %s exceeds 1e-50"
              % (tag, r["max_entry_radius"]))
    if kind == "certified":
        check(r["n_pos"] + r["n_neg"] == r["dim"],
              "%s n_pos + n_neg must equal dim (every sign determined)" % tag)
    check(r["sha256"] and len(r["sha256"]) == 64,
          "%s sha256 must be a 64-hex digest" % tag)
    print("%s OK  n_pos=%s n_neg=%s bound=%s sha256=%s..."
          % (tag, r["n_pos"], r["n_neg"],
             r["lambda_min_lower_bound"], r["sha256"][:16]))

if failures:
    print("\nFAILURES:")
    for f in failures:
        print("  -", f)
    sys.exit(1)
print("\nALL JSON INVARIANTS PASS")
