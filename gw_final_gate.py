# -*- coding: utf-8 -*-
"""Final gate for the psi' identity: which side does the integral agree with?

Prior work (recorded here so this script is self-contained):

  * gw_panel_diag.py      head (GL224) is converged to <= 1.5e-137 by three
                          routes -- GL224 vs GL400, mp.quad on panel 0, and
                          per-panel movement -- and GL96's entire 3.35e-79
                          error was localised to panel 0.
  * gw_cfree_head.py      rewriting the head integrand in a cancellation-free
                          form moved it by only 3.59e-137 and left the
                          residual untouched: 3.391109217077509e-102 both ways.
  * gw_closed_third.py    closed_dpsi rebuilt from its defining series differs
                          from gw_deep_v2.closed_dpsi by EXACTLY
                          3.391109217077509e-102, and the only piece that
                          fails its own series check is mp.lerchphi(z,2,an).

Two hypotheses remain and they make opposite predictions:

  H_mpmath : the integral agrees with gw_deep_v2.closed_dpsi; the series
             reconstruction is wrong, so the residual lives in E1/E2/head.
  H_series : the integral agrees with the series reconstruction; mpmath's
             lerchphi(z,2,an) is the faulty piece.

This script computes the integral at full working precision and compares it
against BOTH sides.  It also sweeps mp.lerchphi over increasing dps: a piece
that is merely inaccurate converges with dps, one that is biased does not.

Read-only with respect to every other file; writes nothing but stdout.

usage: python gw_final_gate.py <c> <N> <dps> <R_cut> <order>
example: python gw_final_gate.py 100 40 160 1000 224
"""
import sys
import time

import mpmath as mp

import gw_arch_check as GA
import gw_deep_v2 as D
import gw_closed_third as T3
import gw_tail_deep as TD

JMAX = 46


def pieces_z(z, an, dps, TOL):
    """Defining-series values of the closed_dpsi ingredients."""
    T3.TOL = TOL
    F, kF = T3.series_F(z, an)
    L2, kL2 = T3.series_lerch(z, 2, an)
    H, kH = T3.series_F(z, mp.mpf(1) / 4)
    return dict(F=F, L2=L2, H=H, kF=kF, kL2=kL2, kH=kH)


def closed_from(pieces, psi_an, psi1_an, psi_q, n, L):
    """closed_dpsi assembled from caller-supplied ingredients (exact copy of
    gw_deep_v2.closed_dpsi's arithmetic, so only the inputs vary)."""
    z = mp.e ** (-2 * L)
    an = mp.mpf(1) / 4 + mp.pi * 1j * n / L
    F, L2, H = pieces["F"], pieces["L2"], pieces["H"]
    t1 = -L * mp.e ** (-L / 2) * mp.im((2 * L / (4 * mp.pi * n - 1j * L)) * F)
    t2 = -(mp.e ** (-L / 2) / 4) * mp.re(L2)
    t3 = mp.mpf(1) / 4 * mp.re(psi1_an)
    beta = (t1 + t2 + t3) / L
    gamma = (-mp.e ** (-L / 2) * mp.re((2 * L / (L + 4 * mp.pi * 1j * n)) * F)
             + 2 * mp.e ** (-L / 2) * H
             - mp.mpf(1) / 2 * (mp.re(psi_an) - psi_q)
             + (mp.mpf(1) / 2 * mp.log((mp.e ** (L / 2) - 1) / (mp.e ** (L / 2) + 1))
                + mp.atan(mp.e ** (L / 2)) - mp.pi / 4 + mp.euler / 2
                + mp.mpf(1) / 2 * mp.log(8 * mp.pi)))
    return -2 * (gamma - beta)


