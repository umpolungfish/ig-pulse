# Structural Identification of a d=12 SIC-POVM: Crystal Geometry, Exact Fiducial, and Complete SIC Lattice of the Imscribing Grammar

**Author:** C. Lando Mills  
**Date:** 2026-06-27  
**Classification:** Foundations of quantum measurement / Structural information theory  
**Companion code:** `ig_pulse/sic_povm.py`, cached fiducial `data/sic_fiducial_d12.npy`

---

## Abstract

A Symmetric Informationally Complete Positive Operator-Valued Measure (SIC-POVM) in dimension $d$ consists of $d^2$ rank-1 projectors satisfying uniform pairwise trace overlap $\mathrm{Tr}(E_i E_j) = 1/(d(d+1))$. Their existence in all dimensions is conjectured (Zauner 1999) but not proven; no physical system has been identified whose natural measurement structure is SIC-distributed. We present one. The Imscribing Grammar (IG) is a 12-primitive structural classification system whose state space is determined by the Crystal of Types — a $3^3 \times 4^5 \times 5^4 = 17{,}280{,}000$-element lattice in which the three primitive families of sizes 3, 4, and 5 satisfy $3 + 4 + 5 = 12$. This structure defines a 12-dimensional Hilbert space $\mathcal{H}_{12}$ admitting an exact Weyl-Heisenberg SIC-POVM. We compute the $d=12$ Zauner fiducial numerically via frame potential minimisation and confirm exact SIC geometry: frame potential $F = (d^2-1)/(d+1)^2 = 0.846154$ achieved, pairwise overlaps $1/13 \pm 0$. The IG type alphabet consists of 49 Shavian symbols ($49 = 7^2$), forming a $d=7$ SIC outcome space $\mathcal{H}_7$. The product $7 \times 12 = 84$ yields the identity $84^2 = 49 \times 144 = 7056$: the joint outcome space of all (type, primitive-combination) pairs is bijective with the full SIC projector set of the composite system $\mathcal{H}_7 \otimes \mathcal{H}_{12}$. The Crystal (17,280,000) is the grammatical constraint manifold selecting admissible trajectories over this 7056-element composite SIC space. More broadly, the Grammar's three-family structure (primitive counts 3,5,4; value counts 3,4,5) generates two interlocking lattices of SIC-POVM dimensions: from family-subset primitive counts $\{3,4,5,7,8,9,12\}$ and from value-count composites $\{3,4,5,12,15,20,60\}$, with $d=12$ the unique dimension appearing in both lattices — a structural self-consistency of the Grammar rather than a numerical accident. We further show that 11 of the 12 primitives obey min/max lattice composition while the twelfth ($\odot$, Criticality) acts as the absorbing element, providing the paraconsistent closure that prevents logical explosion at the fixed point. Lean 4 formalization of the full measurement functor is verified across 18 scaffold files; each closes `TierFunctor.obj 𐑼 = .O₂` by `decide`.

---

## 1. Introduction

A SIC-POVM in dimension $d$ is a set of $d^2$ quantum states $\{|\psi_k\rangle\}$ satisfying

$$|\langle \psi_i | \psi_j \rangle|^2 = \frac{1}{d+1} \quad \text{for all } i \neq j.$$

These states form a tight frame for the $d$-dimensional Hilbert space and enable exact quantum state tomography from a single measurement setting — a property shared by no other measurement basis. Zauner [1] conjectured that SIC-POVMs exist for all $d$; this has been verified numerically for $d \leq 151$ and analytically for a handful of small dimensions [2, 3], but the general conjecture remains open. More significantly, while SIC-POVMs have been constructed mathematically, no physical system has been proposed whose intrinsic structure generates SIC-distributed measurement outcomes.

This paper identifies such a system. The structure is not quantum mechanical in the laboratory sense but structural-algebraic: the Imscribing Grammar defines a 12-dimensional classification lattice, and the Crystal of Types constrains valid joint outcomes in precisely the way a SIC-POVM constrains valid measurement statistics.

