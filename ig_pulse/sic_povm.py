"""
ig_pulse/sic_povm.py

SIC-POVM coverage analysis for ig-pulse.

The 144 = 12² Weyl-Heisenberg SIC elements span the full operator space on
ℂ¹². The 33 existing streams sample a sparse, biased subset. This module:

  1. Maps each existing stream to its nearest SIC element (p, q)
  2. Identifies which of the 144 elements are uncovered
  3. Characterises missing elements by their dominant cross-primitive direction
  4. Proposes physical observables that would probe each missing direction

The key insight: off-axis SIC elements (p,q with both p,q > 0) measure
SUPERPOSITIONS of primitive axes. Many can be synthesised as nonlinear
combinations of existing stream data rather than requiring new data sources.
"""

import numpy as np
from typing import Dict, List, Tuple, Set
from .density_matrix import (
    D, PRIMITIVES, PRIM_IDX, sic_elements, displacement, _FIDUCIAL_VEC,
)


# ── Stream → primitive vector map ─────────────────────────────────────────────
# Each stream has a dominant primitive. Some streams span two primitives.

STREAM_PRIMITIVE_MAP: Dict[str, List[Tuple[str, float]]] = {
    # Crypto / financial
    "btc_dominance":        [("coupling", 0.8), ("dimensionality", 0.2)],
    "fear_greed":           [("coupling", 0.7), ("parity", 0.3)],
    "ln_capacity":          [("coupling", 0.6), ("topology", 0.4)],
    "alt_outperform":       [("dimensionality", 0.6), ("coupling", 0.4)],
    "funding_rate":         [("coupling", 0.8), ("kinetics", 0.2)],
    "open_interest":        [("coupling", 0.7), ("stoichiometry", 0.3)],
    "gas_price":            [("kinetics", 0.6), ("coupling", 0.4)],
    "defi_tvl":             [("coupling", 0.5), ("dimensionality", 0.5)],
    # Macro
    "vix":                  [("parity", 0.7), ("coupling", 0.3)],
    "gold_ratio":           [("parity", 0.6), ("stoichiometry", 0.4)],
    "dxy":                  [("dimensionality", 0.7), ("parity", 0.3)],
    "yield_curve":          [("topology", 0.5), ("coupling", 0.5)],
    "kalshi_health":        [("fidelity", 0.7), ("chirality", 0.3)],
    "kalshi_fed":           [("coupling", 0.6), ("topology", 0.4)],
    "manifold_market":      [("parity", 0.6), ("coupling", 0.4)],
    "predictit":            [("parity", 0.8), ("coupling", 0.2)],
    "polymarket":           [("parity", 0.7), ("coupling", 0.3)],
    "metaculus":            [("criticality", 0.5), ("fidelity", 0.5)],
    # Environmental
    "pm2_5":                [("winding", 0.6), ("kinetics", 0.4)],
    "ozone":                [("winding", 0.7), ("topology", 0.3)],
    "temp_swing":           [("winding", 0.8), ("chirality", 0.2)],
    "surface_wind":         [("kinetics", 0.7), ("winding", 0.3)],
    "tide_range":           [("winding", 0.6), ("topology", 0.4)],
    # Astrophysical
    "solar_wind_speed":     [("dimensionality", 0.6), ("kinetics", 0.4)],
    "kp_index":             [("topology", 0.6), ("winding", 0.4)],
    "goes_xray":            [("criticality", 0.7), ("dimensionality", 0.3)],
    "dscovr_bz":            [("topology", 0.6), ("chirality", 0.4)],
    "stereo_sept":          [("criticality", 0.6), ("dimensionality", 0.4)],
    "solar_flux":           [("criticality", 0.7), ("winding", 0.3)],
    # Seismic
    "seismic_energy":       [("topology", 0.6), ("winding", 0.4)],
    "seismic_major":        [("topology", 0.5), ("criticality", 0.5)],
    "seismic_network":      [("topology", 0.4), ("winding", 0.3), ("criticality", 0.3)],
}


