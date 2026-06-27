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
from .density_matrix import metrics_from_snapshot

# ── Constants ──────────────────────────────────────────────────────────────────

# Space-based "origins" — fixed locations for celestial data sources
SPACE_ORIGINS = {
    "L1_dscovr": {
        "type": "space", "name": "DSCOVR (L1 — IMF Bz / solar wind)",
        "lat": 5.0, "lon": -65.0,
        "alt_km": 1_500_000, "instrument": "DSCOVR/MAG",
        "description": "IMF Bz helicity, solar wind — 1.5M km sunward",
        "icon": "satellite",
    },
    "L1_ace": {
        "type": "space", "name": "ACE (L1 — EPAM e⁻/p⁺ ratios)",
        "lat": -5.0, "lon": -75.0,
        "alt_km": 1_500_000, "instrument": "ACE/EPAM",
        "description": "Electron/proton flux ratios, chirality proxy — 1.5M km sunward",
        "icon": "satellite",
    },
    "sun": {
        "type": "space", "name": "Sun (DONKI Flares / CMEs)",
        "lat": 0.0, "lon": 0.0,
        "alt_km": 149_600_000, "instrument": "DONKI/FLR",
        "description": "Solar flares, CMEs — 1 AU",
        "icon": "sun",
    },
    "stereo_a": {
        "type": "space", "name": "STEREO-A (cosmic rays + magnetic helicity)",
        "lat": 0.0, "lon": 70.0,   # ~70° ahead of Earth in its orbit
        "alt_km": 149_600_000, "instrument": "IMPACT/PLASTIC/SEPT",
        "description": "Cosmic ray protons, magnetic helicity, directional particles",
        "icon": "satellite",
    },
    "goes_18": {
        "type": "space", "name": "GOES-18 (GCR + SEP events)",
        "lat": 0.0, "lon": -137.0,  # Geostationary over western Americas
        "alt_km": 35_786, "instrument": "GOES/SGPS",
        "description": "Galactic cosmic rays, solar energetic particles",
        "icon": "satellite",
    },
    "earth_magnetosphere": {
        "type": "space", "name": "Earth Magnetosphere (Kp index)",
        "lat": 90.0, "lon": 0.0,
        "alt_km": 60_000, "instrument": "NOAA_SWPC",
        "description": "Geomagnetic storm index",
        "icon": "magnet",
    },
}

# Maps origin["source"] values emitted by streams → SPACE_ORIGINS key.
# Lets space-based readings render at their actual orbital positions instead of
# falling back to a ground station in PROJECTION_MAP.
SPACE_SOURCE_MAP: dict[str, str] = {
    "sun":                 "sun",
    "L1_lagrange":         "L1_dscovr",
    "DSCOVR":              "L1_dscovr",
    "ACE":                 "L1_ace",
    "GOES-18":             "goes_18",
    "GOES-19":             "goes_18",
    "stereo_a":            "stereo_a",
    "stereo_sept":         "stereo_a",
    "earth_magnetosphere": "earth_magnetosphere",
}

# ── Projection Map: Non-Geo Stream → Approximate Location ────────────────────
# Market/network/social streams get projected to designated hubs

