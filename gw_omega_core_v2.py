#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OMEGA-CORE Falsification Engine v2 -- arb-native LDL^T route.

WHY V2 EXISTS (v1 was too slow, and v1 was weaker)
-------------------------------------------------
v1 fed a mpmath-built matrix into flint.arb as DECIMAL TEXT and then called
arb_mat.eig for the FULL spectrum.  Two problems, both measured:

  (1) SPEED   arb_mat.eig on 801x801 @ 2851 bits ran 94 minutes without
              finishing and was killed by a shell timeout.  A full spectrum
              is O(n^3) with a large constant (deflation iterations).
  (2) RIGOUR  v1's arb radius covered FLINT rounding only; the mpmath origin
              of the digits was NOT enclosed.  That caveat was real.

v2 instead uses the source package's own route, source_arb_ldlt_certify.py:
  * build_arb_tau(c, N, prec)    builds every entry as a genuine Arb BALL
                                 with rigorous enclosure, computed in Arb
                                 (no mpmath decimal hand-off at all).
  * certified_inertia(A, DIM)    interval LDL^T / Sylvester: if every pivot
                                 ball is strictly signed, (n_pos, n_neg) is
                                 PROVED, not observed.

FALSIFICATION is answered directly by LDL^T, and far cheaper than eig:
  * "lambda_min negative"  <=>  n_neg > 0   (proved, not sampled)
  * "Im != 0"              <=>  real symmetric => real spectrum, a THEOREM.
                                v2 verifies exact symmetry so this anomaly is
                                structurally excluded and says so, rather than
                                pretending a numeric Im reading is a test.
  * "radius explosion"     <=>  reported as max entry radius and max pivot
                                radius, measured, never widened to look good.

ZERO-FUDGING: an undetermined pivot is reported as UNDETERMINED and the
precision is escalated and the run repeated.  Nothing is rounded away.

VERIFIED BOUND: besides the positivity certificate, v2 computes a rigorous
lower bound for lambda_min via min|d_i| / ||L^{-1}||_F^2, derived from
A = L D L^T:

    x^T A x = y^T D y  (y = L^T x)  >=  min(d) ||y||^2
                                          >=  min(d) * sigma_min(L)^2 ||x||^2
    sigma_min(L) = 1 / sigma_max(L^{-1}) >= 1 / ||L^{-1}||_F

    =>  lambda_min(A) >= min(d_i) / ||L^{-1}||_F^2   (rigorous, ball-safe)

L^{-1} is obtained from flint arb_mat.inv (interval), so the bound inherits
Arb rigor instead of floating point.

TOOL STATUS: python 3.14 + python-flint 0.9.0 (+ mpmath only for the source's
optional selftest).  lean / coqc / isabelle / dkcheck / z3 / gcc NOT RUN.
Automatic verified numerics, NOT proof-assistant verification; must never be
cited as the latter.

SCOPE: a measurement on one preprint's matrix (arXiv:2607.02828v3, which
disclaims RH, Weil-positivity, prime counting and factorisation).  Not the
Riemann Hypothesis.

usage:
    python gw_omega_core_v2.py                       # defaults: c=100, N 400 800
    python gw_omega_core_v2.py --c 100 --dims 400 800 --prec 9000
    python gw_omega_core_v2.py --dims 400 --prec 9000 --skip-bound
