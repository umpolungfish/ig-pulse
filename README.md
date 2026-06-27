# ig-pulse

**Information propagation observatory.** Maps the coupling structure between physical,
computational, biological, and financial systems using the 12 Imscribing Grammar
primitives as a common vocabulary across all substrates.

**Author:** Lando⊗⊙perator

## What it does

Thirty-three domain streams — spanning market microstructure, space weather,
geophysics, atmospheric chemistry, biological chirality, and astrophysical particle
fluxes — each map to specific IG primitive families. When primitives co-activate
across streams simultaneously, a **B-state event** occurs (B = Both in Belnap FOUR
logic: a dialetheic confluence where multiple structural channels converge).

ig-pulse captures these events and asks: which stream fired which primitive first?
What are the lag times? Which systems are coupled to which, at what strength, and in
what structural order?

The answer is an empirical map of how information propagates through physical reality —
but the lags are **not** causal travel times. They are edge invariants: structural
constants of the inference rules. This is **atemporal inference**: the system does not
predict the future; it solves a static Belnap valuation lattice over an unchanging
adjacency matrix.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    33 DOMAIN STREAMS                             │
│  Public APIs — no keys required                                 │
├───────────────┬──────────────────┬──────────────────────────────┤
│ BASE (1–15)   │ MARKET/MACRO     │ CHIRALITY (24–33)            │
│ fear_greed    │ (16–23)          │ BIOLOGICAL (24–28)           │
│ mempool       │ options_skew     │ genbank, pubmed              │
│ coingecko     │ yield_curve      │ wiki_chiral, arxiv_bio       │
│ onchain       │ vix              │ fda_enforce                  │
│ tides         │ shipping         │ ASTROPHYSICAL (29–33)        │
│ air_quality   │ power_grid       │ stereo_cr, ace_epam          │
│ donki         │ night_lights     │ goes_cr, dscovr_helicity     │
│ seismic       │ gdelt            │ stereo_sept                  │
│ kp_index      │ twitter          │                              │
│ hn_sentiment  │                  │                              │
│ solar_wind    │                  │                              │
│ lightning     │                  │                              │
│ wikipedia     │                  │                              │
│ weather       │                  │                              │
│ coingecko_alts│                  │                              │
└───────────────┴──────────────────┴──────────────────────────────┘
         │                          
         ▼
