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
    # SIC gap fill streams
    "wiki_entropy":        (37.774, -122.419, "San Francisco — Wikimedia Foundation"),
    "wiki_concentration":  (37.774, -122.419, "San Francisco — Wikimedia Foundation"),
    "bgp_asns":            (52.374, 4.898,   "Amsterdam — RIPE NCC"),
    "bgp_delta":           (52.374, 4.898,   "Amsterdam — RIPE NCC"),
    "arxiv_ai_rate":       (42.360, -71.094, "Cambridge MA — ArXiv/MIT"),
    "arxiv_ai_spike":      (42.360, -71.094, "Cambridge MA — ArXiv/MIT"),
}


# ── Megalithic Reference Sites ────────────────────────────────────────────────
# Landmark ancient / sacred sites added as a static reference layer.
# Option-B ley-line analysis (2026-06-29): Stonehenge and Teotihuacan rank
# highest for correlation-arc great-circle intersections in the current
# coupling graph.
MEGALITHIC_SITES = {
    "Stonehenge":       {"lat":  51.179, "lon":  -1.826, "region": "Wiltshire, UK",      "tier": "A"},
    "Avebury":          {"lat":  51.428, "lon":  -1.854, "region": "Wiltshire, UK",      "tier": "A"},
    "Newgrange":        {"lat":  53.695, "lon":  -6.476, "region": "County Meath, IE",   "tier": "A"},
    "Carnac":           {"lat":  47.589, "lon":  -3.074, "region": "Brittany, FR",       "tier": "A"},
    "Great Pyramid":    {"lat":  29.979, "lon":  31.134, "region": "Giza, EG",           "tier": "A"},
    "Göbekli Tepe":     {"lat":  37.223, "lon":  38.922, "region": "Anatolia, TR",       "tier": "A"},
    "Angkor Wat":       {"lat":  13.412, "lon": 103.867, "region": "Siem Reap, KH",      "tier": "A"},
    "Teotihuacan":      {"lat":  19.692, "lon": -98.844, "region": "State of Mexico, MX","tier": "A"},
    "Machu Picchu":     {"lat": -13.163, "lon": -72.545, "region": "Cusco, PE",          "tier": "A"},
    "Tiwanaku":         {"lat": -16.554, "lon": -68.674, "region": "La Paz, BO",         "tier": "A"},
    "Easter Island":    {"lat": -27.113, "lon":-109.350, "region": "Rapa Nui, CL",       "tier": "A"},
    "Nazca Lines":      {"lat": -14.739, "lon": -75.130, "region": "Ica, PE",            "tier": "A"},
    "Chichen Itza":     {"lat":  20.684, "lon": -88.568, "region": "Yucatan, MX",        "tier": "A"},
}


# Per-primitive colors — each of the 12 primitives has a fixed hue
PRIMITIVE_COLOR = {
    "recognition":    "#ff6200",  # Ř — electric orange
    "chirality":      "#9b00ff",  # Ħ — electric purple
    "winding":        "#00ffcc",  # Ω — neon teal
    "dimensionality": "#6600ff",  # Ð — electric indigo
    "stoichiometry":  "#ff8800",  # Σ — deep orange
    "parity":         "#cc00ff",  # Φ — electric violet
    "kinetics":       "#ff3d00",  # Ç — plasma orange
    "fidelity":       "#00e5ff",  # ƒ — electric cyan
    "coupling":       "#00ff88",  # ɢ — neon green
    "granularity":    "#ff00cc",  # Γ — hot magenta
    "topology":       "#ff1744",  # Þ — electric red
    "criticality":    "#ffe600",  # ⊙ — electric yellow
}
_DEFAULT_COLOR = "#94a3b8"  # slate — unknown primitive