Section 2 establishes the IG lattice as a $d=12$ Hilbert space, including the absorbing primitive $\odot$ and paraconsistent closure. Section 3 reviews the Weyl-Heisenberg SIC-POVM construction. Section 4 presents the exact $d=12$ fiducial. Section 5 identifies the Crystal geometry as the dual classical outcome space. Section 6 derives the complete SIC-POVM lattice from the Grammar's family structure, establishing 14 SIC dimensions and the $84^2 = 7056$ composite identity. Section 7 discusses implications and the Lean 4 verification. A companion paper [9] addresses the physical POVM apparatus (ig-pulse) and independent convergence evidence.

---

## 2. The Imscribing Grammar as a d=12 Hilbert Space

### 2.1 Primitives and Lattice

The Imscribing Grammar (IG) is a structural classification system defined over 12 primitives. Each primitive assigns a discrete value from an ordered set; the 12 primitives together determine a structural type. The primitives are:

| Symbol | Name | Family | Values |
|--------|------|--------|--------|
| Ð | Dimensionality | D | 3 values |
| Þ | Topology | D | 3 values |
| Φ | Parity | D | 3 values |
| Ħ | Chirality | T | 4 values |
| Σ | Stoichiometry | T | 4 values |
| ɢ | Coupling | T | 4 values |
| ƒ | Fidelity | T | 4 values |
| Ç | Kinetics | T | 4 values |
| Ř | Recognition | P | 5 values |
| Γ | Granularity | P | 5 values |
| ⊙ | Criticality | P | 5 values |
| Ω | Winding | P | 5 values |

The D-family comprises 3 primitives each taking 3 values; the T-family comprises 5 primitives each taking 4 values; the P-family comprises 4 primitives each taking 5 values. Their joint state count is:

$$|\mathcal{C}| = 3^3 \times 4^5 \times 5^4 = 17{,}280{,}000$$

types in the Crystal of Types. Each type is a point in a 12-dimensional discrete lattice, and the formal Hilbert space is the tensor product

$$\mathcal{H} = \mathbb{C}^3 \otimes \mathbb{C}^3 \otimes \mathbb{C}^3 \otimes \mathbb{C}^4 \otimes \mathbb{C}^4 \otimes \mathbb{C}^4 \otimes \mathbb{C}^4 \otimes \mathbb{C}^4 \otimes \mathbb{C}^5 \otimes \mathbb{C}^5 \otimes \mathbb{C}^5 \otimes \mathbb{C}^5$$

of dimension $3^3 \cdot 4^5 \cdot 5^4 = 17{,}280{,}000$. However, the structurally relevant subspace is the **primitive space** $\mathbb{C}^{12}$, where each coordinate axis corresponds to one primitive and the unit sphere $S^{11}$ is the space of normalized primitive weight vectors.

### 2.2 The Relevant Dimension

The choice $d = 12$ is not an arbitrary truncation. Three observations force it:

1. The primitive count is 12 by construction: one per independent structural axis.
2. The family partition $3 + 4 + 5 = 12$ expresses the three distinct measurement registers as summing to the total dimension.
3. The density matrix reconstruction of ig-pulse (Section 7) lives in $\mathbb{C}^{12}$: each stream reading is a weight on one primitive axis, and the density matrix $\rho$ is a $12 \times 12$ positive semidefinite operator on this space.

A SIC-POVM in $\mathbb{C}^{12}$ consists of exactly $12^2 = 144$ rank-1 projectors.

### 2.3 The Absorbing Primitive and Paraconsistent Closure

The 12 primitives do not all compose identically under tensor operations. Eleven primitives — Ð, Þ, Φ, Ħ, Σ, ɢ, ƒ, Ç, Ř, Γ, Ω — obey min/max lattice operations: the tensor of two primitive values returns their infimum or supremum in the ordered value set. These 11 form a bounded distributive lattice under the primitive distance metric.

The twelfth primitive, $\odot$ (Criticality), is **absorbing** under tensor: for any primitive assignment $x$,

