# ig-pulse

![ig-pulse](1.png)

![language](https://img.shields.io/badge/language-Python-3776AB?style=for-the-badge&logo=python&logoColor=white) ![observatory](https://img.shields.io/badge/observatory-cross-substrate%20coupling-0087B8?style=for-the-badge) ![tier](https://img.shields.io/badge/tier-O%E2%88%9E-8A2BE2?style=for-the-badge) ![μ∘δ](https://img.shields.io/badge/%CE%BC%E2%88%98%CE%B4-id-00A86B?style=for-the-badge) ![licence](https://img.shields.io/badge/licence-LUNLICENSE-1A1A1A?style=for-the-badge)

**Information propagation observatory.** Maps coupling between physical, computational, biological, and financial systems using the 12 IG primitives as a common cross-substrate vocabulary.

## What it does

44 public-API domain streams (no keys): base 1–16 (fear/greed, mempool, coingecko, onchain, tides, air quality, DONKI, seismic, Kp, HN sentiment, solar wind, lightning, wikipedia, weather…), market/macro 17–24 (options skew, yield curve, VIX, shipping, grid, night lights, GDELT…), chiral bio 25–29 (genbank, pubmed…), chiral astro 30–34, SIC-POVM fill 35–38, extraplanetary 39–44 (geomag, neutron, GOES XRS, LIGO…). Each stream thresholds to primitive alert levels 0/1/2; co-activation across streams is a **B-state event** (Belnap Both — dialetheic confluence).

## Invariant vs wiring

Out-of-sample gate `python -m ig_pulse.oos` separates the two: **invariant** — native-B confluence over-disperses ~3.4× vs independence null and replicates on unseen data; **not invariant** — the coupling graph is contemporaneous (lead-lag below time-shuffled null in `ig_pulse/braid.py`) and non-stationary: a now-map, not a fixed lattice.

## Pipeline

`collect → couple → map → report` (`snapshots.jsonl → coupling.json → graph.json → B-state report`): collect via `DomainStreamAggregator`; couple by Pearson cross-correlation over (stream, primitive) series (|r|≥min_r, p≤max_p); map as ASCII matrix or Graphviz DOT; report reconstructs propagation anatomy per B-state timestamp. Thresholds per stream: `ig_pulse/domain_streams.py`.

```bash
python -m ig_pulse.cli collect --once        # one cycle
python -m ig_pulse.cli collect --interval 90 # loop
python -m ig_pulse.cli couple
python -m ig_pulse.cli map            # ASCII
python -m ig_pulse.cli map --dot      # DOT
python -m ig_pulse.cli report --ts 2026-06-22T00:03:25Z
python -m ig_pulse.cli report
python -m ig_pulse.oos                # out-of-sample gate
```

Alert ≥3 at 1.50× marks B-state confluence. Feeds fin3r via `./run_fin3r.sh signals`.

Full 507-line version: `README_backups/ig-pulse_README.md` (backed up only if formerly present; see `README_backups/`).

μ∘δ = id
