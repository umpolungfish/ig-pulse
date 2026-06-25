"""
geo_viz.py — Geographic Visualization Server for the Datanado

Serves the live geo-map: signals pinging and spreading across the Earth.
Backend: Flask (GeoJSON API + WebSocket for live updates)
Frontend: Leaflet.js + D3.js (geodesic arcs, heatmaps, space layer)

Architecture:
  /api/geojson/nodes     → GeoJSON FeatureCollection of signal origins
  /api/geojson/edges     → GeoJSON LineString features for coupling propagation arcs
  /api/geojson/space     → GeoJSON for space-based origins (L1, Sun)
  /api/heatmap           → [lat, lon, weight] array for heatmap layer
  /api/stats             → Current graph statistics (spectral radius, tick, etc.)
  /api/snapshots/latest  → Raw latest snapshot data
  /                      → Interactive Leaflet dashboard

The "universal tick" of ~2.04 days determines the animation cycle:
edges pulse with a delay proportional to their lag_seconds / tick_duration.
"""

from __future__ import annotations

import json
import math
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from flask import Flask, jsonify, render_template, request, send_from_directory

from .schema import Snapshot, ReadingRecord, load_snapshots

# ── Constants ──────────────────────────────────────────────────────────────────

# Space-based "origins" — fixed locations for celestial data sources
SPACE_ORIGINS = {
    "L1_lagrange": {
        "type": "space", "name": "DSCOVR (L1 Lagrange Point)",
        "lat": 0.0, "lon": -70.0,  # Rendered as special marker — L1 is at ~1.5M km sunward
        "alt_km": 1_500_000, "instrument": "DSCOVR",
        "description": "Solar wind, IMF Bz — 1.5M km sunward",
        "icon": "satellite",
    },
    "sun": {
        "type": "space", "name": "Sun (DONKI Flares/CMEs)",
        "lat": 0.0, "lon": 0.0,  # Positioned at (0,0) for special rendering
        "alt_km": 149_600_000, "instrument": "DONKI/FLR",
        "description": "Solar flares, CMEs — 1 AU",
        "icon": "sun",
    },
    "earth_magnetosphere": {
        "type": "space", "name": "Earth Magnetosphere (Kp)",
        "lat": 90.0, "lon": 0.0,  # North magnetic pole approximation
        "alt_km": 60_000, "instrument": "NOAA_SWPC",
        "description": "Geomagnetic storm index",
        "icon": "magnet",
    },
}
# ── Projection Map: Non-Geo Stream → Approximate Location ────────────────────
# Market/network/social streams get projected to designated hubs

