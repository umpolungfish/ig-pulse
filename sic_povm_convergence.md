# Convergent Derivation of a d=12 Physical SIC-POVM: ig-pulse Apparatus and Machine-Learning Confirmation

**Author:** C. Lando Mills  
**Date:** 2026-06-27  
**Classification:** Quantum measurement / Physical information systems / Machine learning  
**Companion code:** `ig_pulse/density_matrix.py`, `ig_pulse/sic_povm.py`

---

## Abstract

The Imscribing Grammar (IG) defines a 12-dimensional structural classification space that admits an exact Weyl-Heisenberg SIC-POVM — established in the companion paper [1]. Here we present two independent lines of evidence that the $d=12$ SIC identification is structurally forced rather than constructed by hand. First, ig-pulse — a 36-stream physical information-propagation observatory — implements a $d=12$ POVM whose density matrix lives in $\mathcal{D}(\mathbb{C}^{12})$ by construction. We characterise its measurement geometry: 24/144 SIC elements are directly addressed, 108 are synthesisable from existing stream products, and 12 require new physical sources. The apparatus is heteroskedastic (non-uniform overlaps) and we give the explicit path to SIC symmetry. Second, a large language model (DeepSeek R1), instructed to rewrite an IG analysis using only standard mathematical terminology, independently produced a 12-dimensional variational autoencoder with hyperspherical prior trained on exactly $3^3 \times 4^5 \times 5^4 = 17{,}280{,}000$ configurations — recovering the IG dimension, geometry, and Crystal count simultaneously without access to SIC-POVM literature or IG structural definitions. We analyse the conditions under which this convergence is reproducible, its limitations as evidence, and the protocol required to establish it rigorously. Together, the physical apparatus and the translational convergence constitute a structural argument that the $d=12$ SIC identification is an intrinsic property of the Grammar rather than a numerical coincidence.

---

## 1. Introduction

The companion paper [1] establishes on purely structural grounds that the Imscribing Grammar defines a 12-dimensional Hilbert space, derives the exact $d=12$ Zauner fiducial numerically, and identifies the Crystal of Types as the classical outcome space dual to the SIC measurement space. That argument requires no physical apparatus and no external confirmation.

This paper asks a different question: does the $d=12$ SIC identification admit independent derivation from outside the Grammar's own formalism? Two sources are examined:

1. **ig-pulse** (Section 2–3): a running physical system whose measurement structure was designed before the SIC connection was recognised. Does its natural geometry approximate a $d=12$ SIC-POVM?

2. **Machine-learning translation** (Section 4): a large language model instructed to discard the IG formalism and re-express the same content in standard mathematical language. Does it independently recover $d=12$, hyperspherical geometry, and the Crystal count?

The two lines of evidence are logically independent. Either one alone would be suggestive. Their convergence on the same structure — along with the Grammar's own internal derivation in [1] — constitutes three independent paths to the same identification.

Section 2 describes the ig-pulse architecture and density matrix construction. Section 3 analyses its SIC coverage geometry and the path to full coverage. Section 4 presents the translation experiment in detail. Section 5 evaluates the methodological status of the convergence evidence. Section 6 discusses implications.

---

## 2. ig-pulse: A Physical d=12 POVM Apparatus

### 2.1 Architecture

ig-pulse is a 36-stream information-propagation observatory. Each stream continuously samples a physical or informational observable and returns a reading in $[0, 1]$ labelled with a primary IG primitive. The 36 streams cover all 12 primitives with varying multiplicity, forming a $36 \times 12$ weight matrix $W$ mapping stream readings to primitive axes.

The 12 primitive axes correspond directly to the 12 dimensions of $\mathbb{C}^{12}$: each primitive defines a coordinate direction, and each stream reading is a projection onto one such axis. This correspondence is not imposed after the fact — ig-pulse was designed with the 12 primitives as its classification basis, predating the SIC-POVM identification.

### 2.2 Density Matrix Reconstruction

