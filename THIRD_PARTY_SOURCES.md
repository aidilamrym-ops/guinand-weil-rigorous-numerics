# Third-Party Sources

Files in this repository that were not written by the OMEGA authors, together
with the licence under which they are redistributed.

---

## 1. `source_arb_ldlt_certify.py`

| field | value |
|---|---|
| origin | `https://github.com/akivag613/connes-cvs-` |
| path | `papers/2_guinand_weil_dictionary_tail_order/scripts/arb_ldlt_certify.py` |
| retrieved | 2026-09-27 |
| size | 12256 bytes |
| SHA-256 | `b7fee730a83baedc860ca456547d2799ec10894a79edecc6d5612931b41509e3` |
| licence | MIT — `Copyright (c) 2026 Akiva Groskin` |
| used by | `gw_opt_a_diff.py` (Option (a) entrywise matrix diff) |

### Why this file is stored verbatim

The SHA-256 above is **byte-identical** to the `script_sha256` field recorded in
the upstream provenance file
`artifacts/c100_N200_arb_ldlt_prec9000_provenance.json`, which also records
`n_pos = 401`, `n_neg = 0`, `dimension = 401`, `prec_bits = 9000`,
`c = 100`, `N = 200`, `package_commit = 8ce0fc791ed9c9ca6f4ba512322720b4be80421b`.

Storing the file byte-for-byte is therefore part of the *evidence*: it makes
reproduction of the diff in `gw_opt_a_diff.py` a check against the exact code
that produced the published certificate, rather than against an approximation
of it. Re-typing the formulas by hand would have destroyed that link.

### MIT licence text (as distributed with the source package)

```
MIT License

Copyright (c) 2026 Akiva Groskin

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## Scope statement

`source_arb_ldlt_certify.py` is vendored for **comparison only**. No claim in
this repository is derived from running its `certified_inertia()` path; the
inertias reported here were produced by `flint.arb_mat.eig` in
`gw_corrected_eig.py` and `gw_opt_b_arb.py`.

Nothing in this repository establishes the Riemann Hypothesis, Weil
positivity, a prime-counting result, or a factorisation method. The upstream
preprint disclaims all four.

---

## 2. Runtime third-party dependencies (not vendored, not modified)

These are consumed from the interpreter environment. No file from them is
copied into this repository, and none of their code was edited.

| component | version | role in the verification chain |
|---|---|---|
| CPython | 3.14.4 (`C:\Python314\python.exe`) | interpreter; `py_compile` sweep |
| NumPy | 2.5.2 | `eigvalsh`, the pair-difference histogram in `r2_curve` |
| SciPy | present (`scipy.stats.norm`) | the Gaussian CDF inside `unfold()` |
| mpmath | present | arbitrary-precision path |
| python-flint | 0.9.0 | `arb_mat.eig` certified inertia path |

**Tool status:** `python 3.14` + `numpy` + `scipy` were **RUN**.
`lean` / `coqc` / `isabelle` / `dkcheck` / `z3` / `gcc` were **NOT RUN** in the
session that produced the freeze.

### Provenance of first-party artifacts

SHA-256 for every verification script, run log and input file — including the
two *failed* diagnostic logs, which are retained so that the bugs behind them
stay auditable — is recorded in [`PROVENANCE.txt`](PROVENANCE.txt). Living
documents (`GW_STATUS_2026-09-26.md`, `state/STATE.md`,
`state/PROJECT_REGISTRY.json`) are deliberately excluded from that file because
they are edited as work proceeds; hash them at the moment of archiving instead.

Known residuals carried into the freeze are listed at the end of
`PROVENANCE.txt` (defect 18, the unexplained K5 row of `GW_STATUS` §h.3,
defect 19, and the repository-wide `py_compile` count of 853/856).
