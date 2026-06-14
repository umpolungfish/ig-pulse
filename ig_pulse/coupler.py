from __future__ import annotations
import json
from dataclasses import dataclass
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
    lag_hours: int
    strength_r: float
    p_value: float

    def label(self) -> str:
        return (
            f"{self.source_stream}:{self.source_primitive} "
            f"→ {self.target_stream}:{self.target_primitive} "
            f"lag={self.lag_hours}h r={self.strength_r:.3f} p={self.p_value:.3f}"
        )


def _stream_primitive_series(snaps: List[Snapshot], stream: str, primitive: str) -> np.ndarray:
    series = []
    for s in snaps:
        val = 0
        for r in s.readings:
            if r.stream == stream and r.primitive == primitive:
                val = r.alert
                break
        series.append(val)
    return np.array(series, dtype=float)


def _cross_correlate(x: np.ndarray, y: np.ndarray, max_lag: int) -> tuple[int, float, float]:
    best_lag, best_r, best_p = 0, 0.0, 1.0
    n = len(x)
    for lag in range(0, max_lag + 1):
        if lag >= n:
            break
        x_trim = x[:n - lag]
        y_trim = y[lag:]
        if len(x_trim) < 10:
            continue
        if x_trim.std() < 1e-9 or y_trim.std() < 1e-9:
            continue
        r, p = stats.pearsonr(x_trim, y_trim)
        if abs(r) > abs(best_r):
            best_r, best_p, best_lag = r, p, lag
    return best_lag, best_r, best_p


def analyze(
    snaps: List[Snapshot],
    max_lag_hours: int = 72,
    min_r: float = 0.3,
    max_p: float = 0.05,
) -> List[CouplingEdge]:
    if len(snaps) < 20:
        print(f"  [coupler] only {len(snaps)} snapshots — need ≥20 for meaningful analysis")
        return []

    # Build per-(stream, primitive) alert series
    series: dict[tuple[str, str], np.ndarray] = {}
    seen_streams = set()
    for s in snaps:
        for r in s.readings:
            seen_streams.add(r.stream)

    for stream in seen_streams:
        for prim in PRIMITIVES:
            arr = _stream_primitive_series(snaps, stream, prim)
            if arr.sum() > 0:
                series[(stream, prim)] = arr

    keys = list(series.keys())
    edges = []
    total = len(keys) * (len(keys) - 1)
    done = 0
    for i, src in enumerate(keys):
        for j, tgt in enumerate(keys):
            if src == tgt:
                continue
            done += 1
            lag, r, p = _cross_correlate(series[src], series[tgt], max_lag_hours)
            if abs(r) >= min_r and p <= max_p and lag >= 0:
                edges.append(CouplingEdge(
                    source_stream=src[0], source_primitive=src[1],
                    target_stream=tgt[0], target_primitive=tgt[1],
                    lag_hours=lag, strength_r=r, p_value=p,
                ))
    edges.sort(key=lambda e: -abs(e.strength_r))
    return edges


def save_coupling(edges: List[CouplingEdge], path: Path) -> None:
    data = [
        {
            "source_stream": e.source_stream,
            "source_primitive": e.source_primitive,
            "target_stream": e.target_stream,
            "target_primitive": e.target_primitive,
            "lag_hours": e.lag_hours,
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
