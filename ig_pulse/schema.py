from __future__ import annotations
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import List


@dataclass
class ReadingRecord:
    stream: str
    primitive: str
    value: float
    unit: str
    alert: int


@dataclass
class Snapshot:
    ts: str
    multiplier: float
    total_alerts: int
    is_b_state: bool
    primitives: dict[str, int]
    readings: List[ReadingRecord]
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Snapshot":
        readings = [ReadingRecord(**r) for r in d.get("readings", [])]
        return cls(
            ts=d["ts"],
            multiplier=d["multiplier"],
            total_alerts=d["total_alerts"],
            is_b_state=d["is_b_state"],
            primitives=d["primitives"],
            readings=readings,
            errors=d.get("errors", []),
        )


def snapshot_from_domain_signal(sig) -> Snapshot:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    primitives = {
        "criticality":   sig.criticality,
        "parity":        sig.parity,
        "kinetics":      sig.kinetics,
        "topology":      sig.topology,
        "coupling":      sig.coupling,
        "dimensionality": sig.dimensionality,
        "stoichiometry": sig.stoichiometry,
        "granularity":   sig.granularity,
        "winding":       sig.winding,
        "chirality":     sig.chirality,
        "recognition":   sig.recognition,
        "fidelity":      sig.fidelity,
    }
    readings = [
        ReadingRecord(
            stream=r.stream,
            primitive=r.primitive,
            value=float(r.value),
            unit=r.unit,
            alert=r.alert,
        )
        for r in sig.readings
    ]
    errors = list(sig.errors) if sig.errors else []
    return Snapshot(
        ts=ts,
        multiplier=sig.multiplier,
        total_alerts=sig.total_alerts,
        is_b_state=sig.is_b_state,
        primitives=primitives,
        readings=readings,
        errors=errors,
    )


def append_snapshot(snap: Snapshot, path: Path) -> None:
    with open(path, "a") as f:
        f.write(json.dumps(snap.to_dict()) + "\n")


def load_snapshots(path: Path) -> List[Snapshot]:
    snaps = []
    if not path.exists():
        return snaps
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    snaps.append(Snapshot.from_dict(json.loads(line)))
                except Exception:
                    pass
    return snaps
