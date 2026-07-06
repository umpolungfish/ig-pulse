"""
ig_pulse/oos.py

The out-of-sample honesty gate. Every in-sample check (headroom recalibration,
common-mode removal, over-dispersion vs null) can pass on structure that is
merely fit to one epoch. This gate splits the live stream temporally, fits
calibration on the EARLIER portion only, and asks what actually transfers to
the LATER, unseen portion.

Finding (2026-07): native-B TRANSFERS, the coupling structure does NOT.
  * internal over-dispersion is ~x3.4 in BOTH halves, self-calibrated -> the
    confluence (native B) is a stable, replicable statistical property.
  * full-matrix transfer ~+0.1, PC1 ~+0.27, residual both-sign forks ~-0.05 ->
    the adjacency matrix reshuffles between epochs. It is NON-STATIONARY.

Consequence: the broadcast fans (broadcast_coupling.py) are an epoch-local map
of the current contradiction pattern, not the "unchanging adjacency matrix /
edge invariants" the README claims. Native-B is invariant; the wiring is not.

Usage:  python -m ig_pulse.oos [frac]
"""
from __future__ import annotations
import json, re, collections, sys
from pathlib import Path
import numpy as np
from .dialetheia import PRIMS, glut_structure, confluence_test

_SEIS = re.compile(r"^seismic_([A-Z0-9]+)_[A-Z0-9]+$")
_PIDX = {p: i for i, p in enumerate(PRIMS)}
_IU = np.triu_indices(12, 1)
def _collapse(s):
    m = _SEIS.match(s); return f"seismic_net_{m.group(1)}" if m else s


def load_split(path, frac=0.60):
    """CDFs fit on the earlier `frac` of functioning snapshots, applied to all."""
    path = str(path)
    nfun = 0
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line: continue
            try: s = json.loads(line)
            except json.JSONDecodeError: continue
            if s.get("readings"): nfun += 1
    split = int(frac * nfun)

    valmap = collections.defaultdict(list); idx = 0
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line: continue
            try: s = json.loads(line)
            except json.JSONDecodeError: continue
            if not s.get("readings"): continue
            if idx < split:
                for r in s["readings"]:
                    pr, v = r.get("primitive"), r.get("value")
                    if pr in _PIDX and v is not None:
                        valmap[(_collapse(r.get("stream", "")), pr)].append(float(v))
            idx += 1
            if idx >= nfun: break
    sortmap = {k: np.array(sorted(v)) for k, v in valmap.items()}

    def se(key, v):
        a = sortmap.get(key)
        if a is None or not len(a): return 0.0
        lo = np.searchsorted(a, v, "left"); hi = np.searchsorted(a, v, "right")
        return 2.0 * (((lo + hi) / 2) / len(a) - 0.5)

    X = np.zeros((nfun, 12)); idx = 0
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line: continue
            try: s = json.loads(line)
            except json.JSONDecodeError: continue
            if not s.get("readings"): continue
            if idx >= nfun: break
            best = np.zeros(12)
            for r in s["readings"]:
                pr, v = r.get("primitive"), r.get("value")
                if pr not in _PIDX or v is None: continue
                e = se((_collapse(r.get("stream", "")), pr), float(v)); k = _PIDX[pr]
                if abs(e) > abs(best[k]): best[k] = e
            X[idx] = best; idx += 1
    return X[:split], X[split:nfun]


def _fullcorr(M):
    Z = (M - M.mean(0)) / (M.std(0) + 1e-12)
    return Z.T @ Z / len(Z)


def _internal_overdispersion(M):
    mag = np.abs(M)
    thr = np.array([np.quantile(mag[:, k], 0.70) for k in range(12)])
    A = ((mag >= thr) & (mag > 0)).astype(int)
    c = confluence_test(A, reps=300)
    return c["var_obs"] / c["var_null"]


def main(path, frac=0.60):
    Xtr, Xte = load_split(path, frac)
    gtr, gte = glut_structure(Xtr), glut_structure(Xte)
    A = np.corrcoef(_fullcorr(Xtr)[_IU], _fullcorr(Xte)[_IU])[0, 1]
    B = abs(np.corrcoef(gtr["pc1_loadings"], gte["pc1_loadings"])[0, 1])
    C = np.corrcoef(gtr["resid_corr"][_IU], gte["resid_corr"][_IU])[0, 1]
    od_tr, od_te = _internal_overdispersion(Xtr), _internal_overdispersion(Xte)

    print(f"train {len(Xtr)}  test {len(Xte)}  (earlier fit -> later unseen)\n")
    print("native-B (self-calibrated over-dispersion, each epoch on its own terms):")
    print(f"  train-on-train x{od_tr:.2f}   test-on-test x{od_te:.2f}   "
          f"-> {'REPLICATES' if od_tr > 1.5 and od_te > 1.5 else 'fails'}")
    print("\ncoupling-structure transfer train -> test (1 = stable law, 0 = epoch-local):")
    print(f"  full coupling matrix : {A:+.3f}")
    print(f"  PC1 dominant mode    : {B:+.3f}")
    print(f"  both-sign forks      : {C:+.3f}")
    print(f"  PC1 var share  train {gtr['eigvals'][0]/12:.1%}  test {gte['eigvals'][0]/12:.1%}")

    stable = C > 0.4 and A > 0.4
    verdict = ("STABLE LAW" if stable else
               "NON-STATIONARY: native-B invariant, adjacency matrix epoch-local"
               if od_te > 1.5 and A < 0.4 else "IN-SAMPLE ARTIFACT")
    print(f"\nVERDICT: {verdict}")


if __name__ == "__main__":
    frac = float(sys.argv[1]) if len(sys.argv) > 1 else 0.60
    default = Path(__file__).parent.parent / "data" / "snapshots.jsonl"
    main(default, frac)