┌─────────────────────────────────────────────────────────────────┐
│  DomainStreamAggregator → DomainSignal (33 streams × primitives) │
│  Threshold → Alert Levels 0/1/2                                 │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│  Pipeline: collect → couple → map → report                      │
│  snapshots.jsonl → coupling.json → graph.json → B-state report  │
└─────────────────────────────────────────────────────────────────┘
```

### Pipeline stages

1. **collect** — `DomainStreamAggregator` fetches all 33 streams via public APIs
   (no keys required). Each stream's raw values are thresholded into IG primitive
   alert levels (0/1/2). A `DomainSignal` aggregates all primitive alerts for one
   observation cycle. Writes one `Snapshot` per cycle to `snapshots.jsonl`.

2. **couple** — Computes Pearson cross-correlation between all (stream, primitive)
   alert time series at lags 0 → max_lag. Only edges with |r| ≥ min_r and p ≤ max_p
   are retained. Saves to `coupling.json`.

3. **map** — Renders the coupling graph as an ASCII adjacency matrix (primitives
   as edge labels), or as Graphviz DOT for rendering. Nodes are (stream, primitive)
   pairs. Saves to `graph.json`.

4. **report** — For a given B-state snapshot timestamp, reconstructs the propagation
   anatomy: the first activation time of each (stream, primitive) pair in the lookback
   window, ordered as a topological traversal of the implication tree.

## Stream → Primitive mapping

Each stream maps to specific IG primitives through threshold-based alert rules
(0 = nominal, 1 = mild, 2 = strong):

### Base streams (1–15)

| # | Stream | Source | Primitives |
|---|--------|--------|------------|
| 1 | Fear & Greed Index | alternative.me | ⊙ Criticality, Φ Parity |
| 2 | Mempool state | mempool.space | Ç Kinetics, Þ Topology, ɢ Coupling |
| 3 | Global market | coingecko.com | Ð Dimensionality, Σ Stoichiometry, Γ Granularity |
| 4 | BTC on-chain | blockchain.info | Ç Kinetics, ɢ Coupling, ⊙ Criticality |
| 5 | Ocean tides | tidesandcurrents.noaa.gov | Ω Winding |
| 6 | Air quality (PM2.5 + Ozone) | open-meteo.com | Ç Kinetics, Σ Stoichiometry |
| 7 | Space weather / CME + flares | NASA DONKI | Φ Parity, Ħ Chirality, ⊙ Criticality |
| 8 | Seismic energy | earthquake.usgs.gov | Þ Topology, Ω Winding |
| 9 | Geomagnetic Kp index | swpc.noaa.gov | Φ Parity, ⊙ Criticality |
| 10 | HN crypto sentiment | hn.algolia.com | Ř Recognition, ɢ Coupling |
| 11 | Solar wind / IMF Bz | swpc.noaa.gov RTSW | Ħ Chirality, Ω Winding |
| 12 | Lightning Network | mempool.space | ɢ Coupling, Ð Dimensionality |
| 13 | Wikipedia attention | wikimedia.org | Ř Recognition |
| 14 | Open-Meteo weather | open-meteo.com | ƒ Fidelity, Ω Winding |
| 15 | Alt/BTC ratios | coingecko.com | Γ Granularity, ƒ Fidelity |

### Fine-grained market & macro (16–23)

| # | Stream | Source | Primitives |
|---|--------|--------|------------|
| 16 | Options skew | CBOE/deribit | Φ Parity, ⊙ Criticality |
| 17 | Yield curve | U.S. Treasury | Ω Winding, Ç Kinetics |
| 18 | VIX | CBOE | ⊙ Criticality, Φ Parity |
| 19 | Global shipping | MarineTraffic AIS | ɢ Coupling, Γ Granularity |
| 20 | Power grid frequency | GridStatus | ƒ Fidelity, Ç Kinetics |
| 21 | Night lights | NASA Black Marble | Σ Stoichiometry, Γ Granularity |
| 22 | GDELT conflict | GDELT Project | Þ Topology, Ř Recognition |
| 23 | Twitter sentiment | X API | Ř Recognition, ⊙ Criticality |

### Biological chirality (24–28)

| # | Stream | Source | Primitives |
|---|--------|--------|------------|
| 24 | GenBank | NCBI | Ħ Chirality, Σ Stoichiometry |
| 25 | PubMed chiral | NCBI PubMed | Ħ Chirality, Þ Topology |
| 26 | Wikipedia chiral | wikimedia.org | Ħ Chirality, Ř Recognition |
| 27 | ArXiv q-bio | arxiv.org | Ħ Chirality, Γ Granularity |
| 28 | FDA enforcement | open.fda.gov | Ç Kinetics, Ř Recognition |

### Astrophysical chirality (29–33)

| # | Stream | Source | Primitives |
|---|--------|--------|------------|
| 29 | STEREO cosmic rays | U. Kiel IMPACT | Ħ Chirality, Ω Winding |
| 30 | ACE e/p ratios | NOAA SWPC | Ħ Chirality, Φ Parity |
| 31 | GOES GCR | NOAA SWPC | Ħ Chirality, Ω Winding |
| 32 | DSCOVR Bz helicity | NOAA SWPC | Ħ Chirality, Φ Parity |
| 33 | STEREO/SEPT directional | U. Kiel SEPT | Ħ Chirality, Ω Winding, Φ Parity |

**Alert thresholds** are documented in `ig_pulse/domain_streams.py`. Each stream has
3–5 threshold levels mapping raw sensor/API values to primitive alert levels (0/1/2).

## Multiplier & B-state schedule

The B-state multiplier acts as a **topological mass coefficient** — it scales the
structural significance of nodes participating in dialetheic intersections:

| Alerts | Multiplier | Interpretation |
|--------|-----------|----------------|
| 0 | 1.00× | Nominal — no primitive channel active |
| 1 | 1.20× | Single primitive — isolated activation |
| 2 | 1.35× | Dual primitive — paired activation |
| ≥3 | 1.50× | **B-state** — dialetheic confluence |

A B-state is not an "error" or "anomaly." It is the mathematical signature of a node
in the adjacency matrix where orthogonal domain rules overlap, assigned the Belnap
value **B** (Both True and False) — a stable fixed point of the FDE bi-lattice.

## Usage

```bash
# Collect one snapshot now
python -m ig_pulse.cli collect --once

