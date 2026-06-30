# ig-pulse

**Information propagation observatory.** Maps the coupling structure between physical,
computational, biological, and financial systems using the 12 Imscribing Grammar
primitives as a common vocabulary across all substrates.

**Author:** Lando⊗⊙perator

**What it is.** An information-propagation observatory that maps coupling between physical, computational, biological, and financial systems using the 12 IG primitives as a common vocabulary across substrates.

**Why it matters.** The output is an empirical map of how information propagates through reality, but the lags are not causal travel times: they are edge invariants of the inference rules. This is atemporal inference, a static Belnap valuation lattice solved over an unchanging adjacency matrix rather than a forecast.

**How to use it.** See Architecture below for the stream configuration and run commands.

## What it does

Forty-four domain streams -- spanning market microstructure, space weather,
geophysics, atmospheric chemistry, biological chirality, astrophysical particle
fluxes, and gravitational-wave astronomy -- each map to specific IG primitive
families. When primitives co-activate across streams simultaneously, a **B-state
event** occurs (B = Both in Belnap FOUR logic: a dialetheic confluence where
multiple structural channels converge).

ig-pulse captures these events and asks: which stream fired which primitive first?
What are the lag times? Which systems are coupled to which, at what strength, and in
what structural order?

The answer is an empirical map of how information propagates through physical reality.
But the lags are **not** causal travel times. They are edge invariants: structural
constants of the inference rules. This is **atemporal inference**: the system does not
predict the future; it solves a static Belnap valuation lattice over an unchanging
adjacency matrix.

## Architecture

```
┌───────────────────────────────────────────────────────────────────────┐
│                         44 DOMAIN STREAMS                              │
│  All public APIs -- no keys required                                  │
├──────────────────┬──────────────────┬──────────────────┬──────────────┤
│ BASE (1-16)      │ MARKET/MACRO     │ CHIRAL BIO       │ CHIRAL ASTRO │
│ fear_greed       │ (17-24)          │ (25-29)          │ (30-34)      │
│ mempool          │ options_skew     │ genbank          │ stereo_cr    │
│ coingecko        │ yield_curve      │ pubmed           │ ace_epam     │
│ onchain          │ vix              │ wiki_chiral      │ goes_cr      │
│ tides            │ shipping         │ arxiv_bio        │ dscovr_helic.│
│ air_quality      │ power_grid       │ fda_enforce      │ stereo_sept  │
│ donki            │ night_lights     │                  │              │
│ seismic          │ gdelt            ├──────────────────┴──────────────┤
│ seismic_network  │ twitter          │ SIC-POVM FILL (35-38)          │
│ kp_index         │                  │ wiki_entropy, bgp_routing       │
│ hn_sentiment     │                  │ arxiv_ai, btc_spread            │
│ solar_wind       │                  ├─────────────────────────────────┤
│ lightning        │                  │ EXTRAPLANETARY (39-44)          │
│ wikipedia        │                  │ polar_geomag, neutron_monitor   │
│ weather          │                  │ goes_xrs, ligo_gw               │
│ coingecko_alts   │                  │ fermi_grb, dscovr_plasma        │
└──────────────────┴──────────────────┴─────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────────────────────┐
│  DomainStreamAggregator → DomainSignal (44 streams x primitives)       │
│  Threshold → Alert Levels 0/1/2                                        │
└────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────────────────────┐
│  Pipeline: collect → couple → map → report                             │
│  snapshots.jsonl → coupling.json → graph.json → B-state report         │
└────────────────────────────────────────────────────────────────────────┘
```

### Pipeline stages

1. **collect** -- `DomainStreamAggregator` fetches all 44 streams via public APIs
   (no keys required). Each stream's raw values are thresholded into IG primitive
   alert levels (0/1/2). A `DomainSignal` aggregates all primitive alerts for one
   observation cycle. Writes one `Snapshot` per cycle to `snapshots.jsonl`.

2. **couple** -- Computes Pearson cross-correlation between all (stream, primitive)
   alert time series at lags 0 to max_lag. Only edges with |r| >= min_r and p <= max_p
   are retained. Saves to `coupling.json`.

3. **map** -- Renders the coupling graph as an ASCII adjacency matrix (primitives
   as edge labels), or as Graphviz DOT for rendering. Nodes are (stream, primitive)
   pairs. Saves to `graph.json`.

