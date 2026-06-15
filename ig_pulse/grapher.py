from __future__ import annotations
import json
from pathlib import Path
from typing import List
from .coupler import CouplingEdge

PRIM_SYMBOL = {
    "criticality": "⊙", "parity": "Φ", "kinetics": "Ç",
    "topology": "Þ", "coupling": "ɢ", "dimensionality": "Ð",
    "stoichiometry": "Σ", "granularity": "Γ", "winding": "Ω",
    "chirality": "Ħ", "recognition": "Ř", "fidelity": "ƒ",
}


def build_graph(edges: List[CouplingEdge]) -> dict:
    nodes = set()
    for e in edges:
        nodes.add((e.source_stream, e.source_primitive))
        nodes.add((e.target_stream, e.target_primitive))
    node_list = [{"stream": s, "primitive": p, "symbol": PRIM_SYMBOL.get(p, p)} for s, p in sorted(nodes)]
    edge_list = [
        {
            "from": f"{e.source_stream}:{e.source_primitive}",
            "to": f"{e.target_stream}:{e.target_primitive}",
            "lag_seconds": e.lag_seconds,
            "strength_r": e.strength_r,
            "p_value": e.p_value,
        }
        for e in edges
    ]
    return {"nodes": node_list, "edges": edge_list}


def save_graph(graph: dict, path: Path) -> None:
    with open(path, "w") as f:
        json.dump(graph, f, indent=2)


def print_ascii_matrix(edges: List[CouplingEdge]) -> None:
    streams = sorted(set(
        [e.source_stream for e in edges] + [e.target_stream for e in edges]
    ))
    if not streams:
        print("  No coupling edges to display.")
        return

    # Abbreviate stream names
    abbr = {s: s[:8] for s in streams}
    col_w = 9

    header = " " * 12 + "  ".join(f"{abbr[s]:<{col_w}}" for s in streams)
    print(header)
    print("-" * len(header))

    for src in streams:
        row = f"{abbr[src]:<12}"
        for tgt in streams:
            if src == tgt:
                row += f"{'---':<{col_w}}  "
                continue
            # Find strongest edge between these streams
            best = max(
                (e for e in edges if e.source_stream == src and e.target_stream == tgt),
                key=lambda e: abs(e.strength_r),
                default=None,
            )
            if best:
                sym = PRIM_SYMBOL.get(best.source_primitive, "?")
                cell = f"{sym}{best.strength_r:+.2f}"
            else:
                cell = "."
            row += f"{cell:<{col_w}}  "
        print(row)


def print_dot(edges: List[CouplingEdge]) -> None:
    print("digraph ig_pulse {")
    print('  rankdir=LR;')
    print('  node [shape=box];')
    for e in edges:
        src = f'"{e.source_stream}\\n{PRIM_SYMBOL.get(e.source_primitive, e.source_primitive)}"'
        tgt = f'"{e.target_stream}\\n{PRIM_SYMBOL.get(e.target_primitive, e.target_primitive)}"'
        label = f'"{e.lag_seconds}s r={e.strength_r:.2f}"'
        print(f'  {src} -> {tgt} [label={label}];')
    print("}")
