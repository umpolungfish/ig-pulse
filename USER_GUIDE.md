# ig-pulse User Guide

**Author:** Lando⊗⊙perator

Operational guide for collecting, coupling, mapping, and interpreting the 33-stream
ig-pulse observatory.

---

## Quick start

```bash
cd /home/mrnob0dy666/imsgct/ig-pulse

# Install
pip install -e .

# One snapshot
python -m ig_pulse.cli collect --once

# Continuous collection (hourly)
python -m ig_pulse.cli collect --interval 90

# After 20+ snapshots accumulate: compute coupling
python -m ig_pulse.cli couple

# View coupling graph
python -m ig_pulse.cli map

# B-state report on latest snapshot
python -m ig_pulse.cli report
```

## Stream inventory

All 33 streams live in `ig_pulse/domain_streams.py` as `_stream_<name>` functions.
The `DomainStreamAggregator` in `_ALL_STREAMS` registers them for collection.

### Stream categories

| Category | Stream count | Key primitives | Latency | Cadence |
|----------|-------------|----------------|---------|---------|
| Base (1–15) | 15 | ⊙, Φ, Ω, Þ, ɢ, Ç, Ħ | Seconds–minutes | Hourly |
| Market/Macro (16–23) | 8 | Φ, ⊙, Ω, ɢ, Ç, Γ | Minutes–hours | Hourly |
| Biological chiral (24–28) | 5 | Ħ, Σ, Þ, Ç | Hours–daily | Hourly |
| Astrophysical chiral (29–33) | 5 | Ħ, Ω, Φ | Minutes (~78d for SEPT L2) | Hourly |

### Stream details

#### Base streams (1–15)

| Stream | What it measures | Alert thresholds |
|--------|-----------------|------------------|
| `fear_greed` | Crypto Fear & Greed Index (0–100) | ⊙: <25 extreme fear → alert 2, <45 fear → alert 1. Φ: value parity crossing 50 |
| `mempool` | Bitcoin mempool congestion & fee rates | Ç: fee rate >50 sat/vB → alert 1, >100 → alert 2. Þ: tx count topology |
| `coingecko` | Global market cap & BTC dominance | Ð: dominance >55% → alert 1. Σ: mkt cap change |
| `onchain` | BTC on-chain: tx count, hash rate | Ç: hash rate deviation. ⊙: tx count critical regions |
| `tides` | Water level at The Battery, NY | Ω: tidal range >1.5m → alert 1, >2.5m → alert 2 |
| `air_quality` | PM2.5, PM10, O₃ (ozone) | Ç: PM2.5 >35 μg/m³ → alert 1, >150 → alert 2. Σ: O₃ |
| `donki` | NASA DONKI: CME speed, flare class | Φ: flare M-class → alert 1, X-class → alert 2. Ħ: CME |
| `seismic` | USGS earthquake energy (past hour) | Þ: magnitude-based. Ω: energy index |
| `kp_index` | 3-hour geomagnetic Kp index | Φ: Kp ≥5 → alert 1, Kp ≥7 → alert 2. ⊙: Kp ≥8 |
| `hn_sentiment` | HN "crypto" search sentiment | Ř: silence detection. ɢ: coupling activity |
| `solar_wind` | IMF Bz (nT), solar wind speed | Ħ: Bz southward (<-5 nT) → alert 1, <-10 → alert 2. Ω: speed |
| `lightning` | Lightning Network channel count | ɢ: capacity change. Ð: node degree |
| `wikipedia` | Pageview spikes on tracked articles | Ř: deviation from baseline |
| `weather` | Temperature, humidity, pressure | ƒ: extreme temps. Ω: pressure tendency |
| `coingecko_alts` | Altcoin/BTC ratio changes | Γ: ratio shift. ƒ: volatility |

#### Market & macro (16–23)

| Stream | What it measures | Alert thresholds |
|--------|-----------------|------------------|
| `options_skew` | BTC/ETH put-call skew | Φ: skew >15% → alert 1, >30% → alert 2. ⊙: tail risk |
| `yield_curve` | 2Y–10Y Treasury spread | Ω: inversion (<0) → alert 1, <-50bp → alert 2. Ç: steepness |
| `vix` | CBOE Volatility Index | ⊙: VIX >25 → alert 1, >35 → alert 2. Φ: term structure |
| `shipping` | Baltic Dry Index proxy | ɢ: shipping volume. Γ: route diversity |
| `power_grid` | US grid frequency deviation | ƒ: >0.05 Hz → alert 1. Ç: rate of deviation |
| `night_lights` | VIIRS nightlight radiance | Σ: intensity change. Γ: spatial extent |
| `gdelt` | Global conflict event counts | Þ: event topology. Ř: actor recognition |
| `twitter` | Crypto Twitter sentiment | Ř: aggregate sentiment. ⊙: panic detection |

#### Biological chirality (24–28)