PROJECTION_MAP = {
    # ── Financial / market ────────────────────────────────────────────────────
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
    # Options / derivatives (Chicago — CBOE)
    "options_skew":         (41.878, -87.629, "CBOE, Chicago"),
    "options_iv":           (41.878, -87.629, "CBOE, Chicago — IV level"),
    "vix":                  (41.878, -87.629, "CBOE VIX, Chicago"),
    "vix_low":              (41.878, -87.629, "CBOE VIX (low), Chicago"),

    # Yield curve / macro (Federal Reserve, DC)
    "yield_curve":          (38.893, -77.046, "Federal Reserve, Washington DC"),
    "yield_curve_invert":   (38.893, -77.046, "Federal Reserve — Inversion, DC"),
    "yield_curve_flat":     (38.893, -77.046, "Federal Reserve — Flat curve, DC"),
    "yield_curve_steep":    (38.893, -77.046, "Federal Reserve — Steep curve, DC"),
    "yield_spread_wide":    (38.893, -77.046, "Federal Reserve — Wide spread, DC"),

    # Shipping (Port of Singapore — global hub)
    "shipping":             (1.290, 103.852, "Port of Singapore"),
    "shipping_weak":        (1.290, 103.852, "Port of Singapore — weak"),
    "shipping_active":      (1.290, 103.852, "Port of Singapore — active"),
    "shipping_surge":       (1.290, 103.852, "Port of Singapore — surge"),
    "shipping_drop":        (1.290, 103.852, "Port of Singapore — drop"),

    # Power grid (CAISO, Folsom CA — Western US grid)
    "grid_load":            (38.681, -121.137, "CAISO Grid, Folsom CA"),
    "grid_elevated":        (38.681, -121.137, "CAISO Grid (elevated), Folsom CA"),
    "grid_peak":            (38.681, -121.137, "CAISO Grid (peak), Folsom CA"),

    # GDELT (global events — distributed; anchor at Atlanta project HQ)
    "gdelt_events":         (33.749, -84.388, "GDELT Project, Atlanta GA"),
    "gdelt_tone":           (33.749, -84.388, "GDELT Tone, Atlanta GA"),
    "gdelt_tone_spread":    (33.749, -84.388, "GDELT Tone Spread, Atlanta GA"),
    "gdelt_instability":    (33.749, -84.388, "GDELT Instability, Atlanta GA"),

    # Twitter/social (San Francisco)
    "twitter_crypto":       (37.429, -122.138, "Twitter/X, San Francisco"),

    # Wikipedia chiral (Wikimedia Foundation, SF)
    "wiki_chiral":          (37.429, -122.138, "Wikipedia — Chiral Articles"),
    "wiki_chiral_total":    (37.429, -122.138, "Wikipedia — Chiral Total Views"),
    "wiki_chiral_diversity": (37.429, -122.138, "Wikipedia — Chiral Diversity"),

    # ArXiv q-bio (Cornell University, Ithaca NY)
    "arxiv_bio_papers":     (42.446, -76.480, "arXiv q-bio, Cornell University"),
    "arxiv_bio_rate":       (42.446, -76.480, "arXiv q-bio (rate), Cornell"),
    "arxiv_bio_critical":   (42.446, -76.480, "arXiv q-bio (critical burst), Cornell"),
    "arxiv_bio_cats":       (42.446, -76.480, "arXiv q-bio categories, Cornell"),

    # GenBank / PubMed (NIH, Bethesda MD)
    "genbank_chiral":       (38.998, -77.103, "NCBI GenBank, NIH Bethesda MD"),
    "genbank_diversity":    (38.998, -77.103, "GenBank Diversity, NIH"),
    "genbank_rate":         (38.998, -77.103, "GenBank Submission Rate, NIH"),
    "genbank_fidelity":     (38.998, -77.103, "GenBank Fidelity, NIH"),
    "pubmed_pubs":          (38.998, -77.103, "PubMed, NIH Bethesda MD"),
    "pubmed_breakthrough":  (38.998, -77.103, "PubMed Breakthroughs, NIH"),

    # FDA enforcement (FDA HQ, Silver Spring MD)
    "fda_enforcement":      (39.043, -77.032, "FDA, Silver Spring MD"),
    "fda_enforcement_rate": (39.043, -77.032, "FDA Enforcement Rate"),
    "fda_enforcement_fidelity": (39.043, -77.032, "FDA Enforcement Fidelity"),

    # NASA night lights (NASA Goddard, Greenbelt MD)
    "night_lights":         (38.996, -76.848, "NASA Goddard, Greenbelt MD"),

    # Space-based streams (map to nearest ground station / NOAA SWPC Boulder)
    "cme_speed":            (40.013, -105.271, "NOAA SWPC, Boulder CO — CME"),
    "solar_flare_M":        (40.013, -105.271, "NOAA SWPC, Boulder CO — M-flare"),
    "solar_flare_X":        (40.013, -105.271, "NOAA SWPC, Boulder CO — X-flare"),
    "solar_wind_speed":     (40.013, -105.271, "NOAA SWPC, Boulder CO — solar wind"),
    "imf_bz":               (40.013, -105.271, "NOAA SWPC, Boulder CO — IMF Bz"),
    "kp_index":             (40.013, -105.271, "NOAA SWPC, Boulder CO — Kp"),
    "dscovr_bz_north":      (40.013, -105.271, "NOAA SWPC — DSCOVR Bz north"),
    "dscovr_bz_south":      (40.013, -105.271, "NOAA SWPC — DSCOVR Bz south"),
    "dscovr_bz_excursion":  (40.013, -105.271, "NOAA SWPC — DSCOVR Bz excursion"),
    "stereo_B_magnitude":   (40.013, -105.271, "NOAA SWPC — STEREO-A B magnitude"),
    "stereo_mag_helicity":  (40.013, -105.271, "NOAA SWPC — STEREO-A helicity"),
    "stereo_phi_sweep":     (40.013, -105.271, "NOAA SWPC — STEREO-A phi sweep"),
    "stereo_cosmic_ray":    (40.013, -105.271, "NOAA SWPC — STEREO-A cosmic rays"),
    "stereo_electron_flux": (40.013, -105.271, "NOAA SWPC — STEREO-A electrons"),
    "ace_proton_total":     (40.013, -105.271, "NOAA SWPC — ACE proton flux"),
    "ace_e_p_ratio":        (40.013, -105.271, "NOAA SWPC — ACE e/p ratio"),
    "ace_electron_flux":    (40.013, -105.271, "NOAA SWPC — ACE electron flux"),
    "ace_fp6p":             (40.013, -105.271, "NOAA SWPC — ACE spectral index"),
    "ace_spectral_hard":    (40.013, -105.271, "NOAA SWPC — ACE spectral hardening"),
    "ace_SEP_onset":        (40.013, -105.271, "NOAA SWPC — ACE SEP onset"),
    "goes_gcr_100MeV":      (40.013, -105.271, "NOAA SWPC — GOES GCR 100MeV"),
    "goes_gcr_500MeV":      (40.013, -105.271, "NOAA SWPC — GOES GCR 500MeV"),
    "goes_sep_10MeV":       (40.013, -105.271, "NOAA SWPC — GOES SEP 10MeV"),
    "goes_spectral_ratio":  (40.013, -105.271, "NOAA SWPC — GOES spectral ratio"),
    "goes_gcr_spectral":    (40.013, -105.271, "NOAA SWPC — GOES GCR spectral"),
    "goes_SEP_onset":       (40.013, -105.271, "NOAA SWPC — GOES SEP onset"),
    "stereo_SEP_onset":     (40.013, -105.271, "NOAA SWPC — STEREO SEP onset"),
    "stereo_proton_rise":   (40.013, -105.271, "NOAA SWPC — STEREO proton rise"),
    "sept_e_ion_ratio":     (40.013, -105.271, "NOAA SWPC — SEPT e/ion ratio"),
    "sept_hard_spectrum_e": (40.013, -105.271, "NOAA SWPC — SEPT hard e spectrum"),
    "sept_hard_spectrum_i": (40.013, -105.271, "NOAA SWPC — SEPT hard ion spectrum"),
    "sept_ns_asymmetry":    (40.013, -105.271, "NOAA SWPC — SEPT N/S asymmetry"),
    "sept_ns_symmetry":     (40.013, -105.271, "NOAA SWPC — SEPT N/S symmetric"),
    "sept_sun_asun_ratio":  (40.013, -105.271, "NOAA SWPC — SEPT sun/antisun"),
    "sept_electron_dominated": (40.013, -105.271, "NOAA SWPC — SEPT e-dominated"),
    "sept_e_flux":          (40.013, -105.271, "NOAA SWPC — SEPT electron flux"),
    "sept_data_freshness":  (40.013, -105.271, "NOAA SWPC — SEPT data latency"),

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

    # Air quality (EPA AQS network — Washington DC hub)
    "pm2_5":               (38.907, -77.037, "EPA AQS Network — PM2.5"),
    "ozone":               (38.907, -77.037, "EPA AQS Network — Ozone"),

    # DSCOVR variants missing from above
    "dscovr_bz_flipping":  (40.013, -105.271, "NOAA SWPC — DSCOVR Bz flipping"),
    "dscovr_bz_variable":  (40.013, -105.271, "NOAA SWPC — DSCOVR Bz variable"),

    # Alt crypto (Wall Street)
    "alt_outperform":      (40.707, -74.011, "Wall Street, NYC — Alt outperform"),
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

            if lat is None or lon is None:
                # 1. Space-based stream: map origin["source"] to orbital position
                sp_key = SPACE_SOURCE_MAP.get(origin.get("source", ""))
                if sp_key and sp_key in SPACE_ORIGINS:
                    sp = SPACE_ORIGINS[sp_key]
                    lat, lon = sp["lat"], sp["lon"]
                    origin_type = "space"
                # 2. Ground/market stream: fall back to PROJECTION_MAP hub
                elif r.stream in PROJECTION_MAP:
                    lat, lon, proj_label = PROJECTION_MAP[r.stream]
                    if not origin:
                        origin_type = "projected"

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

    def _full_geo_lookup(self, geo_nodes: List[GeoNode]) -> Dict[str, GeoNode]:
        """Build a geo lookup covering ALL known stream positions — not just
        streams currently active in the snapshot.  Active snapshot nodes take
        precedence (they carry live alert data); everything else is filled in
        from PROJECTION_MAP and SPACE_ORIGINS so coupling arcs are always
        visible regardless of whether a stream fired this cycle.
        """
        lookup: Dict[str, GeoNode] = {}

        # 1. Fill from static PROJECTION_MAP (alert=0, dim node)
        for stream, (lat, lon, label) in PROJECTION_MAP.items():
            lookup[stream] = GeoNode(
                stream=stream, primitive="", value=0.0, alert=0,
                lat=lat, lon=lon, origin_type="projected", label=label,
                timestamp=0.0,
            )

        # 2. Fill from SPACE_ORIGINS via SPACE_SOURCE_MAP
        for source_key, space_key in SPACE_SOURCE_MAP.items():
            sp = SPACE_ORIGINS.get(space_key)
            if sp:
                lookup[source_key] = GeoNode(
                    stream=source_key, primitive="", value=0.0, alert=0,
                    lat=sp["lat"], lon=sp["lon"], origin_type="space",
                    label=sp["name"], timestamp=0.0,
                )

        # 3. Override with live snapshot nodes (carry real alert/value data)
        for n in geo_nodes:
            lookup[n.stream] = n

        return lookup

    def _extract_geo_edges(self, geo_nodes: List[GeoNode]) -> List[GeoEdge]:
        """Build propagation arcs between geographically-anchored nodes.

        Uses the full geo lookup so arcs between any two known-position streams
        are always rendered — not just when both happen to be active this cycle.
        """
        self._load_if_needed()
        edges = []

        node_map = self._full_geo_lookup(geo_nodes)

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

        # Send all edges to client — threshold filtering happens in the frontend
        edges.sort(key=lambda e: abs(e.strength_r) * (1.0 - e.p_value), reverse=True)
        return edges

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

    def get_seismic_stations_geojson(self) -> dict:
        """Static layer: all IRIS GSN + GEOSCOPE stations as GeoJSON points."""
        from .domain_streams import _get_seismic_stations
        stations = _get_seismic_stations()
        features = []
        for sta in stations:
            features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [sta["lon"], sta["lat"]]},
                "properties": {
                    "type": "seismic_station",
                    "network": sta["net"],
                    "station": sta["sta"],
                    "name": sta["name"],
                    "elev_m": sta.get("elev", 0),
                    "label": f"{sta['net']}.{sta['sta']}",
                    "icon": "seismometer",
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

        spectral_radius = self._graph.get("spectral_radius", 3.4985)
        tick_hours = self._graph.get("tick_hours", 49.0)

        snap = self._latest_snapshot
        return {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "active_alerts": sum(1 for n in nodes if n.alert >= 1),
            "geo_nodes": len(nodes),
            "prop_edges": len(edges),
            "spectral_radius": spectral_radius,
            "tick_hours": tick_hours,
            "tick_days": tick_hours / 24,
            "tick_epoch": "1970-01-01T00:00:00Z",
            "tick_system": "unix_epoch (wall-clock anchored — same phase everywhere, no reset on refresh)",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "snapshot_ts": snap.ts if snap else None,
            "multiplier": snap.multiplier if snap else 1.0,
            "is_b_state": snap.is_b_state if snap else False,
            "total_alerts": snap.total_alerts if snap else 0,
            "total_readings": len(snap.readings) if snap else 0,
            "primitives": snap.primitives if snap else {},
            "errors": snap.errors if snap else [],
        }

    def get_primitives(self) -> dict:
        """Per-primitive alert levels and stream counts."""
        self._load_if_needed()
        snap = self._latest_snapshot
        if not snap:
            return {"primitives": {}}

        by_prim: Dict[str, list] = {}
        for r in snap.readings:
            by_prim.setdefault(r.primitive, []).append({
                "stream": r.stream,
                "alert": r.alert,
                "value": r.value,
                "unit": r.unit,
            })

        result = {}
        for prim, readings in by_prim.items():
            result[prim] = {
                "level": max(r["alert"] for r in readings),
                "stream_count": len(readings),
                "alert_count": sum(1 for r in readings if r["alert"] > 0),
                "readings": readings,
            }
        return {"primitives": result, "snapshot_ts": snap.ts, "multiplier": snap.multiplier}

    def get_streams(self) -> dict:
        """All stream readings grouped by category."""
        self._load_if_needed()
        snap = self._latest_snapshot
        if not snap:
            return {"streams": {}, "categories": {}}

        # Categorize by stream name prefix
        def _categorize(stream_name: str) -> str:
            prefixes = {
                "btc_": "crypto", "mempool_": "crypto", "block_": "crypto",
                "ln_": "crypto", "n_tx": "crypto", "mktcap_": "crypto",
                "alt_": "crypto", "fear_greed": "crypto", "hn_": "crypto",
                "twitter_crypto": "crypto",
                "yield_": "macro", "vix": "macro", "options_": "macro",
                "shipping": "macro", "grid_": "macro", "gdelt_": "macro",
                "ozone": "environment", "pm2_5": "environment",
                "surface_wind": "environment", "temp_swing": "environment",
                "tide_range": "environment", "night_lights": "environment",
                "seismic_": "environment", "wiki_attention": "environment",
                "genbank_": "biological", "pubmed_": "biological",
                "arxiv_bio": "biological", "fda_": "biological",
                "wiki_chiral": "biological",
                "cme_": "astrophysical", "solar_": "astrophysical",
                "imf_bz": "astrophysical", "kp_index": "astrophysical",
                "dscovr_": "astrophysical", "ace_": "astrophysical",
                "goes_": "astrophysical", "stereo_": "astrophysical",
                "sept_": "astrophysical",
            }
            for pfx, cat in prefixes.items():
                if stream_name.startswith(pfx) or stream_name == pfx.rstrip("_"):
                    return cat
            return "other"

        by_stream: Dict[str, dict] = {}
        for r in snap.readings:
            key = r.stream
            if key not in by_stream:
                by_stream[key] = {
                    "stream": key,
                    "category": _categorize(key),
                    "primitives": [],
                    "max_alert": 0,
                }
            by_stream[key]["primitives"].append({
                "primitive": r.primitive,
                "value": r.value,
                "unit": r.unit,
                "alert": r.alert,
            })
            by_stream[key]["max_alert"] = max(by_stream[key]["max_alert"], r.alert)

        # Group by category
        categories: Dict[str, list] = {}
        for s in by_stream.values():
            categories.setdefault(s["category"], []).append(s)

        return {
            "streams": by_stream,
            "categories": categories,
            "snapshot_ts": snap.ts,
            "multiplier": snap.multiplier,
            "is_b_state": snap.is_b_state,
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

    @app.route("/api/primitives")
    def api_primitives():
        return jsonify(engine.get_primitives())

    @app.route("/api/streams")
    def api_streams():
        return jsonify(engine.get_streams())

    @app.route("/api/all")
    def api_all():
        """Single endpoint returning all data for the dashboard."""
        rho_metrics = {}
        snap = engine._latest_snapshot
        if snap:
            try:
                rho_metrics = metrics_from_snapshot(snap)
            except Exception:
                pass
        return jsonify({
            "nodes": engine.get_nodes_geojson(),
            "edges": engine.get_edges_geojson(),
            "space": engine.get_space_geojson(),
            "seismic_stations": engine.get_seismic_stations_geojson(),
            "heatmap": engine.get_heatmap_data(),
            "stats": engine.get_stats(),
            "primitives": engine.get_primitives(),
            "streams": engine.get_streams(),
            "rho": rho_metrics,
        })

    @app.route("/api/density_matrix")
    def api_density_matrix():
        """Full density matrix metrics + SIC-POVM coverage."""
        snap = engine._latest_snapshot
        if not snap:
            return jsonify({"error": "no snapshot"}), 404
        from .sic_povm import coverage_analysis, missing_stream_proposals
        rho_metrics = metrics_from_snapshot(snap)
        cov = coverage_analysis()
        return jsonify({
            "rho": rho_metrics,
            "sic_coverage": cov,
            "missing_proposals": missing_stream_proposals(cov)[:30],
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