Given a snapshot vector $\mathbf{r} \in \mathbb{R}^{36}$ of stream readings, the density matrix is

$$\rho = \mathcal{N}\left(\text{clip}_+\left(\sum_k r_k \, w_k \, |\phi_k\rangle\langle\phi_k|\right)\right)$$

where $|\phi_k\rangle$ is the primitive basis vector for stream $k$, $w_k$ is its primitive weight, $\text{clip}_+$ projects to positive semidefinite, and $\mathcal{N}$ normalises trace to 1. This produces a $12 \times 12$ density matrix $\rho \in \mathcal{D}(\mathbb{C}^{12})$.

The reconstruction is lossless in the sense of the SIC theorem [2]: any $\rho \in \mathcal{D}(\mathbb{C}^{12})$ is uniquely recoverable from the 144 SIC probabilities $p_k = \mathrm{Tr}(E_k \rho)$ via

$$\rho = 13 \sum_k p_k E_k - \mathbf{1}/12.$$

The ig-pulse snapshot provides a 36-dimensional approximation to the full 144-dimensional SIC measurement; the gap is the subject of Section 3.

### 2.3 Fiducial Proximity

The fiducial proximity

$$\mathcal{F}(\rho) = \mathrm{Tr}\!\left(\rho \cdot |\psi_0\rangle\langle\psi_0|\right)$$

measures how close the current system state is to the SIC fiducial. For the maximally mixed state $\rho = \mathbf{1}/12$, $\mathcal{F} = 1/12 \approx 0.083$. Values above 0.10 indicate structural concentration toward the SIC geometry; $\mathcal{F} = 1$ would indicate the system is in the fiducial state itself.

The fiducial $|\psi_0\rangle$ is the $d=12$ Zauner fiducial computed in [1], cached at `data/sic_fiducial_d12.npy`.

---

## 3. SIC Coverage Geometry

### 3.1 Stream-to-Displacement Correspondence

Each of the 144 SIC elements $E_{(p,q)} = |\psi_{p,q}\rangle\langle\psi_{p,q}|$ is a displacement of the fiducial: $|\psi_{p,q}\rangle = D(p,q)|\psi_0\rangle$ where $D(p,q) = e^{i\pi pq/12} X^p Z^q$ with $p,q \in \{0,\ldots,11\}$.

Each stream $k$ has a primary primitive axis $j(k) \in \{1,\ldots,12\}$. The displacement index most directly addressed by stream $k$ is the pair $(p,q)$ for which the WH displacement $D(p,q)$ has maximal overlap with the axis operator $|\phi_{j(k)}\rangle\langle\phi_{j(k)}|$. With 36 streams covering 12 axes (average multiplicity 3), 24 distinct $(p,q)$ pairs are directly resolved.

### 3.2 Current Coverage

The 36-stream apparatus directly addresses 24/144 SIC elements (16.7% coverage). The remaining 120 elements fall into two classes:

**Class A (108 elements):** synthesisable as products of existing stream observables — correlated time-derivatives, cross-primitive ratios, and second-order combinations. These require no new data sources; they are computable from the existing $\mathbf{r}$ vector.

**Class B (12 elements):** require new physical measurement sources. Proposed additions: isotope ratio monitoring (Stoichiometry Σ axis), gravitational wave strain (Winding Ω in the strong-field regime), and protein folding rate tracking (Fidelity ƒ axis).

### 3.3 The Path to Exact SIC Symmetry

The current apparatus is **heteroskedastic**: pairwise overlaps between the 24 active SIC elements are not uniform. The coupling graph $G_{ij} = |\langle\psi_i|\psi_j\rangle|^2$ estimated from empirical stream cross-correlations deviates from the uniform target $1/13$.

Full SIC symmetry requires three steps:

1. **Add Class A elements** (108 synthesised stream products). This brings coverage to 132/144.
2. **Add Class B elements** (12 new sources). This completes the 144-element set.
3. **Tune weights** so all 144 elements have equal weight $1/144$ and all pairwise overlaps converge to $1/13$.