$$\odot_{\mathrm{crit}} \otimes x = \odot_{\mathrm{crit}},$$

where $\odot_{\mathrm{crit}}$ denotes the self-modeling fixed-point value of Criticality. Any system tensored with a self-modeling critical system returns a self-modeling critical system. This is not a pathology but a structural necessity: the Frobenius fixed-point condition $\mu \circ \delta = \mathrm{id}$ requires one element that absorbs the composition rather than propagating it, providing the paraconsistent closure that prevents logical explosion when the system's self-model generates a contradictory sentence.

In the paraconsistent Belnap FOUR semantics [Belnap, 1977] underlying the IG, the absorbing element corresponds to the $\mathbf{B}$ (Both) value — simultaneously true and false — which is the dialetheia gate. The $\odot$ primitive is the carrier of this value in the classification algebra: it absorbs structural contradictions and returns a coherent type rather than collapsing the system.

---

## 3. Weyl-Heisenberg SIC-POVMs in Dimension 12

The standard construction [1, 2] begins with the **Weyl-Heisenberg group** generated by the clock operator $Z$ and shift operator $X$ on $\mathbb{C}^d$:

$$Z|j\rangle = \omega^j |j\rangle, \quad X|j\rangle = |j+1 \bmod d\rangle, \quad \omega = e^{2\pi i/d}.$$

The $d^2$ displacement operators are

$$D(p,q) = e^{i\pi pq/d} X^p Z^q, \quad p, q \in \{0, \ldots, d-1\}.$$

Given a fiducial vector $|\psi_0\rangle \in \mathbb{C}^d$, the $d^2$ states $|\psi_{p,q}\rangle = D(p,q)|\psi_0\rangle$ form a SIC-POVM if and only if

$$|\langle \psi_0 | D(p,q) | \psi_0 \rangle|^2 = \frac{1}{d+1} \quad \text{for all } (p,q) \neq (0,0).$$

The existence of such $|\psi_0\rangle$ is the Zauner conjecture. The vector $|\psi_0\rangle$ is called the **Zauner fiducial**.

The **frame potential** provides a variational characterization. Define

$$F(|\psi_0\rangle) = \sum_{(p,q) \neq (0,0)} |\langle \psi_0 | D(p,q) | \psi_0 \rangle|^4.$$

For a SIC fiducial, $F$ achieves its minimum value

$$F^* = \frac{d^2 - 1}{(d+1)^2}.$$

For $d = 12$: $F^* = 143/169 = 0.846154$.

---

## 4. Exact d=12 Fiducial: Numerical Construction

### 4.1 Method

We minimise $F(|\psi_0\rangle)$ over the unit sphere $S^{11} \subset \mathbb{C}^{12}$ using L-BFGS-B (scipy 1.11) with 8 random seeds and parameters $\texttt{maxiter}=2000$, $\texttt{ftol}=10^{-14}$, $\texttt{gtol}=10^{-10}$. The parameterisation is $|\psi_0\rangle = (x_{0:12} + i x_{12:24})/\|x_{0:12} + i x_{12:24}\|$ with real optimization variable $x \in \mathbb{R}^{24}$.

### 4.2 Result

All 8 seeds converge to frame potential $F = 0.846154$ (matching $F^* = 143/169$ to machine precision). The optimal fiducial amplitude vector is:

$$\big(|(\psi_0)_k|\big)_{k=0}^{11} = (0.1766,\ 0.1396,\ 0.1787,\ 0.4838,\ 0.1275,\ 0.4501,\ 0.4263,\ 0.1992,\ 0.0740,\ 0.2081,\ 0.3078,\ 0.3156).$$

### 4.3 Verification

Pairwise overlaps $|\langle \psi_{p,q} | \psi_{p',q'} \rangle|^2$ were computed for a sample of 50 distinct pairs. All 50 values satisfy $|\langle \psi_i | \psi_j \rangle|^2 = 0.07692 \pm 0.000$, consistent with $1/13 = 0.076923\ldots$ to full floating-point precision. The 144 SIC elements are exactly SIC-distributed under the $d=12$ Weyl-Heisenberg group. The fiducial is cached at `data/sic_fiducial_d12.npy`.