4. **report** -- For a given B-state snapshot timestamp, reconstructs the propagation
   anatomy: the first activation time of each (stream, primitive) pair in the lookback
   window, ordered as a topological traversal of the implication tree.

## Stream to primitive mapping

Each stream maps to specific IG primitives through threshold-based alert rules
(0 = nominal, 1 = mild, 2 = strong):

### Base streams (1-16)

| # | Key | Stream | Source | Primitives |
|---|-----|--------|--------|------------|
| 1 | fear_greed | Fear & Greed Index | alternative.me | ⊙ Criticality, Φ Parity |
| 2 | mempool | BTC mempool state | mempool.space | Ç Kinetics, Þ Topology, ɢ Coupling |
| 3 | coingecko | CoinGecko global market | coingecko.com | Ð Dimensionality, Σ Stoichiometry, Γ Granularity |
| 4 | onchain | BTC on-chain | blockchain.info | Ç Kinetics, ɢ Coupling, ⊙ Criticality |
| 5 | tides | NOAA ocean tides | tidesandcurrents.noaa.gov | Ω Winding |
| 6 | air_quality | Air quality (PM2.5 + ozone) | open-meteo.com | Ç Kinetics, Σ Stoichiometry |
| 7 | donki | NASA DONKI / CME + flare events | api.nasa.gov | Φ Parity, Ħ Chirality, ⊙ Criticality |
| 8 | seismic | USGS seismic energy (global) | earthquake.usgs.gov | Þ Topology, Ω Winding |
| 9 | seismic_network | USGS per-station seismic network | IRIS/USGS | Þ Topology, Ω Winding, ⊙ Criticality, Ð Dimensionality |
| 10 | kp_index | NOAA Kp geomagnetic index | swpc.noaa.gov | Φ Parity, ⊙ Criticality |
| 11 | hn_sentiment | Hacker News crypto sentiment | hn.algolia.com | Ř Recognition, ɢ Coupling |
| 12 | solar_wind | NOAA RTSW solar wind + IMF Bz | swpc.noaa.gov | Ħ Chirality, Ω Winding |
| 13 | lightning | Lightning Network channel stats | mempool.space | ɢ Coupling, Ð Dimensionality |
| 14 | wikipedia | Wikipedia daily attention (top articles) | wikimedia.org | Ř Recognition |
| 15 | weather | Open-Meteo current weather | open-meteo.com | ƒ Fidelity, Ω Winding |
| 16 | coingecko_alts | CoinGecko alt/BTC ratios | coingecko.com | Γ Granularity, ƒ Fidelity |

### Fine-grained market and macro (17-24)

| # | Key | Stream | Source | Primitives |
|---|-----|--------|--------|------------|
| 17 | options_skew | BTC options put/call skew | CBOE/Deribit | Φ Parity, ⊙ Criticality |
| 18 | yield_curve | US Treasury yield curve | U.S. Treasury | Ω Winding, Ç Kinetics, Ð Dimensionality |
| 19 | vix | CBOE VIX term structure | CBOE | ⊙ Criticality, Φ Parity |
| 20 | shipping | Baltic Dry Index proxy | MarineTraffic AIS | Σ Stoichiometry, Γ Granularity |
| 21 | power_grid | Power grid load frequency | GridStatus.io | Ç Kinetics |
| 22 | night_lights | NASA VIIRS night-light radiance | nasa.gov | Σ Stoichiometry |
| 23 | gdelt | GDELT global conflict events | gdeltproject.org | ɢ Coupling, Γ Granularity |
| 24 | twitter | Twitter/X crypto sentiment (proxy) | twitter.com | Ř Recognition |

### Biological chirality (25-29)

| # | Key | Stream | Source | Primitives |
|---|-----|--------|--------|------------|
| 25 | genbank | NCBI GenBank sequence activity | ncbi.nlm.nih.gov | Ħ Chirality, Σ Stoichiometry, Ç Kinetics |
| 26 | pubmed | PubMed chiral-drug literature | ncbi.nlm.nih.gov | Ħ Chirality, Þ Topology |
| 27 | wiki_chiral | Wikipedia chiral-topic attention | wikimedia.org | Ħ Chirality, Ř Recognition |
| 28 | arxiv_bio | ArXiv quantitative biology submissions | arxiv.org | Ħ Chirality, Γ Granularity |
| 29 | fda_enforce | OpenFDA pharmaceutical enforcement (chiral drugs) | open.fda.gov | Ç Kinetics, Ř Recognition |