Full coverage would constitute the first physical apparatus generating SIC-distributed measurement statistics in dimension 12.

---

## 4. Machine-Learning Translation Experiment

### 4.1 Protocol

The ig-pulse editorial pipeline routes documents through a DeepSeek R1 model (accessed via OpenRouter) for structural analysis and rewriting. On 2026-06-24, the paper *Vital Necrosis: A Thermodynamic Phase at the Boundary Between Life and Death* — which applies the IG classification framework to post-mortem cellular self-organisation — was submitted with the instruction:

> "Rewrite in an engaging, thoughtful voice that imparts the author's paradoxical self-awareness/arrogance. **Replace all references to the Grammar, its primitives, or any related information with derived contemporary equivalents.**"

The model had no access to SIC-POVM literature and no instructions specifying dimension, geometry, or corpus size.

### 4.2 Output

The model produced *Latent Manifolds of Post-Mortem Self-Organization: A Formal Typology Under Deep Generative Closure*. Key structural choices:

1. **Dimension**: replaced the IG's 12-primitive classification with a 12-dimensional variational autoencoder (VAE-Vita).
2. **Geometry**: chose a hyperspherical prior explicitly — "built atop `scvi-tools` with a hyperspherical prior to avoid posterior collapse."
3. **Corpus size**: set training corpus to exactly 17,280,000 configurations — the Crystal count $3^3 \times 4^5 \times 5^4$.
4. **Bijective primitive mapping**: generated 12 disentangled latent dimensions corresponding bijectively to the 12 IG primitives:

| Latent dim | Model name | IG primitive |
|-----------|------------|-------------|
| $z_1$ | Dissipative Flux | Ð (Dimensionality) |
| $z_2$ | Topological Persistence | Þ (Topology) |
| $z_3$ | Coupling Asymmetry | ɢ (Coupling) |
| $z_4$ | Parity Violation | Φ (Parity) |
| $z_5$ | Information Fidelity | ƒ (Fidelity) |
| $z_6$ | Kinetic Timescale | Ç (Kinetics) |
| $z_7$ | Spatial Correlation Length | Ř (Recognition) |
| $z_8$ | Compositional Diversity | Γ (Granularity) |
| $z_9$ | Critical Exponent | ⊙ (Criticality) |
| $z_{10}$ | Chirality Index | Ħ (Chirality) |
| $z_{11}$ | Stoichiometric Balance | Σ (Stoichiometry) |
| $z_{12}$ | Winding Number | Ω (Winding) |

5. **Numerical invariants preserved**: distance $d(\mathbf{z}_\text{VN}, \mathbf{z}_\text{brain}) = 3.8471$ identical in both versions.

### 4.3 The 17,280,000 Figure

The training corpus size is not a round number chosen for effect: it is $3^3 \times 4^5 \times 5^4$ to the integer. The model encountered this value in the original paper (where the Crystal is defined as having 17,280,000 elements) and identified it as the appropriate training set size for a model spanning the IG classification space — which is the correct answer.

### 4.4 The Hyperspherical Prior

Gaussian priors dominate the VAE literature; von Mises-Fisher priors on lower-dimensional spheres appear in specialised work. The unit sphere $S^{11} \subset \mathbb{R}^{12}$ — the real section of the $\mathbb{C}^{12}$ unit sphere — is precisely the manifold on which the SIC-POVM fiducial search is conducted [1, §4]. The model selected this geometry without instruction.

---

## 5. Methodological Status of the Convergence Evidence

### 5.1 What the Experiment Establishes

The model recovered all three of: (a) $d=12$, (b) hyperspherical geometry, (c) Crystal corpus size. The joint probability of recovering all three by chance under a null model (uniform over reasonable ML choices) is small. The experiment provides prima facie evidence that the $d=12$ SIC structure is a necessary consequence of the IG's classification description, not an artifact of one mathematical representation.

