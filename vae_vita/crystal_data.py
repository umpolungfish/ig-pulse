"""
crystal_data.py — Crystal of Types dataset generator for VAE-Vita.

Generates all 3^3 × 4^5 × 5^4 = 17,280,000 structural type configurations
as ordinal-encoded feature vectors suitable for VAE training.

Each sample is a 12-dimensional vector where each coordinate ∈ [0, 1]
is the normalized ordinal value of that primitive.

Primitive order (canonical):
  D(3): Ð, Þ, Ř
  T(5): Φ, ƒ, Ç, Γ, ɢ
  P(4): ⊙, Ħ, Σ, Ω

Value counts per primitive:
  Ð(4), Þ(5), Ř(4), Φ(5), ƒ(3), Ç(5), Γ(3), ɢ(4), ⊙(5), Ħ(4), Σ(3), Ω(4)

Total: 4×5×4×5×3×5×3×4×5×4×3×4 = 17,280,000
"""

import numpy as np
from typing import Iterator, Tuple, Optional

# ── Canonical primitive order ─────────────────────────────────────────────────
PRIMS = ["Ð", "Þ", "Ř", "Φ", "ƒ", "Ç", "Γ", "ɢ", "⊙", "Ħ", "Σ", "Ω"]

# Value counts per primitive
VALUE_COUNTS = [4, 5, 4, 5, 3, 5, 3, 4, 5, 4, 3, 4]

# Value sets in Shavian glyphs (for reference / fidelity projection)
VALUES = {
    "Ð": ["𐑛", "𐑨", "𐑼", "𐑦"],
    "Þ": ["𐑡", "𐑰", "𐑥", "𐑶", "𐑸"],
    "Ř": ["𐑩", "𐑑", "𐑽", "𐑾"],
    "Φ": ["𐑗", "𐑿", "𐑬", "𐑯", "𐑹"],
    "ƒ": ["𐑱", "𐑞", "𐑐"],
    "Ç": ["𐑘", "𐑤", "𐑧", "𐑪", "𐑺"],
    "Γ": ["𐑚", "𐑔", "𐑲"],
    "ɢ": ["𐑝", "𐑜", "𐑠", "𐑵"],
    "⊙": ["𐑢", "⊙", "𐑮", "𐑻", "𐑣"],
    "Ħ": ["𐑓", "𐑒", "𐑖", "𐑫"],
    "Σ": ["𐑙", "𐑕", "𐑳"],
    "Ω": ["𐑷", "𐑴", "𐑭", "𐑟"],
}

# One-hot dimensions
ONEHOT_SIZES = VALUE_COUNTS  # [4, 5, 4, 5, 3, 5, 3, 4, 5, 4, 3, 4]
ONEHOT_DIM = sum(ONEHOT_SIZES)  # = 49

# Weights per primitive
WEIGHTS = [1.0, 1.0, 1.0, 1.2, 0.9, 1.0, 1.0, 1.0, 1.1, 0.8, 1.0, 0.7]


class CrystalDataset:
    """
    Iterable dataset over all 17,280,000 crystal configurations.
    
    By default returns ordinal vectors (12 normalized floats ∈ [0,1]).
    Also supports one-hot and Shavian glyph tuple modes.
    """

    def __init__(self, ordinal=True, onehot=False, shavian=False):
        self.total = 17_280_000
        self.ordinal = ordinal
        self.onehot = onehot
        self.shavian = shavian

    def __len__(self) -> int:
        return self.total

    def get_ordinal(self, idx: int) -> np.ndarray:
        """Return ordinal-encoded vector for crystal address idx."""
        vec = np.zeros(12, dtype=np.float32)
        remaining = idx
        for i, nv in enumerate(VALUE_COUNTS):
            vi = remaining % nv
            remaining //= nv
            vec[i] = vi / (nv - 1)
        return vec

    def get_onehot(self, idx: int) -> np.ndarray:
        """Return one-hot encoded vector for crystal address idx."""
        vec = np.zeros(ONEHOT_DIM, dtype=np.float32)
        remaining = idx
        offset = 0
        for i, nv in enumerate(VALUE_COUNTS):
            vi = remaining % nv
            remaining //= nv
            vec[offset + vi] = 1.0
            offset += nv
        return vec

    def get_shavian(self, idx: int) -> dict:
        """Return Shavian glyph tuple for crystal address idx."""
        tup = {}
        remaining = idx
        for prim, nv in zip(PRIMS, VALUE_COUNTS):
            vi = remaining % nv
            remaining //= nv
            tup[prim] = VALUES[prim][vi]
        return tup

    def __getitem__(self, idx: int):
        """Return requested encodings for idx-th configuration."""
        results = []
        if self.ordinal:
            results.append(self.get_ordinal(idx))
        if self.onehot:
            results.append(self.get_onehot(idx))
        if self.shavian:
            results.append(self.get_shavian(idx))
        return results[0] if len(results) == 1 else tuple(results)

    def __iter__(self) -> Iterator:
        for i in range(self.total):
            yield self[i]

    def sample_batch(self, batch_size: int, rng: Optional[np.random.Generator] = None) -> np.ndarray:
        """Sample a random batch of ordinal vectors."""
        if rng is None:
            rng = np.random.default_rng()
        indices = rng.integers(0, self.total, size=batch_size)
        return np.stack([self.get_ordinal(i) for i in indices])

    def batcher(self, batch_size: int, shuffle: bool = True, rng_seed: int = 42):
        """Infinite batcher yielding ordinal batches."""
        rng = np.random.default_rng(rng_seed)
        while True:
            indices = rng.integers(0, self.total, size=batch_size)
            batch = np.stack([self.get_ordinal(i) for i in indices])
            yield batch


def crystal_address(tup: dict) -> int:
    """Encode a Shavian-glyph tuple back to its crystal address."""
    addr = 0
    stride = 1
    for prim, nv in zip(reversed(PRIMS), reversed(VALUE_COUNTS)):
        val = tup.get(prim, VALUES[prim][0])
        idx = VALUES[prim].index(val)
        addr += idx * stride
        stride *= nv
    return addr


def decode_address(addr: int) -> dict:
    """Decode a crystal address to a Shavian-glyph tuple."""
    tup = {}
    remaining = addr
    for prim, nv in zip(PRIMS, VALUE_COUNTS):
        idx = remaining % nv
        remaining //= nv
        tup[prim] = VALUES[prim][idx]
    return tup