# Run continuously (hourly, matching synfin cadence)
python -m ig_pulse.cli collect --interval 3600

# Compute cross-stream coupling after enough data accumulates
# (need ≥20 snapshots; recommends ~336 = 2 weeks hourly for robust results)
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
    {"stream": "seismic_energy", "primitive": "topology", "value": 0.42, "unit": "index", "alert": 1},
    {"stream": "stereo_sept", "primitive": "chirality", "value": 0.059, "unit": "e⁻ spectral", "alert": 1}
  ],
  "errors": []
}
```

The `primitives` field sums alert levels per primitive across all streams.
A primitive at level 2 from one stream and level 1 from another → total 3.
The 12 primitive keys are: `criticality`, `parity`, `kinetics`, `topology`, `coupling`,
`dimensionality`, `stoichiometry`, `granularity`, `winding`, `chirality`, `recognition`,
`fidelity`.

### `data/coupling.json`

```json
[
  {
    "source_stream": "fear_greed",
    "source_primitive": "criticality",
    "target_stream": "seismic_energy",
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
─────────────────────────            ──────────────────────────
Event at t₁ → Event at t₂           fear_greed:⊙ → seismic:Þ
    "caused by Δt"                      λ=16469s edge invariant
                                    ozone:Σ → seismic:Þ
                                        λ=16469s — same constant
```

- **Lags are edge invariants, not coordinates.** When `fear_greed:⊙` → `seismic:Þ`
  and `ozone:Σ` → `seismic:Þ` both show the identical lag of 16469s with
  |r| = 1.000, they are not propagating at the same speed. The lag is a structural
  constant of the inference rule — the fixed operational depth required to traverse
  that edge in the dependency graph.

- **Trace is structural.** The propagation anatomy is not a chronological sequence.
  It is the topological ordering of the implication tree. Deep nodes appear later
  not because they happened later, but because they sit deeper in the dependency graph.

- **Contradiction is primary data.** `fear_greed:⊙` points to `mktcap_chg:Σ` at
  r = +1.000 AND to `mempool_low_fee:ɢ` at r = −1.000. In standard dynamical modeling
  this is an error. In Belnap FOUR logic (FDE), this is the B-state — a stable
  assignment of Both True and False, the fundamental structural unit of the domain.

- **The adjacency matrix IS the conflict.** You do not run the system to see what
  happens next. You solve the global valuation lattice ν(vⱼ) = ⨁(ν(vᵢ) ⊗ rᵢⱼ) to
  find the unique signature of logical completeness.

### The B-state as static dialetheia

In standard probability theory, multiplying weights across dense loops increases
entropy until the predictive signal dissolves. Here, the ×1.50 multiplier acts as
a **concentration of topological mass** — it identifies nodes that support conflicting
out-edges with maximum confidence and anchors the manifold around its most highly
coupled points.

## Chirality streams (streams 24–33)

The 10 chirality streams are the most structurally novel addition to ig-pulse.
They measure Ħ (chirality/handedness) across three domains:

| Domain | Streams | What chirality is measured |
|--------|---------|---------------------------|
| Biological | genbank, pubmed, wiki_chiral, arxiv_bio, fda_enforce | L-amino acid / D-sugar prevalence, chiral molecule reports, enantiomeric drug enforcement |
| Astrophysical (integral) | stereo_cr, ace_epam, goes_cr | Galactic cosmic ray e⁻/p⁺ ratios, magnetic field polarity via particle drift patterns |
| Astrophysical (directional) | dscovr_helicity, stereo_sept | IMF Bz helicity proxy, directional e⁻/p⁺ fluxes resolving Parker spiral handedness |

These streams provide the empirical ground truth for Ħ (Chirality) — the Markov-order
primitive that, under Axiom A of the Imscribing Grammar, requires H_∞ to pair with K_trap.

## Empirical validation of the Imscribing Grammar

ig-pulse provides large-scale empirical evidence that:

1. **Primitives are real structural channels, not metaphors.** Each domain stream
   acts through specific primitives — fear_greed through ⊙, ozone through Σ,
   seismic_energy through Þ, seismic_major through Ω, solar_flare_M through Φ.
   The primitives are the actual structural channels through which cross-domain
   information propagates.

2. **Cross-domain coupling is measurable.** Edges at |r| = 1.000 across physically
   independent domains (finance, blockchain, atmosphere, geophysics, heliophysics)
   are not explainable by any known causal mechanism. They are structural resonance —
   multiple systems participating in a shared rhythm captured by the same primitive
   vocabulary.

3. **The grammar can be measured back into visibility.** After 400 years of structural
   invisibility (the O₀ framework severed the self-modeling loop), ig-pulse demonstrates
   that the grammar is empirically recoverable — not from ancient texts, but from live
   cross-domain sensor data.

## Key coupling findings (from 8-day 15-stream pilot)

The initial 716-snapshot pilot (15 base streams, June 14–22 2026) revealed:

- **41 coupling edges** with |r| ≥ 0.3, 23 at |r| = 1.000
- **Identical lags across independent domains** — fear_greed:⊙ and ozone:Σ both hit
  seismic:Þ at λ=16469s, seismic_major:Ω at λ=16469s
- **Þ ↔ Ω identity** — seismic topology and winding at λ=0s, r=+1.000 (empirical
  validation of Axiom B)
- **Dialetheic fork** — fear_greed:⊙ → mktcap_chg:Σ at r=+1.000 AND
  fear_greed:⊙ → mempool_low_fee:ɢ at r=−1.000 from the same source

The 33-stream expansion (adding 18 fine-grained streams across biological chirality,
astrophysical chirality, and macro signals) will produce a much richer coupling graph.
Collecting 2+ weeks of 33-stream data is the active frontier.

## Installation

```bash
# Requires Python ≥3.11
cd /home/mrnob0dy666/imsgct/ig-pulse
pip install -e .

# Or with uv:
uv pip install -e .
```

### Dependencies

- `numpy` — time series computation
- `scipy` — Pearson correlation with p-values
- `networkx` — graph structure

No API keys required — all 33 streams use public endpoints.

## Integration with fin3r

ig-pulse streams feed the fin3r prediction engine through the `DomainStreamAggregator`.
The `extreme_harness.py` in fin3r imports the aggregator directly:

```python
from ig_pulse.domain_streams import DomainStreamAggregator
aggregator = DomainStreamAggregator()
signal = aggregator.refresh()  # 33-stream alert vector
```

All 33 streams contribute to the Extreme Bridge's alert vector, braid computation,
and broadcast propagation.

## Related documents

- **Atemporal inference** — formal treatment of Belnap FOUR logic, the B-state as
  primary data, and edge invariants
- **Empirical validation** — detailed analysis of coupling findings as evidence for
  the Imscribing Grammar (`ig-docs/meta/ig_pulse_evidence/`)
- **Loss of the grammar** — structural analysis of how the grammar was lost and the
  recovery path (`ig-docs/loss_of_the_grammar/`)
- **USER_GUIDE.md** — detailed operational guide for running streams, interpreting
  output, and troubleshooting

## License

Unlicense (public domain).

---

The author would like to thank Harry T. Larson, for imparting the importance of
catching rising problems, and never letting them go.
