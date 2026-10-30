from __future__ import annotations
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
import numpy as np
from scipy import stats
from .schema import Snapshot, load_snapshots

PRIMITIVES = [
    "criticality", "parity", "kinetics", "topology", "coupling",
    "dimensionality", "stoichiometry", "granularity",
    "winding", "chirality", "recognition", "fidelity",
]

STREAMS = [
    "fear_greed", "mempool", "coingecko", "blockchain_info",
    "noaa_tides", "air_quality", "nasa_donki", "usgs_seismic",
    "noaa_kp", "hn_sentiment",
]


@dataclass
class CouplingEdge:
    source_stream: str
    source_primitive: str
    target_stream: str
    target_primitive: str
    lag_seconds: int
    strength_r: float
    p_value: float

    def label(self) -> str:
        return (
            f"{self.source_stream}:{self.source_primitive} "
            f"→ {self.target_stream}:{self.target_primitive} "
            f"lag={self.lag_seconds}s r={self.strength_r:.3f} p={self.p_value:.3f}"
        )


def _infer_interval_seconds(snaps: List[Snapshot]) -> int:
    """Infer median collection interval from snapshot timestamps."""
    if len(snaps) < 2:
        return 3600
    def parse(ts: str) -> float:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
    diffs = [parse(snaps[i+1].ts) - parse(snaps[i].ts) for i in range(len(snaps) - 1)]
    return max(1, int(np.median(diffs)))


# Per-station seismic streams are named seismic_{NET}_{STA} (e.g. seismic_IU_SLBS).
# The geo map wants every station as its own node, but for coupling they all
# measure the same earthquakes — thousands of them would blow the O(keys^2)
# correlation loop up to millions of pairs. Collapse each to its network so the
# analysis stays bounded (~14 networks) while preserving inter-network structure.
# NET/STA are uppercase, so this never matches seismic_energy / seismic_major.
_SEISMIC_STATION_RE = re.compile(r"^seismic_([A-Z0-9]+)_[A-Z0-9]+$")


def _coupling_stream_name(stream: str) -> str:
    """Normalize a raw stream name to its coupling-analysis identity."""
    m = _SEISMIC_STATION_RE.match(stream)
    if m:
        return f"seismic_net_{m.group(1)}"
    return stream


def _build_series(snaps: List[Snapshot]) -> dict[tuple[str, str], np.ndarray]:
    """Single pass: build a per-(coupling stream, primitive) alert series.

    Streams are normalized via _coupling_stream_name; when several raw streams
    collapse to the same coupling name (per-station seismic), the alert values
    are combined by max per timestamp (any station firing = network active).
    All-zero series are dropped.
    """
    n = len(snaps)
    series: dict[tuple[str, str], np.ndarray] = {}
    for i, s in enumerate(snaps):
        for r in s.readings:
            key = (_coupling_stream_name(r.stream), r.primitive)
            arr = series.get(key)
            if arr is None:
                arr = np.zeros(n)
                series[key] = arr
            if r.alert > arr[i]:
                arr[i] = float(r.alert)
    return {k: v for k, v in series.items() if v.sum() > 0}


