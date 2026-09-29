# Repository Directory Schema

**Project:** OMEGA Framework — Certified Enclosure of Guinand–Weil Matrices at Extreme Scale
**Author:** Muhammad Aidil Amry · ORCID 0009-0002-9718-9710
**Affiliation:** Independent Researcher | South Sulawesi, Indonesia

Target repository: `omega-guinand-weil` (new GitHub repository, public).

Every path below maps to a file that **exists on disk today**. Nothing is
listed that has not been produced by an executed run.

```
omega-guinand-weil/
│
├── README.md                       # repository front page (generated)
├── WORKING_PAPER.md                # preprint draft (generated)
├── REPO_STRUCTURE.md               # this file
├── CITATION.cff                    # machine-readable citation metadata
├── LICENSE                         # MIT — source code
├── LICENSE-DOCS.md                 # CC-BY-4.0 — scholarly documents
├── LICENSING.md                    # the hybrid split, rationale, attribution
│
├── src/                            # 30 gw_*.py + 2 probe_*.py — ENGLISH, as executed
│   │
│   ├── core/                       # construction of Q_inf and its closed forms
│   │   ├── gw_qinf.py                # build_blocks. LINE 47 sets mp.mp.dps=40 at module
│   │   │                             #   level (LANDMINE). LINE 94 calls mp.lerchphi (defect).
│   │   ├── gw_full_vs_even.py        # full_matrix() — full vs even-sector assembly
│   │   ├── gw_v0_exact.py            # exact V0 / leading term
│   │   ├── gw_deep_v2.py             # closed_dpsi, closed_psi — the SHIPPED closed forms
│   │   └── gw_deep_v3.py             # lerchphi_series() — the CORRECTION
│   │
│   ├── gates/                      # identity validation: integral vs closed form
│   │   ├── gw_final_gate.py          # the psi / psi' gate; `python gw_final_gate.py c N dps R GL`
│   │   ├── gw_closed_third.py        # third closed-form cross-check
│   │   ├── gw_arch_check.py          # archimedean baseline sweep in R
│   │   ├── gw_arch_diag.py           # asymptotic diagnostics
│   │   ├── gw_head_diag.py           # head-region diagnostics
│   │   ├── gw_tail_deep.py           # tail via adaptive IBP
│   │   └── gw_panel_diag.py          # per-panel quadrature localisation
│   │
│   ├── eigenspectrum/              # eigenvalue routes and cross-checks
│   │   ├── gw_corrected_eig.py       # corrected build + phases 1-6 (incl. phase_arb)
│   │   ├── gw_compare_builds.py      # SHIPPED vs CORRECTED, same code path
│   │   ├── gw_lam_dps.py             # lambda_min vs dps precision ladder
│   │   ├── gw_det_check.py           # determinant route vs eigensy route
│   │   ├── gw_degeneracy.py          # exact zero eigenspace of the pole block
│   │   ├── gw_spectrum_detail.py     # full eigenvalue listing
│   │   ├── gw_c100_probe.py          # c=100 behaviour probe
│   │   └── gw_cfree_head.py          # c-free head formulation
│   │
│   ├── certified/                  # OMEGA A1 / A2 — ball arithmetic
│   │   ├── probe_flint_eig.py        # API audit: what flint 0.9.0 actually exposes
│   │   ├── probe_arb_rad.py          # API audit: attaching an explicit radius to an arb
│   │   ├── gw_arb_sweep.py           # uniform-radius sweep -> rho* via Weyl
│   │   ├── gw_arb_measured.py        # measured per-entry radii -> FLINT eigen-solver
│   │   ├── gw_entry_error.py         # dps-doubling entry-error measurement
│   │   ├── gw_entry_audit.py         # delta-versus-matrix audit, full -N..N scan
│   │   └── gw_lerchphi_regime.py     # defect regime map over dps
│   │
│   ├── ladder/                     # goal C — the c=13 ladder, fit-only
│   │   ├── gw_ladder_analysis.py
│   │   ├── gw_ladder_ext.py
│   │   └── gw_model_final.py
│   │
│   └── goals/                      # goals A, B, D, E
│       ├── gw_band.py                # goal D — B_T and the band [-B_T, 0)
│       ├── gw_worked_example.py      # goal E — second external anchor
│       └── gw_model_final.py         # (shared with ladder/)
│
├── data/                           # saved intermediate artefacts
│   ├── gw_matrix_100_40_dps180.json   # corrected 81x81 matrix, dps 180, 180-digit strings
│   └── README.md                     # provenance of every JSON: command that produced it
│
├── logs/
│   ├── GW_STATUS_2026-09-26.md       # CANONICAL status report
│   │                                   #   §7  eigen FINAL
│   │                                   #   §7a RETRACTED
│   │                                   #   §7b root-cause log
│   │                                   #   §7c OMEGA A1/A2 execution
│   ├── ladder_bn.txt                 # ladder raw output
│   ├── ladder_fix.txt                # ladder raw output
│   └── run/                          # captured stdout of every command cited in the paper
│
├── proofs/                         # INTENTIONALLY EMPTY — see TRACK_C.md
│   └── TRACK_C.md                    # Lean 4 / Z3 integration plan; STATUS: NOT STARTED
│
├── docs/
│   ├── EPISTEMIC_RULES.md            # the dy gate, the override, the floor test rejection
│   ├── RETRACTIONS.md                # all 8 retracted claims, kept not deleted
│   ├── API_AUDIT.md                  # flint 0.9.0 capability matrix
│   └── IDENTITY_DEPTHS.md            # psi / psi' residuals at every precision run
│
└── scripts/
    └── update_registry.py
```

