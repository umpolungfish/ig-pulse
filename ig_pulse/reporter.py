from __future__ import annotations
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from .schema import Snapshot
from .coupler import CouplingEdge

PRIM_SYMBOL = {
    "criticality": "⊙", "parity": "Φ", "kinetics": "Ç",
    "topology": "Þ", "coupling": "ɢ", "dimensionality": "Ð",
    "stoichiometry": "Σ", "granularity": "Γ", "winding": "Ω",
    "chirality": "Ħ", "recognition": "Ř", "fidelity": "ƒ",
}


def _parse_ts(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def find_snapshot(snaps: List[Snapshot], ts_str: str) -> Optional[Snapshot]:
    target = _parse_ts(ts_str)
    best = min(snaps, key=lambda s: abs((_parse_ts(s.ts) - target).total_seconds()), default=None)
    return best


def reconstruct_propagation(
    snaps: List[Snapshot],
    event_ts: str,
    lookback_hours: int = 72,
) -> None:
    target = _parse_ts(event_ts)
    cutoff = target - timedelta(hours=lookback_hours)

    window = [s for s in snaps if cutoff <= _parse_ts(s.ts) <= target]
    if not window:
        print(f"  No snapshots found in {lookback_hours}h window before {event_ts}")
        return

    # Find first activation of each (stream, primitive) in the window
    first_seen: dict[tuple[str, str], datetime] = {}
    for snap in sorted(window, key=lambda s: s.ts):
        snap_ts = _parse_ts(snap.ts)
        for r in snap.readings:
            if r.alert > 0:
                key = (r.stream, r.primitive)
                if key not in first_seen:
                    first_seen[key] = snap_ts

    if not first_seen:
        print("  No primitive activations found in window.")
        return

    # Sort by first activation time
    ordered = sorted(first_seen.items(), key=lambda x: x[1])

    print(f"\nPropagation anatomy — {lookback_hours}h window before {event_ts}")
    print("=" * 60)
    t0 = ordered[0][1]
    for (stream, prim), ts in ordered:
        delta_h = (ts - t0).total_seconds() / 3600
        sym = PRIM_SYMBOL.get(prim, prim)
        print(f"  T+{delta_h:5.1f}h  {stream:<20} {sym} ({prim})")

    # Check if this was a B-state event
    event_snap = find_snapshot(snaps, event_ts)
    if event_snap and event_snap.is_b_state:
        print(f"\n  → B-STATE at {event_ts} | ×{event_snap.multiplier:.2f} | {event_snap.total_alerts} alerts")
    print()


def compare_to_coupling(
    propagation_order: List[tuple[tuple[str, str], datetime]],
    edges: List[CouplingEdge],
) -> None:
    print("Coupling model validation:")
    print("-" * 40)
    for edge in edges[:10]:
        src = (edge.source_stream, edge.source_primitive)
        tgt = (edge.target_stream, edge.target_primitive)
        src_ts = next((ts for k, ts in propagation_order if k == src), None)
        tgt_ts = next((ts for k, ts in propagation_order if k == tgt), None)
        if src_ts and tgt_ts:
            observed_lag = (tgt_ts - src_ts).total_seconds() / 3600
            predicted_lag = edge.lag_hours
            match = "✓" if abs(observed_lag - predicted_lag) < 6 else "✗"
            print(
                f"  {match} {edge.source_stream}:{PRIM_SYMBOL.get(edge.source_primitive,'?')} "
                f"→ {edge.target_stream}:{PRIM_SYMBOL.get(edge.target_primitive,'?')} "
                f"predicted={predicted_lag}h observed={observed_lag:.1f}h"
            )