PROJECTION_MAP = {
    # Financial hubs
    "fear_greed":           (40.707, -74.011, "Wall Street, NYC"),
    "fear_greed_cross":     (40.707, -74.011, "Wall Street, NYC"),
    "btc_dom":              (40.707, -74.011, "Wall Street, NYC"),
    "btc_dom_low":          (40.707, -74.011, "Wall Street, NYC"),
    "mktcap_chg":           (40.707, -74.011, "Wall Street, NYC"),
    "alt_btc_ratio":        (40.707, -74.011, "Wall Street, NYC"),
    "alt_divergence":       (40.707, -74.011, "Wall Street, NYC"),
    "btc_dominance_surge":  (40.707, -74.011, "Wall Street, NYC"),
    # Kalshi prediction markets → NYC financial district
    "kalshi_economics":     (40.707, -74.011, "Wall Street, NYC"),
    "kalshi_financials":    (40.707, -74.011, "Wall Street, NYC"),
    "kalshi_politics":      (38.907, -77.037, "Washington, DC"),
    "kalshi_elections":     (38.907, -77.037, "Washington, DC"),
    "kalshi_world":         (40.707, -74.011, "Wall Street, NYC"),
    "kalshi_sports":        (40.707, -74.011, "Wall Street, NYC"),
    "kalshi_entertainment": (34.052, -118.244, "Los Angeles, CA"),
    "kalshi_social":        (37.775, -122.419, "Silicon Valley, CA"),
    "kalshi_health":        (42.360, -71.058, "Boston, MA"),
    "kalshi_science_and_technology": (37.775, -122.419, "Silicon Valley, CA"),
    "kalshi_companies":     (37.775, -122.419, "Silicon Valley, CA"),
    "kalshi_climate_and_weather": (40.707, -74.011, "Wall Street, NYC"),
    # Bitcoin network nodes
    "mempool_fee":          (37.775, -122.419, "Bitcoin Network"),
    "mempool_count":        (37.775, -122.419, "Bitcoin Network"),
    "mempool_low_fee":      (37.775, -122.419, "Bitcoin Network"),
    "block_time":           (37.775, -122.419, "Bitcoin Network"),
    "n_tx":                 (37.775, -122.419, "Bitcoin Network"),
    # Lightning Network
    "ln_capacity":          (47.376, 8.541, "Lightning Network, Zurich"),
    "ln_density":           (47.376, 8.541, "Lightning Network, Zurich"),
    # Social media / information
    "hn_sentiment":         (37.775, -122.419, "Hacker News, Silicon Valley"),
    "hn_silence":           (37.775, -122.419, "Hacker News, Silicon Valley"),
    "wiki_attention":       (37.775, -122.419, "Wikipedia CDN, SF"),
    # Generic Kalshi catch-all streams
    "kalshi_elections_KXNEXTUKPM-30-ABUR": (51.507, -0.128, "London, UK — Prediction Markets"),
    "kalshi_elections_KXNEXTUKPM-30-BPHI": (51.507, -0.128, "London, UK — Prediction Markets"),
    "kalshi_elections_KXNEXTUKPM-30-NF":   (51.507, -0.128, "London, UK — Prediction Markets"),
    "kalshi_elections_KXNEXTUKPM-30-SMAH": (51.507, -0.128, "London, UK — Prediction Markets"),
    "kalshi_elections_KXNEXTUKPM-30-YCOO": (51.507, -0.128, "London, UK — Prediction Markets"),
    "kalshi_entertainment_KXSWIFTKELCEWEDDINGLOCATION-30-NEW": (40.707, -74.011, "Wall Street, NYC"),
    "kalshi_entertainment_KXSWIFTKELCEWEDDINGLOCATION-30-OHI": (40.707, -74.011, "Wall Street, NYC"),
    "kalshi_entertainment_KXSWIFTKELCEWEDDINGLOCATION-30-PEN": (40.707, -74.011, "Wall Street, NYC"),
    "kalshi_entertainment_KXSWIFTKELCEWEDDINGLOCATION-30-RHO": (40.707, -74.011, "Wall Street, NYC"),
    "kalshi_entertainment_KXSWIFTKELCEWEDDINGLOCATION-30-TEN": (40.707, -74.011, "Wall Street, NYC"),
    "kalshi_entertainment_KXTAYLORSWIFTWEDDING-30JAN01-BRI": (40.707, -74.011, "Wall Street, NYC"),
    "kalshi_politics_KXTAIWANLVL4-27JAN01": (25.033, 121.565, "Taipei, Taiwan — Prediction Market"),
}


# Color scale for edge strength
def strength_color(r: float) -> str:
    """Map coupling strength to hex color: blue(cold) → white → red(hot)."""
    r_clamped = max(-1.0, min(1.0, r))
    if r_clamped >= 0:
        # Positive correlation: white → red
        return f"hsl(0, {int(100 * r_clamped)}%, 50%)"
    else:
        # Negative correlation: white → blue
        return f"hsl(240, {int(100 * abs(r_clamped))}%, 50%)"


def strength_width(r: float) -> float:
    """Map coupling strength to line width."""
    return 1.0 + 4.0 * abs(r)


# ── Geo-Viz Data Model ─────────────────────────────────────────────────────────

@dataclass
class GeoNode:
    """A geographic signal origin point."""
    stream: str
    primitive: str
    value: float
    alert: int
    lat: float
    lon: float
    origin_type: str       # "seismic", "ocean", "atmosphere", "space", "network", "market", "social"
    label: str
    timestamp: float

    def to_geojson(self) -> dict:
        return {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [self.lon, self.lat]},
            "properties": {
                "stream": self.stream,
                "primitive": self.primitive,
                "value": self.value,
                "alert": self.alert,
                "origin_type": self.origin_type,
                "label": self.label,
                "ts": self.timestamp,
                "radius": 3 + self.alert * 3,  # Alert 2 = big dot
                "color": {0: "#4ade80", 1: "#facc15", 2: "#ef4444"}[self.alert],
            },
        }


@dataclass
class GeoEdge:
    """A propagation arc between two geographic signal origins."""
    source_node: GeoNode
    target_node: GeoNode
    lag_seconds: float
    strength_r: float
    p_value: float

    def to_geojson(self) -> dict:
        # Geodesic arc approximated as a 3-point polyline with midpoint lift
        mid_lon = (self.source_node.lon + self.target_node.lon) / 2
        mid_lat = (self.source_node.lat + self.target_node.lat) / 2
        # Lift proportional to distance and strength
        dlon = self.target_node.lon - self.source_node.lon
        dlat = self.target_node.lat - self.source_node.lat
        dist = math.sqrt(dlon**2 + dlat**2)
        lift = dist * 0.3 * abs(self.strength_r)  # Higher lift for stronger edges

        # Arc: source → lifted midpoint → target
        arc = [
            [self.source_node.lon, self.source_node.lat],
            [mid_lon, mid_lat + lift],
            [self.target_node.lon, self.target_node.lat],
        ]
        return {
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": arc},
            "properties": {
                "source": self.source_node.label,
                "target": self.target_node.label,
                "lag_seconds": self.lag_seconds,
                "strength_r": self.strength_r,
                "p_value": self.p_value,
                "color": strength_color(self.strength_r),
                "width": strength_width(self.strength_r),
                "opacity": 1.0 - self.p_value,
            },
        }


