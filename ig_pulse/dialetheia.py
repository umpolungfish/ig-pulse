"""
ig_pulse/dialetheia.py

Honest, calibration-proof B-state test.

The original is_b_state heuristic (>=3 raw alerts) and the diagonal density
matrix cannot tell a genuine dialetheia from a stuck needle: hand-tuned
thresholds pinned some channels near their ceiling, which both manufactured a
constant alert floor and degenerated the Pearson coupler to spurious r=+/-1.

This module replays stored snapshots under data-driven, headroom-guaranteed
calibration and asks three falsifiable questions:

  1. HEADROOM   -- recalibrate every channel to a fixed marginal fire rate from
                   its own empirical CDF (two-sided, direction-agnostic). No
                   channel can be a stuck needle by construction.

  2. CONFLUENCE -- is the count of simultaneously-active channels OVER-DISPERSED
                   relative to a time-shuffled null that preserves each channel's
                   marginal but destroys cross-channel synchrony? Over-dispersion
                   at the high tail = reality floods together beyond chance.

  3. GLUT       -- keep the SIGN of each excursion, remove the leading common
                   mode (PC1), and look at the residual correlation structure.
                   A flat residual means it was common-cause synchrony. Strong
                   residual BOTH-SIGN forks (a channel + with one partner and -
                   with another) are the structural fingerprint of Belnap B:
                   opposed channels both live, locked in anti-phase.

Confluence separates B/N from sparse-Boolean. The glut structure separates
B (glut) from N (gap) and from a single common driver.

Usage:  python -m ig_pulse.dialetheia [path/to/snapshots.jsonl]
"""
from __future__ import annotations
import json, re, sys, collections
from pathlib import Path
import numpy as np

PRIMS = ["criticality", "parity", "kinetics", "topology", "coupling",
         "dimensionality", "stoichiometry", "granularity", "winding",
         "chirality", "recognition", "fidelity"]
_PIDX = {p: i for i, p in enumerate(PRIMS)}
_SEIS = re.compile(r"^seismic_([A-Z0-9]+)_[A-Z0-9]+$")


def _collapse(stream: str) -> str:
    """Collapse per-station seismic to its network (matches coupler.py)."""
    m = _SEIS.match(stream)
    return f"seismic_net_{m.group(1)}" if m else stream


def signed_excursions(path: str | Path) -> np.ndarray:
    """Two-pass replay -> (N, 12) signed percentile-excursion matrix in [-1, 1].

    Only snapshots that actually collected readings are used (empty pulls are
    dead collections, not observations). For a primitive with several
    contributing streams in one snapshot, the most extreme (max |excursion|)
    wins. Sign encodes which tail of that stream's own history the value sits in.
    """
    path = str(path)
    valmap: dict[tuple, list] = collections.defaultdict(list)
    n = 0
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                s = json.loads(line)
            except json.JSONDecodeError:
                continue
            rds = s.get("readings") or []
            if not rds:
                continue
            for r in rds:
                pr = r.get("primitive")
                v = r.get("value")
                if pr in _PIDX and v is not None:
                    valmap[(_collapse(r.get("stream", "")), pr)].append(float(v))
            n += 1
    sortmap = {k: np.array(sorted(v)) for k, v in valmap.items()}

    def se(key, v):
        a = sortmap[key]
        lo = np.searchsorted(a, v, "left")
        hi = np.searchsorted(a, v, "right")
        return 2.0 * (((lo + hi) / 2) / len(a) - 0.5)

    X = np.zeros((n, 12))
    j = 0
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                s = json.loads(line)
            except json.JSONDecodeError:
                continue
            rds = s.get("readings") or []
            if not rds:
                continue
            best = np.zeros(12)
            for r in rds:
                pr = r.get("primitive")
                v = r.get("value")
                if pr not in _PIDX or v is None:
                    continue
                e = se((_collapse(r.get("stream", "")), pr), float(v))
                k = _PIDX[pr]
                if abs(e) > best[k]:
                    best[k] = abs(e)
                    X[j, k] = e
            j += 1
    return X


def calibrate(X: np.ndarray, fire: float = 0.30) -> np.ndarray:
    """Headroom calibration: channel active when |excursion| in its top `fire`."""
    A = np.zeros(X.shape, dtype=int)
    mag = np.abs(X)
    for k in range(X.shape[1]):
        thr = np.quantile(mag[:, k], 1 - fire)
        A[:, k] = (mag[:, k] >= thr) & (mag[:, k] > 0)
    return A