def _stream_operator(components: List[Tuple[str, float]]) -> np.ndarray:
    """Build a 12×12 POVM operator from (primitive, weight) components."""
    psi = np.zeros(D)
    for prim, w in components:
        idx = PRIM_IDX.get(prim)
        if idx is not None:
            psi[idx] += w
    n = np.linalg.norm(psi)
    if n < 1e-10:
        return np.eye(D) / D
    psi /= n
    return np.outer(psi, psi)


def _nearest_sic_element(M: np.ndarray, elems) -> Tuple[int, int, float]:
    """Find the SIC element (p, q) with maximum Tr(M · Π_{p,q})."""
    best_pq = (0, 0)
    best_overlap = -np.inf
    for p, q, Pi in elems:
        overlap = float(np.real(np.trace(M @ Pi)))
        if overlap > best_overlap:
            best_overlap = overlap
            best_pq = (p, q)
    return best_pq[0], best_pq[1], best_overlap


# ── Coverage analysis ─────────────────────────────────────────────────────────

def coverage_analysis() -> Dict:
    """
    Compute which SIC elements are covered by existing streams.
    Returns structured coverage report.
    """
    elems = sic_elements()
    covered: Set[Tuple[int, int]] = set()
    stream_assignments: Dict[str, Tuple[int, int]] = {}

    for stream, components in STREAM_PRIMITIVE_MAP.items():
        M = _stream_operator(components)
        p, q, overlap = _nearest_sic_element(M, elems)
        covered.add((p, q))
        stream_assignments[stream] = (p, q)

    all_pq = {(p, q) for p in range(D) for q in range(D)}
    missing = sorted(all_pq - covered)

    return {
        "total_sic_elements":  D * D,
        "covered":             len(covered),
        "missing":             len(missing),
        "coverage_fraction":   round(len(covered) / (D * D), 4),
        "stream_assignments":  {s: list(pq) for s, pq in stream_assignments.items()},
        "missing_elements":    [list(pq) for pq in missing],
    }


# ── Missing element characterisation ─────────────────────────────────────────

def _sic_element_character(p: int, q: int) -> Dict:
    """
    Characterise a SIC element D(p,q)|ψ_fid⟩ by its dominant primitive axes
    and cross-primitive structure.
    """
    D_pq = displacement(p, q)
    psi = D_pq @ _FIDUCIAL_VEC
    psi /= np.linalg.norm(psi)

    amplitudes = np.abs(psi)
    phases = np.angle(psi)

    top_idx = np.argsort(amplitudes)[::-1][:3]
    dominant = [
        {"primitive": PRIMITIVES[i], "amplitude": round(float(amplitudes[i]), 4),
         "phase_deg": round(float(np.degrees(phases[i])), 1)}
        for i in top_idx
    ]

    is_on_axis = (p == 0 or q == 0)
    cross_pair = (PRIMITIVES[top_idx[0]], PRIMITIVES[top_idx[1]]) if len(top_idx) >= 2 else None

    return {
        "p": p, "q": q,
        "dominant_primitives": dominant,
        "is_on_axis": is_on_axis,
        "cross_pair": list(cross_pair) if cross_pair else None,
    }


# ── Observable proposals for missing elements ─────────────────────────────────