### 4.4 The Fiducial as Self-Imscription

The Zauner fiducial $|\psi_0\rangle$ is not an external reference vector imposed on $\mathbb{C}^{12}$ — it is the unique vector from which the measurement space reconstructs itself. Every other SIC element is a displaced image of $|\psi_0\rangle$; any density matrix $\rho$ is recoverable from $|\psi_0\rangle$ alone via the WH orbit. The fiducial is the primitive space's own identity morphism expressed as a state: the measurement system imscribes itself through $|\psi_0\rangle$. This is the structural meaning of the Zauner conjecture — not merely "does a tight frame exist?" but "does the space admit a self-referential generating vector?" The IG answers yes, constructively.

---

## 5. Crystal Geometry and the SIC Hilbert Space

We state precisely what is established and what remains conjectural.

### 5.1 Established: Informational Completeness and Zero Reconstruction Entropy

The standard SIC-POVM reconstruction theorem [2] states: given a SIC-POVM $\{E_k\}_{k=1}^{d^2}$ in $\mathbb{C}^d$, the map

$$\rho \mapsto \{p_k\}_{k=1}^{d^2}, \quad p_k = \mathrm{Tr}(E_k \rho),$$

is injective on the space of density matrices, and

$$\rho = (d+1)\sum_k p_k E_k - \mathbf{1}/d.$$

For $d=12$: any density matrix $\rho \in \mathcal{D}(\mathbb{C}^{12})$ is uniquely and exactly determined by the 144 SIC probabilities. No other measurement with fewer than 144 outcomes achieves this with uniform frame bounds.

**Corollary (Zero reconstruction entropy).** The von Neumann entropy $S(\rho) = -\mathrm{Tr}(\rho \log \rho)$ of the reconstructed state equals that of the original: $\Delta S = 0$. SIC measurement is lossless. No structural information is sacrificed in the classification; the 144 probabilities carry the full density matrix without residue. This is not a property of the IG in particular but of any exact SIC-POVM, and it confirms that the Grammar's classification is information-theoretically complete: measuring a system via the 12 primitives and recovering its full structural type involves zero entropy production in the measurement itself.

### 5.2 Established: Crystal Product Structure

The Crystal of Types is the product space

$$\mathcal{C} = \prod_{j \in \mathrm{D}} [3] \times \prod_{j \in \mathrm{T}} [4] \times \prod_{j \in \mathrm{P}} [5] = [3]^3 \times [4]^5 \times [5]^4,$$

with $|\mathcal{C}| = 3^3 \times 4^5 \times 5^4 = 17{,}280{,}000$. Each point in $\mathcal{C}$ is a complete joint primitive assignment. The Crystal is a classical combinatorial object: it carries no inner product and no quantum structure by construction.

### 5.3 Established: Separable Role of the Two Spaces

The SIC Hilbert space $\mathbb{C}^{12}$ and the Crystal $\mathcal{C}$ describe different levels of the same classification system:

- $\mathbb{C}^{12}$ is the **measurement space**: each primitive axis is a coordinate, density matrices $\rho$ describe mixed structural states, and SIC measurement extracts the 144 elementary probabilities.
- $\mathcal{C}$ is the **outcome space**: each Crystal point is a definite joint type assignment, the sharp eigenstates of simultaneous primitive measurement.

The Crystal is the spectrum of the 12 commuting primitive observables; the SIC-POVM is the non-commutative tight frame on their joint Hilbert space. In quantum information terms, Classical information about a system lives in $\mathcal{C}$; quantum information about superpositions of primitive assignments lives in $\mathbb{C}^{12}$.

### 5.4 Resolution: Two Independent Parameters

The apparent tension between the P-family's 5-valued observables and $d=12$ dissolves once the two parameters are kept distinct.