def confluence_test(active: np.ndarray, reps: int = 800, seed: int = 0) -> dict:
    """Observed vs time-shuffled-null distribution of simultaneous active count."""
    n, c = active.shape
    nact = active.sum(1)
    rng = np.random.default_rng(seed)
    ks = np.arange(0, c + 1)
    ge_obs = np.array([(nact >= k).mean() for k in ks])
    null_ge = np.zeros((reps, c + 1))
    null_var = np.zeros(reps)
    for rep in range(reps):
        perm = np.argsort(rng.random((n, c)), axis=0)
        na = active[perm, np.arange(c)].sum(1)
        null_ge[rep] = [(na >= k).mean() for k in ks]
        null_var[rep] = na.var()
    return {
        "ks": ks,
        "ge_obs": ge_obs,
        "ge_null_mean": null_ge.mean(0),
        "ge_null_lo": np.quantile(null_ge, 0.025, 0),
        "ge_null_hi": np.quantile(null_ge, 0.975, 0),
        "var_obs": float(nact.var()),
        "var_null": float(null_var.mean()),
        "mean_obs": float(nact.mean()),
        "mean_null": float(active.mean() * c),
    }


def glut_structure(X: np.ndarray) -> dict:
    """Eigen-spectrum, PC1 loadings, and residual both-sign forks after PC1."""
    Z = (X - X.mean(0)) / (X.std(0) + 1e-12)
    C = Z.T @ Z / len(Z)
    w, V = np.linalg.eigh(C)
    order = np.argsort(w)[::-1]
    w, V = w[order], V[:, order]
    g = Z @ V[:, 0]
    Zres = Z - np.outer(g, V[:, 0])
    Zr = (Zres - Zres.mean(0)) / (Zres.std(0) + 1e-12)
    Cr = Zr.T @ Zr / len(Zr)
    np.fill_diagonal(Cr, 0.0)
    forks = []
    for i in range(12):
        jp, jn = int(np.argmax(Cr[i])), int(np.argmin(Cr[i]))
        if Cr[i, jp] > 0.15 and Cr[i, jn] < -0.15:
            forks.append((PRIMS[i], PRIMS[jp], float(Cr[i, jp]),
                          PRIMS[jn], float(Cr[i, jn])))
    return {
        "eigvals": w,
        "pc1_loadings": V[:, 0],
        "pc1_uniform_sign": bool(np.all(V[:, 0] > 0) or np.all(V[:, 0] < 0)),
        "resid_corr": Cr,
        "forks": forks,
        "resid_mean_abs_corr": float(np.abs(Cr[np.triu_indices(12, 1)]).mean()),
    }


def main(path: str | Path) -> None:
    X = signed_excursions(path)
    n = len(X)
    A = calibrate(X)
    conf = confluence_test(A)
    glut = glut_structure(X)

    print(f"functioning snapshots replayed : {n}\n")
    print("[1] headroom -- recalibrated marginals (each ~0.30, no stuck needle):")
    rates = A.mean(0)
    for k in range(12):
        print(f"    {PRIMS[k]:<14} {rates[k]:.3f}")
    print()
    print("[2] confluence vs time-shuffled null")
    print(f"    active-count variance : obs {conf['var_obs']:.2f} "
          f"vs null {conf['var_null']:.2f}  "
          f"(overdispersion x{conf['var_obs']/conf['var_null']:.2f})")
    print(f"    {'k':>3} {'P>=k obs':>9} {'null':>7} {'95% hi':>8}")
    for k in range(5, 12):
        flag = " ABOVE" if conf["ge_obs"][k] > conf["ge_null_hi"][k] else ""
        print(f"    {k:>3} {conf['ge_obs'][k]:>9.4f} {conf['ge_null_mean'][k]:>7.4f} "
              f"{conf['ge_null_hi'][k]:>8.4f}{flag}")
    print()
    print("[3] glut vs common-cause")
    print(f"    PC1 variance share : {glut['eigvals'][0]/12:.1%}  "
          f"(one common driver would be >50%)")
    print(f"    PC1 uniform sign   : {glut['pc1_uniform_sign']}  "
          f"(False => leading mode is oppositional)")
    print(f"    residual mean |corr| after removing PC1 : {glut['resid_mean_abs_corr']:.3f}")
    print(f"    both-sign forks (glut fingerprint): {len(glut['forks'])}")
    for src, pp, rp, pn, rn in glut["forks"]:
        print(f"      {src:<13} +{rp:.2f} {pp:<13} {rn:+.2f} {pn}")


if __name__ == "__main__":
    default = Path(__file__).parent.parent / "data" / "snapshots.jsonl"
    main(sys.argv[1] if len(sys.argv) > 1 else default)
