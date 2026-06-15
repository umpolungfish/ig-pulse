# ig-pulse

Information propagation observatory. Maps the coupling structure between physical,
computational, and financial systems using the 12 Imscribing Grammar primitives as
a common vocabulary across all substrates.

## What it does

Ten domain streams — solar wind, geomagnetic field, seismic energy, ocean tides,
air quality, mempool congestion, on-chain activity, global market state, fear/greed
index, and tech sentiment — each map to specific IG primitive families. When
primitives co-activate across streams simultaneously, a B-state event occurs.

ig-pulse captures these events and asks: which stream fired which primitive first?
What are the lag times? Which systems are coupled to which, at what strength, and
in what causal order?

The answer is an empirical map of how information propagates through physical reality.

## Stream → Primitive mapping

| Stream | Primitives |
|--------|-----------|
| fear/greed | ⊙ Criticality, Φ Parity |
| mempool | Ç Kinetics, Þ Topology, ɢ Coupling |
| global market (coingecko) | Ð Dimensionality, Σ Stoichiometry, Γ Granularity |
| BTC on-chain | Ç Kinetics, ɢ Coupling, ⊙ Criticality |
| ocean tides (NOAA) | Ω Winding |
| air quality | Ç Kinetics, Σ Stoichiometry |
| solar/CME (NASA DONKI) | Φ Parity, Ħ Chirality, ⊙ Criticality |
| seismic (USGS) | Þ Topology, Ω Winding |
| geomagnetic Kp (NOAA) | Φ Parity, ⊙ Criticality |
| HN sentiment | Ř Recognition, ɢ Coupling |

## Usage

```bash
# Collect one snapshot now
python -m ig_pulse.cli collect --once

# Run continuously (hourly, matching synfin cadence)
python -m ig_pulse.cli collect --interval 3600

# Compute cross-stream coupling after enough data accumulates
python -m ig_pulse.cli couple

# Display coupling graph as ASCII matrix
python -m ig_pulse.cli map

# Display as Graphviz DOT
python -m ig_pulse.cli map --dot

# Reconstruct propagation anatomy for a B-state event
python -m ig_pulse.cli report --ts 2026-06-14T13:48:11Z

# Report on latest snapshot
python -m ig_pulse.cli report
```

## Data

`data/snapshots.jsonl` — append-only log, one JSON object per collection cycle:

```json
{
  "ts": "2026-06-14T22:39:57Z",
  "multiplier": 1.50,
  "total_alerts": 12,
  "is_b_state": true,
  "primitives": {"criticality": 2, "parity": 1, "topology": 2, ...},
  "readings": [
    {"stream": "fear_greed", "primitive": "criticality", "value": 18.0, "unit": "index", "alert": 2},
    ...
  ]
}
```

## Physical coupling priors

Known ground-truth lags the coupling analysis should recover:

- **CME → Kp**: 18–72h (solar wind travel time Earth–Sun distance)
- **Kp → fear/greed**: 24–48h (geomagnetic → behavioral)
- **mempool ↔ global market**: ~0h (co-financial layer)
- **seismic ↔ tidal**: unknown (solid Earth tide coupling)

Meaningful coupling analysis requires approximately 2 weeks of hourly snapshots
(~336 data points). The `couple` command will report if the corpus is too small.

## License

Unlicense (public domain).