# Physical observables that probe cross-primitive superpositions.
# Keyed by (dominant_prim_a, dominant_prim_b) pair.
CROSS_PRIMITIVE_OBSERVABLES: Dict[Tuple[str, str], List[str]] = {
    ("recognition", "coupling"):      ["Twitter/Mastodon viral topic × BTC dominance", "Google Trends finance × market cap"],
    ("recognition", "parity"):        ["Wikipedia page edits on political topics", "Reddit r/politics karma flow"],
    ("recognition", "criticality"):   ["Arxiv AI paper submission rate", "HackerNews score × topic entropy"],
    ("recognition", "winding"):       ["Climate news sentiment index", "Environmental hashtag trending"],
    ("recognition", "topology"):      ["Geopolitical event NLP stream (GDELT)", "Wikipedia conflict-page edit rate"],
    ("recognition", "fidelity"):      ["PubMed new paper rate", "bioRxiv preprint sentiment"],
    ("recognition", "granularity"):   ["Google Trends cross-topic diversity index", "BGP prefix announcement rate"],
    ("recognition", "stoichiometry"): ["Commodity news mention frequency", "Shipping route news density"],
    ("chirality", "winding"):         ["Atmospheric CO₂ isotope ratio δ¹³C (Mauna Loa)", "Circadian melatonin proxy (blue light index)"],
    ("chirality", "coupling"):        ["Bid-ask spread asymmetry (market microstructure)", "Options put/call skew"],
    ("chirality", "kinetics"):        ["Ocean current reversal index (RAPID array)", "River discharge L/R bank asymmetry"],
    ("chirality", "topology"):        ["Magnetic field polarity sector boundary crossings", "CME handedness (helicity)"],
    ("chirality", "criticality"):     ["Solar wind Bz north/south flip rate", "Flare peak asymmetry index"],
    ("chirality", "dimensionality"):  ["Crypto long/short ratio asymmetry", "SPX skewness (3rd moment)"],
    ("stoichiometry", "coupling"):    ["Global M2 money supply growth rate", "Eurodollar open interest"],
    ("stoichiometry", "kinetics"):    ["Manufacturing PMI (ISM)", "Baltic Dry Index"],
    ("stoichiometry", "topology"):    ["AIS global ship density (OpenSeaMap)", "Port container throughput"],
    ("stoichiometry", "winding"):     ["Global electricity generation (EIA weekly)", "Natural gas storage delta"],
    ("stoichiometry", "parity"):      ["CFTC COT net positions", "Futures term structure spread"],
    ("stoichiometry", "dimensionality"):["BTC supply-side ratio (miner revenue/fees)", "ETH issuance rate"],
    ("granularity", "coupling"):      ["Market microstructure fractal dimension", "Order book depth entropy"],
    ("granularity", "topology"):      ["Internet BGP routing table size", "Autonomous system path diversity"],
    ("granularity", "kinetics"):      ["Urban traffic flow density (Uber Movement)", "Ride-share surge pricing entropy"],
    ("granularity", "winding"):       ["Precipitation radar texture (NEXRAD)", "Cloud fraction variance (GOES)"],
    ("granularity", "criticality"):   ["Solar image texture (AIA 171Å)", "X-ray photon count variance"],
    ("granularity", "dimensionality"):["Crypto transaction size distribution entropy", "NFT floor price fractal dim"],
    ("granularity", "stoichiometry"): ["Supply chain node degree distribution", "Port queue length distribution"],
    ("granularity", "fidelity"):      ["Genomic sequencing base-call quality score", "Lab assay precision index"],
    ("kinetics", "topology"):         ["Seismic wave propagation velocity anomaly", "Fault slip rate (GNSS)"],
    ("kinetics", "coupling"):         ["HFT order-cancel rate", "Dark pool fill ratio"],
    ("kinetics", "dimensionality"):   ["Crypto mempool transaction arrival rate", "Lightning payment routing speed"],
    ("kinetics", "parity"):           ["Options gamma exposure", "Delta-hedging flow rate"],
    ("fidelity", "winding"):          ["Climate model ensemble spread", "GCM forecast skill score"],
    ("fidelity", "topology"):         ["GNSS ionospheric TEC variance", "GPS signal multipath index"],
    ("fidelity", "coupling"):         ["Prediction market calibration score (Brier)", "Superforecaster Brier drift"],
    ("fidelity", "criticality"):      ["Solar irradiance spectral fidelity (SORCE/TIM)", "CMB anisotropy residual"],
    ("fidelity", "dimensionality"):   ["Blockchain fork rate", "Protocol upgrade adoption speed"],
    ("fidelity", "stoichiometry"):    ["Drug trial success rate by phase", "Vaccine efficacy confidence interval"],
    ("topology", "dimensionality"):   ["Satellite orbital debris density (LeoLabs)", "Spacecraft conjunction alerts"],
    ("topology", "parity"):           ["Treaty/sanction network topology change", "UN vote polarity shift"],
    ("topology", "coupling"):         ["Banking network contagion index", "CDS spread topology"],
    ("winding", "dimensionality"):    ["Ionospheric TEC (GPS derived)", "Magnetic storm ring current Dst"],
    ("winding", "coupling"):          ["Carbon credit price × VIX", "ESG fund flow × commodity"],
    ("winding", "parity"):            ["Climate policy sentiment × election cycle", "Carbon tax vote probability"],
    ("dimensionality", "criticality"): ["Cosmic ray flux × solar minimum depth", "Dark matter detector event rate"],
    ("coupling", "parity"):           ["Cross-asset correlation entropy", "Risk-on/risk-off regime index"],
    ("coupling", "criticality"):      ["Systemic risk index (SRISK)", "Bank stress test score distribution"],
    ("parity", "criticality"):        ["Election outcome × AI risk forecasts", "Nuclear treaty status × geomagnetic"],
}