def main(argv):
    c = int(argv[1])
    N = int(argv[2])
    dps = int(argv[3])
    R_cut = mp.mpf(argv[4])
    order = int(argv[5])

    mp.mp.dps = dps
    T3.TOL = mp.mpf(10) ** (-(dps + 10))

    L = mp.log(c)
    T = 2 * mp.pi / L
    rho = T
    K = int(mp.floor(R_cut / T))
    R_head = K * T
    d = rho * N
    g, gk = TD.make_g('dpsi', d)
    pref = rho / mp.pi ** 2
    z = mp.e ** (-2 * L)
    an = mp.mpf(1) / 4 + mp.pi * 1j * N / L

    print("=" * 100)
    print("# FINAL GATE (psi'): integral vs mpmath closed  vs  series closed")
    print("# c = %d, N = %d, dps = %d, R = %s, K = %d, order = %d"
          % (c, N, dps, mp.nstr(R_cut, 6), K, order))
    print("# lambda_min target = 1.32105051975e-102 ; gate requires residual < that")
    print("=" * 100, flush=True)

    # ---- full-precision head ------------------------------------------------
    x, w = mp.gauss_quadrature(order, "legendre")
    t0 = time.time()
    head = mp.mpf(0)
    for k in range(K):
        a, b = k * T, (k + 1) * T
        half, mid = (b - a) / 2, (b + a) / 2
        acc = mp.mpf(0)
        for xi, wi in zip(x, w):
            r = mid + half * xi
            acc += wi * half * GA.hplus(r) * (1 - mp.cos(L * r)) * g(r)
        head += acc
    print("  head at order %d : %.1f s,  full precision = %s"
          % (order, time.time() - t0, mp.nstr(head, dps // 4)), flush=True)

    # ---- integral ----------------------------------------------------------
    E1 = GA.tail_E1(R_head, g, dps)
    E2, last, n_terms, turned = TD.E2_deep(g, gk, L, R_head, JMAX)
    integral = pref * (head + E1 - E2)
    print("  E1 = %s" % mp.nstr(E1, 40))
    print("  E2 = %s (last %s, %d terms, turned=%s)"
          % (mp.nstr(E2, 40), mp.nstr(last, 8), n_terms, turned))
    print("  integral = pref*(head + E1 - E2) =", mp.nstr(integral, 60))

    # ---- the two candidate closed values -----------------------------------
    closed_mp = D.closed_dpsi(N, L)

    T3.TOL = mp.mpf(10) ** (-(dps + 10))
    pieces = pieces_z(z, an, dps, T3.TOL)
    psi_an, _ = T3.psi_ind(an, 400)
    psi1_an, _ = T3.psi1_ind(an, 400)
    psi_q = -mp.euler - mp.pi / 2 - 3 * mp.log(2)
    closed_sr = closed_from(pieces, psi_an, psi1_an, psi_q, N, L)

    print("")
    print("-" * 100)
    print("CLOSED VALUES")
    print("-" * 100)
    print("  gw_deep_v2.closed_dpsi (mpmath pieces) = %s" % mp.nstr(closed_mp, 60))
    print("  reconstructed from defining series      = %s" % mp.nstr(closed_sr, 60))
    print("  |mpmath - series|                       = %s" % mp.nstr(abs(closed_mp - closed_sr), 16))

    # ---- the decisive comparison ------------------------------------------
    print("")
    print("-" * 100)
    print("DECISIVE: |integral - closed|")
    print("-" * 100)
    d_mp = abs(integral - closed_mp)
    d_sr = abs(integral - closed_sr)
    print("  |integral - mpmath closed| = %s" % mp.nstr(d_mp, 16))
    print("  |integral - series closed| = %s" % mp.nstr(d_sr, 16))
    print("  the disputed residual      = 3.391109217077509e-102")
    print("  gate (lambda_min)          = 1.32105051975e-102")
    print("")
    if d_sr < d_mp:
        print("  VERDICT: the integral agrees with the SERIES reconstruction.")
        print("           gw_deep_v2.closed_dpsi is the outlier.")
    elif d_mp < d_sr:
        print("  VERDICT: the integral agrees with gw_deep_v2.closed_dpsi.")
        print("           the series reconstruction is the outlier.")
    else:
        print("  VERDICT: no separation.")

    # ---- isolate the lerchphi piece ---------------------------------------
    print("")
    print("-" * 100)
    print("lerchphi(z, 2, an): defining series  vs  mpmath, over increasing dps")
    print("-" * 100)
    # One reference at the working dps, kept for the chain-rule check below.
    L2_ref0, _ = T3.series_lerch(z, 2, an)
    # Inside the sweep the reference is recomputed at EACH dps.  Reusing one
    # reference computed at the starting dps would make the gap report OUR
    # truncation error instead of mpmath's.
    prev = None
    for dd in (dps, int(dps * 1.4), int(dps * 1.8), int(dps * 2.4)):
        mp.mp.dps = dd
        T3.TOL = mp.mpf(10) ** (-(dd + 10))
        ref_dd, nref = T3.series_lerch(z, 2, an)
        v = mp.lerchphi(z, 2, an)
        dref = v - ref_dd
        dy = abs(v - prev) if prev is not None else mp.mpf(0)
        prev = v
        print("  dps %4d : series terms = %-3d |mp - series| = %-22s Re = %-24s Im = %-24s dy(prev) = %s"
              % (dd, nref, mp.nstr(abs(dref), 12), mp.nstr(mp.re(dref), 12),
                 mp.nstr(mp.im(dref), 12), mp.nstr(dy, 8)))

    # chain rule: closed depends on Re(L2) with coefficient -0.05/L
    mp.mp.dps = dps
    coef = -2 * (mp.mpf(1) / L) * (-mp.e ** (-L / 2) / 4)
    dL2 = mp.lerchphi(z, 2, an) - L2_ref0
    print("")
    print("  d(closed)/d(Re L2) = -2 * (1/L) * (-e^{-L/2}/4) = %s" % mp.nstr(coef, 16))
    print("  predicted |d closed| from the lerchphi gap = %s"
          % mp.nstr(abs(coef) * abs(mp.re(dL2)), 16))
    print("  observed  |closed_mpmath - closed_series|  = %s" % mp.nstr(abs(closed_mp - closed_sr), 16))
    print("=" * 100)


if __name__ == "__main__":
    main(sys.argv)