def primitive_color(primitive: str, alert: int) -> str:
    """Return primitive hue dimmed at alert=0, full at alert=1, bright at alert=2."""
    base = PRIMITIVE_COLOR.get(primitive, _DEFAULT_COLOR)
    if alert == 0:
        return base + "55"   # 33% opacity
    elif alert == 1:
        return base + "bb"   # 73% opacity
    else:
        return base          # full


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
                "color": primitive_color(self.primitive, self.alert),
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
                "color": primitive_color(self.source_node.primitive, min(1, int(abs(self.strength_r) * 2))),
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

    def get_megalithic_geojson(self) -> dict:
        """Static layer: megalithic / ancient sacred sites as GeoJSON points."""
        features = []
        for name, site in MEGALITHIC_SITES.items():
            features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [site["lon"], site["lat"]]},
                "properties": {
                    "name": name,
                    "region": site["region"],
                    "origin_type": "megalithic",
                    "label": name,
                    "radius": 8,
                    "color": "#ffd700",
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
    # Pick up template edits without a full restart (Jinja caches otherwise).
    app.config["TEMPLATES_AUTO_RELOAD"] = True
    app.jinja_env.auto_reload = True
    try:
        from flask_cors import CORS
        CORS(app, resources={r"/api/*": {"origins": ["https://imscribe.com", "https://www.imscribe.com",
                                                      "https://igpulse.imscribe.com", "http://localhost:5050",
                                                      "http://localhost:*"]}})
    except ImportError:
        pass
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
            "megalithic": engine.get_megalithic_geojson(),
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

    @app.route("/solar-seismic")
    def solar_seismic():
        return render_template("solar_seismic.html")

    @app.route("/api/solar-seismic/warnings")
    def api_solar_seismic_warnings():
        import time as _time, json as _json
        snap = engine._latest_snapshot
        if not snap:
            return jsonify({"warnings": [], "ts": None})

        # Known lag correlations from coupling data (hardcoded from observed r/p/lag)
        LAG_RULES = [
            {"trigger": "cme_speed",         "alert_min": 1, "r": -0.730, "lag_h": 62.9,
             "label": "CME impact",
             "msg": "CME detected ({val:.0f} km/s). Correlation: seismic suppression at network stations in ~{lag:.0f}h (arrival ~{eta})."},
            {"trigger": "ace_electron_flux",  "alert_min": 1, "r": +0.680, "lag_h": 2.7,
             "label": "ACE e⁻ flux",
             "msg": "Energetic electron flux elevated ({val:.0f} cts). Correlation: seismic elevation expected in ~{lag:.1f}h (arrival ~{eta})."},
            {"trigger": "ace_proton_total",   "alert_min": 2, "r": +0.600, "lag_h": 3.5,
             "label": "ACE proton storm",
             "msg": "ACE proton flux storm-level (alert {alv}). Seismic network may activate in ~{lag:.1f}h."},
            {"trigger": "solar_wind_speed",   "alert_min": 1, "r": +0.400, "lag_h": 18.0,
             "label": "Fast solar wind",
             "msg": "Solar wind elevated ({val:.0f} km/s). Correlated seismic response window opens in ~{lag:.0f}h (arrival ~{eta})."},
            {"trigger": "solar_flare_M",      "alert_min": 1, "r": +0.350, "lag_h": 8.0,
             "label": "M-class flare",
             "msg": "M-class solar flare detected ({cls}). Monitor for CME follow-up; seismic window ~{lag:.0f}h."},
            {"trigger": "goes_gcr_500MeV",    "alert_min": 2, "r": +0.450, "lag_h": 1.5,
             "label": "SEP event",
             "msg": "Solar energetic particle event (500 MeV, alert {alv}). Fast seismic response window ~{lag:.1f}h."},
            {"trigger": "stereo_mag_helicity","alert_min": 1, "r": +0.380, "lag_h": 24.0,
             "label": "Helicity surge",
             "msg": "STEREO-A magnetic helicity surge. Seismic correlation window ~{lag:.0f}h."},
            {"trigger": "kp_index",           "alert_min": 1, "r": +0.310, "lag_h": 12.0,
             "label": "Kp elevated",
             "msg": "Kp index elevated (Kp={val:.1f}). Geomagnetic loading — seismic correlation window ~{lag:.0f}h."},
        ]

        readings = snap.readings if hasattr(snap, 'readings') else []
        now_ts = _time.time()
        import datetime as _dt

        # Load coupling edges and station coords once
        coupling_path = engine.data_dir / "coupling.json"
        coupling = _json.loads(coupling_path.read_text()) if coupling_path.exists() else []
        try:
            from .domain_streams import _get_seismic_stations
            station_list = _get_seismic_stations()
            station_map = {f"{s['net']}_{s['sta']}": s for s in station_list}
        except Exception:
            station_map = {}

        def stations_for_trigger(trigger_stream, lag_h, tol_h=6.0):
            """Return list of {code, name, lat, lon} correlated with this solar stream at ~lag_h."""
            results = []
            seen = set()
            for e in coupling:
                src, tgt = e['source_stream'], e['target_stream']
                if src != trigger_stream or 'seismic_' not in tgt:
                    continue
                if abs(e['lag_seconds'] / 3600 - lag_h) > tol_h:
                    continue
                key = tgt.replace('seismic_', '', 1)
                if key in seen:
                    continue
                seen.add(key)
                s = station_map.get(key)
                if s:
                    results.append({"code": key, "name": s['name'], "lat": s['lat'], "lon": s['lon']})
            return results

        warnings = []
        seen_triggers = set()

        for rule in LAG_RULES:
            trigger = rule["trigger"]
            if trigger in seen_triggers:
                continue
            matches = [r for r in readings if r.stream == trigger and r.alert >= rule["alert_min"]]
            if not matches:
                continue
            best = max(matches, key=lambda r: r.alert)
            val = best.value
            alv = best.alert
            cls = best.origin.get("flare_class", "M-class") if isinstance(best.origin, dict) else "M-class"
            lag_h = rule["lag_h"]
            eta_ts = now_ts + lag_h * 3600
            eta = _dt.datetime.utcfromtimestamp(eta_ts).strftime("%Y-%m-%d %H:%MZ")
            severity = "critical" if alv >= 2 else "elevated"
            stations = stations_for_trigger(trigger, lag_h)
            msg = rule["msg"].format(val=val, lag=lag_h, eta=eta, alv=alv, cls=cls)
            warnings.append({
                "label": rule["label"],
                "trigger_stream": trigger,
                "trigger_value": val,
                "trigger_alert": alv,
                "r": rule["r"],
                "lag_h": lag_h,
                "eta": eta,
                "severity": severity,
                "msg": msg,
                "stations": stations,
            })
            seen_triggers.add(trigger)

        warnings.sort(key=lambda w: (-w["trigger_alert"], -abs(w["r"])))
        return jsonify({"warnings": warnings, "ts": snap.ts})

    @app.route("/api/solar-seismic/chains")
    def api_solar_seismic_chains():
        import time as _time
        import datetime as _dt
        snap = engine._latest_snapshot
        if not snap:
            return jsonify({"chains": [], "ts": None})

        readings = snap.readings if hasattr(snap, 'readings') else []
        rd = {(r.stream, r.primitive): r for r in readings}
        now = _time.time()

        def active(stream, primitive, alert_min=1):
            r = rd.get((stream, primitive))
            return r is not None and r.alert >= alert_min

        def val(stream, primitive):
            r = rd.get((stream, primitive))
            return r.value if r else None

        def eta_str(lag_s):
            t = now + lag_s
            return _dt.datetime.utcfromtimestamp(t).strftime("%H:%MZ")

        def node(label, glyph, stream, primitive, alert_min=1):
            a = active(stream, primitive, alert_min)
            v = val(stream, primitive)
            return {"label": label, "glyph": glyph, "stream": stream,
                    "primitive": primitive, "active": a, "value": v}

        # Each chain: list of nodes + list of lags between consecutive nodes (seconds, or None for zero-lag)
        CHAINS = [
            {
                "id": "aurora_seismic",
                "title": "Aurora → Seismic",
                "desc": "Winding leads chirality leads topology",
                "nodes": [
                    node("oval:Ω", "Ω", "aurora_oval_extent", "winding"),
                    node("south:Ħ", "Ħ", "aurora_south_peak", "chirality"),
                    node("seismic:Þ", "Þ", "seismic_IU_GUMO", "topology"),
                ],
                "lags": [7264, None],   # Ω→Ħ 7264s observed; Ħ→Þ unknown
                "r": [0.968, None],
            },
            {
                "id": "knowledge_market",
                "title": "Knowledge → Market → Event",
                "desc": "Recognition leads criticality leads coupling",
                "nodes": [
                    node("pubmed:Ř", "Ř", "pubmed_pubs", "recognition"),
                    node("options:⊙", "⊙", "options_iv", "criticality"),
                    node("gdelt:ɢ", "ɢ", "gdelt_events", "coupling"),
                ],
                "lags": [3859, 454],
                "r": [0.939, 0.931],
            },
            {
                "id": "cosmic_ray_identity",
                "title": "Cosmic Ray Identity",
                "desc": "Chirality and winding are degenerate at zero lag",
                "nodes": [
                    node("gcr100:Ħ", "Ħ", "goes_gcr_100MeV", "chirality"),
                    node("gcr500:Ω", "Ω", "goes_gcr_500MeV", "winding"),
                ],
                "lags": [0],
                "r": [1.000],
            },
            {
                "id": "aurora_storm",
                "title": "Aurora ↔ Polar Storm",
                "desc": "Winding and criticality locked at zero lag",
                "nodes": [
                    node("oval:Ω", "Ω", "aurora_oval_extent", "winding"),
                    node("storm:⊙", "⊙", "polar_gstorm_level", "criticality"),
                ],
                "lags": [0],
                "r": [1.000],
            },
        ]

        # Annotate each chain: which step is the leading edge, what's the ETA for the next node
        result = []
        for ch in CHAINS:
            nodes = ch["nodes"]
            lags = ch["lags"]
            rs = ch["r"]
            active_count = sum(1 for n in nodes if n["active"])
            # Find furthest active node
            leading = -1
            for i, n in enumerate(nodes):
                if n["active"]:
                    leading = i
            eta = None
            lag_running = None
            if 0 <= leading < len(nodes) - 1:
                next_lag = lags[leading]
                if next_lag and next_lag > 0:
                    eta = eta_str(next_lag)
                    lag_running = next_lag
            # Chain status
            if active_count == 0:
                status = "dormant"
            elif active_count == len(nodes):
                status = "complete"
            elif leading == 0:
                status = "initiated"
            else:
                status = "propagating"

            result.append({
                "id": ch["id"],
                "title": ch["title"],
                "desc": ch["desc"],
                "nodes": nodes,
                "lags": lags,
                "r": rs,
                "status": status,
                "leading": leading,
                "next_eta": eta,
                "lag_running_s": lag_running,
                "active_count": active_count,
            })

        return jsonify({"chains": result, "ts": snap.ts})

    @app.route("/api/solar-seismic")
    def api_solar_seismic():
        import json as _json
        coupling_path = engine.data_dir / "coupling.json"
        if not coupling_path.exists():
            return jsonify({"edges": [], "stations": [], "solar": []})
        edges = _json.loads(coupling_path.read_text())
        seismic_keys = {s for s in
                        set(e['source_stream'] for e in edges) | set(e['target_stream'] for e in edges)
                        if 'seismic' in s}
        # All edges where at least one side is seismic
        hits = [e for e in edges
                if e['source_stream'] in seismic_keys or e['target_stream'] in seismic_keys]
        # Station coordinates from IRIS
        try:
            from .domain_streams import _get_seismic_stations
            all_stations = _get_seismic_stations()
            station_map = {f"{s['net']}_{s['sta']}": s for s in all_stations}
        except Exception:
            all_stations = []
            station_map = {}
        # Coupling collapses per-station seismic streams to seismic_net_{NET}
        # (see coupler._coupling_stream_name), so resolve a network to the
        # centroid of its stations. Longitude uses a circular mean so globe-
        # spanning networks (IU/II/G) don't average to a bogus mid-ocean point.
        import math as _math
        _net_groups: dict = {}
        for s in all_stations:
            _net_groups.setdefault(s['net'], []).append(s)
        net_map = {}
        for net, lst in _net_groups.items():
            lat = sum(x['lat'] for x in lst) / len(lst)
            cx = sum(_math.cos(_math.radians(x['lon'])) for x in lst)
            cy = sum(_math.sin(_math.radians(x['lon'])) for x in lst)
            lon = _math.degrees(_math.atan2(cy, cx)) if (cx or cy) else 0.0
            net_map[net] = {'lat': lat, 'lon': lon,
                            'name': f'{net} network ({len(lst)} stations)'}
        # Coordinates + category for every non-seismic stream that couples with seismic
        # category drives colour in the frontend: solar / financial / environmental / info / bio
        partner_coords = {
            # ── Space weather ──────────────────────────────────────────────────
            'cme_speed':          {'lat': 40.0,  'lon':-105.3, 'label':'NOAA SWPC (CME)',           'cat':'solar'},
            'solar_flare_M':      {'lat': 40.0,  'lon':-105.3, 'label':'NOAA SWPC (M-flare)',       'cat':'solar'},
            'solar_flare_X':      {'lat': 40.0,  'lon':-105.3, 'label':'NOAA SWPC (X-flare)',       'cat':'solar'},
            'solar_wind_speed':   {'lat': 28.3,  'lon': -80.6, 'label':'ACE/DSCOVR L1',             'cat':'solar'},
            'imf_bz':             {'lat': 28.3,  'lon': -80.6, 'label':'IMF Bz (L1)',               'cat':'solar'},
            'kp_index':           {'lat': 40.0,  'lon':-105.3, 'label':'NOAA SWPC (Kp)',            'cat':'solar'},
            'ace_electron_flux':  {'lat': 28.3,  'lon': -80.6, 'label':'ACE (L1)',                  'cat':'solar'},
            'ace_proton_total':   {'lat': 28.3,  'lon': -80.6, 'label':'ACE (L1)',                  'cat':'solar'},
            'ace_e_p_ratio':      {'lat': 28.3,  'lon': -80.6, 'label':'ACE e/p ratio (L1)',        'cat':'solar'},
            'stereo_B_magnitude': {'lat': 32.0,  'lon':-110.9, 'label':'STEREO-A',                  'cat':'solar'},
            'stereo_mag_helicity':{'lat': 32.0,  'lon':-110.9, 'label':'STEREO-A (helicity)',       'cat':'solar'},
            'stereo_phi_sweep':   {'lat': 32.0,  'lon':-110.9, 'label':'STEREO-A (phi sweep)',      'cat':'solar'},
            'goes_gcr_100MeV':    {'lat': 28.3,  'lon': -80.6, 'label':'GOES-18 (GCR 100MeV)',     'cat':'solar'},
            'goes_gcr_500MeV':    {'lat': 28.3,  'lon': -80.6, 'label':'GOES-18 (GCR 500MeV)',     'cat':'solar'},
            'goes_gcr_depression':{'lat': 28.3,  'lon': -80.6, 'label':'GOES-18 (GCR depression)', 'cat':'solar'},
            'dscovr_bz_flipping': {'lat': 28.3,  'lon': -80.6, 'label':'DSCOVR Bz flipping (L1)', 'cat':'solar'},
            'dscovr_bz_variable': {'lat': 28.3,  'lon': -80.6, 'label':'DSCOVR Bz variable (L1)', 'cat':'solar'},
            # ── Environmental ──────────────────────────────────────────────────
            'pm2_5':              {'lat': 39.0,  'lon': -77.0, 'label':'EPA PM2.5 (US)',            'cat':'environmental'},
            'ozone':              {'lat': 39.0,  'lon': -77.0, 'label':'EPA Ozone (US)',            'cat':'environmental'},
            'tide_range':         {'lat': 37.8,  'lon':-122.5, 'label':'NOAA Tides (SF Bay)',       'cat':'environmental'},
            'grid_elevated':      {'lat': 38.9,  'lon': -77.0, 'label':'NERC Grid Alert',           'cat':'environmental'},
            # ── Financial / market ─────────────────────────────────────────────
            'fear_greed':         {'lat': 40.71, 'lon': -74.0, 'label':'CNN Fear & Greed (NYSE)',   'cat':'financial'},
            'options_iv':         {'lat': 41.88, 'lon': -87.6, 'label':'Options IV (CME)',          'cat':'financial'},
            'shipping_weak':      {'lat': 22.3,  'lon': 114.2, 'label':'Baltic Dry / Shipping',     'cat':'financial'},
            'btc_dominance_surge':{'lat': 40.71, 'lon': -74.0, 'label':'BTC Dominance',            'cat':'financial'},
            'n_tx':               {'lat': 40.71, 'lon': -74.0, 'label':'BTC Transaction Count',    'cat':'financial'},
            'mempool_count':      {'lat': 40.71, 'lon': -74.0, 'label':'Mempool Count',            'cat':'financial'},
            'mempool_low_fee':    {'lat': 40.71, 'lon': -74.0, 'label':'Mempool Low Fee',          'cat':'financial'},
            'ln_capacity':        {'lat': 40.71, 'lon': -74.0, 'label':'Lightning Network capacity','cat':'financial'},
            'alt_divergence':     {'lat': 40.71, 'lon': -74.0, 'label':'Altcoin Divergence',       'cat':'financial'},
            'alt_outperform':     {'lat': 40.71, 'lon': -74.0, 'label':'Altcoin Outperform',       'cat':'financial'},
            # ── Prediction markets (Kalshi) ────────────────────────────────────
            'kalshi_economics':   {'lat': 40.71, 'lon': -74.0, 'label':'Kalshi (economics)',       'cat':'financial'},
            'kalshi_world':       {'lat': 40.71, 'lon': -74.0, 'label':'Kalshi (world)',           'cat':'financial'},
            'kalshi_elections':   {'lat': 40.71, 'lon': -74.0, 'label':'Kalshi (elections)',       'cat':'financial'},
            'kalshi_health':      {'lat': 40.71, 'lon': -74.0, 'label':'Kalshi (health)',          'cat':'financial'},
            'kalshi_companies':   {'lat': 40.71, 'lon': -74.0, 'label':'Kalshi (companies)',       'cat':'financial'},
            'kalshi_social':      {'lat': 40.71, 'lon': -74.0, 'label':'Kalshi (social)',          'cat':'financial'},
            'kalshi_politics':    {'lat': 40.71, 'lon': -74.0, 'label':'Kalshi (politics)',        'cat':'financial'},
            'kalshi_climate_and_weather':{'lat':40.71,'lon':-74.0,'label':'Kalshi (climate)',      'cat':'financial'},
            'kalshi_sports':      {'lat': 40.71, 'lon': -74.0, 'label':'Kalshi (sports)',          'cat':'financial'},
            'kalshi_financials':  {'lat': 40.71, 'lon': -74.0, 'label':'Kalshi (financials)',      'cat':'financial'},
            'kalshi_entertainment':{'lat':40.71, 'lon': -74.0, 'label':'Kalshi (entertainment)',   'cat':'financial'},
            'kalshi_science_and_technology':{'lat':40.71,'lon':-74.0,'label':'Kalshi (science/tech)','cat':'financial'},
            # ── Information / social ───────────────────────────────────────────
            'gdelt_tone_spread':  {'lat': 33.7,  'lon': -84.4, 'label':'GDELT Tone Spread',        'cat':'info'},
            'gdelt_events':       {'lat': 33.7,  'lon': -84.4, 'label':'GDELT Events',             'cat':'info'},
            'wiki_chiral':        {'lat': 37.8,  'lon':-122.4, 'label':'Wikipedia Chiral edits',   'cat':'info'},
            'wiki_entropy':       {'lat': 37.8,  'lon':-122.4, 'label':'Wikipedia Edit Entropy',   'cat':'info'},
            'hn_silence':         {'lat': 37.4,  'lon':-122.1, 'label':'HN Comment Silence',       'cat':'info'},
            'arxiv_ai_rate':      {'lat': 42.4,  'lon': -76.5, 'label':'arXiv AI submission rate', 'cat':'info'},
            'arxiv_bio_critical': {'lat': 42.4,  'lon': -76.5, 'label':'arXiv Bio (critical)',     'cat':'info'},
            'arxiv_bio_rate':     {'lat': 42.4,  'lon': -76.5, 'label':'arXiv Bio submission rate','cat':'info'},
            # ── Biological / health ────────────────────────────────────────────
            'pubmed_pubs':        {'lat': 39.0,  'lon': -77.1, 'label':'PubMed Publications',      'cat':'bio'},
            'pubmed_breakthrough':{'lat': 39.0,  'lon': -77.1, 'label':'PubMed Breakthroughs',     'cat':'bio'},
            'genbank_chiral':     {'lat': 39.0,  'lon': -77.1, 'label':'GenBank Chiral sequences', 'cat':'bio'},
            'genbank_diversity':  {'lat': 39.0,  'lon': -77.1, 'label':'GenBank Diversity index',  'cat':'bio'},
            'fda_enforcement':    {'lat': 39.0,  'lon': -77.1, 'label':'FDA Enforcement actions',  'cat':'bio'},
            # ── Extraplanetary ─────────────────────────────────────────────────
            'aurora_north_peak':            {'lat': 64.8, 'lon':-147.9, 'label':'Aurora — north polar cap peak (Fairbanks AK)',  'cat':'extraplanetary'},
            'aurora_south_peak':            {'lat':-54.8, 'lon': -68.3, 'label':'Aurora — south polar cap peak (Ushuaia)', 'cat':'extraplanetary'},
            'aurora_ns_asymmetry':          {'lat': 64.8, 'lon':-147.9, 'label':'Aurora N/S asymmetry',           'cat':'extraplanetary'},
            'aurora_oval_extent':           {'lat': 64.8, 'lon':-147.9, 'label':'Auroral oval extent (Fairbanks)','cat':'extraplanetary'},
            'polar_gstorm_level':           {'lat': 40.0, 'lon':-105.3, 'label':'NOAA SWPC G-scale storm level', 'cat':'extraplanetary'},
            'neutron_monitor_oulu':         {'lat': 39.4, 'lon':-106.2, 'label':'GCR flux — Oulu NM / Climax CO anchor', 'cat':'extraplanetary'},
            'neutron_monitor_oulu_forbush': {'lat': 39.4, 'lon':-106.2, 'label':'Forbush decrease — Oulu NM',    'cat':'extraplanetary'},
            'goes_xrs_b':                   {'lat': 28.3, 'lon': -80.6, 'label':'GOES XRS-B (solar X-ray flux)', 'cat':'extraplanetary'},
            'goes_xrs_b_xclass':            {'lat': 28.3, 'lon': -80.6, 'label':'GOES XRS-B (X-class flare)',   'cat':'extraplanetary'},
            'goes_xrs_b_mclass':            {'lat': 28.3, 'lon': -80.6, 'label':'GOES XRS-B (M-class flare)',   'cat':'extraplanetary'},
            'ligo_gw_alert':                {'lat': 46.45,'lon':-119.41,'label':'LIGO Hanford (GW candidate)',   'cat':'extraplanetary'},
            'ligo_gw_rate':                 {'lat': 46.45,'lon':-119.41,'label':'LIGO (GW event rate)',          'cat':'extraplanetary'},
            'ligo_gw_far':                  {'lat': 30.56,'lon': -90.77,'label':'LIGO Livingston (GW FAR)',      'cat':'extraplanetary'},
            'fermi_grb_rate':               {'lat': 28.3, 'lon': -80.6, 'label':'Fermi GBM (GRB rate)',         'cat':'extraplanetary'},
            'dscovr_sw_density':            {'lat': 28.3, 'lon': -80.6, 'label':'DSCOVR SW density (L1)',       'cat':'extraplanetary'},
            'dscovr_sw_kinetics':           {'lat': 28.3, 'lon': -80.6, 'label':'DSCOVR SW kinetics (L1)',      'cat':'extraplanetary'},
        }
        # Build edge features — all seismic coupling edges
        # Deduplicate: multiple primitives can produce the same (stream-pair, lag, r) display row.
        features = []
        _seen_display = set()
        for e in sorted(hits, key=lambda x: abs(x['strength_r']), reverse=True):
            src = e['source_stream']; tgt = e['target_stream']
            if src in seismic_keys:
                sei_stream, partner_stream = src, tgt
                direction = 'seismic→partner'
            else:
                sei_stream, partner_stream = tgt, src
                direction = 'partner→seismic'
            # Resolve partner coordinates; fall back to prefix-match for kalshi sub-markets
            partner = partner_coords.get(partner_stream)
            if partner is None:
                for key, val in partner_coords.items():
                    if partner_stream.startswith(key):
                        partner = {**val, 'label': f"{val['label']} / {partner_stream[len(key):].lstrip('_')}"}
                        break
            if sei_stream.startswith('seismic_net_'):
                sei = net_map.get(sei_stream[len('seismic_net_'):])
            else:
                sei = station_map.get(sei_stream.replace('seismic_', '', 1))
            if not partner or not sei:
                continue
            lag_h = e['lag_seconds'] / 3600
            _display_key = (sei_stream, partner_stream, round(lag_h, 1), round(e['strength_r'], 3))
            if _display_key in _seen_display:
                continue
            _seen_display.add(_display_key)
            features.append({
                'partner_stream': partner_stream,
                'seismic_stream': sei_stream,
                'partner_cat':    partner['cat'],
                'partner_lat': partner['lat'], 'partner_lon': partner['lon'],
                'partner_label': partner['label'],
                'sei_lat': sei['lat'], 'sei_lon': sei['lon'],
                'sei_label': f"{sei_stream} ({sei['name']})",
                # Keep legacy sol_* keys so old JS still works during transition
                'sol_lat': partner['lat'], 'sol_lon': partner['lon'],
                'sol_label': partner['label'],
                'solar_stream': partner_stream,
                'r': e['strength_r'], 'p': e['p_value'],
                'lag_h': lag_h, 'direction': direction,
            })
        # Return all stations as background nodes (not just correlated ones)
        all_sta = [
            {"code": f"{s['net']}_{s['sta']}", "name": s['name'],
             "lat": s['lat'], "lon": s['lon'], "net": s['net']}
            for s in all_stations
        ]
        return jsonify({"edges": features, "stations": all_sta})

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