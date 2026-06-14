from __future__ import annotations
import argparse
import sys
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
SNAPSHOTS_PATH = DATA_DIR / "snapshots.jsonl"
COUPLING_PATH  = DATA_DIR / "coupling.json"
GRAPH_PATH     = DATA_DIR / "graph.json"


def cmd_collect(args) -> None:
    from .collector import collect_once, run
    if args.once:
        collect_once(verbose=True)
    else:
        run(interval_seconds=args.interval)


def cmd_couple(args) -> None:
    from .schema import load_snapshots
    from .coupler import analyze, save_coupling
    snaps = load_snapshots(SNAPSHOTS_PATH)
    print(f"  Loaded {len(snaps)} snapshots from {SNAPSHOTS_PATH}")
    edges = analyze(snaps, max_lag_hours=args.max_lag, min_r=args.min_r, max_p=args.max_p)
    print(f"  Found {len(edges)} coupling edges (|r|≥{args.min_r}, p≤{args.max_p})")
    for e in edges[:20]:
        print(f"    {e.label()}")
    save_coupling(edges, COUPLING_PATH)
    print(f"  Saved to {COUPLING_PATH}")


def cmd_map(args) -> None:
    from .coupler import load_coupling
    from .grapher import build_graph, save_graph, print_ascii_matrix, print_dot
    edges = load_coupling(COUPLING_PATH)
    if not edges:
        print("  No coupling data found. Run `ig-pulse couple` first.")
        return
    print(f"\nCoupling graph — {len(edges)} edges\n")
    if args.dot:
        print_dot(edges)
    else:
        print_ascii_matrix(edges)
    graph = build_graph(edges)
    save_graph(graph, GRAPH_PATH)
    print(f"\n  Graph saved to {GRAPH_PATH}")


def cmd_report(args) -> None:
    from .schema import load_snapshots
    from .coupler import load_coupling
    from .reporter import reconstruct_propagation
    snaps = load_snapshots(SNAPSHOTS_PATH)
    if not snaps:
        print("  No snapshots found. Run `ig-pulse collect` first.")
        return
    ts = args.ts or snaps[-1].ts
    reconstruct_propagation(snaps, ts, lookback_hours=args.lookback)


def main() -> None:
    parser = argparse.ArgumentParser(prog="ig-pulse", description="Information propagation observatory")
    sub = parser.add_subparsers(dest="command")

    p_collect = sub.add_parser("collect", help="Poll streams and store snapshots")
    p_collect.add_argument("--once", action="store_true", help="Collect one snapshot and exit")
    p_collect.add_argument("--interval", type=int, default=3600, help="Poll interval in seconds (default 3600)")

    p_couple = sub.add_parser("couple", help="Compute cross-stream coupling from snapshots")
    p_couple.add_argument("--max-lag", type=int, default=72, help="Maximum lag to test in hours")
    p_couple.add_argument("--min-r", type=float, default=0.3, help="Minimum |Pearson r| to include")
    p_couple.add_argument("--max-p", type=float, default=0.05, help="Maximum p-value to include")

    p_map = sub.add_parser("map", help="Display coupling graph")
    p_map.add_argument("--dot", action="store_true", help="Output Graphviz DOT format")

    p_report = sub.add_parser("report", help="Reconstruct propagation anatomy for a B-state event")
    p_report.add_argument("--ts", type=str, default=None, help="Event timestamp (ISO 8601). Defaults to latest snapshot.")
    p_report.add_argument("--lookback", type=int, default=72, help="Hours to look back (default 72)")

    args = parser.parse_args()
    if args.command == "collect":
        cmd_collect(args)
    elif args.command == "couple":
        cmd_couple(args)
    elif args.command == "map":
        cmd_map(args)
    elif args.command == "report":
        cmd_report(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