## Inventory as executed

| category | count |
|---|---:|
| `gw_*.py` (canonical) | **30** |
| `probe_*.py` (API audits) | 2 |
| `ladder_*.txt` (raw logs) | 2 |
| status reports | 1 (`GW_STATUS_2026-09-26.md`, 37 kB) |
| JSON matrices in `data/` | 1 (`gw_matrix_100_40_dps180.json`) |

All 30 `gw_*.py` plus both probes pass `py_compile`. SHA256 of the working
copies matches the canonical copies byte-for-byte.

## What goes in `proofs/` and why it is empty

`TRACK_C.md` will document the Lean 4 / Z3 plan. **No proof assistant has been
run on any claim in this repository.** The directory is created empty rather
than omitted, so that an empty folder cannot be mistaken for a completed one.


---

## Postscript (2026-09-29) -- layout as actually published

The tree above was written against the original *nested* proposal. The
repository as published is **flat-root**: every file sits directly in the
repository root, with no `src/`, `data/`, `logs/`, `proofs/`, `docs/` or
`scripts/` directories. README path references were flattened to match
(commit `8ec0745`); this file is corrected here rather than rewritten, so the
original proposal stays auditable.

Consequently the sentence "Every path below maps to a file that exists on disk
today" no longer holds for the **directories** it names. The *files* it names
all exist, in the root. `proofs/` never existed as a directory at all -- the
statement that no proof assistant has been run still holds, and still applies.

### Files added 2026-09-29 (OMEGA-CORE chain)

| file | role |
|---|---|
| `OMEGA_CORE_CERTIFICATE.md` | matrix definition, zero-fudging architecture, the $N=400$ certificate, telemetry schema, byte-hash inventory |
| `gw_omega_core_v2.py` | the engine: interval $LDL^T$, auto-escalation, three anomaly gates |
| `gw_sysmon.ps1` | 60 s system telemetry + ALERT taxonomy (log-and-continue) |
| `gw_watchdog.py` | 60 s liveness watcher against the JSON heartbeat |
| `gw_launch_v2.ps1` | detached launcher |
| `gw_check_refs.py` | static reference gate (pre-run) |
| `gw_verify_results.py` | JSON invariant gate (post-run) |
| `omega_core_v2_results.json` | the $N=400$ certificate |
| `omega_core_v2_run.log` | forensic run log, VERDICT lines |
| `omega_v2_sysmon.log`, `omega_core_v2_watchdog.log`, `omega_core_v2_heartbeat.json` | telemetry snapshot |
| `*_FAILED_absbug_*` (5 files) | the failed run, kept as audit trail |
| `smoke*` (6 files) | both smoke gates, green |

`omega_v2_sysmon.log` and `omega_core_v2_watchdog.log` are **live logs**
snapshotted while the $N=800$ target was still running; their hashes describe
that instant, not a final state.