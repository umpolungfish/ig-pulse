"""
domain_streams.py — Free cross-domain data stream aggregator for synfin.

15 streams, no API keys required:
  1. Fear & Greed Index    (alternative.me)                   → ⊙ Criticality, Φ Parity
  2. Mempool state         (mempool.space)                    → Ç Kinetics, Þ Topology, ɢ Coupling
  3. Global market         (coingecko.com)                    → Ð Dimensionality, Σ Stoichiometry, Γ Granularity
  4. BTC on-chain          (api.blockchain.info/stats)        → Ç Kinetics, ɢ Coupling, ⊙ Criticality
  5. Ocean tides           (tidesandcurrents.noaa.gov)        → Ω Winding
  6. Air quality           (air-quality-api.open-meteo.com)   → Ç Kinetics, Σ Stoichiometry
  7. Space weather / CME   (kauai.ccmc.gsfc.nasa.gov/DONKI)   → Φ Parity, Ħ Chirality, ⊙ Criticality
  8. Seismic energy        (earthquake.usgs.gov)              → Þ Topology, Ω Winding
  9. Geomagnetic Kp        (services.swpc.noaa.gov)           → Φ Parity, ⊙ Criticality
 10. HN crypto sentiment   (hn.algolia.com)                   → Ř Recognition, ɢ Coupling
 11. Solar wind / IMF Bz   (services.swpc.noaa.gov RTSW)      → Ħ Chirality, Ω Winding
 12. Lightning Network     (mempool.space/api/v1/lightning)   → ɢ Coupling, Ð Dimensionality
 13. Wikipedia attention   (wikimedia.org pageviews)          → Ř Recognition
 14. Open-Meteo weather    (api.open-meteo.com)               → ƒ Fidelity, Ω Winding
 15. Alt/BTC ratios        (coingecko.com)                    → Γ Granularity, ƒ Fidelity

Multiplier schedule:
  0 alerts → 1.00×
  1 alert  → 1.20×
  2 alerts → 1.35×
  ≥3 alerts → 1.50× (B-state dialetheic confluence)

"alert" = sum of alert levels across all primitives
(a primitive at level 2 contributes 2; level 1 contributes 1)
"""

from __future__ import annotations

import csv
import io
import json
import time
import urllib.request
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Optional


# ── StreamValue & DomainSignal ────────────────────────────────────────────────

@dataclass
class StreamValue:
    stream:    str
    primitive: str
    value:     float
    unit:      str
    alert:     int   # 0=nominal, 1=mild, 2=strong


@dataclass
class DomainSignal:
    """Aggregated cross-domain IG primitive alert signal."""

    criticality:    int = 0   # ⊙
    parity:         int = 0   # Φ
    kinetics:       int = 0   # Ç
    topology:       int = 0   # Þ
    coupling:       int = 0   # ɢ
    dimensionality: int = 0   # Ð
    stoichiometry:  int = 0   # Σ
    granularity:    int = 0   # Γ
    winding:        int = 0   # Ω
    chirality:      int = 0   # Ħ
    recognition:    int = 0   # Ř
    fidelity:       int = 0   # ƒ

    readings: list = field(default_factory=list)
    errors:   list = field(default_factory=list)
    fetched:  str  = ""

    _GLYPHS = {
        "criticality": "⊙", "parity": "Φ", "kinetics": "Ç",
        "topology": "Þ", "coupling": "ɢ", "dimensionality": "Ð",
        "stoichiometry": "Σ", "granularity": "Γ", "winding": "Ω",
        "chirality": "Ħ", "recognition": "Ř", "fidelity": "ƒ",
    }

    def _set(self, primitive: str, level: int, stream: str, value: float, unit: str) -> None:
        current = getattr(self, primitive, 0)
        setattr(self, primitive, max(current, level))
        self.readings.append(StreamValue(stream, primitive, value, unit, level))

    def _nom(self, primitive: str, stream: str, value: float, unit: str) -> None:
        """Record a nominal (no-alert) reading."""
        self.readings.append(StreamValue(stream, primitive, value, unit, 0))

    @property
    def total_alerts(self) -> int:
        return sum(
            getattr(self, p, 0)
            for p in self._GLYPHS
        )

    @property
    def is_b_state(self) -> bool:
        return self.total_alerts >= 3

    @property
    def multiplier(self) -> float:
        a = self.total_alerts
        if a == 0:   return 1.00
        elif a == 1: return 1.20
        elif a == 2: return 1.35
        else:        return 1.50

    def summary(self) -> str:
        active = [
            f"{self._GLYPHS[p]}:{getattr(self, p)}"
            for p in self._GLYPHS if getattr(self, p) > 0
        ]
        b = " [B-state]" if self.is_b_state else ""
        return (
            f"×{self.multiplier:.2f} | alerts={self.total_alerts}{b}"
            + (f" | {' '.join(active)}" if active else " | nominal")
        )

    def report(self) -> str:
        lines = [f"Domain streams @ {self.fetched}", f"  {self.summary()}"]
        for r in self.readings:
            if r.alert > 0:
                lines.append(
                    f"  [{r.stream}] {self._GLYPHS.get(r.primitive,'?')}"
                    f" level={r.alert}  {r.value:.3g} {r.unit}"
                )
        if self.errors:
            lines.append(f"  errors: {'; '.join(self.errors[:6])}")
        return "\n".join(lines)