"""

import argparse
import hashlib
import json
import os
import sys
import time
import traceback

# The source module must be importable from its own directory.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flint import arb, arb_mat, ctx  # noqa: E402

import source_arb_ldlt_certify as src  # noqa: E402


_LOG_FH = None
_HEARTBEAT = None


def ckpt(msg):
    """Print AND append to the run log file.

    The previous run wrote only through a PowerShell `Tee-Object` pipe.  When
    the harness dropped the shell record the pipe died with it, python's
    stdout broke, and ZERO recoverable evidence was left.  A file the process
    owns cannot be taken away by the harness.
    """
    print(msg, flush=True)
    if _LOG_FH is not None:
        _LOG_FH.write(msg + "\n")
        _LOG_FH.flush()


def heartbeat(stage, **kw):
    """Drop a liveness marker for an external watchdog.

    build_arb_tau is silent for hours, so log silence alone cannot distinguish
    "still building" from "dead".  This file can.
    """
    if not _HEARTBEAT:
        return
    data = {"ts": time.strftime("%Y-%m-%d %H:%M:%S"), "pid": os.getpid(),
            "stage": stage}
    data.update(kw)
    try:
        with open(_HEARTBEAT, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, default=str)
    except OSError:
        pass


def peak_mb():
    try:
        import ctypes

        class PMC(ctypes.Structure):
            _fields_ = [
                ("cb", ctypes.c_uint32),
                ("PageFaultCount", ctypes.c_uint32),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        pmc = PMC()
        pmc.cb = ctypes.sizeof(PMC)
        ok = ctypes.windll.psapi.GetProcessMemoryInfo(
            ctypes.windll.kernel32.GetCurrentProcess(), ctypes.byref(pmc), pmc.cb)
        if ok and pmc.PeakWorkingSetSize:
            return pmc.PeakWorkingSetSize / 1e6
    except Exception:
        pass
    try:
        import psutil
        return psutil.Process().memory_info().peak_wset / 1e6
    except Exception:
        return float("nan")


def max_entry_radius(A, DIM):
    """Widest enclosure radius over every entry -- a rigor signal, never widened."""
    best = arb(0)
    at = (0, 0)
    for i in range(DIM):
        for j in range(DIM):
            r = A[i, j].rad()
            if r > best:
                best, at = r, (i, j)
    return best, at


def symmetry_check(A, DIM):
    """Decide whether A is symmetric AS AN INTERVAL MATRIX.

    Returns (is_symmetric, worst_dev, at).

    The predicate is MUTUAL CONTAINMENT: for every pair (i, j) the two entries
    must enclose the SAME set of reals.  That is precisely what the real-spectrum
    theorem requires -- the certified LDL^T factorises one representative of the
    uncertainty box, so every matrix inside that box must be symmetric.

    Why NOT |A[i,j] - A[j,i]| == 0: interval arithmetic has no dependency
    tracking, so x - x for a ball of radius r is [0 +/- 2r], never 0.  Measuring
    the deviation that way reported a spurious ASYMMETRY of ~1.03e-2697 -- which
    is exactly the entry radius -- on a matrix that build_arb_tau makes symmetric
    by construction (it assigns the same `val` to both slots).  A falsification
    engine must never manufacture its own signal.

    (Also: python-flint 0.9.0 arb `==` returns False even for a ball compared
    with itself when the radius is nonzero, so `==` cannot test identity here.)
    """
    worst = arb(0)
    at = None
    for i in range(DIM):
        for j in range(i + 1, DIM):
            a, b = A[i, j], A[j, i]
            if a.contains(b) and b.contains(a):
                continue
            if at is None:
                at = (i, j)
            d = (a - b).abs_upper()
            if d > worst:
                worst = d
    return at is None, worst, at


def certified_ldlt_with_L(A, DIM, heartbeat=50):
    """Interval LDL^T returning L, d, counts and transcript.

    Same algorithm as source_arb_ldlt_certify.certified_inertia, but also
    materialises L and d so a rigorous lambda_min lower bound can be formed.
    """
    d = [None] * DIM
    Lf = [[arb(0)] * DIM for _ in range(DIM)]
    n_pos = 0
    n_neg = 0
    transcript = []
    max_pivot_rad = arb(0)
    t0 = time.time()
    for i in range(DIM):
        s = A[i, i]
        for k in range(i):
            s = s - Lf[i][k] * Lf[i][k] * d[k]
        d[i] = s
        # L is UNIT lower triangular: its diagonal is 1.  The source's
        # certified_inertia never stores it (the recurrence only ever reads
        # Lf[i][k] for k<i and writes Lf[j][i] for j>i, so it cannot tell),
        # but materialising L with a zero diagonal makes arb_mat.inv() report
        # "matrix is singular" and cost us the whole lambda_min bound.
        Lf[i][i] = arb(1)
        r = s.rad()
        if r > max_pivot_rad:
            max_pivot_rad = r
        if s > 0:
            n_pos += 1
            sign = "+"
        elif s < 0:
            n_neg += 1
            sign = "-"
        else:
            transcript.append("%d ? %s %s" % (i, s.mid().str(40, radius=False),
                                              s.rad().str(10, radius=False)))
            return dict(n_pos=n_pos, n_neg=n_neg, undetermined=i,
                        transcript=transcript, L=Lf, d=d,
                        max_pivot_rad=max_pivot_rad, elapsed=time.time() - t0)
        transcript.append("%d %s %s %s" % (i, sign, s.mid().str(40, radius=False),
                                           s.rad().str(10, radius=False)))
        for j in range(i + 1, DIM):
            t = A[j, i]
            for k in range(i):
                t = t - Lf[j][k] * Lf[i][k] * d[k]
            Lf[j][i] = t / d[i]
        if heartbeat and (i + 1) % heartbeat == 0:
            el = time.time() - t0
            eta = el / (i + 1) * (DIM - i - 1)
            ckpt("  [ldlt] pivot %d/%d  elapsed=%.0fs  eta=%.0fs"
                 % (i + 1, DIM, el, eta))
    return dict(n_pos=n_pos, n_neg=n_neg, undetermined=None,
                transcript=transcript, L=Lf, d=d,
                max_pivot_rad=max_pivot_rad, elapsed=time.time() - t0)


def lambda_min_lower_bound(res, DIM):
    """Rigorous lambda_min >= min|d_i| / ||L^{-1}||_F^2.

    Returns (bound, detail) or (None, reason) when the hypothesis
    ||L^{-1}||_F < infinity cannot be formed safely.
    """
    Lm = arb_mat(DIM, DIM)
    for i in range(DIM):
        for j in range(DIM):
            Lm[i, j] = res["L"][i][j]
    try:
        Linv = Lm.inv()
    except Exception as exc:
        return None, "L.inv() failed: %s" % exc

    # rigorous Frobenius norm upper bound: sum of |entry| upper bounds^2
    acc = arb(0)
    for i in range(DIM):
        for j in range(DIM):
            e = Linv[i, j]
            ub = e.abs_upper()
            acc = acc + ub * ub
    nrm_f = acc.sqrt()
    if not nrm_f.contains(arb(0)) and nrm_f > 0:
        pass
    else:
        return None, "||L^-1||_F not strictly positive"

    min_abs_d = None
    min_d_sign = None
    for i in range(DIM):
        di = res["d"][i]
        # abs_lower() is a proved lower bound on |d_i|; on a ball containing 0
        # it returns 0, so the bound degrades instead of overclaiming.
        a = di.abs_lower()
        if min_abs_d is None or a < min_abs_d:
            min_abs_d = a
            min_d_sign = "+" if di > 0 else "-"

    bound = min_abs_d / (nrm_f * nrm_f)
    detail = {
        "min_abs_pivot": min_abs_d.str(25, radius=False),
        "pivot_sign": min_d_sign,
        "norm_Linv_F_upper": nrm_f.str(25, radius=False),
    }
    return bound, detail


def sha256_of(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True,
                                     default=str).encode()).hexdigest()


def run_target(c, N, prec, do_bound=True, max_prec_escalations=3, out_path=None):
    """One (c, N) falsification attempt with dynamic precision scaling."""
    dim = 2 * N + 1
    ckpt("")
    ckpt("=" * 96)
    ckpt("TARGET c=%d N=%d  dim=%d x %d  starting prec=%d bits" % (c, N, dim, dim, prec))
    ckpt("=" * 96)

    attempts = []
    cur = prec
    for attempt in range(1, max_prec_escalations + 2):
        ctx.prec = cur
        ckpt("\n--- attempt %d : prec = %d bits (~%d digits) ---"
             % (attempt, cur, cur // 3))

        heartbeat("build_arb_tau:start", c=c, N=N, prec=cur, attempt=attempt)
        t0 = time.time()
        A, DIM = src.build_arb_tau(c, N, cur)
        t_build = time.time() - t0
        ckpt("  build_arb_tau      : %.1f s" % t_build)
        heartbeat("build_arb_tau:done", c=c, N=N, prec=cur, attempt=attempt,
                  build_s=round(t_build, 1))

        rad, rad_at = max_entry_radius(A, DIM)
        ckpt("  max entry radius   : %s  at %s"
             % (rad.str(14, radius=False), str(rad_at)))

        # Symmetry is a SIDE-CONDITION. It must never be able to discard a
        # finished multi-hour build: N=400's build completed successfully and
        # was thrown away because an untested .abs() raised HERE, before any
        # certification had run. sym_ok = None means "not verified", which is
        # neither a pass nor a falsification signal.
        try:
            sym_ok, sym_dev, sym_at = symmetry_check(A, DIM)
            ckpt("  symmetry (mutual containment) : %s  at %s -> %s"
                 % (sym_dev.str(14, radius=False), str(sym_at),
                    "SYMMETRIC (spectrum provably real)" if sym_ok
                    else "NOT SYMMETRIC"))
        except Exception as exc:
            sym_dev, sym_at, sym_ok = None, None, None
            ckpt("  symmetry : CHECK FAILED %r -- NOT VERIFIED "
                 "(continuing: the build is too expensive to discard)" % exc)
        # A single guarded string: sym_dev is None when the check failed, and
        # "NOT VERIFIED" must never be printed as if it were a measured value.
        sym_dev_str = (sym_dev.str(25, radius=False) if sym_dev is not None
                       else "NOT VERIFIED")

        heartbeat("certified_ldlt:start", c=c, N=N, prec=cur, attempt=attempt)
        res = certified_ldlt_with_L(A, DIM, heartbeat=max(1, DIM // 8))
        ckpt("  certified_inertia  : %.1f s" % res["elapsed"])
        ckpt("  n_pos=%d  n_neg=%d  undetermined_pivot=%s  max_pivot_rad=%s"
             % (res["n_pos"], res["n_neg"], res["undetermined"],
                res["max_pivot_rad"].str(14, radius=False)))
        heartbeat("certified_ldlt:done", c=c, N=N, prec=cur, attempt=attempt,
                  n_pos=res["n_pos"], n_neg=res["n_neg"],
                  undetermined=res["undetermined"])

        # Save the inertia certificate BEFORE the lambda_min bound.  The bound
        # runs flint arb_mat.inv, which is the heaviest and most interruptible
        # step; losing a finished certificate to it would waste hours.
        if out_path:
            partial = {"c": c, "N": N, "dim": dim, "prec": cur,
                       "n_pos": res["n_pos"], "n_neg": res["n_neg"],
                       "undetermined_pivot": res["undetermined"],
                       "stage": "inertia_certified",
                       "max_pivot_radius": res["max_pivot_rad"].str(25, radius=False),
                       "max_entry_radius": rad.str(25, radius=False),
                       "symmetry_dev": sym_dev_str,
                       "symmetry_exact": (bool(sym_ok) if sym_ok is not None
                                          else None)}
            partial["sha256"] = sha256_of(partial)
            try:
                with open(out_path, "w", encoding="utf-8") as fh:
                    json.dump([partial], fh, indent=2, default=str)
            except OSError as exc:
                ckpt("  (partial save failed: %r)" % exc)

        attempts.append({
            "attempt": attempt, "prec": cur, "build_s": round(t_build, 1),
            "ldlt_s": round(res["elapsed"], 1), "n_pos": res["n_pos"],
            "n_neg": res["n_neg"], "undetermined_pivot": res["undetermined"],
            "max_entry_radius": rad.str(20, radius=False),
            "max_pivot_radius": res["max_pivot_rad"].str(20, radius=False),
        })

        # ---- falsification checks -------------------------------------
        # These three are properties OF THE MATRIX. A tool failure (sym_ok is
        # None) is NOT an anomaly -- it means a question went unanswered, and
        # must never be reported as a falsification signal.
        anomalies = []
        caveats = []
        if res["n_neg"] > 0:
            anomalies.append("NEGATIVE EIGENVALUE CERTIFIED: n_neg=%d (n_pos=%d)"
                             % (res["n_neg"], res["n_pos"]))
        if sym_ok is False:
            anomalies.append("ASYMMETRIC: max|A-A^T| upper bound = %s "
                             "(real-symmetry theorem no longer excludes Im != 0)"
                             % sym_dev_str)
        elif sym_ok is None:
            caveats.append("SYMMETRY NOT VERIFIED -- the Im!=0 question is "
                           "UNANSWERED for this target, not exonerated")
        if rad > arb("1e-50"):
            anomalies.append("RADIUS EXPLOSION: max entry radius %s > 1e-50"
                             % rad.str(14, radius=False))

        if res["undetermined"] is None:
            # certified -- form the verified bound
            bound, bdetail = (None, "skipped")
            if do_bound:
                tb = time.time()
                bound, bdetail = lambda_min_lower_bound(res, DIM)
                ckpt("  lambda_min >= %s   (%.1f s)"
                     % (bound.str(25, radius=False) if bound is not None else bdetail,
                        time.time() - tb))
            result = {
                "c": c, "N": N, "dim": dim, "prec": cur,
                "attempts": attempts,
                "n_pos": res["n_pos"], "n_neg": res["n_neg"],
                "undetermined_pivot": None,
                "max_entry_radius": rad.str(25, radius=False),
                "max_pivot_radius": res["max_pivot_rad"].str(25, radius=False),
                "symmetry_dev": sym_dev_str,
                "symmetry_exact": (bool(sym_ok) if sym_ok is not None else None),
                "lambda_min_lower_bound": (bound.str(30, radius=False)
                                           if bound is not None else None),
                "bound_detail": bdetail if isinstance(bdetail, dict) else str(bdetail),
                "anomalies": anomalies,
                "caveats": caveats,
                "anomaly": bool(anomalies),
                "non_result": False,
                "peak_mb": peak_mb(),
                "transcript_head": res["transcript"][:3],
                "transcript_tail": res["transcript"][-3:],
            }
            result["sha256"] = sha256_of(result)
            return result

        # undetermined pivot -> escalate precision (never fudge)
        ckpt("  UNDETERMINED pivot at index %d -> escalating precision" % res["undetermined"])
        if attempt > max_prec_escalations:
            break
        cur = int(cur * 2)

    # all escalations exhausted
    result = {
        "c": c, "N": N, "dim": dim, "prec": cur,
        "attempts": attempts,
        "n_pos": res["n_pos"], "n_neg": res["n_neg"],
        "undetermined_pivot": res["undetermined"],
        "max_entry_radius": rad.str(25, radius=False),
        "max_pivot_radius": res["max_pivot_rad"].str(25, radius=False),
        "symmetry_dev": sym_dev_str,
        "symmetry_exact": (bool(sym_ok) if sym_ok is not None else None),
        "caveats": caveats,
        "lambda_min_lower_bound": None,
        "bound_detail": "not formed: LDL^T unresolved",
        # A certified negative eigenvalue MUST still halt the sweep from here.
        # This used to be a hardcoded False with `anomalies` overwritten by the
        # undetermined message, which silently swallowed a real falsification
        # signal whenever a negative pivot preceded an undetermined one -- the
        # worst failure mode a falsification engine can have.  `anomalies` is
        # re-initialised every attempt, so it holds only this attempt's true
        # signals; `undetermined` is reported separately, as a non-result.
        "anomalies": anomalies,
        "anomaly": bool(anomalies),
        "non_result_reason": ("UNDETERMINED after precision escalation "
                              "to %d bits" % cur),
        "non_result": True,
        "peak_mb": peak_mb(),
    }
    result["sha256"] = sha256_of(result)
    return result


def main():
    ap = argparse.ArgumentParser(description="OMEGA-CORE Falsification Engine v2")
    ap.add_argument("--c", type=int, default=100)
    ap.add_argument("--dims", type=int, nargs="+", default=[400, 800])
    ap.add_argument("--prec", type=int, default=9000,
                    help="starting arb precision in bits (default 9000)")
    ap.add_argument("--escalations", type=int, default=3,
                    help="max precision doublings on undetermined pivot")
    ap.add_argument("--skip-bound", action="store_true",
                    help="skip the lambda_min lower bound (faster)")
    ap.add_argument("--out", type=str, default="omega_core_v2_results.json")
    ap.add_argument("--log", type=str, default=None,
                    help="append run log to this file (process-owned, "
                         "survives harness shell teardown)")
    ap.add_argument("--heartbeat", type=str, default=None,
                    help="liveness marker file for an external watchdog")
    args = ap.parse_args()

    global _LOG_FH, _HEARTBEAT
    _HEARTBEAT = args.heartbeat
    if args.log:
        _LOG_FH = open(args.log, "a", encoding="utf-8")

    ckpt("#" * 96)
    ckpt("# OMEGA-CORE Falsification Engine v2  (arb-native LDL^T route)")
    ckpt("# c=%d  dims=%s  start_prec=%d  escalations=%d  bound=%s"
         % (args.c, args.dims, args.prec, args.escalations,
            "off" if args.skip_bound else "on"))
    ckpt("#" * 96)
    ckpt("")
    ckpt("CAVEAT that must travel with every number below:")
    ckpt("  Entries are Arb balls built natively by build_arb_tau (source")
    ckpt("  package, SHA-256 b7fee730...1509e3) -- enclosure covers FLINT")
    ckpt("  rigorously; there is NO mpmath decimal hand-off in this route.")
    ckpt("  Inertia is PROVED by interval LDL^T (Sylvester), not sampled.")
    ckpt("  The lambda_min bound is a derived rigorous inequality; the")
    ckpt("  original positivity certificate does not depend on it.")
    ckpt("  TOOL STATUS: python 3.14 + python-flint 0.9.0.")
    ckpt("  lean/coqc/isabelle/dkcheck/z3/gcc NOT RUN -> NOT proof-assistant")
    ckpt("  verified.  Not RH, not Weil-positivity, not prime counting.")
    ckpt("")

    results = []
    heartbeat("sweep:start", dims=args.dims, prec=args.prec)
    for N in args.dims:
        try:
            r = run_target(args.c, N, args.prec,
                           do_bound=not args.skip_bound,
                           max_prec_escalations=args.escalations,
                           out_path=args.out)
        except KeyboardInterrupt:
            ckpt("\n*** INTERRUPTED at N=%d -- saving what is proven so far ***" % N)
            r = {"c": args.c, "N": N, "error": "KeyboardInterrupt",
                 "anomaly": False, "non_result": True}
            results.append(r)
            with open(args.out, "w", encoding="utf-8") as fh:
                json.dump(results, fh, indent=2, default=str)
            break
        except Exception as exc:
            ckpt("\n*** EXCEPTION at N=%d: %r ***" % (N, exc))
            traceback.print_exc()
            r = {"c": args.c, "N": N, "error": repr(exc), "anomaly": False,
                 "non_result": True}
        results.append(r)

        # incremental save so a kill cannot lose finished targets
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(results, fh, indent=2, default=str)
        heartbeat("sweep:target_done", N=N, verdict=describe(r))

        ckpt("\n" + "-" * 96)
        ckpt("VERDICT N=%d : %s" % (N, describe(r)))
        ckpt("-" * 96)

        if r.get("anomaly"):
            ckpt("*** ANOMALY CONFIRMED at N=%d -- halting sweep ***" % N)
            break

    ckpt("\n" + "=" * 96)
    ckpt("SUMMARY")
    ckpt("=" * 96)
    ckpt("%-7s %-8s %-8s %-6s %-14s %-14s %s"
         % ("N", "dim", "prec", "n_neg", "max_entry_rad", "lam_min_bound", "verdict"))
    ckpt("-" * 96)
    for r in results:
        ckpt("%-7s %-8s %-8s %-6s %-14s %-14s %s"
             % (r.get("N"), r.get("dim"), r.get("prec"),
                r.get("n_neg", "-"),
                str(r.get("max_entry_radius", "-"))[:14],
                str(r.get("lambda_min_lower_bound", "-"))[:14],
                describe(r)))
    ckpt("-" * 96)
    ckpt("Results -> %s" % os.path.abspath(args.out))
    heartbeat("sweep:complete", results=len(results))
    if _LOG_FH is not None:
        _LOG_FH.close()


def describe(r):
    if r.get("error"):
        return "ERROR: %s" % r["error"]
    if r.get("non_result"):
        return "NOT DETERMINED (precision escalation exhausted)"
    if r.get("anomaly"):
        return "FALSIFICATION SIGNAL: " + "; ".join(r["anomalies"])
    if r.get("n_neg") == 0 and r.get("undetermined_pivot") is None:
        return ("VERIFIED POSITIVE DEFINITE  (n+=%d, n-=0, %d/%d certified)"
                % (r["n_pos"], r["n_pos"], r["dim"]))
    return "INCONCLUSIVE"


if __name__ == "__main__":
    main()