# ── Geo-Viz Engine ─────────────────────────────────────────────────────────────

class GeoVizEngine:
    """Converts ig-pulse data into geographic visualization structures."""

    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.snapshots_path = self.data_dir / "snapshots.jsonl"
        self.coupling_path = self.data_dir / "coupling.json"
        self.graph_path = self.data_dir / "graph.json"

        # Cached state
        self._latest_snapshot: Optional[Snapshot] = None
        self._coupling_edges: List[dict] = []
        self._graph: dict = {}
        self._last_load: float = 0.0
        self._cache_ttl: float = 5.0  # seconds

    def _should_reload(self) -> bool:
        return (time.time() - self._last_load) > self._cache_ttl

    def _load_if_needed(self):
        if not self._should_reload():
            return
        self._last_load = time.time()

        # Load latest snapshot
        snaps = load_snapshots(self.snapshots_path)
        if snaps:
            self._latest_snapshot = snaps[-1]

        # Load coupling edges
        if self.coupling_path.exists():
            with open(self.coupling_path) as f:
                self._coupling_edges = json.load(f)

        # Load graph metadata
        if self.graph_path.exists():
            with open(self.graph_path) as f:
                self._graph = json.load(f)

    def _extract_geo_nodes(self) -> List[GeoNode]:
        """Extract all readings with geographic origins or projected positions."""
        self._load_if_needed()
        nodes = []
        if not self._latest_snapshot:
            return nodes

        for r in self._latest_snapshot.readings:
            origin = r.origin or {}

            lat = origin.get("lat")
            lon = origin.get("lon")
            origin_type = origin.get("type", "unknown")

            # Check projection map for streams without explicit coords
            if (lat is None or lon is None) and r.stream in PROJECTION_MAP:
                proj_lat, proj_lon, proj_label = PROJECTION_MAP[r.stream]
                lat, lon = proj_lat, proj_lon
                if not origin:
                    origin_type = "projected"
                    origin = {"type": "projected", "label": proj_label}

            if lat is not None and lon is not None:
                nodes.append(GeoNode(
                    stream=r.stream,
                    primitive=r.primitive,
                    value=r.value,
                    alert=r.alert,
                    lat=lat,
                    lon=lon,
                    origin_type=origin_type,
                    label=f"{r.stream}:{r.primitive}",
                    timestamp=time.time(),
                ))

        return nodes

    def _extract_geo_edges(self, geo_nodes: List[GeoNode]) -> List[GeoEdge]:
        """Build propagation arcs between geographically-anchored nodes."""
        self._load_if_needed()
        edges = []

        # Build lookup: (stream, primitive) -> GeoNode
        node_map: Dict[str, GeoNode] = {}
        for n in geo_nodes:
            # Map by stream name (without primitive suffix for broader matching)
            node_map[n.stream] = n

        # Match coupling edges to geo nodes
        for ce in self._coupling_edges:
            src_stream = ce.get("source_stream", "")
            tgt_stream = ce.get("target_stream", "")
            src_node = node_map.get(src_stream)
            tgt_node = node_map.get(tgt_stream)

            if src_node and tgt_node:
                edges.append(GeoEdge(
                    source_node=src_node,
                    target_node=tgt_node,
                    lag_seconds=ce.get("lag_seconds", 0),
                    strength_r=ce.get("strength_r", 0),
                    p_value=ce.get("p_value", 0),
                ))
            elif src_node and not tgt_node:
                # Source has geo origin, target doesn't — still show as outgoing
                # Use the target stream name to create a synthetic node at origin
                # Or skip — we only draw arcs between geo-anchored nodes
                pass

        # Filter to top 100 strongest edges for visual clarity
        edges.sort(key=lambda e: abs(e.strength_r) * (1.0 - e.p_value), reverse=True)
        return edges[:100]

    def get_nodes_geojson(self) -> dict:
        """GeoJSON FeatureCollection of signal origins."""
        nodes = self._extract_geo_nodes()
        features = [n.to_geojson() for n in nodes]
        return {
            "type": "FeatureCollection",
            "features": features,
        }

    def get_edges_geojson(self) -> dict:
        """GeoJSON FeatureCollection of propagation arcs."""
        nodes = self._extract_geo_nodes()
        edges = self._extract_geo_edges(nodes)
        features = [e.to_geojson() for e in edges]
        return {
            "type": "FeatureCollection",
            "features": features,
        }

    def get_space_geojson(self) -> dict:
        """GeoJSON FeatureCollection for space-based origins."""
        features = []
        for key, sp in SPACE_ORIGINS.items():
            features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [sp["lon"], sp["lat"]]},
                "properties": {
                    "name": sp["name"],
                    "origin_type": "space",
                    "instrument": sp["instrument"],
                    "alt_km": sp["alt_km"],
                    "description": sp["description"],
                    "icon": sp["icon"],
                    "key": key,
                    "radius": 12,
                    "color": "#fbbf24",
                },
            })
        return {"type": "FeatureCollection", "features": features}

    def get_heatmap_data(self) -> List[list]:
        """Build alert-weighted [lat, lon, weight] array for heatmap layer."""
        self._load_if_needed()
        if not self._latest_snapshot:
            return []

        points: Dict[Tuple[float, float], float] = defaultdict(float)
        for r in self._latest_snapshot.readings:
            origin = r.origin or {}
            lat = origin.get("lat")
            lon = origin.get("lon")
            if lat is not None and lon is not None:
                # Weight = alert level (0,1,2) scaled to 0-1
                key = (round(lat, 2), round(lon, 2))
                points[key] += r.alert / 2.0  # Normalize alert to [0, 1]

        return [[lat, lon, min(1.0, w)] for (lat, lon), w in points.items()]

    def get_stats(self) -> dict:
        """Current graph statistics."""
        self._load_if_needed()
        nodes = self._extract_geo_nodes()
        edges = self._extract_geo_edges(nodes)

        # Compute spectral radius from coupling if available
        spectral_radius = self._graph.get("spectral_radius", 3.4985)
        tick_hours = self._graph.get("tick_hours", 49.0)

        return {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "active_alerts": sum(1 for n in nodes if n.alert >= 1),
            "spectral_radius": spectral_radius,
            "tick_hours": tick_hours,
            "tick_days": tick_hours / 24,
            "tick_epoch": "1970-01-01T00:00:00Z",
            "tick_system": "unix_epoch (wall-clock anchored — same phase everywhere, no reset on refresh)",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "snapshot_ts": self._latest_snapshot.ts if self._latest_snapshot else None,
        }

    def get_latest_snapshot(self) -> Optional[dict]:
        self._load_if_needed()
        if self._latest_snapshot:
            return self._latest_snapshot.to_dict()
        return None