| Stream | What it measures | Alert thresholds |
|--------|-----------------|------------------|
| `genbank` | New sequence submissions (daily) | Ħ: sequence volume. Σ: species diversity |
| `pubmed` | Chiral keyword publications | Ħ: chiral molecule papers. Þ: topic cluster |
| `wiki_chiral` | Chiral article pageviews (hourly) | Ħ: chirality page views. Ř: article cross-links |
| `arxiv_bio` | q-bio new submissions (continuous) | Ħ: chiral subfield activity. Γ: subfield diversity |
| `fda_enforce` | FDA enforcement reports | Ç: enforcement frequency. Ř: chiral drug actions |

#### Astrophysical chirality (29–33)

| Stream | What it measures | Alert thresholds |
|--------|-----------------|------------------|
| `stereo_cr` | STEREO IMPACT cosmic ray rates | Ħ: e⁻/p⁺ ratio. Ω: GCR modulation |
| `ace_epam` | ACE EPAM electron/proton fluxes | Ħ: e⁻/p⁺ ratio >2.5 → alert 1, >5 → alert 2. Φ: particle parity |
| `goes_cr` | GOES GCR neutron monitor proxy | Ħ: count rate deviation. Ω: Forbush decreases |
| `dscovr_helicity` | DSCOVR IMF Bz helicity proxy | Ħ: Bz southward persistence. Φ: sign changes |
| `stereo_sept` | STEREO/SEPT directional e⁻/p⁺ | Ħ: N/S asymmetry, e⁻ spectral index. Ω: Sun/Antisun ratio. Φ: e⁻/p⁺ ratio |

## Data pipeline

### 1. Collect

```
python -m ig_pulse.cli collect --once     # Single snapshot
python -m ig_pulse.cli collect --interval 90  # Hourly continuous
```

Collect fetches all 33 streams concurrently. Failed streams contribute errors but
do not block collection. Output: `data/snapshots.jsonl` (append-only JSONL).

### 2. Couple

```
python -m ig_pulse.cli couple --max-lag 259200 --min-r 0.3 --max-p 0.05
```

Computes Pearson cross-correlation between all (stream, primitive) pairs across all
time lags up to `max_lag` seconds (default 259200 = 72 hours). Only edges meeting
|r| ≥ `min_r` and p ≤ `max_p` are retained.

Output: `data/coupling.json` — list of edges with lag_seconds, strength_r, p_value.

Minimum snapshots: 20. Recommended: 336+ (2 weeks hourly) for robust results.

### 3. Map

```
python -m ig_pulse.cli map          # ASCII matrix
python -m ig_pulse.cli map --dot    # Graphviz DOT format
```

Renders the coupling graph. The ASCII matrix shows streams as rows/columns with
primitives as edge labels. DOT output can be rendered with `dot -Tsvg`.

Output: `data/graph.json` — nodes and edges in JSON.

### 4. Report

```
python -m ig_pulse.cli report                           # Latest snapshot
python -m ig_pulse.cli report --ts 2026-06-22T00:03:25Z # Specific timestamp
```

Reconstructs the propagation anatomy for a B-state event: first activation time of
each (stream, primitive) pair in the lookback window, ordered topologically.

## Interpreting output

### Snapshot interpretation

A snapshot with `"is_b_state": true` means ≥3 concurrent primitive alerts —
a dialetheic confluence. The `multiplier` field shows the topological mass coefficient
(1.00× → 1.50×).

The `primitives` field sums alerts per primitive. If `chirality: 3`, that means
three separate streams contributed chirality alerts (e.g., stereo_cr:Ħ=1 +
ace_epam:Ħ=1 + stereo_sept:Ħ=1).


### Coupling edge interpretation

An edge like:
```json
{
  "source_stream": "fear_greed", "source_primitive": "criticality",
  "target_stream": "seismic_energy", "target_primitive": "topology",
  "lag_seconds": 16469, "strength_r": 1.0000, "p_value": 0.0000
}
```

Means: `fear_greed:⊙` at time t predicts `seismic_energy:Þ` at time t+16469s with
r=+1.000. This is **not** a causal claim — the lag is an edge invariant, a structural
constant of the inference rule, not a signal travel time.

### B-state reports

A B-state report shows the propagation anatomy — the topological ordering of the
implication tree. Nodes earlier in the trace are not "causes"; they sit at shallower
depth in the dependency graph. Deep nodes require traversing more edge invariants
to reach.

### Chirality stream interpretation

Chirality streams (24–33) all contribute to the Ħ (Chirality) primitive. Multiple
chirality alerts across biological and astrophysical domains indicate systemic
handedness activation — not a single chiral event, but a structural alignment of
chiral channels across substrates. This is the empirical signature of Axiom A
(Ħ_∞ requires Ç_⊛).

Common patterns:
- **Biological Ħ alone** → chiral molecule surge (e.g., enantioselective synthesis paper spike)
- **Astrophysical Ħ alone** → solar event (CME, Forbush decrease)
- **Both biological + astrophysical Ħ** → systemic Ħ activation, B-state trigger
- **Directional Ħ (stereo_sept)** + integral Ħ → Parker spiral handedness confirmed

