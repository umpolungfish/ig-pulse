"""
Imscribing Primitives for Financial Markets

The 12 primitives form the type signature of every financial asset.
Each primitive is an enum with ordinal values for lattice operations.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, IntEnum
from typing import NamedTuple
import hashlib


class Dimensionality(IntEnum):
    """
    Market structure dimensionality.
    
    Financial interpretation:
    - D_wedge: Single asset, simple price series
    - D_triangle: Triangular arbitrage, 3-asset relations
    - D_infty: Unbounded depth, continuous orderbook
    - D_holo: Full market microstructure, boundary encodes bulk
    """
    D_wedge = 0
    D_triangle = 1
    D_infty = 2
    D_holo = 3


class Topology(IntEnum):
    """
    Market connectivity topology.
    
    Financial interpretation:
    - T_network: DeFi, DEX, distributed liquidity
    - T_in: Isolated, single venue
    - T_bowtie: Market-maker centered
    - T_box: Siloed exchanges
    - T_holo: Fully connected, cross-venue arbitrage
    """
    T_network = 0
    T_in = 1
    T_bowtie = 2
    T_box = 3
    T_holo = 4


class RelationalMode(IntEnum):
    """
    Trading relational mode.
    
    Financial interpretation:
    - R_super: Perpetual futures, leveraged
    - R_cat: Spot trading, categorical
    - R_dagger: Derivatives, options/futures
    - R_lr: Long/short equity
    """
    R_super = 0
    R_cat = 1
    R_dagger = 2
    R_lr = 3


class Parity(IntEnum):
    """
    Long/short symmetry structure.
    
    Financial interpretation:
    - P_asym: Long-only bias
    - P_psi: Momentum-driven asymmetry
    - P_pm: Market-neutral capable
    - P_sym: Perfect symmetry
    - P_pm_sym: Exact Z₂ symmetry (Frobenius condition)
    """
    P_asym = 0
    P_psi = 1
    P_pm = 2
    P_sym = 3
    P_pm_sym = 4


class Fidelity(IntEnum):
    """
    Signal/prediction fidelity.
    
    Financial interpretation:
    - F_ell: Noisy, low signal-to-noise
    - F_eth: Technical analysis level
    - F_hbar: Fundamental/high conviction
    """
    F_ell = 0
    F_eth = 1
    F_hbar = 2


class KineticCharacter(IntEnum):
    """
    Volatility/velocity regime.
    
    Financial interpretation:
    - K_fast: High volatility, rapid price discovery
    - K_mod: Moderate volatility
    - K_slow: Low volatility, stable
    - K_trap: Trapped (halted, illiquid, circuit breaker)
    """
    K_fast = 0
    K_mod = 1
    K_slow = 2
    K_trap = 3


class Scope(IntEnum):
    """
    Market cap/granularity scope.
    
    Financial interpretation:
    - G_beth: Small cap, micro structure
    - G_gimel: Mid cap
    - G_aleph: Large cap, macro
    """
    G_beth = 0
    G_gimel = 1
    G_aleph = 2


class InteractionGrammar(IntEnum):
    """
    Correlation/interaction structure.
    
    Financial interpretation:
    - G_and: Tightly coupled (sector ETFs)
    - G_or: Uncoupled, independent
    - G_seq: Temporal/lead-lag relations
    - G_broad: Market-wide factor exposure
    """
    G_and = 0
    G_or = 1
    G_seq = 2
    G_broad = 3


class Criticality(IntEnum):
    """
    Market criticality state.
    
    Financial interpretation:
    - Phi_sub: Sub-critical, quiet
    - Phi_c: Critical, trending (absorbing state)
    - Phi_c_complex: Complex criticality
    - Phi_EP: Exceptional point (flash crash)
    - Phi_super: Super-critical, bubble
    """
    Phi_sub = 0
    Phi_c = 1
    Phi_c_complex = 2
    Phi_EP = 3
    Phi_super = 4


class Chirality(IntEnum):
    """
    Chirality.
    
    Financial interpretation:
    - H0: Intraday, no temporal structure
    - H1: Daily/weekly cycles
    - H2: Seasonal/quarterly
    - H_inf: Multi-year, secular trends
    """
    H0 = 0
    H1 = 1
    H2 = 2
    H_inf = 3


class Stoichiometry(IntEnum):
    """
    Pair/basket structure.
    
    Financial interpretation:
    - one_one: Single asset
    - n_n: Basket (ETF, index)
    - n_m: Multi-asset strategy
    """
    one_one = 0
    n_n = 1
    n_m = 2


class TopologicalProtection(IntEnum):
    """
    Regulatory/stability protection.
    
    Financial interpretation:
    - Omega_0: Unprotected, wild west
    - Omega_Z2: Regulated, some protection
    - Omega_Z: Sovereign backing, maximum protection
    """
    Omega_0 = 0
    Omega_Z2 = 1
    Omega_Z = 2


# Mapping from old ASCII enum names to phonetic glyph IDs
_GLYPH_IDS: dict[str, str] = {
    # Ð — Dimensionality
    "D_wedge": "Ð_ß", "D_triangle": "Ð_C", "D_infty": "Ð_;", "D_holo": "Ð_ω",
    # Þ — Topology
    "T_network": "Þ_6", "T_in": "Þ_K", "T_bowtie": "Þ_ò", "T_box": "Þ_¨", "T_holo": "Þ_O",
    # Ř — Relational Mode
    "R_super": "Ř_¯", "R_cat": "Ř_ý", "R_dagger": "Ř_Ť", "R_lr": "Ř_=",
    # Φ — Parity
    "P_asym": "Φ_ɐ", "P_psi": "Φ_υ", "P_pm": "Φ_F", "P_sym": "Φ_˙", "P_pm_sym": "Φ_}",
    # ƒ — Fidelity
    "F_ell": "ƒ_ì", "F_eth": "ƒ_ð", "F_hbar": "ƒ_ż",
    # Ç — Kinetics
    "K_fast": "Ç_-", "K_mod": "Ç_W", "K_slow": "Ç_@", "K_trap": "Ç_Ù",
    # Γ — Scope
    "G_beth": "Γ_β", "G_gimel": "Γ_γ", "G_aleph": "Γ_ʔ",
    # ɢ — Interaction Grammar
    "G_and": "ɢ_^", "G_or": "ɢ_˝", "G_seq": "ɢ_ˌ", "G_broad": "ɢ_Ş",
    # ⊙ — Criticality
    "Phi_sub": "⊙_ž", "Phi_c": "⊙_ÿ", "Phi_c_complex": "⊙_Æ", "Phi_EP": "⊙_3", "Phi_super": "⊙_Ţ",
    # Ħ — Chirality
    "H0": "Ħ_Ñ", "H1": "Ħ_£", "H2": "Ħ_A", "H_inf": "Ħ_!",
    # Σ — Stoichiometry
    "one_one": "Σ_S", "n_n": "Σ_ő", "n_m": "Σ_ï",
    # Ω — Topological Protection
    "Omega_0": "Ω_Å", "Omega_Z2": "Ω_2", "Omega_Z": "Ω_z",
}
_NAME_FROM_GLYPH: dict[str, str] = {v: k for k, v in _GLYPH_IDS.items()}

# Primitive weights for distance computation
PRIMITIVE_WEIGHTS: dict[str, float] = {
    "D": 1.0,
    "T": 1.0,
    "R": 1.0,
    "P": 1.0,
    "F": 1.0,
    "K": 1.0,
    "G": 1.0,
    "Gamma": 1.0,
    "Phi": 1.0,
    "H": 0.8,
    "S": 1.0,
    "Omega": 0.7,
}

# Maximum ordinal values for normalization
PRIMITIVE_MAXIMA: dict[str, int] = {
    "D": 3,
    "T": 4,
    "R": 3,
    "P": 4,
    "F": 2,
    "K": 3,
    "G": 2,
    "Gamma": 3,
    "Phi": 4,
    "H": 3,
    "S": 2,
    "Omega": 2,
}


@dataclass(frozen=True)
class Imscription:
    """
    A financial asset type — a 12-primitive tuple.
    
    The boundary encoding determines the bulk behavior.
    This IS NOT a labeling system; it IS a holographic type theory.
    """
    D: Dimensionality
    T: Topology
    R: RelationalMode
    P: Parity
    F: Fidelity
    K: KineticCharacter
    G: Scope
    Gamma: InteractionGrammar
    Phi: Criticality
    H: Chirality
    S: Stoichiometry
    Omega: TopologicalProtection
    
    # Cached hash for performance
    _hash: str = field(init=False, default="")
    
    def __post_init__(self) -> None:
        # Compute hash once at construction
        object.__setattr__(self, "_hash", self._compute_hash())
    
    def _compute_hash(self) -> str:
        """Compute a unique hash for this imscription."""
        sig = self.signature()
        return hashlib.sha256(sig.encode()).hexdigest()[:16]
    
    def __hash__(self) -> int:
        return hash(self._hash)
    
    def signature(self) -> str:
        """Return the canonical string signature using phonetic glyph IDs."""
        g = lambda name: _GLYPH_IDS.get(name, name)
        return (
            f"⟨{g(self.D.name)};{g(self.T.name)};{g(self.R.name)};{g(self.P.name)};"
            f"{g(self.F.name)};{g(self.K.name)};{g(self.G.name)};{g(self.Gamma.name)};"
            f"{g(self.Phi.name)};{g(self.H.name)};{g(self.S.name)};{g(self.Omega.name)}⟩"
        )
    
    def to_tuple(self) -> tuple[int, ...]:
        """Convert to tuple of ordinal values."""
        return (
            int(self.D), int(self.T), int(self.R), int(self.P),
            int(self.F), int(self.K), int(self.G), int(self.Gamma),
            int(self.Phi), int(self.H), int(self.S), int(self.Omega)
        )
    
    def __str__(self) -> str:
        return self.signature()
    
    def __repr__(self) -> str:
        return f"Imscription({self.signature()})"
    
    @classmethod
    def from_tuple(cls, values: tuple[int, ...]) -> Imscription:
        """Construct from tuple of ordinal values."""
        if len(values) != 12:
            raise ValueError(f"Expected 12 values, got {len(values)}")
        return cls(
            D=Dimensionality(values[0]),
            T=Topology(values[1]),
            R=RelationalMode(values[2]),
            P=Parity(values[3]),
            F=Fidelity(values[4]),
            K=KineticCharacter(values[5]),
            G=Scope(values[6]),
            Gamma=InteractionGrammar(values[7]),
            Phi=Criticality(values[8]),
            H=Chirality(values[9]),
            S=Stoichiometry(values[10]),
            Omega=TopologicalProtection(values[11]),
        )
    
    @classmethod
    def from_signature(cls, sig: str) -> Imscription:
        """Parse from signature string like ⟨D_wedge;T_network;...⟩."""
        # Remove angle brackets and split
        inner = sig.strip("⟨⟩")
        parts = inner.split(";")
        if len(parts) != 12:
            raise ValueError(f"Expected 12 primitives in signature, got {len(parts)}")
        
        # Map each part to its enum value
        enum_classes = [
            Dimensionality,
            Topology,
            RelationalMode,
            Parity,
            Fidelity,
            KineticCharacter,
            Scope,
            InteractionGrammar,
            Criticality,
            Chirality,
            Stoichiometry,
            TopologicalProtection,
        ]
        
        values = []
        for enum_class, part in zip(enum_classes, parts):
            name = _NAME_FROM_GLYPH.get(part, part)
            values.append(enum_class[name])
        
        return cls(*values)  # type: ignore


# Convenience constructors for common patterns
def minimal_imscription() -> Imscription:
    """Return the minimal imscription (all primitives at minimum)."""
    return Imscription(
        D=Dimensionality.D_wedge,
        T=Topology.T_network,
        R=RelationalMode.R_super,
        P=Parity.P_asym,
        F=Fidelity.F_ell,
        K=KineticCharacter.K_fast,
        G=Scope.G_beth,
        Gamma=InteractionGrammar.G_and,
        Phi=Criticality.Phi_sub,
        H=Chirality.H0,
        S=Stoichiometry.one_one,
        Omega=TopologicalProtection.Omega_0,
    )


def maximal_imscription() -> Imscription:
    """Return the maximal imscription (all primitives at maximum)."""
    return Imscription(
        D=Dimensionality.D_holo,
        T=Topology.T_holo,
        R=RelationalMode.R_lr,
        P=Parity.P_pm_sym,
        F=Fidelity.F_hbar,
        K=KineticCharacter.K_trap,
        G=Scope.G_aleph,
        Gamma=InteractionGrammar.G_broad,
        Phi=Criticality.Phi_super,
        H=Chirality.H_inf,
        S=Stoichiometry.n_m,
        Omega=TopologicalProtection.Omega_Z,
    )


def o_inf_imscription() -> Imscription:
    """
    Return an O_∞ imscription (ouroboric infinity).
    
    Requires Phi_c AND P_pm_sym — the special Frobenius condition.
    This IS the self-referential loop perfectly closed.
    """
    return Imscription(
        D=Dimensionality.D_holo,
        T=Topology.T_holo,
        R=RelationalMode.R_super,
        P=Parity.P_pm_sym,  # Required for O_∞
        F=Fidelity.F_hbar,
        K=KineticCharacter.K_mod,
        G=Scope.G_aleph,
        Gamma=InteractionGrammar.G_broad,
        Phi=Criticality.Phi_c,  # Required for O_∞
        H=Chirality.H_inf,
        S=Stoichiometry.n_n,
        Omega=TopologicalProtection.Omega_Z2,
    )