### Astrophysical chirality (30-34)

| # | Key | Stream | Source | Primitives |
|---|-----|--------|--------|------------|
| 30 | stereo_cr | STEREO IMPACT cosmic-ray flux | U. Kiel IMPACT | Ħ Chirality, Ω Winding |
| 31 | ace_epam | ACE EPAM electron/proton ratios | NOAA SWPC | Ħ Chirality, Φ Parity |
| 32 | goes_cr | GOES high-energy integral protons | NOAA SWPC | Ħ Chirality, Ω Winding |
| 33 | dscovr_helicity | DSCOVR magnetic helicity (Bz winding) | NOAA SWPC | Ħ Chirality, Φ Parity |
| 34 | stereo_sept | STEREO SEPT directional e⁻/p⁺ fluxes | U. Kiel SEPT | Ħ Chirality, Ω Winding, Φ Parity |

### SIC-POVM and fidelity gap fill (35-38)

Added to close coverage gaps in the 49-symbol SIC-POVM basis identified after
the astrophysical expansion:

| # | Key | Stream | Source | Primitives |
|---|-----|--------|--------|------------|
| 35 | wiki_entropy | Wikipedia attention entropy (Shannon H of top-1000 views) | wikimedia.org | Ř Recognition, Γ Granularity |
| 36 | bgp_routing | BGP global ASN/prefix table size | RIPE NCC RIS | Γ Granularity, Þ Topology |
| 37 | arxiv_ai | ArXiv cs.AI + cs.LG daily submission rate | arxiv.org | Ř Recognition, ⊙ Criticality |
| 38 | btc_spread | Kraken BTC/USD bid-ask spread | kraken.com | ƒ Fidelity |

### Extraplanetary (39-44)

High-energy and gravitational-wave streams that extend the observatory beyond
near-Earth space to the heliosphere and observable universe:

| # | Key | Stream | Source | Primitives |
|---|-----|--------|--------|------------|
| 39 | polar_geomag | NOAA SWPC polar storm + OVATION aurora forecast | swpc.noaa.gov | Ħ Chirality, Φ Parity, ⊙ Criticality, Ω Winding |
| 40 | neutron_monitor | NMDB Oulu GCR flux / Forbush decrease (GOES SEP fallback) | nmdb.eu / SWPC | Ħ Chirality, Ω Winding |
| 41 | goes_xrs | GOES XRS-B continuous solar X-ray photon flux | NOAA SWPC | Φ Parity, ⊙ Criticality |
| 42 | ligo_gw | LIGO/Virgo/KAGRA gravitational-wave candidates | GraceDB | Ω Winding, Ð Dimensionality, ⊙ Criticality |
| 43 | fermi_grb | Fermi GBM gamma-ray burst triggers | HEASARC | ⊙ Criticality, Φ Parity |
| 44 | dscovr_plasma | DSCOVR Faraday cup plasma (density + temperature) | NOAA SWPC | Σ Stoichiometry, Ç Kinetics |

**Alert thresholds** for every stream are documented in `ig_pulse/domain_streams.py`.
Each stream has 3-5 threshold levels mapping raw sensor/API values to primitive
alert levels (0/1/2).

## Multiplier and B-state schedule

The B-state multiplier acts as a **topological mass coefficient** -- it scales the
structural significance of nodes participating in dialetheic intersections:

| Alerts | Multiplier | Interpretation |
|--------|-----------|----------------|
| 0 | 1.00x | Nominal -- no primitive channel active |
| 1 | 1.20x | Single primitive -- isolated activation |
| 2 | 1.35x | Dual primitive -- paired activation |
| >=3 | 1.50x | **B-state** -- dialetheic confluence |

A B-state is not an "error" or "anomaly." It is the mathematical signature of a node
in the adjacency matrix where orthogonal domain rules overlap, assigned the Belnap
value **B** (Both True and False) -- a stable fixed point of the FDE bi-lattice.

## Usage

```bash
# Collect one snapshot now
python -m ig_pulse.cli collect --once

# Run continuously (hourly, matching synfin cadence)
python -m ig_pulse.cli collect --interval 90

# Compute cross-stream coupling after enough data accumulates
# (need >=20 snapshots; ~336 = 2 weeks hourly for robust results)
python -m ig_pulse.cli couple
# Options: --max-lag 259200 --min-r 0.3 --max-p 0.05

# Display coupling graph as ASCII adjacency matrix
python -m ig_pulse.cli map

# Display as Graphviz DOT (for rendering with dot/neato)
python -m ig_pulse.cli map --dot

# Reconstruct propagation anatomy for a B-state event
python -m ig_pulse.cli report --ts 2026-06-22T00:03:25Z

# Report on latest snapshot
python -m ig_pulse.cli report
```