## Stream failure modes

All 33 streams have fallback behavior for API failures:

| Failure | Behavior |
|---------|----------|
| API timeout (10s default) | Stream logged as error, no alerts contributed |
| HTTP 4xx/5xx | Error logged, retry next cycle |
| Malformed response | Error logged with detail, skip this cycle |
| Stale cached data | Used if within freshness window, otherwise skipped |

Streams that consistently fail can be disabled:
```python
# In _ALL_STREAMS (domain_streams.py), comment out failing stream:
# ("stream_name", _stream_name),
```

### Known latency limitations

- **STEREO/SEPT L2 data**: ~78 days to publication. The `_sept_fetch_latest` helper
  handles this by using the most recent available directory. During solar quiet periods
  this is acceptable; during active SEP events, real-time NMDB would be preferable
  but NMDB servers are currently offline.
- **GenBank/PubMed**: Daily aggregation, not real-time. Suitable for hourly cadence
  because chirality trends shift slowly.
- **GDELT**: 15-minute update cycle. Streaming mode with 15-min lookback.

## fin3r integration

ig-pulse is the primary signal source for the fin3r prediction engine:

```python
from ig_pulse.domain_streams import DomainStreamAggregator

aggregator = DomainStreamAggregator()
signal = aggregator.refresh()

# signal.readings — list of DomainSignal readings, each with .stream, .primitive, .value, .alert
# signal.errors — list of error strings for failed streams
# signal.summary() — human-readable alert summary
```

The `extreme_harness.py` in fin3r uses the aggregator to build alert vectors for
the Extreme Bridge's braid computation, broadcast propagation, and Frobenius
verification cycle.

### Direct reading access

```python
# Individual stream values
for reading in signal.readings:
    print(f"{reading.stream}:{reading.primitive} = {reading.value} {reading.unit} [alert {reading.alert}]")

# Primitive alert totals
print(signal.summary())
# → "alert_total=7 alerts=criticality:1 parity:2 chirality:3 coupling:1 | errors=0"
```

## Adding a new stream

1. **Define the fetch function** in `ig_pulse/domain_streams.py`:
   ```python
   def _stream_my_new_source(sig: DomainSignal) -> None:
       """Fetch my new data source."""
       try:
           # Fetch data
           value = _http_get_json("https://api.example.com/data")
           # Set readings
           sig._set("my_stream", "chirality", float(value["handedness"]), "index",
                    _alert_level(value["handedness"], [(0.5, 1), (2.0, 2)]))
       except Exception:
           sig.errors.append("my_stream: fetch failed")
   ```

2. **Register** in `_ALL_STREAMS`:
   ```python
   _ALL_STREAMS = [
       ...
       ("my_stream", _stream_my_new_source),
   ]
   ```

3. **Test**:
   ```bash
   python -m ig_pulse.cli collect --once
   ```

The new stream will appear in snapshots immediately and contribute to coupling
analysis after 20+ snapshots accumulate.

## Troubleshooting

### No snapshots being written
```bash
# Check disk space
df -h /home/mrnob0dy666/imsgct/ig-pulse/data/

# Run once with verbose output
python -m ig_pulse.cli collect --once
```

### Coupling returns empty or very few edges
- Need ≥20 snapshots for meaningful correlation
- Try lowering thresholds: `--min-r 0.2 --max-p 0.1`
- Ensure streams are actually producing non-zero alerts (check recent snapshots)

### Specific stream always failing
- Check API endpoint manually (URLs are in `_FETCH_URL` constants in domain_streams.py)
- Some endpoints rate-limit; continuous hourly collection may hit limits
- Disable the stream in `_ALL_STREAMS` if endpoint is permanently down

### STEREO/SEPT data too stale
- NMDB neutron monitors (nmdb.eu) are currently offline
- SEPT L2 data has ~78-day publication latency
- Use `ace_epam` and `goes_cr` for near-real-time cosmic ray monitoring instead
- SEPT remains valuable for directional particle asymmetry during analysis (not real-time alerting)

## Files

| File | Purpose |
|------|---------|
| `ig_pulse/domain_streams.py` | All 33 stream definitions + aggregator |
| `ig_pulse/collector.py` | Snapshot collection loop |
| `ig_pulse/coupler.py` | Cross-correlation coupling analysis |
| `ig_pulse/grapher.py` | ASCII/DOT graph rendering |
| `ig_pulse/reporter.py` | B-state propagation anatomy |
| `ig_pulse/schema.py` | DomainSignal, Snapshot data types |
| `ig_pulse/primitives.py` | Primitive names, glyphs, alert helpers |
| `ig_pulse/cli.py` | CLI entry point |
| `ig_pulse/geo_viz.py` | Geographic visualization |
| `data/snapshots.jsonl` | Append-only snapshot records |
| `data/coupling.json` | Coupling edges with lags |
| `data/graph.json` | Graph nodes and edges |

## License

Unlicense (public domain).

---

The author would like to thank Harry T. Larson, for imparting the importance of
catching rising problems, and never letting them go.