# ── Flask Application ──────────────────────────────────────────────────────────

def create_app(data_dir: str = None) -> Flask:
    """Create the geo-viz Flask application."""

    if data_dir is None:
        data_dir = str(Path(__file__).parent.parent / "data")

    app = Flask(__name__, 
                template_folder=str(Path(__file__).parent / "templates"),
                static_folder=str(Path(__file__).parent / "static"))
    engine = GeoVizEngine(Path(data_dir))

    # ── API Routes ─────────────────────────────────────────────────────────

    @app.route("/api/geojson/nodes")
    def api_nodes():
        return jsonify(engine.get_nodes_geojson())

    @app.route("/api/geojson/edges")
    def api_edges():
        return jsonify(engine.get_edges_geojson())

    @app.route("/api/geojson/space")
    def api_space():
        return jsonify(engine.get_space_geojson())

    @app.route("/api/heatmap")
    def api_heatmap():
        return jsonify(engine.get_heatmap_data())

    @app.route("/api/stats")
    def api_stats():
        return jsonify(engine.get_stats())

    @app.route("/api/snapshots/latest")
    def api_latest_snapshot():
        snap = engine.get_latest_snapshot()
        if snap:
            return jsonify(snap)
        return jsonify({"error": "no snapshots"}), 404

    @app.route("/api/all")
    def api_all():
        """Single endpoint returning all data for the dashboard."""
        return jsonify({
            "nodes": engine.get_nodes_geojson(),
            "edges": engine.get_edges_geojson(),
            "space": engine.get_space_geojson(),
            "heatmap": engine.get_heatmap_data(),
            "stats": engine.get_stats(),
        })

    # ── Dashboard Routes ───────────────────────────────────────────────────

    @app.route("/")
    def dashboard():
        return render_template("geo_map.html")

    @app.route("/health")
    def health():
        return jsonify({"status": "ok", "service": "geo_viz"})

    return app


# ── CLI Entry Point ────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Geo-Viz: Datanado Geographic Dashboard")
    parser.add_argument("--data-dir", default=None, help="Path to ig-pulse data directory")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host")
    parser.add_argument("--port", type=int, default=5050, help="Port")
    parser.add_argument("--debug", action="store_true", help="Debug mode")
    args = parser.parse_args()

    app = create_app(data_dir=args.data_dir)
    print(f"🌍 Geo-Viz Dashboard: http://{args.host}:{args.port}")
    print(f"   API: http://{args.host}:{args.port}/api/all")
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()