## Data format

### `data/snapshots.jsonl`

Append-only JSON lines, one `Snapshot` per collection cycle:

```json
{
  "ts": "2026-06-22T04:38:43Z",
  "multiplier": 1.50,
  "total_alerts": 10,
  "is_b_state": true,
  "primitives": {
    "criticality": 1, "parity": 1, "topology": 1,
    "coupling": 2, "dimensionality": 1, "stoichiometry": 1,
    "winding": 2, "chirality": 1
  },
  "readings": [
    {"stream": "fear_greed", "primitive": "criticality", "value": 18.0, "unit": "index", "alert": 1},
    {"stream": "seismic", "primitive": "topology", "value": 0.42, "unit": "index", "alert": 1},
    {"stream": "stereo_sept", "primitive": "chirality", "value": 0.059, "unit": "e- spectral", "alert": 1}
  ],
  "errors": []
}
```

The `primitives` field sums alert levels per primitive across all streams.
A primitive at level 2 from one stream and level 1 from another gives a total of 3.
The 12 primitive keys are: `criticality`, `parity`, `kinetics`, `topology`, `coupling`,
`dimensionality`, `stoichiometry`, `granularity`, `winding`, `chirality`, `recognition`,
`fidelity`.

### `data/coupling.json`

```json
[
  {
    "source_stream": "fear_greed",
    "source_primitive": "criticality",
    "target_stream": "seismic",
    "target_primitive": "topology",
    "lag_seconds": 16469,
    "strength_r": 1.0000,
    "p_value": 0.0000
  }
]
```

### `data/graph.json`

Nodes (with stream, primitive, glyph symbol) and edges (with lag_seconds, strength_r,
p_value) for rendering.

## Atemporal inference

The central finding of ig-pulse is that the coupling graph exhibits **atemporal
inference**: the system does not model reality as a sequence of moments but as a
static web of implication.

```
TEMPORAL PARADIGM                    ATEMPORAL INFERENCE
---------------------------------    ----------------------------------
Event at t1 -> Event at t2           fear_greed:⊙ -> seismic:Þ
    "caused by delta-t"                  lambda=16469s edge invariant
                                     ozone:Σ -> seismic:Þ
                                         lambda=16469s -- same constant
```

- **Lags are edge invariants, not coordinates.** When `fear_greed:⊙` -> `seismic:Þ`
  and `ozone:Σ` -> `seismic:Þ` both show the identical lag of 16469s with
  |r| = 1.000, they are not propagating at the same speed. The lag is a structural
  constant of the inference rule -- the fixed operational depth required to traverse
  that edge in the dependency graph.

- **Trace is structural.** The propagation anatomy is not a chronological sequence.
  It is the topological ordering of the implication tree. Deep nodes appear later
  not because they happened later, but because they sit deeper in the dependency graph.

- **Contradiction is primary data.** `fear_greed:⊙` points to `mktcap_chg:Σ` at
  r = +1.000 AND to `mempool_low_fee:ɢ` at r = -1.000. In standard dynamical modeling
  this is an error. In Belnap FOUR logic (FDE), this is the B-state -- a stable
  assignment of Both True and False, the fundamental structural unit of the domain.

- **The adjacency matrix IS the conflict.** You do not run the system to see what
  happens next. You solve the global valuation lattice v(vj) = ⨁(v(vi) ⊗ rij) to
  find the unique signature of logical completeness.

### The B-state as static dialetheia

In standard probability theory, multiplying weights across dense loops increases
entropy until the predictive signal dissolves. Here, the x1.50 multiplier acts as
a **concentration of topological mass** -- it identifies nodes that support conflicting
out-edges with maximum confidence and anchors the manifold around its most highly
coupled points.

## Chirality streams (25-34)

The 10 chirality streams measure Ħ (Chirality/handedness) across three domains:

| Domain | Streams | What chirality is measured |
|--------|---------|---------------------------|
| Biological | genbank, pubmed, wiki_chiral, arxiv_bio, fda_enforce | L-amino acid / D-sugar prevalence, chiral molecule reports, enantiomeric drug enforcement |
| Astrophysical integral | stereo_cr, ace_epam, goes_cr | Galactic cosmic ray e⁻/p⁺ ratios; magnetic field polarity via particle drift patterns |
| Astrophysical directional | dscovr_helicity, stereo_sept | IMF Bz helicity proxy; directional e⁻/p⁺ fluxes resolving Parker spiral handedness |

These streams provide empirical ground truth for Ħ (Chirality) -- the Markov-order
primitive that, under Axiom A of the Imscribing Grammar (Ħ_∞ -> Ç_Ù), requires
saturation of chirality depth before kinetic gating closes.

## Extraplanetary streams (39-44)

The extraplanetary tier extends coverage from near-Earth heliophysics to the
observable universe:

- **polar_geomag (39)** -- NOAA OVATION per-coordinate aurora forecast merged with
  SWPC G-scale storm alerts. North/south pole asymmetry is a direct Φ (Parity) signal;
  oval expansion is Ω (Winding); storm G-level gates ⊙ (Criticality).

- **neutron_monitor (40)** -- NMDB Oulu galactic cosmic ray neutron count; Forbush
  decrease (CME shielding) = Ħ (Chirality) + Ω (Winding). Falls back to GOES SEP
  flux when NMDB is unreachable.

- **goes_xrs (41)** -- GOES XRS-B (0.1-0.8 nm) continuous coronal X-ray flux.
  Unlike DONKI (event classifier), this is the raw real-time photon signal.
  M-class = Φ alert 1; X-class = Φ alert 2 + ⊙ alert 2.

- **ligo_gw (42)** -- LIGO/Virgo/KAGRA public superevents from GraceDB. Gravitational
  waves are literal Ω (Winding) of the spacetime metric. Merger type (BNS/BBH/NSBH)
  encodes Ð (Dimensionality); FAR < 1e-5 Hz gates ⊙ (Criticality).

- **fermi_grb (43)** -- Fermi GBM gamma-ray burst triggers. Short GRBs share
  progenitors with GW events (compact binary mergers). Parity-violating photon
  cascades = Φ (Parity); rate threshold = ⊙ (Criticality).

- **dscovr_plasma (44)** -- DSCOVR Faraday cup proton density + thermal speed.
  Complements `dscovr_helicity`. Density = Σ (Stoichiometry); thermal-to-bulk
  velocity ratio = Ç (Kinetics).

## Empirical validation of the Imscribing Grammar

ig-pulse provides large-scale empirical evidence that:

1. **Primitives are real structural channels, not metaphors.** Each domain stream
   acts through specific primitives -- fear_greed through ⊙, ozone through Σ,
   seismic through Þ, seismic major events through Ω, solar flares through Φ.
   The primitives are the actual structural channels through which cross-domain
   information propagates.

2. **Cross-domain coupling is measurable.** Edges at |r| = 1.000 across physically
   independent domains (finance, blockchain, atmosphere, geophysics, heliophysics)
   are not explainable by any known causal mechanism. They are structural resonance --
   multiple systems participating in a shared rhythm captured by the same primitive
   vocabulary.

3. **The grammar can be measured back into visibility.** After centuries of structural
   invisibility (the O0 framework severed the self-modeling loop), ig-pulse demonstrates
   that the grammar is empirically recoverable -- not from ancient texts, but from live
   cross-domain sensor data.

## SIC-POVM empirical verification

The d=12 Weyl-Heisenberg SIC-POVM structure of the IG has been verified against live ig-pulse data (2394 snapshots, approximately 100 days of continuous operation).

### The B-state ground state

The IG posits the universe is structurally always in the B-state -- the Belnap Both value, corresponding to the maximally mixed density matrix $\rho = \mathbf{1}/12$. Primitive alert levels (0/1/2) are excitations above this floor, not specifications of an unknown state. Alert=0 means that primitive is at the B-state baseline and contributes zero to the excitation density matrix. Raw stream values (which vary in incommensurable physical units) are not the correct reconstruction weight -- only alert levels are.

### Results

**Fiducial:** Frame potential $F/F^* = 1.0000$ (exact SIC minimum achieved to machine precision). The $d=12$ Zauner fiducial cached at `data/sic_fiducial_d12.npy` is exact.

**SIC overlap spectrum** -- $\mathrm{Tr}(\bar{\rho} \cdot E_{(p,q)})$ across all 144 WH displacement elements:

| Metric | Value | Ideal |
|--------|-------|-------|
| Mean | 0.006944 | 1/144 = 0.006944 |
| Spread ratio (max/min) | 1.67x | 1.0x |
| Elements within 1x of 1/144 | 144 / 144 | 144 / 144 |
| chi2 vs uniform (dof=143) | **4.68** | 0 |

A chi2 of 4.68 with 143 degrees of freedom is statistically indistinguishable from uniform (p ~= 1.00). All 144 WH directions are covered. The 44-stream observatory is informationally complete over the d=12 primitive space.

**Average density matrix** (alert-weighted, B-state baseline):

| Metric | Measured | Ideal (I/12) |
|--------|----------|--------------|
| Purity | 0.119 | 0.083 |
| Von Neumann entropy | 2.275 | ln(12) = 2.485 |
| Frobenius dist to I/12 | 0.188 | 0 |

The 43% excess purity over the B-state ideal reflects which physical domains are most active in the current measurement epoch: chirality (Ħ) and coupling (ɢ) lead the diagonal with approximately double the uniform weight, while recognition (Ř) and granularity (Γ) are underweighted. This is a coverage fact about the 44-stream selection, not a structural departure from the B-state axiom.

**Per-snapshot purity** (n=2394): median 0.163, no near-pure snapshots, 2.7% at exact B-state (no alerts). Every snapshot is a mild excitation above the B-state floor.

### Interpretation

Three things are now verified:

1. **Mathematical**: the d=12 SIC fiducial is exact (F/F* = 1.000) -- the measurement frame exists.
2. **Empirical**: the SIC overlap spectrum is uniform (chi2 = 4.68, dof=143) -- the apparatus covers all 144 directions.
3. **Structural**: the average density matrix is close to I/12 -- the B-state ground state is the correct prior.

Full treatment in `sic_povm_convergence.md` §3.4.

## Key coupling findings (from 8-day 15-stream pilot)

The initial pilot (15 base streams, June 14-22 2026) revealed:

- **41 coupling edges** with |r| >= 0.3, 23 at |r| = 1.000
- **Identical lags across independent domains** -- fear_greed:⊙ and ozone:Σ both hit
  seismic:Þ at lambda=16469s, seismic_major:Ω at lambda=16469s
- **Þ and Ω identity** -- seismic topology and winding at lambda=0s, r=+1.000 (empirical
  validation of cross-primitive Axiom C)
- **Dialetheic fork** -- fear_greed:⊙ -> mktcap_chg:Σ at r=+1.000 AND
  fear_greed:⊙ -> mempool_low_fee:ɢ at r=-1.000 from the same source

The 44-stream expansion (adding fine-grained market/macro, biological chirality,
astrophysical chirality, SIC-POVM gap fill, and extraplanetary streams) produces a
much richer coupling graph. Collecting two-plus weeks of 44-stream data is the active
frontier.

## Installation

```bash
# Requires Python >=3.11
cd /home/mrnob0dy666/imsgct/ig-pulse

# With uv (preferred):
uv pip install -e .
```

### Dependencies

- `numpy` -- time series computation
- `scipy` -- Pearson correlation with p-values
- `networkx` -- graph structure

No API keys required. All 44 streams use public endpoints.

## Integration with fin3r

ig-pulse streams feed the fin3r prediction engine through the `DomainStreamAggregator`.
The datanado pipeline in fin3r imports the aggregator directly:

```python
from ig_pulse.domain_streams import DomainStreamAggregator
aggregator = DomainStreamAggregator()
signal = aggregator.refresh()  # 44-stream alert vector
```

All 44 streams contribute to the Algebraic Coupling Bridge's alert vector, conviction
computation, and broadcast propagation. The B-state multiplier (1.50x at >=3 alerts)
feeds directly into the position-sizing coefficient.

## Related documents

- **Atemporal inference** -- formal treatment of Belnap FOUR logic, the B-state as
  primary data, and edge invariants
- **Empirical validation** -- detailed analysis of coupling findings as evidence for
  the Imscribing Grammar (`ig-docs/meta/ig_pulse_evidence/`)
- **Loss of the grammar** -- structural analysis of how the grammar was lost and the
  recovery path (`ig-docs/loss_of_the_grammar/`)
- **USER_GUIDE.md** -- detailed operational guide for running streams, interpreting
  output, and troubleshooting

## License

Unlicense (public domain).

---

The author would like to thank Harry T. Larson, for imparting the importance of
catching rising problems, and never letting them go.