def _cross_correlate(x: np.ndarray, y: np.ndarray, max_lag: int) -> tuple[int, float, float]:
    """Lag with the strongest |Pearson r| between x[:n-lag] and y[lag:].

    Vectorized: r is computed for every lag at once via prefix sums (per-lag
    mean/variance of the trimmed windows) and one FFT-backed cross-correlation
    for the numerator, instead of an O(max_lag) loop of scipy.stats.pearsonr.
    The p-value — the expensive part — is then computed once, for the winning
    lag only. Results are identical to the naive loop (validated to 1e-6).
    """
    n = len(x)
    max_lag = min(max_lag, n - 10)  # each trimmed window needs ≥10 points
    if max_lag < 0:
        return 0, 0.0, 1.0
    lags = np.arange(0, max_lag + 1)
    m = (n - lags).astype(float)  # window length per lag

    px = np.concatenate(([0.0], np.cumsum(x)))
    px2 = np.concatenate(([0.0], np.cumsum(x * x)))
    py = np.concatenate(([0.0], np.cumsum(y)))
    py2 = np.concatenate(([0.0], np.cumsum(y * y)))

    # x window is x[:n-lag]; y window is y[lag:]
    sx, sxx = px[n - lags], px2[n - lags]
    sy, syy = py[n] - py[lags], py2[n] - py2[lags]
    # numerator cross term: sum_i x[i]*y[i+lag]  ==  correlate(x, y, 'full')[n-1-lag]
    sxy = np.correlate(x, y, "full")[(n - 1) - lags]

    var_x = m * sxx - sx * sx
    var_y = m * syy - sy * sy
    with np.errstate(invalid="ignore", divide="ignore"):
        r = (m * sxy - sx * sy) / np.sqrt(var_x * var_y)
    # drop near-constant windows (std < 1e-9 ⇒ variance ≈ 0) and any NaN/inf
    r = np.where((var_x <= 1e-9) | (var_y <= 1e-9) | ~np.isfinite(r), 0.0, r)

    best = int(np.argmax(np.abs(r)))
    best_lag, best_r = int(lags[best]), float(r[best])
    if best_r == 0.0:
        return 0, 0.0, 1.0
    _, best_p = stats.pearsonr(x[:n - best_lag], y[best_lag:])
    return best_lag, best_r, float(best_p)


def analyze(
    snaps: List[Snapshot],
    max_lag_seconds: int = 259200,  # 72 hours
    min_r: float = 0.3,
    max_p: float = 0.05,
) -> List[CouplingEdge]:
    if len(snaps) < 20:
        print(f"  [coupler] only {len(snaps)} snapshots — need ≥20 for meaningful analysis")
        return []

    interval_seconds = _infer_interval_seconds(snaps)
    max_lag_snapshots = max(1, max_lag_seconds // interval_seconds)
    print(f"  [coupler] interval={interval_seconds}s | max_lag={max_lag_seconds}s ({max_lag_snapshots} snapshots)")

    # Build per-(stream, primitive) alert series (per-station seismic collapsed
    # to per-network — see _coupling_stream_name).
    series = _build_series(snaps)
    keys = list(series.keys())
    print(f"  [coupler] {len(keys)} active series → {len(keys) * (len(keys) - 1)} pairs")
    edges = []
    for src in keys:
        for tgt in keys:
            if src == tgt:
                continue
            lag_idx, r, p = _cross_correlate(series[src], series[tgt], max_lag_snapshots)
            if abs(r) >= min_r and p <= max_p and lag_idx >= 0:
                edges.append(CouplingEdge(
                    source_stream=src[0], source_primitive=src[1],
                    target_stream=tgt[0], target_primitive=tgt[1],
                    lag_seconds=lag_idx * interval_seconds,
                    strength_r=r, p_value=p,
                ))
    # Primary: strongest |r|. Secondary: longest lag (so r=1.0 at 241266s
    # beats r=1.0 at 0s — long-lag causal leads surface before batch artifacts).
    edges.sort(key=lambda e: (-abs(e.strength_r), -e.lag_seconds))
    return edges


def save_coupling(edges: List[CouplingEdge], path: Path) -> None:
    data = [
        {
            "source_stream": e.source_stream,
            "source_primitive": e.source_primitive,
            "target_stream": e.target_stream,
            "target_primitive": e.target_primitive,
            "lag_seconds": e.lag_seconds,
            "strength_r": round(e.strength_r, 4),
            "p_value": round(e.p_value, 4),
        }
        for e in edges
    ]
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def load_coupling(path: Path) -> List[CouplingEdge]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with open(path) as f:
        data = json.load(f)
    return [CouplingEdge(**d) for d in data]
