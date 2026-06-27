from __future__ import annotations
import time
from pathlib import Path
from .domain_streams import DomainStreamAggregator
from .schema import snapshot_from_domain_signal, append_snapshot

DATA_DIR = Path(__file__).parent.parent / "data"
SNAPSHOTS_PATH = DATA_DIR / "snapshots.jsonl"


def collect_once(verbose: bool = True) -> None:
    agg = DomainStreamAggregator(refresh_interval=0)
    sig = agg.refresh(force=True)
    snap = snapshot_from_domain_signal(sig)
    append_snapshot(snap, SNAPSHOTS_PATH)
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


def run(interval_seconds: int = 3600, verbose: bool = True) -> None:
    from .domain_streams import _dsn_stereo_contact_recent
    contact_interval = 90  # seconds — poll fast during DSN downlink windows
    print(f"ig-pulse collector running | interval={interval_seconds}s (contact={contact_interval}s) | writing to {SNAPSHOTS_PATH}")
    while True:
        try:
            collect_once(verbose=verbose)
        except Exception as e:
            print(f"  [ERROR] collect_once failed: {e}")
        sleep = contact_interval if _dsn_stereo_contact_recent() else interval_seconds
        if verbose and sleep == contact_interval:
            print(f"  [DSN contact active — next collect in {contact_interval}s]")
        time.sleep(sleep)