def missing_stream_proposals(coverage: Dict) -> List[Dict]:
    """
    For each missing SIC element, characterise and propose observables.
    Returns list sorted by cross-primitive interest (off-axis first).
    """
    elems_by_pq = {(p, q): Pi for p, q, Pi in sic_elements()}
    proposals = []

    for pq in coverage["missing_elements"]:
        p, q = pq
        char = _sic_element_character(p, q)
        cross = char.get("cross_pair")
        observables = []
        if cross:
            key = tuple(sorted(cross))
            observables = CROSS_PRIMITIVE_OBSERVABLES.get(key, [])
            if not observables:
                # Try reverse
                observables = CROSS_PRIMITIVE_OBSERVABLES.get((cross[1], cross[0]), [])

        proposals.append({
            "sic_element": [p, q],
            "character": char,
            "proposed_streams": observables,
            "synthesisable": not char["is_on_axis"],
        })

    # Off-axis (synthesisable) first, then on-axis gaps
    proposals.sort(key=lambda x: (not x["synthesisable"], x["sic_element"]))
    return proposals


def synthesisable_streams(coverage: Dict) -> List[Dict]:
    """
    Return only the missing elements that can be synthesised from existing
    stream data as nonlinear combinations (products, ratios, phase relations).
    These require no new data sources.
    """
    all_proposals = missing_stream_proposals(coverage)
    return [p for p in all_proposals if p["synthesisable"]]


def full_report() -> Dict:
    """Complete SIC-POVM coverage report."""
    cov = coverage_analysis()
    proposals = missing_stream_proposals(cov)
    synth = [p for p in proposals if p["synthesisable"]]
    new_source = [p for p in proposals if not p["synthesisable"]]

    return {
        "coverage": cov,
        "missing_proposals": proposals,
        "synthesisable_count": len(synth),
        "new_source_required_count": len(new_source),
        "top_synthesisable": synth[:20],
        "top_new_source": new_source[:20],
    }


if __name__ == "__main__":
    import json
    rpt = full_report()
    cov = rpt["coverage"]
    print(f"\nSIC-POVM Coverage: {cov['covered']}/{cov['total_sic_elements']} "
          f"({cov['coverage_fraction']:.1%})")
    print(f"Missing: {cov['missing']} elements")
    print(f"  Synthesisable from existing streams: {rpt['synthesisable_count']}")
    print(f"  Require new data sources:            {rpt['new_source_required_count']}")
    print(f"\nTop synthesisable missing elements:")
    for p in rpt["top_synthesisable"][:8]:
        cp = p["character"]["cross_pair"]
        obs = p["proposed_streams"][:1]
        print(f"  ({p['sic_element'][0]:2d},{p['sic_element'][1]:2d}) "
              f"{cp[0]}⊗{cp[1]}: {obs[0] if obs else '—'}")
