"""
ig_pulse/broadcast_coupling.py

The G: seq -> broadcast promotion (ɢ 𐑠 -> 𐑵) the Grammar prescribes.

cl8nk_navigator types ig_pulse_observatory at O2, d(CLINK L8)=0.69, one distant
primitive, needing exactly ɢ:𐑠->𐑵 (SEQAX sequential -> broadcast) and Ω:𐑭->𐑟.
The same ɢ=𐑠 defect is shared by measurement_problem_mismatch and physical_reality:
coupling stuck one-way/sequential when it must be one-to-all/simultaneous.

In code that defect was the Pearson lag coupler: it emits seq!(f,g) directed-lag
edges (ɢ=𐑠) and, on saturated series, degenerated to 292 spurious r=+1.000 @ lag0
with the negative half of every contradiction fork discarded. This module replaces
it with the broadcast object:

  * each channel's SIMULTANEOUS (lag-0) signed coupling to ALL others, both signs
    kept, computed on residuals after the common mode is removed -> the one-to-all
    both-sign fan (ɢ=𐑵). This is where the dialetheic B forks actually live.

  * the density matrix rebuilt from FULL signed excursion vectors instead of
    single-axis one-hots. reconstruct() summed e_idx e_idx^T (forced diagonal ->
    belnap_four_topology ƒ=𐑞). Summing |v><v| over the full signed 12-vector gives
    real off-diagonal coherence: the coherences ARE the broadcast couplings.

Usage:  python -m ig_pulse.broadcast_coupling
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np

from .dialetheia import PRIMS, signed_excursions, glut_structure


def broadcast_fans(X: np.ndarray, min_abs: float = 0.15) -> dict:
    """Per-channel one-to-all signed coupling (ɢ=𐑵), residual, both-sign kept."""
    g = glut_structure(X)
    Cr = g["resid_corr"]
    fans = {}
    for i in range(12):
        targets = sorted(
            ((PRIMS[j], float(Cr[i, j])) for j in range(12)
             if j != i and abs(Cr[i, j]) >= min_abs),
            key=lambda t: -abs(t[1]),
        )
        pos = [t for t in targets if t[1] > 0]
        neg = [t for t in targets if t[1] < 0]
        fans[PRIMS[i]] = {"broadcast_plus": pos, "broadcast_minus": neg,
                          "is_fork": bool(pos and neg)}
    return fans, g


def density_matrix(X: np.ndarray) -> np.ndarray:
    """Rebuild rho from full signed vectors -> off-diagonal coherence (not diagonal)."""
    rho = np.zeros((12, 12))
    for v in X:
        n = np.linalg.norm(v)
        if n < 1e-12:
            continue
        u = v / n
        rho += n * np.outer(u, u)      # full 12-vector, not one-hot -> off-diagonals live
    w, V = np.linalg.eigh(rho)
    w = np.maximum(w, 0.0)             # PSD projection
    rho = V @ np.diag(w) @ V.T
    return rho / np.trace(rho)


def _purity(rho):    return float(np.trace(rho @ rho))
def _entropy(rho):
    w = np.linalg.eigvalsh(rho); w = w[w > 1e-12]
    return float(-np.sum(w * np.log(w)))


def main(path: str | Path) -> None:
    X = signed_excursions(path)
    fans, g = broadcast_fans(X)

    print("ɢ 𐑠->𐑵  broadcast coupling fans (one-to-all, both-sign, lag-0 residual)\n")
    nfork = 0
    for src, fan in fans.items():
        if not (fan["broadcast_plus"] or fan["broadcast_minus"]):
            continue
        plus = " ".join(f"+{r:.2f}{p}" for p, r in fan["broadcast_plus"][:3])
        minus = " ".join(f"{r:.2f}{p}" for p, r in fan["broadcast_minus"][:3])
        mark = "  <- FORK" if fan["is_fork"] else ""
        print(f"  {src:<14} | {plus:<34} | {minus}{mark}")
        nfork += fan["is_fork"]
    print(f"\n  both-sign broadcast forks (glut): {nfork} channels")
    print(f"  PC1 share {g['eigvals'][0]/12:.1%} (no single driver) | "
          f"PC1 uniform-sign {g['pc1_uniform_sign']}\n")

    rho = density_matrix(X)
    diag = np.diag(np.diag(rho)); diag = diag / np.trace(diag)
    print("ƒ 𐑞->  density matrix: diagonal-only (old) vs full off-diagonal (broadcast)")
    print(f"  purity  Tr(rho^2) : diagonal {_purity(diag):.4f}   full {_purity(rho):.4f}   (I/12 = {1/12:.4f})")
    print(f"  entropy S(rho)    : diagonal {_entropy(diag):.4f}   full {_entropy(rho):.4f}   (ln12 = {np.log(12):.4f})")
    coh = rho - np.diag(np.diag(rho))
    iu = np.triu_indices(12, 1)
    top = sorted(zip(coh[iu], iu[0], iu[1]), key=lambda t: -abs(t[0]))[:5]
    print("  largest coherences (off-diagonal rho_ij, the broadcast couplings):")
    for c, i, j in top:
        print(f"    {PRIMS[i]:<13} {PRIMS[j]:<13} {c:+.4f}")

    out = Path(path).parent / "broadcast_coupling.json"
    out.write_text(json.dumps(
        {"fans": fans, "pc1_share": float(g["eigvals"][0] / 12),
         "rho_diagonal": [float(rho[i, i]) for i in range(12)],
         "purity_full": _purity(rho), "purity_diagonal": _purity(diag)},
        indent=2))
    print(f"\n  wrote {out}")


if __name__ == "__main__":
    default = Path(__file__).parent.parent / "data" / "snapshots.jsonl"
    import sys
    main(sys.argv[1] if len(sys.argv) > 1 else default)