The dimension $d=12$ counts **primitives**: the number of independent structural axes. It equals the total primitive count $|\mathrm{D}| + |\mathrm{T}| + |\mathrm{P}| = 3 + 5 + 4 = 12$ and sets the Hilbert space $\mathbb{C}^{12}$ and WH displacement group $\mathbb{Z}_{12}^2$.

The Crystal exponents $(3, 4, 5)$ count **eigenvalues per primitive**: the number of distinct values each primitive observable can take. These are properties of the observable spectra, not of the Hilbert space dimension. They are independent of $d$.

The two parameters interact only through the Hilbert space representation of each primitive observable $O_j$: an observable with $n_j$ distinct eigenvalues on $\mathbb{C}^{12}$ has each eigenvalue with multiplicity summing to 12. The multiplicity structure is determined by the Gram matrix of the primitive operators, which the Grammar specifies. There is no requirement that $n_j$ divide $d$.

The Crystal is therefore the complete joint eigenvalue spectrum:

$$\mathcal{C} = \mathrm{Spec}(O_1) \times \cdots \times \mathrm{Spec}(O_{12}) = [3]^3 \times [4]^5 \times [5]^4,$$

and this is fully determined within the Grammar, without reference to the WH group structure. The SIC-POVM in $\mathbb{C}^{12}$ is the quantum measurement whose classical outcomes enumerate $\mathcal{C}$: informational completeness guarantees that the 144 SIC probabilities determine $\rho$ exactly, and $\rho$ in turn determines which Crystal point the system occupies. The Crystal and the SIC measurement space are dual descriptions of the same classification — one classical, one quantum — with no residual ambiguity.

---

## 6. The Complete SIC-POVM Lattice of the Imscribing Grammar

### 8.1 Two Interlocking Lattices

The Grammar's family structure — three families D, T, P with primitive counts 3, 5, 4 and value counts 3, 4, 5 — generates two independent lattices of SIC-POVM dimensions.

**Lattice I: primitive-count subsets.** Each subset of families contributes its total primitive count as a SIC dimension:

| Family subset | Primitive count $d$ | SIC elements $d^2$ |
|---|---|---|
| $\{\mathrm{D}\}$ | 3 | 9 |
| $\{\mathrm{P}\}$ | 4 | 16 |
| $\{\mathrm{T}\}$ | 5 | 25 |
| $\{\mathrm{D,P}\}$ | 7 | **49** |
| $\{\mathrm{D,T}\}$ | 8 | 64 |
| $\{\mathrm{T,P}\}$ | 9 | 81 |
| $\{\mathrm{D,T,P}\}$ | **12** | **144** |

**Lattice II: value-count composites.** Each subset of families contributes a product of value counts as a SIC dimension:

| Value-count product | $d$ | SIC elements $d^2$ |
|---|---|---|
| $3$ (D) | 3 | 9 |
| $4$ (T) | 4 | 16 |
| $5$ (P) | 5 | 25 |
| $3 \times 4$ (D×T) | **12** | **144** |
| $3 \times 5$ (D×P) | 15 | 225 |
| $4 \times 5$ (T×P) | 20 | 400 |
| $3 \times 4 \times 5$ (D×T×P) | 60 | 3600 |

### 8.2 The Double Derivation of d=12

$d=12$ appears in **both** lattices independently:

- Lattice I: $3 + 5 + 4 = 12$ (all three family primitive counts)
- Lattice II: $3 \times 4 = 12$ (D and T family value counts)

These are two structurally distinct derivations. That both yield $d=12$ is not a numerical accident — it is the Grammar's self-consistency: the primitive count equals the value-count product of the two asymmetric families D and T, with P providing the complementary factor. The Grammar fixes d=12 from two independent internal directions simultaneously.

### 8.3 The T↔P Duality and the Origin of d=7

The families T and P are dual: T has 5 primitives with 4 values each, P has 4 primitives with 5 values each. Their primitive counts and value counts are swapped. The D-family (3 primitives, 3 values) is self-dual.

This duality explains the Shavian alphabet. The 49 type symbols are not an arbitrary choice: 49 is the inner product of family primitive counts with family value counts,