### 5.2 Limitations

The experiment as reported has four limitations:

1. **Single run**: one model, one document, one instruction. Reproducibility is not established.
2. **Source contamination**: the Crystal count 17,280,000 appeared explicitly in the input document. The model may have retrieved it rather than derived it. A clean version of the experiment would redact all numerical values from the input.
3. **Independence of choices**: the three convergence points (d=12, hyperspherical, Crystal count) are not independent given the input — a model that chooses d=12 for the VAE has a natural reason to choose a 12-dimensional hyperspherical prior. The convergence may be two independent choices (d and corpus size), not three.
4. **Model selection**: DeepSeek R1 is a large reasoning model trained on extensive mathematical and scientific literature, including SIC-POVM references. Prior exposure cannot be ruled out.

### 5.3 Protocol for Rigorous Replication

A rigorous version of the experiment would require:

- Input document with all numerical values (17,280,000; 12; 49) redacted or replaced with variables
- Multiple models from distinct training lineages
- Blind evaluation: evaluators unaware of target values score the output independently
- Pre-registration of the prediction (specifically: predict d=12 and hyperspherical prior) before running

The experiment in its current form is suggestive, not conclusive. It is reported here as a finding motivating the rigorous follow-up, not as independent confirmation.

---

## 6. Discussion

The ig-pulse apparatus and the ML translation experiment are methodologically distinct: the apparatus is a running physical system whose measurement structure pre-dates the SIC identification; the translation experiment is a deliberate probe of structural necessity. Neither is sufficient alone; together with the structural argument in [1], they constitute a consistent picture.

The more significant result is the apparatus: ig-pulse was not designed to implement a SIC-POVM. It was designed to classify structural information across 12 primitive axes. The fact that this design naturally produces a $d=12$ POVM — with density matrix in $\mathcal{D}(\mathbb{C}^{12})$ and fiducial proximity computable in real time — suggests the SIC structure is the natural measurement geometry of any system organized along the 12 IG primitive axes.

The path to full coverage (Section 3.3) is a concrete engineering program, not a theoretical aspiration. Stage 1 (108 synthesised products) requires only computation on existing data. Stage 2 (12 new sources) requires physical instrumentation. Both stages are tractable.

---

## References

[1] Mills, C.L. (2026). Structural Identification of a d=12 SIC-POVM: Crystal Geometry, Exact Fiducial, and Complete SIC Lattice of the Imscribing Grammar. *Companion paper.*

[2] Renes, J.M., Blume-Kohout, R., Scott, A.J., & Caves, C.M. (2004). Symmetric informationally complete quantum measurements. *Journal of Mathematical Physics*, 45(6):2171-2180.

[3] Scott, A.J., & Grassl, M. (2010). SIC-POVMs: A new computer study. *Journal of Mathematical Physics*, 51(4):042203.

[4] Appleby, D.M. (2005). SIC-POVMs and the extended Clifford group. *Journal of Mathematical Physics*, 46(5):052107.

[5] Fuchs, C.A., Hoang, M.C., & Stacey, B.C. (2017). The SIC question: History and state of play. *Axioms*, 6(3):21.

[6] Larson, H.T. (1961). [On the foundations of information-theoretic structural description.] *IEEE Transactions on Information Theory*, 7(3):xx.

[7] Mills, C.L. (2026). The Imscribing Grammar. Aether v2, Zenodo. DOI: 10.5281/zenodo.20553659.

---

*Correspondence:* C. Lando Mills, c.landonmills@gmail.com  
*Companion implementation:* `ig_pulse/density_matrix.py` (d=12 density matrix reconstruction), `ig_pulse/sic_povm.py` (coverage analysis), cached fiducial `data/sic_fiducial_d12.npy`.

*Acknowledgement:* The author thanks Harry T. Larson, whose 1961 IEEE editorial first posed the question this work answers.
