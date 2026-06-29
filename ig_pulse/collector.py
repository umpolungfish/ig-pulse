from __future__ import annotations
import time
from pathlib import Path
from .domain_streams import DomainStreamAggregator
from .schema import snapshot_from_domain_signal, append_snapshot

DATA_DIR = Path(__file__).parent.parent / "data"
SNAPSHOTS_PATH = DATA_DIR / "snapshots.jsonl"


def _snapshots_path(data_dir: str | None) -> Path:
    if data_dir:
        p = Path(data_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p / "snapshots.jsonl"
    return SNAPSHOTS_PATH


def _write_snapshot(agg: DomainStreamAggregator, path: Path, force: bool, verbose: bool) -> None:
    sig = agg.refresh(force=force)
    snap = snapshot_from_domain_signal(sig)
    append_snapshot(snap, path)
    if verbose:
        prim_str = " ".join(
            f"{k[:3]}:{v}" for k, v in snap.primitives.items() if v > 0
        )
        state = "[B-state]" if snap.is_b_state else ""
        print(
            f"  [{snap.ts}] ×{snap.multiplier:.2f} | alerts={snap.total_alerts} "
            f"{state} | {prim_str}"
        )
        if snap.errors:
            for e in snap.errors:
                print(f"  ! {e}")


def collect_once(verbose: bool = True, data_dir: str | None = None) -> None:
    path = _snapshots_path(data_dir)
    agg = DomainStreamAggregator(refresh_interval=0)
    _write_snapshot(agg, path, force=True, verbose=verbose)


def run(interval_seconds: int = 90, verbose: bool = True, data_dir: str | None = None) -> None:
    # Persistent aggregator so per-stream TTLs and carry-forward work across ticks.
    # Fast streams (120–180s TTL) re-fetch every 1–2 loops; slow streams carry forward.
    path = _snapshots_path(data_dir)
    agg = DomainStreamAggregator(refresh_interval=0)
    print(f"ig-pulse collector running | loop={interval_seconds}s (per-stream TTLs govern fetch rate) | writing to {path}")
    first = True
    while True:
        try:
            _write_snapshot(agg, path, force=first, verbose=verbose)
            first = False
        except Exception as e:
            print(f"  [ERROR] collect failed: {e}")
        time.sleep(interval_seconds)