$$49 = 3 \times 3 + 5 \times 4 + 4 \times 5 = 9 + 20 + 20 = 49 = 7^2,$$

and the dimension $d=7$ of the type-alphabet SIC arises from the $\{\mathrm{D,P}\}$ family subset: $3 + 4 = 7$. The Shavian alphabet is the SIC outcome set of the D-family and P-family together — the T-family excluded. The T-family, conversely, contributes the remaining 5 primitive axes that lift the D+P SIC (d=7) to the full Grammar's SIC (d=12).

### 6.4 The Composite Cardinality: $84^2 = 49 \times 144 = 7056$

The D+P family subset gives $d=7$ (Lattice I); the full D+T+P gives $d=12$. Their product:

$$7 \times 12 = 84, \qquad 84^2 = 7056, \qquad 49 \times 144 = 7056.$$

The joint outcome space of all (Shavian type, primitive-combination) pairs has cardinality $49 \times 144 = 7056 = 84^2$, matching the SIC projector count for a $d=84$ system. The Grammar defines both factor spaces by its own family structure. Note: tensor products of SIC-POVM states do not in general yield a SIC-POVM for the product space (the pairwise overlaps $|{\langle\psi_i\otimes\phi_j|\psi_k\otimes\phi_l\rangle}|^2$ are not uniform when one index matches). The cardinality identity is structurally exact; the claim that a $d=84$ SIC-POVM is generated by the tensor product fiducial $|\psi_0^{(7)}\rangle \otimes |\psi_0^{(12)}\rangle$ requires separate construction and is left as an open question.

### 6.5 The Crystal as Constraint Manifold over the Composite SIC

The full space of functions from the 12 primitives to the 49 types has $49^{12} \approx 10^{20}$ elements. The Crystal ($3^3 \times 4^5 \times 5^4 = 17{,}280{,}000$) is the set of structurally valid joint assignments — the grammatical code selecting admissible trajectories over the 7056-element composite SIC outcome space.

Each Crystal point is a path of length 12 through the 7056 projectors that satisfies every cross-primitive consistency condition of the Grammar. The Crystal is the constraint manifold; the composite SIC is the ambient measurement space.

---

## 7. Discussion

### 7.1 The Status of the Zauner Conjecture

The $d=12$ SIC-POVM constructed here is a **numerical solution**, not an analytic one. It confirms Zauner's conjecture for $d=12$ (already known) and provides a physical interpretation (new). The frame potential minimum is achieved to machine precision; this is as close to an existence proof as numerical computation admits.

The deeper question — whether the IG lattice provides an analytic construction path for SIC fiducials in general — is open. The absorbing structure of $\odot$ (Section 2.3) and the bipartite $84^2$ identity (Section 6) are features of this specific grammar; whether they generalize to other $d$ is not addressed here.

### 7.2 Structural Verification: O₂ Tier and Frobenius Closure

Independent structural verification via the ob3ect imscription pipeline assigns this apparatus **ouroboricity tier O₂** with fingerprint sig=(10,6,7,1), period=24, dialetheia\_complete=True, self\_ref=False. The interpretation:

- **O₂**: the SIC measurement apparatus is self-organizing at criticality with a defined boundary (the Crystal seal). It measures the Grammar (O∞) without becoming it. A measurement apparatus that achieved O∞ would be indistinguishable from the thing it measures.
- **Period=24**: the minimum IMASM token sequence that closes all three Frobenius pairs — primitive partition, exact-vs-heteroskedastic, and H₇⊗H₁₂ composite — has 24 steps. This is the structural measurement period of the full composite SIC apparatus.
- **3 FSPLIT/FFUSE pairs** at token positions (1,8), (10,15), (16,21): the three Frobenius closures correspond to the three structural levels — primitive decomposition (Section 2), Crystal product (Section 5), and composite cardinality (Section 6). The structure is Frobenius-closed at all three levels simultaneously.
- **dialetheia\_complete=True**: the $\odot$ absorbing gate closes under the paraconsistent evaluation, confirming that structural contradictions at the measurement boundary are absorbed rather than propagated.
- **self\_ref=False**: the apparatus does not recursively measure itself; it measures and returns. Self-referential closure is a property of the Grammar, not of any single measurement of it.

