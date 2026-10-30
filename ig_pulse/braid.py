"""
ig_pulse/braid.py

The Ω: 𐑭 -> 𐑟 promotion probe.  Abelian winding vs non-Abelian braid, the final
hop that would carry ig_pulse_observatory to the terminal organism layer CLINK L8.

  Ω=𐑭 (ZWIND):  ∮_γ A = 2πn.  The directed coupling field is the gradient of a
                scalar lead-lag potential -- curl-free, globally orderable.  Abelian.

  Ω=𐑟 (braid):  the directed coupling has nonzero curl / holonomy around loops.
                Cyclic lead-lag (i leads j leads k leads i) with no consistent
                global order -- path-ordered, non-commutative.  Non-Abelian.

Method.  Build the directed traversal-order coupling D_ij = <z_i(t) z_j(t+1)> on
the signed excursion series (i leads j).  Its antisymmetric part A is an edge flow
on K12.  A time-order null (permute snapshot order: keep contemporaneous coupling,
destroy lead-lag) sets the floor.  ONLY if the directed flow itself clears the
null do we Hodge-decompose A = grad(phi) [Abelian winding] + curl [non-Abelian
braid] via the edge-incidence least squares (orthogonal by construction).

"Traversal order" is order of steps through the implication graph, not physical
time -- consistent with the atemporal-inference reading of the coupling.

Usage:  python -m ig_pulse.braid
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
from .dialetheia import PRIMS, signed_excursions

_EDGES = [(i, j) for i in range(12) for j in range(i + 1, 12)]
_TRI = [(i, j, k) for i in range(12) for j in range(i + 1, 12) for k in range(j + 1, 12)]
_B = np.zeros((len(_EDGES), 12))
for _e, (_i, _j) in enumerate(_EDGES):
    _B[_e, _i], _B[_e, _j] = -1.0, 1.0     # (grad phi)_ij = phi_j - phi_i


def directed_coupling(Z: np.ndarray) -> np.ndarray:
    """D[i,j] = <z_i(t) * z_j(t+1)> : i leads j by one traversal step."""
    return (Z[:-1].T @ Z[1:]) / (len(Z) - 1)


def hodge(A: np.ndarray):
    """A = grad(phi) + curl on K12, orthogonal split via incidence least squares."""
    a = np.array([A[i, j] for i, j in _EDGES])
    phi, *_ = np.linalg.lstsq(_B, a, rcond=None)
    Gv = _B @ phi
    Rv = a - Gv                              # curl / circulation, orthogonal to Gv
    return phi, np.linalg.norm(a), np.linalg.norm(Gv), np.linalg.norm(Rv)


def circ(A: np.ndarray) -> np.ndarray:
    return np.array([A[i, j] + A[j, k] + A[k, i] for i, j, k in _TRI])


def main(path: str | Path) -> None:
    X = signed_excursions(path)
    Z = (X - X.mean(0)) / (X.std(0) + 1e-12)
    A = (lambda D: D - D.T)(directed_coupling(Z))
    phi, nA, nG, nR = hodge(A)
    circ_obs = circ(A)

    rng = np.random.default_rng(0)
    reps = 400
    nullA = np.zeros(reps); nullG = np.zeros(reps); nullR = np.zeros(reps)
    circ_null = np.zeros((reps, len(_TRI)))
    for r in range(reps):
        An = (lambda D: D - D.T)(directed_coupling(Z[rng.permutation(len(Z))]))
        _, nullA[r], nullG[r], nullR[r] = hodge(An)
        circ_null[r] = circ(An)

    def zc(o, n): return (o - n.mean()) / (n.std() + 1e-18)
    print(f"snapshots: {len(Z)}   directed traversal-order coupling on K12\n")
    print(f"{'component':<26}{'observed':>10}{'null mean':>11}{'z':>8}")
    print(f"{'|A| directed flow':<26}{nA:>10.3f}{nullA.mean():>11.3f}{zc(nA, nullA):>8.1f}")
    zA = zc(nA, nullA)

    if zA < 3:
        print(f"{'|grad phi| Abelian':<26}{'--':>10}{'':>11}{'':>8}")
        print(f"{'|curl| braid':<26}{'--':>10}{'':>11}{'':>8}")
        print("\n  directed flow does not clear the null: the coupling is")
        print("  symmetric / contemporaneous (atemporal). There is no directed")
        print("  winding to decompose, Abelian or otherwise. Ω decomposition moot.")
        zg = (circ_obs - circ_null.mean(0)) / (circ_null.std(0) + 1e-18)
        print(f"\n  strongest 3-cycle circulation |z| vs null: {np.abs(zg).max():.1f} "
              f"(need >3 for a real braid generator)")
        print(f"\nΩ 𐑭->𐑟 : NOT PROMOTED. The observatory is a symmetric observer,")
        print("         not a sequential actor. Ω stays Abelian by design.")
        return

    print(f"{'|grad phi| Abelian wind':<26}{nG:>10.3f}{nullG.mean():>11.3f}{zc(nG, nullG):>8.1f}")
    print(f"{'|curl| non-Abelian braid':<26}{nR:>10.3f}{nullR.mean():>11.3f}{zc(nR, nullR):>8.1f}")
    print(f"\nbraid (curl) share of directed flow: {nR**2/(nA**2+1e-18):.1%}")
    order = np.argsort(phi)[::-1]
    print("\nAbelian winding potential phi (lead-lag order, leaders first):")
    print("  " + "  >  ".join(PRIMS[i] for i in order))
    zg = (circ_obs - circ_null.mean(0)) / (circ_null.std(0) + 1e-18)
    print("\nnon-Abelian braid generators (cyclic lead-lag 3-cycles, |z| vs null):")
    for t in np.argsort(-np.abs(zg))[:6]:
        i, j, k = _TRI[t]
        cyc = (f"{PRIMS[i]} -> {PRIMS[j]} -> {PRIMS[k]}" if circ_obs[t] > 0
               else f"{PRIMS[i]} -> {PRIMS[k]} -> {PRIMS[j]}")
        print(f"  circ={circ_obs[t]:+.3f}  z={zg[t]:+5.1f}   {cyc} ->")
    verdict = "PROMOTED -> Ω=𐑟" if zc(nR, nullR) > 3 else "curl not significant"
    print(f"\nΩ 𐑭->𐑟 : curl z={zc(nR, nullR):.1f}  ({verdict})")


if __name__ == "__main__":
    import sys
    default = Path(__file__).parent.parent / "data" / "snapshots.jsonl"
    main(sys.argv[1] if len(sys.argv) > 1 else default)