# ── HTTP helpers ──────────────────────────────────────────────────────────────

_HEADERS = {"User-Agent": "imscribing-grammar/synfin"}


def _json(url: str, timeout: int = 10):
    try:
        req = urllib.request.Request(url, headers=_HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except Exception:
        return None


def _text(url: str, timeout: int = 12) -> Optional[str]:
    try:
        req = urllib.request.Request(url, headers=_HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode()
    except Exception:
        return None


def _today() -> str:
    return date.today().strftime("%Y-%m-%d")


def _ago(n: int) -> str:
    return (date.today() - timedelta(days=n)).strftime("%Y-%m-%d")


# ── Stream 1: Fear & Greed ────────────────────────────────────────────────────

def _stream_fear_greed(sig: DomainSignal) -> None:
    data = _json("https://api.alternative.me/fng/?limit=2")
    if not data or "data" not in data:
        sig.errors.append("fear_greed: no data"); return
    try:
        entries = data["data"]
        v = int(entries[0]["value"])
        if v < 20:
            sig._set("criticality", 2, "fear_greed", v, "index")
            sig._set("parity",      1, "fear_greed", v, "index")
        elif v < 30:
            sig._set("criticality", 1, "fear_greed", v, "index")
        elif v > 80:
            sig._set("criticality", 2, "fear_greed", v, "index")
            sig._set("parity",      1, "fear_greed", v, "index")
        elif v > 70:
            sig._set("criticality", 1, "fear_greed", v, "index")
        else:
            sig._nom("criticality", "fear_greed", v, "index")
        # Parity inversion: value crossed 50 since yesterday
        if len(entries) >= 2:
            prev = int(entries[1]["value"])
            if (prev < 50) != (v < 50):
                sig._set("parity", 2, "fear_greed_cross", v - prev, "delta")
    except Exception as e:
        sig.errors.append(f"fear_greed: {e}")


# ── Stream 2: Mempool state ───────────────────────────────────────────────────

def _stream_mempool(sig: DomainSignal) -> None:
    fees = _json("https://mempool.space/api/v1/fees/recommended")
    pool = _json("https://mempool.space/api/mempool")

    if fees:
        f = fees.get("fastestFee", 0)
        if f > 100:
            sig._set("kinetics", 2, "mempool_fee", f, "sat/vB")
        elif f > 40:
            sig._set("kinetics", 1, "mempool_fee", f, "sat/vB")
        elif f < 3:
            sig._set("coupling", 1, "mempool_low_fee", f, "sat/vB")
        else:
            sig._nom("kinetics", "mempool_fee", f, "sat/vB")
    else:
        sig.errors.append("mempool_fees: no data")

    if pool:
        c = pool.get("count", 0)
        if c > 150_000:
            sig._set("topology", 2, "mempool_count", c, "tx")
        elif c > 80_000:
            sig._set("topology", 1, "mempool_count", c, "tx")
        else:
            sig._nom("topology", "mempool_count", c, "tx")
    else:
        sig.errors.append("mempool_pool: no data")


# ── Stream 3: CoinGecko global ────────────────────────────────────────────────

def _stream_coingecko(sig: DomainSignal) -> None:
    data = _json("https://api.coingecko.com/api/v3/global")
    if not data or "data" not in data:
        sig.errors.append("coingecko: no data"); return
    try:
        d = data["data"]
        dom = d.get("market_cap_percentage", {}).get("bitcoin", 50.0)
        if dom > 62:
            sig._set("dimensionality", 2, "btc_dom", dom, "%")
        elif dom > 56:
            sig._set("dimensionality", 1, "btc_dom", dom, "%")
        elif dom < 38:
            sig._set("granularity", 2, "btc_dom_low", dom, "%")
        elif dom < 44:
            sig._set("granularity", 1, "btc_dom_low", dom, "%")
        else:
            sig._nom("dimensionality", "btc_dom", dom, "%")

        chg = d.get("market_cap_change_percentage_24h_usd", 0.0) or 0.0
        if abs(chg) > 8:
            sig._set("stoichiometry", 2, "mktcap_chg", chg, "%/24h")
        elif abs(chg) > 4:
            sig._set("stoichiometry", 1, "mktcap_chg", chg, "%/24h")
        else:
            sig._nom("stoichiometry", "mktcap_chg", chg, "%/24h")
    except Exception as e:
        sig.errors.append(f"coingecko: {e}")


# ── Stream 4: BTC on-chain (blockchain.info) ──────────────────────────────────

def _stream_onchain(sig: DomainSignal) -> None:
    data = _json("https://api.blockchain.info/stats")
    if not data:
        sig.errors.append("blockchain_info: no data"); return
    try:
        mbb = data.get("minutes_between_blocks", 10.0) or 10.0
        ntx = data.get("n_tx", 300_000) or 300_000
        hr  = data.get("hash_rate", 0) or 0

        # Block time deviation from 10-min target
        if mbb > 18:
            sig._set("kinetics", 2, "block_time", mbb, "min")
        elif mbb > 13:
            sig._set("kinetics", 1, "block_time", mbb, "min")
        elif mbb < 6:
            sig._set("criticality", 1, "block_time_fast", mbb, "min")
        else:
            sig._nom("kinetics", "block_time", mbb, "min")

        # Transaction throughput
        if ntx > 600_000:
            sig._set("coupling", 2, "n_tx", ntx, "tx/day")
        elif ntx > 400_000:
            sig._set("coupling", 1, "n_tx", ntx, "tx/day")
        elif ntx < 150_000:
            sig._set("coupling", 1, "n_tx_low", ntx, "tx/day")
        else:
            sig._nom("coupling", "n_tx", ntx, "tx/day")
    except Exception as e:
        sig.errors.append(f"blockchain_info: {e}")


# ── Stream 5: NOAA ocean tides ────────────────────────────────────────────────

def _stream_tides(sig: DomainSignal, station: str = "8518750") -> None:
    begin = (date.today() - timedelta(days=3)).strftime("%Y%m%d")
    end   = date.today().strftime("%Y%m%d")
    url = (
        "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
        f"?product=water_level&application=synfin_ig"
        f"&begin_date={begin}&end_date={end}"
        f"&datum=MLLW&station={station}&time_zone=GMT&units=metric&format=json"
    )
    data = _json(url, timeout=15)
    if not data or "data" not in data:
        sig.errors.append("noaa_tides: no data"); return
    try:
        levels = [float(d["v"]) for d in data["data"] if d.get("v")]
        if not levels:
            return
        rng = max(levels) - min(levels)
        if rng > 1.5:
            sig._set("winding", 2, "tide_range", rng, "m")
        elif rng > 1.0:
            sig._set("winding", 1, "tide_range", rng, "m")
        else:
            sig._nom("winding", "tide_range", rng, "m")
    except Exception as e:
        sig.errors.append(f"noaa_tides: {e}")


# ── Stream 6: Air quality ─────────────────────────────────────────────────────

def _stream_air_quality(sig: DomainSignal, lat: float = 40.71, lon: float = -74.01) -> None:
    url = (
        "https://air-quality-api.open-meteo.com/v1/air-quality"
        f"?latitude={lat}&longitude={lon}"
        "&hourly=pm2_5,ozone&forecast_days=1"
    )
    data = _json(url, timeout=12)
    if not data or "hourly" not in data:
        sig.errors.append("air_quality: no data"); return
    try:
        h = data["hourly"]

        pm = [v for v in h.get("pm2_5", []) if v is not None]
        if pm:
            v = pm[-1]
            if v > 55:
                sig._set("kinetics", 2, "pm2_5", v, "µg/m³")
            elif v > 25:
                sig._set("kinetics", 1, "pm2_5", v, "µg/m³")
            else:
                sig._nom("kinetics", "pm2_5", v, "µg/m³")

        o3 = [v for v in h.get("ozone", []) if v is not None]
        if o3:
            v = o3[-1]
            if v > 100:
                sig._set("stoichiometry", 2, "ozone", v, "µg/m³")
            elif v > 60:
                sig._set("stoichiometry", 1, "ozone", v, "µg/m³")
            else:
                sig._nom("stoichiometry", "ozone", v, "µg/m³")
    except Exception as e:
        sig.errors.append(f"air_quality: {e}")


# ── Stream 7: NASA DONKI space weather ───────────────────────────────────────

def _stream_donki(sig: DomainSignal) -> None:
    base  = "https://kauai.ccmc.gsfc.nasa.gov/DONKI/WS/get"
    start = _ago(7)
    end   = _today()

    # Solar flares
    flares = _json(f"{base}/FLR?startDate={start}&endDate={end}", timeout=12)
    if isinstance(flares, list):
        for f in flares:
            cls = f.get("classType", "")
            if cls.startswith("X"):
                try:
                    intensity = float(cls[1:]) if len(cls) > 1 else 1.0
                except ValueError:
                    intensity = 1.0
                level = 2 if intensity >= 3 else 1
                sig._set("parity", level, "solar_flare_X", intensity, "X-class")
                if intensity >= 3:
                    sig._set("criticality", 1, "solar_flare_X3", intensity, "X-class")
            elif cls.startswith("M"):
                sig._set("parity", 1, "solar_flare_M", 1.0, "M-class")
    else:
        sig.errors.append("donki_flares: no data")

    # CMEs
    cmes = _json(f"{base}/CME?startDate={start}&endDate={end}", timeout=12)
    if isinstance(cmes, list):
        for cme in cmes:
            for analysis in (cme.get("cmeAnalyses") or []):
                speed = analysis.get("speed") or 0
                if speed > 1500:
                    sig._set("chirality", 2, "cme_speed", speed, "km/s")
                elif speed > 800:
                    sig._set("chirality", 1, "cme_speed", speed, "km/s")
    else:
        sig.errors.append("donki_cme: no data")


# ── Stream 8: USGS seismic ────────────────────────────────────────────────────

def _stream_seismic(sig: DomainSignal) -> None:
    url = (
        "https://earthquake.usgs.gov/fdsnws/event/1/query"
        f"?format=geojson&starttime={_ago(7)}&endtime={_today()}"
        "&minmagnitude=4.5&orderby=time&limit=500"
    )
    data = _json(url, timeout=20)
    if not data or "features" not in data:
        sig.errors.append("usgs_seismic: no data"); return
    try:
        mags = [f["properties"].get("mag", 0) or 0 for f in data["features"]]
        if not mags:
            sig._nom("topology", "seismic_energy", 0.0, "index"); return

        energy = sum(10 ** (1.5 * m) for m in mags if m > 0)
        energy_index = min(1.0, energy / 10 ** (1.5 * 8.0))
        max_mag = max(mags)

        if energy_index > 0.7 or max_mag >= 7.5:
            sig._set("topology", 2, "seismic_energy", energy_index, "index")
            sig._set("winding",  1, "seismic_major",  max_mag,       "M")
        elif energy_index > 0.35 or max_mag >= 6.5:
            sig._set("topology", 1, "seismic_energy", energy_index, "index")
        else:
            sig._nom("topology", "seismic_energy", energy_index, "index")
    except Exception as e:
        sig.errors.append(f"usgs_seismic: {e}")


# ── Stream 9: NOAA Kp geomagnetic index ──────────────────────────────────────

def _stream_kp(sig: DomainSignal) -> None:
    data = _json("https://services.swpc.noaa.gov/json/planetary_k_index_1m.json")
    if not isinstance(data, list):
        sig.errors.append("noaa_kp: no data"); return
    try:
        vals = [float(d.get("kp_index", 0)) for d in data[-30:] if d.get("kp_index") is not None]
        if not vals:
            return
        kp_max = max(vals)
        kp_now = vals[-1]
        if kp_max >= 6:
            sig._set("parity",      2, "kp_index", kp_max, "Kp")
            sig._set("criticality", 1, "kp_index", kp_max, "Kp")
        elif kp_max >= 5:
            sig._set("parity",      1, "kp_index", kp_max, "Kp")
            sig._set("criticality", 1, "kp_index", kp_max, "Kp")
        elif kp_max >= 4:
            sig._set("parity", 1, "kp_index", kp_max, "Kp")
        else:
            sig._nom("parity", "kp_index", kp_now, "Kp")
    except Exception as e:
        sig.errors.append(f"noaa_kp: {e}")


# ── Stream 10: Hacker News crypto sentiment ───────────────────────────────────

def _stream_hn(sig: DomainSignal) -> None:
    since = int(time.time()) - 86400
    url = (
        "https://hn.algolia.com/api/v1/search"
        "?query=bitcoin+ethereum+crypto"
        "&tags=story"
        f"&numericFilters=created_at_i>{since}"
        "&hitsPerPage=100"
    )
    data = _json(url, timeout=10)
    if not data:
        sig.errors.append("hn_sentiment: no data"); return
    try:
        n = data.get("nbHits", 0)
        if n > 30:
            sig._set("recognition", 2, "hn_stories", n, "stories/24h")
        elif n > 10:
            sig._set("recognition", 1, "hn_stories", n, "stories/24h")
        elif n == 0:
            sig._set("coupling", 1, "hn_silence", 0, "stories/24h")
        else:
            sig._nom("recognition", "hn_stories", n, "stories/24h")
    except Exception as e:
        sig.errors.append(f"hn_sentiment: {e}")


# ── Stream 11: NOAA RTSW solar wind + IMF Bz ─────────────────────────────────

def _stream_solar_wind(sig: DomainSignal) -> None:
    mag  = _json("https://services.swpc.noaa.gov/json/rtsw/rtsw_mag_1m.json")
    wind = _json("https://services.swpc.noaa.gov/json/rtsw/rtsw_wind_1m.json")

    if isinstance(mag, list):
        try:
            vals = [float(d["bz_gsm"]) for d in mag[-30:]
                    if d.get("bz_gsm") is not None and d.get("overall_quality") == 0]
            if vals:
                bz_min = min(vals)
                bz_now = vals[-1]
                # Negative Bz = southward IMF = chiral coupling with Earth's field
                if bz_min < -20:
                    sig._set("chirality", 2, "imf_bz", bz_min, "nT")
                elif bz_min < -10:
                    sig._set("chirality", 1, "imf_bz", bz_min, "nT")
                else:
                    sig._nom("chirality", "imf_bz", bz_now, "nT")
        except Exception as e:
            sig.errors.append(f"noaa_imf_bz: {e}")
    else:
        sig.errors.append("noaa_imf_bz: no data")

    if isinstance(wind, list):
        try:
            speeds = [float(d["proton_speed"]) for d in wind[-30:]
                      if d.get("proton_speed") is not None]
            if speeds:
                spd_max = max(speeds)
                if spd_max > 700:
                    sig._set("winding", 2, "solar_wind_speed", spd_max, "km/s")
                elif spd_max > 500:
                    sig._set("winding", 1, "solar_wind_speed", spd_max, "km/s")
                else:
                    sig._nom("winding", "solar_wind_speed", spd_max, "km/s")
        except Exception as e:
            sig.errors.append(f"noaa_wind_speed: {e}")
    else:
        sig.errors.append("noaa_wind_speed: no data")


# ── Stream 12: Lightning Network stats ───────────────────────────────────────

def _stream_lightning(sig: DomainSignal) -> None:
    data = _json("https://mempool.space/api/v1/lightning/statistics/latest")
    if not data or "latest" not in data:
        sig.errors.append("lightning: no data"); return
    try:
        d = data["latest"]
        nodes    = d.get("node_count", 0) or 0
        channels = d.get("channel_count", 0) or 0
        capacity = (d.get("total_capacity", 0) or 0) / 1e8  # sats → BTC

        if nodes > 0:
            density = channels / nodes
            if density > 12:
                sig._set("coupling", 2, "ln_density", density, "ch/node")
            elif density > 8:
                sig._set("coupling", 1, "ln_density", density, "ch/node")
            else:
                sig._nom("coupling", "ln_density", density, "ch/node")

        if capacity > 6000:
            sig._set("dimensionality", 2, "ln_capacity", capacity, "BTC")
        elif capacity > 4000:
            sig._set("dimensionality", 1, "ln_capacity", capacity, "BTC")
        else:
            sig._nom("dimensionality", "ln_capacity", capacity, "BTC")
    except Exception as e:
        sig.errors.append(f"lightning: {e}")


# ── Stream 13: Wikipedia daily attention ─────────────────────────────────────

_WIKI_CRYPTO_TERMS = {
    "bitcoin", "ethereum", "cryptocurrency", "crypto", "blockchain",
    "solana", "ripple", "defi", "nft", "binance", "coinbase",
}
_WIKI_TECH_TERMS = {
    "artificial_intelligence", "openai", "chatgpt", "quantum", "spacex",
    "tesla", "nvidia", "semiconductor", "computer", "internet",
}


def _stream_wikipedia(sig: DomainSignal) -> None:
    yesterday = (date.today() - timedelta(days=1)).strftime("%Y/%m/%d")
    url = (
        f"https://wikimedia.org/api/rest_v1/metrics/pageviews/top/"
        f"en.wikipedia/all-access/{yesterday}"
    )
    data = _json(url, timeout=12)
    if not data or "items" not in data:
        sig.errors.append("wikipedia: no data"); return
    try:
        articles = data["items"][0]["articles"][:100]
        crypto_hits = sum(
            1 for a in articles
            if any(t in a["article"].lower() for t in _WIKI_CRYPTO_TERMS)
        )
        tech_total = sum(
            1 for a in articles
            if any(t in a["article"].lower() for t in _WIKI_TECH_TERMS | _WIKI_CRYPTO_TERMS)
        )
        # Crypto/tech topics in top-100 = recognition signal
        if crypto_hits >= 3:
            sig._set("recognition", 2, "wiki_crypto", crypto_hits, "top-100 articles")
        elif crypto_hits >= 1:
            sig._set("recognition", 1, "wiki_crypto", crypto_hits, "top-100 articles")
        elif tech_total >= 5:
            sig._set("recognition", 1, "wiki_tech", tech_total, "top-100 articles")
        else:
            sig._nom("recognition", "wiki_attention", tech_total, "top-100 articles")
    except Exception as e:
        sig.errors.append(f"wikipedia: {e}")


# ── Stream 14: Open-Meteo current weather ────────────────────────────────────

def _stream_weather(sig: DomainSignal, lat: float = 40.71, lon: float = -74.01) -> None:
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&current=wind_speed_10m,precipitation"
        "&daily=temperature_2m_max,temperature_2m_min"
        "&forecast_days=1"
    )
    data = _json(url, timeout=12)
    if not data:
        sig.errors.append("open_meteo: no data"); return
    try:
        daily = data.get("daily", {})
        tmax_list = daily.get("temperature_2m_max") or []
        tmin_list = daily.get("temperature_2m_min") or []
        if tmax_list and tmin_list and tmax_list[0] is not None and tmin_list[0] is not None:
            swing = tmax_list[0] - tmin_list[0]
            # Large daily swing = thermodynamic fidelity breakdown
            if swing > 22:
                sig._set("fidelity", 2, "temp_swing", swing, "°C")
            elif swing > 14:
                sig._set("fidelity", 1, "temp_swing", swing, "°C")
            else:
                sig._nom("fidelity", "temp_swing", swing, "°C")

        current = data.get("current", {})
        wind = current.get("wind_speed_10m") or 0
        if wind > 60:
            sig._set("winding", 2, "surface_wind", wind, "km/h")
        elif wind > 35:
            sig._set("winding", 1, "surface_wind", wind, "km/h")
        else:
            sig._nom("winding", "surface_wind", wind, "km/h")
    except Exception as e:
        sig.errors.append(f"open_meteo: {e}")


# ── Stream 15: CoinGecko alt/BTC ratios ──────────────────────────────────────

def _stream_coingecko_alts(sig: DomainSignal) -> None:
    data = _json(
        "https://api.coingecko.com/api/v3/simple/price"
        "?ids=ethereum,solana,polkadot,near-protocol"
        "&vs_currencies=btc&include_24hr_change=true",
        timeout=12,
    )
    if not data:
        sig.errors.append("coingecko_alts: no data"); return
    try:
        changes = [
            v.get("btc_24h_change", 0) or 0
            for v in data.values()
            if isinstance(v, dict) and v.get("btc_24h_change") is not None
        ]
        if not changes:
            return

        avg = sum(changes) / len(changes)
        # Alt outperformance vs BTC = granularity (fine-grained market structure)
        if avg > 5:
            sig._set("granularity", 2, "alt_outperform", avg, "%/24h vs BTC")
        elif avg > 2:
            sig._set("granularity", 1, "alt_outperform", avg, "%/24h vs BTC")
        elif avg < -5:
            sig._set("granularity", 2, "btc_dominance_surge", avg, "%/24h vs BTC")
        elif avg < -2:
            sig._set("granularity", 1, "btc_dominance_surge", avg, "%/24h vs BTC")
        else:
            sig._nom("granularity", "alt_btc_ratio", avg, "%/24h vs BTC")

        # Cross-alt divergence = fidelity (coherent vs fragmented alt market)
        if len(changes) >= 2:
            divergence = max(changes) - min(changes)
            if divergence > 10:
                sig._set("fidelity", 2, "alt_divergence", divergence, "%")
            elif divergence > 5:
                sig._set("fidelity", 1, "alt_divergence", divergence, "%")
            else:
                sig._nom("fidelity", "alt_divergence", divergence, "%")
    except Exception as e:
        sig.errors.append(f"coingecko_alts: {e}")


# ── Aggregator ────────────────────────────────────────────────────────────────

_ALL_STREAMS = [
    ("fear_greed",   _stream_fear_greed),
    ("mempool",      _stream_mempool),
    ("coingecko",    _stream_coingecko),
    ("onchain",      _stream_onchain),
    ("tides",        _stream_tides),
    ("air_quality",  _stream_air_quality),
    ("donki",        _stream_donki),
    ("seismic",      _stream_seismic),
    ("kp_index",        _stream_kp),
    ("hn_sentiment",    _stream_hn),
    ("solar_wind",      _stream_solar_wind),
    ("lightning",       _stream_lightning),
    ("wikipedia",       _stream_wikipedia),
    ("weather",         _stream_weather),
    ("coingecko_alts",  _stream_coingecko_alts),
]


class DomainStreamAggregator:
    """
    Fetches all 15 domain streams and returns a DomainSignal.
    Refreshes every `refresh_interval` seconds (default: 3600 = hourly).
    Network errors degrade gracefully — a failed stream contributes no alerts.
    """

    def __init__(self, refresh_interval: int = 3600):
        self._signal: DomainSignal = DomainSignal()
        self._last: Optional[datetime] = None
        self._interval = refresh_interval

    def refresh(self, force: bool = False) -> DomainSignal:
        if (not force
                and self._last is not None
                and (datetime.now() - self._last).total_seconds() < self._interval):
            return self._signal

        sig = DomainSignal(fetched=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        print(f"  [Streams] fetching {len(_ALL_STREAMS)} domain streams …")

        for name, fn in _ALL_STREAMS:
            try:
                fn(sig)
            except Exception as e:
                sig.errors.append(f"{name}: unexpected {e}")

        self._signal = sig
        self._last   = datetime.now()
        print(f"  [Streams] {sig.summary()}")
        if sig.errors:
            print(f"  [Streams] ! {'; '.join(sig.errors[:5])}")
        return sig

    @property
    def current(self) -> DomainSignal:
        return self._signal