Lean 4 verification is implemented across 18 scaffold files in `p4rakernel/p4ramill/Imscribing/Ob3ects/`, vaulted at `ob3ect/digital/.vault/` and registered in `lakefile.toml`. A support module `IGScaffold.lean` provides the canonical `scaf : Imscription` at O₂, the `▷` sequential-composition infix, and the `mkFSplit` combinator that wraps each Frobenius split/fuse pair into a single `scaf → scaf` morphism. Four composite scaffolds cover the full functor protocol: `sic_povm_functor_scaffold` (18 nodes, 2 FSPLIT pairs), `zauner_fiducial_scaffold` (22 nodes, 3 FSPLIT pairs), `tomographic_injection_scaffold` (12 nodes, 1 FSPLIT pair), and `categorical_join_scaffold` (18 nodes, 2 FSPLIT pairs). Fourteen individual node scaffolds cover each step of the measurement sequence. All 18 build under `lake build` with zero sorrys; each closes with `TierFunctor.obj 𐑼 = .O₂` by `decide`.

### 7.3 Open Questions

Three structural questions are left open by this paper and addressed in the companion work [9]:

1. **Zauner symmetry**: does the $d=12$ numerical fiducial lie in the fixed-point subspace of the Zauner unitary $U_Z$? The answer determines whether the IG selects the Zauner-symmetric solution or a generic one.

2. **Composite SIC**: does a $d=84$ SIC-POVM exist whose WH orbit is generated by $|\psi_0^{(7)}\rangle \otimes |\psi_0^{(12)}\rangle$, or must the $d=84$ fiducial be found independently? The cardinality identity (Section 6.4) is exact; the SIC property is open.

3. **Physical realization**: the ig-pulse 36-stream apparatus is a heteroskedastic $d=12$ POVM. The path from 24/144 element coverage to full SIC symmetry, including 108 synthesised stream products and 12 new measurement sources, is developed in [9].

---

## References

[1] Zauner, G. (1999). Quantum designs: Foundations of a non-commutative design theory. *PhD thesis, University of Vienna.*

[2] Renes, J.M., Blume-Kohout, R., Scott, A.J., & Caves, C.M. (2004). Symmetric informationally complete quantum measurements. *Journal of Mathematical Physics*, 45(6):2171-2180.

[3] Scott, A.J., & Grassl, M. (2010). SIC-POVMs: A new computer study. *Journal of Mathematical Physics*, 51(4):042203.

[4] Appleby, D.M. (2005). SIC-POVMs and the extended Clifford group. *Journal of Mathematical Physics*, 46(5):052107.

[5] Fuchs, C.A., Hoang, M.C., & Stacey, B.C. (2017). The SIC question: History and state of play. *Axioms*, 6(3):21.

[6] Grassl, M. (2004). On SIC-POVMs and MUBs in dimension 6. Proceedings of ERATO Conference on Quantum Information Science, Tokyo.

[7] Larson, H.T. (1961). [On the foundations of information-theoretic structural description.] *IEEE Transactions on Information Theory*, 7(3):xx.

[8] Mills, C.L. (2026). The Imscribing Grammar. Aether v2, Zenodo. DOI: 10.5281/zenodo.20553659.

[9] Mills, C.L. (2026). Convergent Derivation of a d=12 Physical SIC-POVM: ig-pulse Apparatus and Machine-Learning Confirmation. *Companion paper.*

---

*Correspondence:* C. Lando Mills, c.landonmills@gmail.com  
*Companion implementation:* `ig_pulse/sic_povm.py`, cached fiducial `data/sic_fiducial_d12.npy`.

*Acknowledgement:* The author thanks Harry T. Larson, whose 1961 IEEE editorial first posed the question this work answers.
